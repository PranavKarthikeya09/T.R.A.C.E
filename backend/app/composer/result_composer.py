"""Result Composer, T.R.A.C.E. Alert Logic, and Structured Evidence Presentation."""
from typing import Dict, Any, List, Optional
from app.schemas.analysis import (
    TraceAlert,
    EvidenceItem,
    AIDetectionResult,
    ProvenanceResult,
    MetadataForensicsResult,
    SpatialAnomalyMap,
    ExternalAIDetectionResult,
)


class ResultComposer:
    """
    Composes normalized results, contextual T.R.A.C.E. alerts, and a structured
    evidence presentation model grounded in verified observations, calibrated interpretations,
    methodological limitations, and verification statuses.
    """

    STANDARD_LIMITATIONS: List[str] = [
        "Automated AI detection outputs are statistical indicators, not definitive proof of manipulation or authenticity.",
        "Absence of detected artifacts does not guarantee that the media is genuine.",
        "Absence of provenance credentials does not imply manipulation, nor do valid credentials guarantee truthful real-world content."
    ]

    FORENSIC_LIMITATIONS: List[str] = [
        "Error Level Analysis is an exploratory heuristic visualization of compression differences and does not provide a validated manipulation probability or tamper localization mask.",
        "Container metadata and EXIF tags can be stripped by social platforms or modified post-capture; presence or absence of metadata does not establish authenticity or manipulation."
    ]

    @staticmethod
    def compose_alert(ai_result: Dict[str, Any], provenance_result: Dict[str, Any]) -> TraceAlert:
        """
        Derive alert level and message from completed checks.
        Never declares certainty.
        """
        ai_status = ai_result.get("status")
        prov_status = (provenance_result.get("status") or "").lower()

        if ai_status != "completed":
            if ai_status == "not_requested":
                return TraceAlert(
                    level="inconclusive",
                    message="Visual assessment was not included in this investigation scope. Review the selected checks before drawing conclusions."
                )
            return TraceAlert(
                level="inconclusive",
                message="Automated detection could not be completed. Independent verification recommended."
            )

        # Check for cryptographic tampering or failure in provenance credentials
        if prov_status in ("invalid", "tampered"):
            return TraceAlert(
                level="caution",
                message="Caution: Provenance credentials failed verification or indicate tampering. Media integrity cannot be trusted."
            )

        label = (ai_result.get("label") or "").lower()

        # Handle 'potential_manipulation', 'manipulated', 'synthetic', 'fake', 'deepfake'
        if "manipulat" in label or "fake" in label or "synthetic" in label or "deepfake" in label:
            return TraceAlert(
                level="caution",
                message="Caution: Potential media manipulation detected by automated analysis. Verify original source before trusting or sharing."
            )
        elif "authentic" in label or "real" in label:
            return TraceAlert(
                level="info",
                message="No strong signs of manipulation detected by the available checks. Authenticity cannot be definitively established."
            )
        else:
            return TraceAlert(
                level="inconclusive",
                message="Inconclusive: Automated analysis returned ambiguous indicators. Further verification recommended."
            )

    @staticmethod
    def build_evidence_items(
        ai_detection: AIDetectionResult,
        provenance: ProvenanceResult,
        metadata_forensics: Optional[MetadataForensicsResult] = None,
        spatial_anomaly_map: Optional[SpatialAnomalyMap] = None,
        external_ai_detection: Optional[ExternalAIDetectionResult] = None,
        deepfake_detection: Optional[ExternalAIDetectionResult] = None,
    ) -> List[EvidenceItem]:
        """
        Build a structured evidence presentation layer from actual analysis exhibits.
        Each item clearly distinguishes:
        - OBSERVATION: What was directly measured or returned.
        - INTERPRETATION: What the observation suggests, with calibrated, non-definitive language.
        - LIMITATION: What the observation cannot establish.
        - STATUS: Execution status (completed, not_configured, disabled, failed, unavailable).
        """
        items: List[EvidenceItem] = []

        # 1. General visual assessment (Vision Backbone)
        if ai_detection.status == "completed":
            vis_obs = f"Vision model assigned categorical heuristic classification '{ai_detection.label}'"
            if ai_detection.score is not None:
                vis_obs += f" with reported score {ai_detection.score:.4f}"
            vis_obs += "."
            vis_interp = ai_detection.interpretation
        elif ai_detection.status == "not_requested":
            vis_obs = "Visual assessment was not requested for this investigation."
            vis_interp = "No visual model output is available for this scope."
        else:
            vis_obs = "Vision model assessment could not be completed."
            vis_interp = "Qualitative visual inspection is unavailable."

        items.append(
            EvidenceItem(
                id="ev_visual_assessment",
                category="visual_assessment",
                source=f"Vision Model ({ai_detection.model_id})",
                observation=vis_obs,
                interpretation=vis_interp,
                limitation=(
                    "Vision backbones evaluate qualitative rendering coherence and semantic consistency; "
                    "they represent automated statistical impressions and do not constitute certified mathematical or forensic proof."
                ),
                status=ai_detection.status,
                details={
                    "model_id": ai_detection.model_id,
                    "label": ai_detection.label,
                    "score": ai_detection.score,
                    "score_semantics": ai_detection.score_semantics,
                }
            )
        )

        # 2. AI-Generation Detection (Sightengine genai)
        if external_ai_detection is not None:
            ext_status = external_ai_detection.status
            if ext_status == "completed" and external_ai_detection.score is not None:
                gen_obs = f"Sightengine reported an AI-generation score of {external_ai_detection.score:.4f} ({external_ai_detection.score * 100:.1f}%)."
                if external_ai_detection.generator_scores:
                    high_gens = [
                        f"{name}: {val:.2f}"
                        for name, val in sorted(external_ai_detection.generator_scores.items(), key=lambda x: x[1], reverse=True)
                        if val >= 0.20
                    ]
                    if high_gens:
                        gen_obs += f" Detector-indicated generator correlations: {', '.join(high_gens[:3])}."
                gen_interp = external_ai_detection.interpretation
            elif ext_status in ("not_configured", "disabled"):
                gen_obs = f"Sightengine AI-generation detection was {ext_status.replace('_', ' ')}."
                gen_interp = external_ai_detection.interpretation
            elif ext_status == "unavailable":
                gen_obs = "Sightengine AI-generation detection was unavailable."
                gen_interp = external_ai_detection.interpretation
            else:
                gen_obs = f"Sightengine AI-generation detection failed: {external_ai_detection.error or 'Provider error'}."
                gen_interp = external_ai_detection.interpretation

            items.append(
                EvidenceItem(
                    id="ev_ai_generation",
                    category="ai_generation",
                    source="Sightengine genai",
                    observation=gen_obs,
                    interpretation=gen_interp,
                    limitation=(
                        "This detector score is not proof of the image's origin and does not independently establish whether the depicted event occurred. "
                        "Generator-specific scores reflect detector pattern similarity and do not prove which software or model created the image."
                    ),
                    status=ext_status,
                    details={
                        "score": external_ai_detection.score,
                        "label": external_ai_detection.label,
                        "generator_scores": external_ai_detection.generator_scores,
                        "error": external_ai_detection.error,
                    }
                )
            )

        # 3. Deepfake Detection (Sightengine deepfake)
        if deepfake_detection is not None:
            df_status = deepfake_detection.status
            if df_status == "completed" and deepfake_detection.score is not None:
                df_obs = f"Sightengine reported a deepfake face manipulation score of {deepfake_detection.score:.4f} ({deepfake_detection.score * 100:.1f}%)."
                df_interp = deepfake_detection.interpretation
            elif df_status in ("disabled", "not_configured"):
                df_obs = f"Sightengine deepfake detection is {df_status.replace('_', ' ')}."
                df_interp = deepfake_detection.interpretation
            elif df_status == "unavailable":
                df_obs = "Sightengine deepfake detection was unavailable."
                df_interp = deepfake_detection.interpretation
            else:
                df_obs = f"Sightengine deepfake detection failed: {deepfake_detection.error or 'Provider error'}."
                df_interp = deepfake_detection.interpretation

            items.append(
                EvidenceItem(
                    id="ev_deepfake",
                    category="deepfake",
                    source="Sightengine deepfake",
                    observation=df_obs,
                    interpretation=df_interp,
                    limitation=(
                        "Deepfake detection evaluates prominent faces for signs of facial swapping or replacement in photographic media. "
                        "It does not evaluate whole-image generative synthesis, non-facial manipulations, or background scene integrity."
                    ),
                    status=df_status,
                    details={
                        "score": deepfake_detection.score,
                        "label": deepfake_detection.label,
                        "error": deepfake_detection.error,
                    }
                )
            )

        # 4. Container & EXIF Metadata
        if metadata_forensics is not None:
            meta_status = metadata_forensics.status
            if meta_status == "completed":
                if metadata_forensics.has_exif:
                    cam_parts = [metadata_forensics.camera_make, metadata_forensics.camera_model]
                    cam_str = " ".join([p for p in cam_parts if p])
                    meta_obs = f"Container metadata headers detected ({len(metadata_forensics.identifiable_fields)} tags discovered)."
                    if cam_str:
                        meta_obs += f" Hardware device: {cam_str}."
                    if metadata_forensics.software:
                        meta_obs += f" Software signature: {metadata_forensics.software}."
                    if metadata_forensics.capture_time:
                        meta_obs += f" Capture time: {metadata_forensics.capture_time}."
                    meta_interp = "Embedded container headers provide capture or processing context, subject to post-capture modification."
                else:
                    meta_obs = "No EXIF or camera container headers were detected in the file."
                    meta_interp = "Metadata headers were absent or stripped prior to upload."
            else:
                meta_obs = f"Metadata extraction {meta_status}: {metadata_forensics.error or 'no result available'}."
                meta_interp = "Container headers could not be examined."

            items.append(
                EvidenceItem(
                    id="ev_metadata",
                    category="metadata",
                    source="Container & EXIF Parser",
                    observation=meta_obs,
                    interpretation=meta_interp,
                    limitation=(
                        "Container headers and EXIF tags can be stripped by social platforms or modified post-capture; "
                        "presence or absence of metadata does not establish authenticity or manipulation."
                    ),
                    status=meta_status,
                    details={
                        "has_exif": metadata_forensics.has_exif,
                        "camera_make": metadata_forensics.camera_make,
                        "camera_model": metadata_forensics.camera_model,
                        "software": metadata_forensics.software,
                        "identifiable_fields_count": len(metadata_forensics.identifiable_fields),
                    }
                )
            )

        # 5. Compression Analysis (Error Level Analysis)
        if spatial_anomaly_map is not None:
            ela_status = spatial_anomaly_map.status
            if ela_status == "completed":
                stats = spatial_anomaly_map.residual_statistics or {}
                mean_res = stats.get("mean_residual")
                max_res = stats.get("max_residual")
                rms_res = stats.get("rms_residual")
                ela_obs = "Error Level Analysis recompression generated a spatial residual map."
                if mean_res is not None and max_res is not None:
                    ela_obs += f" Residual statistics: mean={mean_res:.2f}, max={max_res:.2f}"
                    if rms_res is not None:
                        ela_obs += f", RMS={rms_res:.2f}"
                    ela_obs += "."
                ela_interp = "Spatial residual patterns highlight compression rate differences across image regions which may warrant contextual review."
            else:
                ela_obs = f"Error Level Analysis {ela_status}: {spatial_anomaly_map.error or 'no result available'}."
                ela_interp = "Compression anomaly visualization could not be generated."

            items.append(
                EvidenceItem(
                    id="ev_compression_analysis",
                    category="compression_analysis",
                    source="Error Level Analysis (ELA)",
                    observation=ela_obs,
                    interpretation=ela_interp,
                    limitation=(
                        "Compression differences can arise from ordinary image processing, varying textures, or multiple saves, "
                        "and are not proof of manipulation. ELA does not provide a validated manipulation probability or tamper localization mask."
                    ),
                    status=ela_status,
                    details=spatial_anomaly_map.residual_statistics
                )
            )

        # 6. Provenance (C2PA)
        prov_status = provenance.status.lower()
        if prov_status == "not_requested":
            prov_obs = "Cryptographic origin verification was not requested for this inspection session."
            prov_interp = "Provenance credentials and C2PA manifests were not evaluated."
        elif prov_status in ("verified", "valid"):
            prov_obs = "Valid cryptographic provenance manifest was detected and verified."
            prov_interp = "The media container contains an intact cryptographic assertion chain from an authorized signer."
        elif prov_status in ("invalid", "tampered"):
            prov_obs = "Cryptographic provenance manifest was detected but failed signature or digest verification."
            prov_interp = "The container assertion has been modified or corrupted relative to the signed manifest."
        elif prov_status == "disabled":
            prov_obs = "C2PA inspection was requested but is disabled by server configuration."
            prov_interp = "No manifest presence or signature conclusion is available."
        elif prov_status == "unavailable":
            prov_obs = "C2PA inspection was requested, but verification tooling is unavailable."
            prov_interp = "This application does not currently parse C2PA manifests or verify their signatures."
        elif prov_status == "failed":
            prov_obs = "The requested C2PA inspection failed during execution."
            prov_interp = "No manifest presence or signature conclusion is available."
        else:
            prov_obs = "No supported provenance credentials or C2PA manifests were detected."
            prov_interp = "The image's provenance could not be established through this mechanism."

        items.append(
            EvidenceItem(
                id="ev_provenance",
                category="provenance",
                source="C2PA Provenance Verifier",
                observation=prov_obs,
                interpretation=prov_interp,
                limitation=(
                    "Missing credentials do not establish that the image is fake or manipulated, as most capture hardware does not support C2PA signing. "
                    "Valid credentials confirm manifest integrity from the signing device; they do not guarantee that the real-world scene was truthful."
                ),
                status=provenance.status,
                details={"checks_performed": len(provenance.checks)}
            )
        )

        return items
