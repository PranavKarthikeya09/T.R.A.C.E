"""Analysis orchestration service."""
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

from app.adapters.base import BaseInferenceAdapter
from app.adapters.exceptions import (
    ModelUnavailableException,
    ModelAuthenticationException,
    ModelRateLimitException,
    ModelNetworkException,
)
from app.adapters.model_adapter import get_default_model_adapter
from app.adapters.sightengine_adapter import SightengineAdapter
from app.provenance.provenance_adapter import ProvenanceAdapter
from app.composer.result_composer import ResultComposer
from app.forensics import (
    extract_image_metadata,
    generate_ela_map,
    METADATA_DISCLAIMER,
    ELA_DISCLAIMER,
    ELA_LIMITATIONS,
)
from app.schemas.analysis import (
    AnalysisResponse,
    MediaInfo,
    AIDetectionResult,
    ProvenanceResult,
    ProvenanceCheck,
    InvestigationScope,
    MetadataForensicsResult,
    SpatialAnomalyMap,
    ExternalAIDetectionResult,
    EvidenceItem,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    """Orchestrates image analysis across AI inference, provenance checks, and forensic signals."""

    def __init__(
        self,
        model_adapter: Optional[BaseInferenceAdapter] = None,
        provenance_adapter: Optional[ProvenanceAdapter] = None,
        sightengine_adapter: Optional[SightengineAdapter] = None,
    ):
        self.model_adapter = model_adapter or get_default_model_adapter()
        self.provenance_adapter = provenance_adapter or ProvenanceAdapter()
        self.sightengine_adapter = sightengine_adapter or SightengineAdapter()

    def _run_forensics(self, target_input: Any, selected_checks: set[str]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Safely execute metadata and ELA forensics without risking pipeline crashes."""
        metadata_raw = None
        try:
            metadata_raw = extract_image_metadata(target_input) if "metadata" in selected_checks else None
        except Exception as meta_err:
            logger.warning("Metadata extraction failed safely: %s", str(meta_err))
            metadata_raw = {
                "status": "failed",
                "has_exif": False,
                "disclaimer": METADATA_DISCLAIMER,
                "error": f"Metadata extraction failed: {str(meta_err)}",
                "noteworthy_markers": ["Metadata extraction encountered an unexpected error."]
            }

        ela_raw = None
        try:
            ela_raw = generate_ela_map(target_input) if "spatial_analysis" in selected_checks else None
        except Exception as ela_err:
            logger.warning("ELA anomaly map generation failed safely: %s", str(ela_err))
            ela_raw = {
                "status": "failed",
                "map_type": "error_level_analysis",
                "disclaimer": ELA_DISCLAIMER,
                "error": f"ELA generation failed: {str(ela_err)}",
                "noteworthy_markers": ["Spatial anomaly generator encountered an unexpected error."]
            }

        return metadata_raw, ela_raw

    def _compose_response(
        self,
        filename: str,
        detection_raw: Dict[str, Any],
        provenance_raw: Dict[str, Any],
        metadata_raw: Optional[Dict[str, Any]] = None,
        ela_raw: Optional[Dict[str, Any]] = None,
        sightengine_raw: Optional[Dict[str, Any]] = None,
        sightengine_deepfake_raw: Optional[Dict[str, Any]] = None,
        selected_checks: Optional[set[str]] = None,
        legacy_request: bool = False,
    ) -> AnalysisResponse:
        """Compose raw adapter, external detector, and forensic outputs into standard AnalysisResponse."""
        legacy_request = legacy_request or selected_checks is None
        selected_checks = selected_checks or {"visual_assessment", "ai_generation", "deepfake", "metadata", "spatial_analysis"}
        ai_selected = "visual_assessment" in selected_checks
        ai_result = AIDetectionResult(
            status=detection_raw.get("status", "completed" if ai_selected else "not_requested"),
            model_id=self.model_adapter.model_id,
            label=detection_raw.get("label", "not_assessed"),
            score=detection_raw.get("score") if ai_selected else None,
            score_semantics=detection_raw.get("score_semantics", "not_applicable_qualitative_heuristic"),
            interpretation=detection_raw.get("interpretation", "Visual assessment was not requested." if not ai_selected else "Visual inspection completed.")
        )

        checks = [
            ProvenanceCheck(name=c["name"], status=c["status"], details=c.get("details"))
            for c in provenance_raw.get("checks", [])
        ]
        provenance_result = ProvenanceResult(
            status=provenance_raw.get("status", "not_requested"),
            checks=checks
        )

        # Build optional metadata forensics record
        metadata_result: Optional[MetadataForensicsResult] = None
        if metadata_raw is not None:
            has_error = bool(metadata_raw.get("error"))
            metadata_result = MetadataForensicsResult(
                status="failed" if has_error else "completed",
                has_exif=metadata_raw.get("has_exif", False),
                camera_make=metadata_raw.get("camera_make"),
                camera_model=metadata_raw.get("camera_model"),
                lens_model=metadata_raw.get("lens_model"),
                capture_time=metadata_raw.get("capture_time"),
                software=metadata_raw.get("software"),
                orientation=metadata_raw.get("orientation"),
                orientation_description=metadata_raw.get("orientation_description"),
                identifiable_fields=metadata_raw.get("identifiable_fields", []),
                raw_tags=metadata_raw.get("raw_tags", {}),
                noteworthy_markers=metadata_raw.get("noteworthy_markers", []),
                disclaimer=metadata_raw.get("disclaimer", METADATA_DISCLAIMER),
                error=metadata_raw.get("error"),
            )

        # Build optional spatial anomaly map record
        spatial_map_result: Optional[SpatialAnomalyMap] = None
        if ela_raw is not None:
            has_error = bool(ela_raw.get("error"))
            in_w = ela_raw.get("width")
            in_h = ela_raw.get("height")
            vis_w = ela_raw.get("visualization_width", in_w)
            vis_h = ela_raw.get("visualization_height", in_h)
            spatial_map_result = SpatialAnomalyMap(
                status="failed" if has_error else "completed",
                map_type=ela_raw.get("map_type", "error_level_analysis"),
                input_width=in_w,
                input_height=in_h,
                visualization_width=vis_w,
                visualization_height=vis_h,
                is_downsampled=ela_raw.get("is_downsampled", False),
                jpeg_quality=ela_raw.get("jpeg_quality", 95),
                scale_factor=ela_raw.get("scale_factor", 1.0),
                normalization_method=ela_raw.get("normalization_method", "percentile_linear_p99"),
                residual_statistics=ela_raw.get("statistics", {}),
                heatmap_data_uri=ela_raw.get("heatmap_data_uri"),
                grayscale_data_uri=ela_raw.get("grayscale_data_uri"),
                limitations=ela_raw.get("limitations", ELA_LIMITATIONS),
                disclaimer=ela_raw.get("disclaimer", ELA_DISCLAIMER),
                noteworthy_markers=ela_raw.get("noteworthy_markers", []),
                error=ela_raw.get("error"),
            )

        # Build optional external AI detection record (Sightengine genai)
        external_ai_result: Optional[ExternalAIDetectionResult] = None
        if sightengine_raw is not None:
            external_ai_result = ExternalAIDetectionResult(
                provider=sightengine_raw.get("provider", "Sightengine"),
                task=sightengine_raw.get("task", "ai_generated_image_detection"),
                status=sightengine_raw.get("status", "unavailable"),
                label=sightengine_raw.get("label"),
                score=sightengine_raw.get("score"),
                score_semantics=sightengine_raw.get("score_semantics", "ai_generated_probability"),
                generator_scores=sightengine_raw.get("generator_scores"),
                interpretation=sightengine_raw.get("interpretation", ""),
                error=sightengine_raw.get("error"),
            )

        # Build optional external deepfake detection record (Sightengine deepfake)
        deepfake_result: Optional[ExternalAIDetectionResult] = None
        if sightengine_deepfake_raw is not None:
            deepfake_result = ExternalAIDetectionResult(
                provider=sightengine_deepfake_raw.get("provider", "Sightengine"),
                task=sightengine_deepfake_raw.get("task", "deepfake_face_manipulation_detection"),
                status=sightengine_deepfake_raw.get("status", "disabled"),
                label=sightengine_deepfake_raw.get("label"),
                score=sightengine_deepfake_raw.get("score"),
                score_semantics=sightengine_deepfake_raw.get("score_semantics", "deepfake_face_manipulation_probability"),
                generator_scores=None,
                interpretation=sightengine_deepfake_raw.get("interpretation", ""),
                error=sightengine_deepfake_raw.get("error"),
            )

        trace_alert = ResultComposer.compose_alert(
            ai_result.model_dump(),
            provenance_result.model_dump()
        )

        # Build structured evidence presentation items
        evidence_items: List[EvidenceItem] = ResultComposer.build_evidence_items(
            ai_detection=ai_result,
            provenance=provenance_result,
            metadata_forensics=metadata_result,
            spatial_anomaly_map=spatial_map_result,
            external_ai_detection=external_ai_result,
            deepfake_detection=deepfake_result,
        )

        # Merge standard limitations with model-specific and forensic limitations
        model_limitations: List[str] = detection_raw.get("limitations") or []
        forensic_limitations: List[str] = []
        if metadata_result is not None:
            forensic_limitations.append(
                "Container metadata and EXIF tags can be stripped by social platforms or modified post-capture; "
                "presence or absence of metadata does not establish authenticity or manipulation."
            )
        if spatial_map_result is not None:
            forensic_limitations.append(
                "Error Level Analysis (ELA) is an exploratory compression-difference visualization and does not "
                "provide a validated manipulation probability or tamper localization mask."
            )
        if external_ai_result is not None and external_ai_result.status == "completed":
            forensic_limitations.append(
                "Sightengine AI-generation detection measures statistical synthesis indicators; it does not evaluate "
                "traditional manual digital modifications (such as splicing, cloning, or object removal) and can produce "
                "false positives on heavily stylized digital art."
            )
        if deepfake_result is not None and deepfake_result.status == "completed":
            forensic_limitations.append(
                "Sightengine deepfake detection evaluates facial manipulation in photographic media; it does not evaluate "
                "whole-image generative synthesis, non-facial modifications, or background scene alterations."
            )

        combined_limitations = list(dict.fromkeys(
            ResultComposer.STANDARD_LIMITATIONS + model_limitations + forensic_limitations
        ))

        check_statuses = {
            "visual_assessment": ai_result.status,
            "ai_generation": external_ai_result.status if external_ai_result is not None else "not_requested",
            "deepfake": deepfake_result.status if deepfake_result is not None else "not_requested",
            "metadata": metadata_result.status if metadata_result is not None else "not_requested",
            "spatial_analysis": spatial_map_result.status if spatial_map_result is not None else "not_requested",
            "provenance": provenance_result.status,
        }
        selected_statuses = [check_statuses.get(check, "not_requested") for check in selected_checks]
        analysis_status = "completed" if legacy_request or (selected_statuses and all(value == "completed" for value in selected_statuses)) else "partial"

        return AnalysisResponse(
            analysis_id=f"an_{uuid.uuid4().hex[:12]}",
            status=analysis_status,
            media=MediaInfo(type="image", filename=filename),
            ai_detection=ai_result,
            provenance=provenance_result,
            investigation_scope=InvestigationScope(
                selected_checks=sorted(selected_checks),
                check_statuses=check_statuses,
            ),
            metadata_forensics=metadata_result,
            spatial_anomaly_map=spatial_map_result,
            external_ai_detection=external_ai_result,
            deepfake_detection=deepfake_result,
            evidence_items=evidence_items,
            trace_alert=trace_alert,
            limitations=combined_limitations,
            created_at=datetime.now(timezone.utc)
        )

    def analyze_image(
        self,
        filename: str,
        image: Image.Image,
        include_provenance: bool = False,
        image_bytes: Optional[bytes] = None,
        selected_checks: Optional[List[str]] = None,
    ) -> AnalysisResponse:
        """
        Synchronously orchestrate detection, verification, and forensic signal processing.
        Raises appropriate exceptions on model failure.
        """
        effective_checks = set(selected_checks) if selected_checks is not None else {
            "visual_assessment", "ai_generation", "deepfake", "metadata", "spatial_analysis"
        }
        if selected_checks is None and include_provenance:
            effective_checks.add("provenance")
        target_forensic_input = image_bytes if image_bytes is not None else image
        metadata_raw, ela_raw = self._run_forensics(target_forensic_input, effective_checks)

        effective_bytes = image_bytes
        if effective_bytes is None and image is not None:
            buf = io.BytesIO()
            image.save(buf, format=image.format or "JPEG")
            effective_bytes = buf.getvalue()

        sightengine_genai_raw = None
        sightengine_deepfake_raw = None
        detector_checks = effective_checks & {"ai_generation", "deepfake"}
        if effective_bytes and detector_checks:
            try:
                if selected_checks is None:
                    sightengine_genai_raw, sightengine_deepfake_raw = self.sightengine_adapter.detect_all(effective_bytes, filename)
                else:
                    sightengine_genai_raw, sightengine_deepfake_raw = self.sightengine_adapter.detect_all(effective_bytes, filename, detector_checks)
            except Exception as se_err:
                logger.warning("Sightengine synchronous detection failed safely: %s", str(se_err))
                sightengine_genai_raw = {
                    "provider": "Sightengine",
                    "task": "ai_generated_image_detection",
                    "status": "failed",
                    "label": None,
                    "score": None,
                    "score_semantics": "ai_generated_probability",
                    "generator_scores": None,
                    "interpretation": "External AI detection encountered an unexpected error.",
                    "error": str(se_err),
                }
                sightengine_deepfake_raw = {
                    "provider": "Sightengine",
                    "task": "deepfake_face_manipulation_detection",
                    "status": "failed",
                    "label": None,
                    "score": None,
                    "score_semantics": "deepfake_face_manipulation_probability",
                    "generator_scores": None,
                    "interpretation": "Deepfake detection encountered an unexpected error.",
                    "error": str(se_err),
                }

        if "ai_generation" not in effective_checks:
            sightengine_genai_raw = None
        if "deepfake" not in effective_checks:
            sightengine_deepfake_raw = None

        if "visual_assessment" in effective_checks:
            try:
                detection_raw = self.model_adapter.predict(image)
            except Exception as error:
                if selected_checks is None:
                    raise
                detection_raw = self._model_error_result(error)
        else:
            detection_raw = {}
        if "provenance" in effective_checks:
            try:
                provenance_raw = self.provenance_adapter.verify("")
            except Exception as error:
                provenance_raw = {"status": "failed", "checks": [{"name": "c2pa_manifest", "status": "failed", "details": "C2PA inspection failed during processing."}]}
        else:
            provenance_raw = {"status": "not_requested", "checks": []}
        return self._compose_response(
            filename,
            detection_raw,
            provenance_raw,
            metadata_raw,
            ela_raw,
            sightengine_genai_raw,
            sightengine_deepfake_raw,
            effective_checks,
            selected_checks is None,
        )

    async def analyze_image_async(
        self,
        filename: str,
        image: Image.Image,
        include_provenance: bool = False,
        image_bytes: Optional[bytes] = None,
        selected_checks: Optional[List[str]] = None,
    ) -> AnalysisResponse:
        """
        Asynchronously orchestrate detection, verification, and forensic signal processing.
        Uses non-blocking predict_async() and detect_all_async() to avoid stalling the event loop.
        """
        effective_checks = set(selected_checks) if selected_checks is not None else {
            "visual_assessment", "ai_generation", "deepfake", "metadata", "spatial_analysis"
        }
        if selected_checks is None and include_provenance:
            effective_checks.add("provenance")
        target_forensic_input = image_bytes if image_bytes is not None else image
        metadata_raw, ela_raw = self._run_forensics(target_forensic_input, effective_checks)

        effective_bytes = image_bytes
        if effective_bytes is None and image is not None:
            buf = io.BytesIO()
            image.save(buf, format=image.format or "JPEG")
            effective_bytes = buf.getvalue()

        sightengine_genai_raw = None
        sightengine_deepfake_raw = None
        detector_checks = effective_checks & {"ai_generation", "deepfake"}
        if effective_bytes and detector_checks:
            try:
                if selected_checks is None:
                    sightengine_genai_raw, sightengine_deepfake_raw = await self.sightengine_adapter.detect_all_async(effective_bytes, filename)
                else:
                    sightengine_genai_raw, sightengine_deepfake_raw = await self.sightengine_adapter.detect_all_async(effective_bytes, filename, detector_checks)
            except Exception as se_err:
                logger.warning("Sightengine async detection failed safely: %s", str(se_err))
                sightengine_genai_raw = {
                    "provider": "Sightengine",
                    "task": "ai_generated_image_detection",
                    "status": "failed",
                    "label": None,
                    "score": None,
                    "score_semantics": "ai_generated_probability",
                    "generator_scores": None,
                    "interpretation": "External AI detection encountered an unexpected error.",
                    "error": str(se_err),
                }
                sightengine_deepfake_raw = {
                    "provider": "Sightengine",
                    "task": "deepfake_face_manipulation_detection",
                    "status": "failed",
                    "label": None,
                    "score": None,
                    "score_semantics": "deepfake_face_manipulation_probability",
                    "generator_scores": None,
                    "interpretation": "Deepfake detection encountered an unexpected error.",
                    "error": str(se_err),
                }

        if "ai_generation" not in effective_checks:
            sightengine_genai_raw = None
        if "deepfake" not in effective_checks:
            sightengine_deepfake_raw = None

        if "visual_assessment" in effective_checks:
            try:
                detection_raw = await self.model_adapter.predict_async(image)
            except Exception as error:
                if selected_checks is None:
                    raise
                detection_raw = self._model_error_result(error)
        else:
            detection_raw = {}
        if "provenance" in effective_checks:
            try:
                provenance_raw = self.provenance_adapter.verify("")
            except Exception as error:
                provenance_raw = {"status": "failed", "checks": [{"name": "c2pa_manifest", "status": "failed", "details": "C2PA inspection failed during processing."}]}
        else:
            provenance_raw = {"status": "not_requested", "checks": []}
        return self._compose_response(
            filename,
            detection_raw,
            provenance_raw,
            metadata_raw,
            ela_raw,
            sightengine_genai_raw,
            sightengine_deepfake_raw,
            effective_checks,
            selected_checks is None,
        )

    @staticmethod
    def _model_error_result(error: Exception) -> Dict[str, Any]:
        status = "unavailable" if isinstance(error, (
            ModelUnavailableException,
            ModelAuthenticationException,
            ModelRateLimitException,
            ModelNetworkException,
        )) else "failed"
        return {
            "status": status,
            "label": "inconclusive",
            "score": None,
            "interpretation": (
                "Visual assessment could not run because the configured provider is unavailable or not configured."
                if status == "unavailable" else "Visual assessment failed during processing."
            ),
            "limitations": [],
        }
