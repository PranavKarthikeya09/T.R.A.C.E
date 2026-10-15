"""Analysis orchestration service."""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from PIL import Image

from app.adapters.base import BaseInferenceAdapter
from app.adapters.model_adapter import get_default_model_adapter
from app.provenance.provenance_adapter import ProvenanceAdapter
from app.composer.result_composer import ResultComposer
from app.schemas.analysis import (
    AnalysisResponse,
    MediaInfo,
    AIDetectionResult,
    ProvenanceResult,
    ProvenanceCheck
)


class AnalysisService:
    """Orchestrates image analysis across AI inference and provenance checks."""

    def __init__(
        self,
        model_adapter: Optional[BaseInferenceAdapter] = None,
        provenance_adapter: Optional[ProvenanceAdapter] = None
    ):
        self.model_adapter = model_adapter or get_default_model_adapter()
        self.provenance_adapter = provenance_adapter or ProvenanceAdapter()

    def _compose_response(
        self,
        filename: str,
        detection_raw: Dict[str, Any],
        provenance_raw: Dict[str, Any]
    ) -> AnalysisResponse:
        """Compose raw adapter outputs into standard AnalysisResponse."""
        ai_result = AIDetectionResult(
            status="completed",
            model_id=self.model_adapter.model_id,
            label=detection_raw.get("label", "inconclusive"),
            score=detection_raw.get("score"),
            score_semantics=detection_raw.get("score_semantics", "not_applicable_qualitative_heuristic"),
            interpretation=detection_raw.get("interpretation", "Visual inspection completed.")
        )

        checks = [
            ProvenanceCheck(name=c["name"], status=c["status"], details=c.get("details"))
            for c in provenance_raw.get("checks", [])
        ]
        provenance_result = ProvenanceResult(
            status=provenance_raw.get("status", "not_requested"),
            checks=checks
        )

        trace_alert = ResultComposer.compose_alert(
            ai_result.model_dump(),
            provenance_result.model_dump()
        )

        # Merge standard limitations with any model-specific limitations
        model_limitations: List[str] = detection_raw.get("limitations") or []
        combined_limitations = list(dict.fromkeys(ResultComposer.STANDARD_LIMITATIONS + model_limitations))

        return AnalysisResponse(
            analysis_id=f"an_{uuid.uuid4().hex[:12]}",
            status="completed",
            media=MediaInfo(type="image", filename=filename),
            ai_detection=ai_result,
            provenance=provenance_result,
            trace_alert=trace_alert,
            limitations=combined_limitations,
            created_at=datetime.now(timezone.utc)
        )

    def analyze_image(
        self,
        filename: str,
        image: Image.Image,
        include_provenance: bool = False
    ) -> AnalysisResponse:
        """
        Synchronously orchestrate detection and verification.
        Raises appropriate exceptions on model failure.
        """
        detection_raw = self.model_adapter.predict(image)
        provenance_raw = self.provenance_adapter.verify("") if include_provenance else {"status": "not_requested", "checks": []}
        return self._compose_response(filename, detection_raw, provenance_raw)

    async def analyze_image_async(
        self,
        filename: str,
        image: Image.Image,
        include_provenance: bool = False
    ) -> AnalysisResponse:
        """
        Asynchronously orchestrate detection and verification.
        Uses non-blocking predict_async() to avoid stalling event loop.
        """
        detection_raw = await self.model_adapter.predict_async(image)
        provenance_raw = self.provenance_adapter.verify("") if include_provenance else {"status": "not_requested", "checks": []}
        return self._compose_response(filename, detection_raw, provenance_raw)
