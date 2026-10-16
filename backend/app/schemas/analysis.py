"""Analysis request and response schemas according to API_SPEC.md."""
from typing import List, Optional, Dict, Any
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
    """Provenance and cryptographic metadata verification findings."""
    status: str = Field(
        default="not_requested",
        description="Provenance status: not_requested, verified, invalid, not_found, inconclusive, unavailable"
    )
    checks: List[ProvenanceCheck] = Field(default_factory=list, description="List of performed checks")


class InvestigationScope(BaseModel):
    """Requested checks and the outcome recorded for each supported check."""
    selected_checks: List[str] = Field(default_factory=list)
    check_statuses: Dict[str, str] = Field(default_factory=dict)


class MetadataForensicsResult(BaseModel):
    """Container and EXIF metadata forensic inspection findings."""
    status: str = Field(default="completed", description="Extraction status: completed, failed, unavailable")
    has_exif: bool = Field(default=False, description="Whether EXIF metadata headers were present")
    camera_make: Optional[str] = Field(default=None, description="Camera manufacturer make tag")
    camera_model: Optional[str] = Field(default=None, description="Camera hardware model tag")
    lens_model: Optional[str] = Field(default=None, description="Camera lens model tag")
    capture_time: Optional[str] = Field(default=None, description="Original capture timestamp")
    software: Optional[str] = Field(default=None, description="Editing or processing software tag")
    orientation: Optional[int] = Field(default=None, description="EXIF orientation integer code")
    orientation_description: Optional[str] = Field(default=None, description="Human-readable orientation description")
    identifiable_fields: List[str] = Field(default_factory=list, description="Identifiable metadata keys discovered")
    raw_tags: Dict[str, Any] = Field(default_factory=dict, description="Raw extracted container tags")
    noteworthy_markers: List[str] = Field(default_factory=list, description="Contextual forensic markers or software indicators")
    disclaimer: str = Field(..., description="Methodological caveats regarding metadata manipulability")
    error: Optional[str] = Field(default=None, description="Error detail if metadata extraction failed")


class SpatialAnomalyMap(BaseModel):
    """Exploratory spatial compression anomaly heatmap and residual metrics."""
    status: str = Field(default="completed", description="Analysis status: completed, failed, unavailable")
    map_type: str = Field(default="error_level_analysis", description="Methodology identifier: error_level_analysis")
    input_width: Optional[int] = Field(default=None, description="Input image width in pixels")
    input_height: Optional[int] = Field(default=None, description="Input image height in pixels")
    visualization_width: Optional[int] = Field(default=None, description="Visualization map width in pixels")
    visualization_height: Optional[int] = Field(default=None, description="Visualization map height in pixels")
    is_downsampled: bool = Field(default=False, description="Whether the visualization map was downsampled to limit payload size")
    jpeg_quality: int = Field(default=95, description="JPEG quality used for in-memory recompression reference")
    scale_factor: float = Field(default=1.0, description="Contrast normalization multiplier")
    normalization_method: str = Field(default="percentile_linear_p99", description="Contrast normalization methodology applied")
    residual_statistics: Dict[str, float] = Field(default_factory=dict, description="Unscaled residual metrics (min, max, mean, std, rms, p99)")
    heatmap_data_uri: Optional[str] = Field(default=None, description="Base64-encoded PNG data URI of colored thermal anomaly heatmap")
    grayscale_data_uri: Optional[str] = Field(default=None, description="Base64-encoded PNG data URI of normalized grayscale anomaly map")
    limitations: List[str] = Field(default_factory=list, description="Specific limitations of the spatial anomaly method")
    disclaimer: str = Field(..., description="Forensic notice on exploratory nature of compression visualization")
    noteworthy_markers: List[str] = Field(default_factory=list, description="Observational markers regarding residual variance or compression behavior")
    error: Optional[str] = Field(default=None, description="Error detail if anomaly map generation failed")


class TraceAlert(BaseModel):
    """T.R.A.C.E. caution alert."""
    level: str = Field(..., description="Alert level: info, caution, inconclusive")
    message: str = Field(..., description="Actionable alert message grounded in evidence")


class ExternalAIDetectionResult(BaseModel):
    """External hosted AI detection service findings (e.g., Sightengine)."""
    provider: str = Field(default="Sightengine", description="External detection service provider")
    task: str = Field(default="ai_generated_image_detection", description="Detection task")
    status: str = Field(..., description="Status: completed, failed, not_configured, disabled, unavailable")
    label: Optional[str] = Field(default=None, description="Returned categorical classification, if available")
    score: Optional[float] = Field(default=None, description="Reported score [0.0 - 1.0], if returned")
    score_semantics: str = Field(
        default="ai_generated_probability",
        description="Semantics of score: reported probability that media was generated by AI or contains deepfake facial manipulation"
    )
    generator_scores: Optional[Dict[str, float]] = Field(
        default=None,
        description="Detector-indicated generator-specific confidence scores [0.0 - 1.0]"
    )
    interpretation: str = Field(..., description="Safe, user-readable explanation of findings and limitations")
    error: Optional[str] = Field(default=None, description="Error detail if upstream analysis failed")


class EvidenceItem(BaseModel):
    """Structured evidence presentation item clearly distinguishing observation, interpretation, and limitation."""
    id: str = Field(..., description="Unique evidence item identifier")
    category: str = Field(
        ...,
        description="Evidence category: ai_generation, deepfake, metadata, compression_analysis, provenance, visual_assessment"
    )
    source: str = Field(..., description="Specific tool or detector producing the observation")
    observation: str = Field(..., description="Empirical measurement or raw returned finding")
    interpretation: str = Field(..., description="Calibrated interpretation of the finding without claiming certainty")
    limitation: str = Field(..., description="Methodological boundary or what the finding cannot establish")
    status: str = Field(..., description="Verification status: completed, unavailable, failed, not_configured, disabled")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured details, scores, or tags")


class AnalysisResponse(BaseModel):
    """Complete image analysis response matching API_SPEC.md Section 4 with forensic extensions."""
    analysis_id: str = Field(..., description="Opaque analysis identifier")
    status: str = Field(..., description="Analysis status: completed, partial, or failed")
    media: MediaInfo
    ai_detection: AIDetectionResult
    provenance: ProvenanceResult
    investigation_scope: Optional[InvestigationScope] = Field(
        default=None,
        description="Selected checks and their execution statuses; absent for legacy serialized responses"
    )
    metadata_forensics: Optional[MetadataForensicsResult] = Field(
        default=None,
        description="Extracted container headers and EXIF forensic findings"
    )
    spatial_anomaly_map: Optional[SpatialAnomalyMap] = Field(
        default=None,
        description="Exploratory spatial compression anomaly heatmap and residual statistics"
    )
    external_ai_detection: Optional[ExternalAIDetectionResult] = Field(
        default=None,
        description="External hosted AI-generation detection findings (e.g., Sightengine genai)"
    )
    deepfake_detection: Optional[ExternalAIDetectionResult] = Field(
        default=None,
        description="External hosted deepfake detection findings (e.g., Sightengine deepfake)"
    )
    evidence_items: List[EvidenceItem] = Field(
        default_factory=list,
        description="Structured evidence items explaining observations, interpretations, limitations, and verification status"
    )
    trace_alert: TraceAlert
    limitations: List[str] = Field(..., description="Explicit limitations and caveats")
    created_at: datetime = Field(..., description="ISO 8601 timestamp in UTC")
