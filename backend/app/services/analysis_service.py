"""Analysis orchestration service."""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from PIL import Image

from app.adapters.model_adapter import UninitializedModelAdapter
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
        model_adapter: Optional[UninitializedModelAdapter] = None,
        provenance_adapter: Optional[ProvenanceAdapter] = None
    ):
        self.model_adapter = model_adapter or UninitializedModelAdapter()
        self.provenance_adapter = provenance_adapter or ProvenanceAdapter()

    def analyze_image(
        self,
        filename: str,
        image: Image.Image,
        include_provenance: bool = False
    ) -> AnalysisResponse:
        """
        Orchestrate detection and verification.
        Raises RuntimeError/Exception if model inference cannot run.
        """
        # Execute real inference (will raise until model is configured in Phase 2)
        detection_raw = self.model_adapter.predict(image)

        ai_result = AIDetectionResult(
            status="completed",
            model_id=self.model_adapter.model_id,
            label=detection_raw.get("label", "unknown"),
            score=detection_raw.get("score"),
            score_semantics=detection_raw.get("score_semantics", "documented-by-model"),
            interpretation=detection_raw.get("interpretation", "Model inference completed.")
        )

        # Provenance check
        provenance_raw = self.provenance_adapter.verify("")
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

        return AnalysisResponse(
            analysis_id=f"an_{uuid.uuid4().hex[:12]}",
            status="completed",
            media=MediaInfo(type="image", filename=filename),
            ai_detection=ai_result,
            provenance=provenance_result,
            trace_alert=trace_alert,
            limitations=ResultComposer.STANDARD_LIMITATIONS,
            created_at=datetime.now(timezone.utc)
        )
