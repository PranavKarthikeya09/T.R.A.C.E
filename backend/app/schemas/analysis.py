"""Analysis request and response schemas according to API_SPEC.md."""
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class MediaInfo(BaseModel):
    """Media information."""
    type: str = Field(default="image", description="Media type")
    filename: str = Field(..., description="Uploaded file name")


class AIDetectionResult(BaseModel):
    """AI manipulation detection findings."""
    status: str = Field(..., description="Detection status: completed, failed, unavailable")
    model_id: str = Field(..., description="Identifier of the model used")
    label: str = Field(..., description="Detection label from model output")
    score: Optional[float] = Field(default=None, description="Score if provided by model, else null")
    score_semantics: str = Field(default="documented-by-model", description="Semantics of the score")
    interpretation: str = Field(..., description="Human-readable interpretation without claiming certainty")


class ProvenanceCheck(BaseModel):
    """Individual provenance check detail."""
    name: str = Field(..., description="Name of check")
    status: str = Field(..., description="Status of check")
    details: Optional[str] = Field(default=None, description="Details or findings")


class ProvenanceResult(BaseModel):
    """Provenance and metadata verification findings."""
    status: str = Field(
        default="not_requested",
        description="Provenance status: not_requested, verified, invalid, not_found, inconclusive, unavailable"
    )
    checks: List[ProvenanceCheck] = Field(default_factory=list, description="List of performed checks")


class TraceAlert(BaseModel):
    """T.R.A.C.E. caution alert."""
    level: str = Field(..., description="Alert level: info, caution, inconclusive")
    message: str = Field(..., description="Actionable alert message grounded in evidence")


class AnalysisResponse(BaseModel):
    """Complete image analysis response matching API_SPEC.md Section 4."""
    analysis_id: str = Field(..., description="Opaque analysis identifier")
    status: str = Field(..., description="Analysis status: completed, failed")
    media: MediaInfo
    ai_detection: AIDetectionResult
    provenance: ProvenanceResult
    trace_alert: TraceAlert
    limitations: List[str] = Field(..., description="Explicit limitations and caveats")
    created_at: datetime = Field(..., description="ISO 8601 timestamp in UTC")
