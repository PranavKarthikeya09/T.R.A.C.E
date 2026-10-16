/**
 * T.R.A.C.E. Frontend API Interfaces
 * Strictly aligned with API_SPEC.md and backend Pydantic schemas.
 */

export type AlertLevel = 'info' | 'caution' | 'inconclusive';

export interface MediaInfo {
  type: string;
  filename: string;
}

export interface AIDetectionResult {
  status: string;
  model_id: string;
  label: string;
  score: number | null;
  score_semantics: string;
  interpretation: string;
}

export interface ProvenanceCheck {
  name: string;
  status: string;
  details?: string | null;
}

export interface ProvenanceResult {
  status: string;
  checks: ProvenanceCheck[];
}

export interface TraceAlert {
  level: AlertLevel;
  message: string;
}

export interface MetadataForensicsResult {
  status: string;
  has_exif: boolean;
  camera_make?: string | null;
  camera_model?: string | null;
  lens_model?: string | null;
  capture_time?: string | null;
  software?: string | null;
  orientation?: number | null;
  orientation_description?: string | null;
  identifiable_fields: string[];
  raw_tags?: Record<string, unknown>;
  noteworthy_markers: string[];
  disclaimer: string;
  error?: string | null;
}

export interface ResidualStatistics {
  min_residual?: number;
  max_residual?: number;
  mean_residual?: number;
  std_residual?: number;
  rms_residual?: number;
  p99_residual?: number;
  [key: string]: number | undefined;
}

export interface SpatialAnomalyMap {
  status: string;
  map_type: string;
  input_width?: number | null;
  input_height?: number | null;
  visualization_width?: number | null;
  visualization_height?: number | null;
  is_downsampled: boolean;
  jpeg_quality: number;
  scale_factor: number;
  normalization_method: string;
  residual_statistics: ResidualStatistics;
  heatmap_data_uri?: string | null;
  grayscale_data_uri?: string | null;
  limitations: string[];
  disclaimer: string;
  noteworthy_markers: string[];
  error?: string | null;
}

export interface ExternalAIDetectionResult {
  provider: string;
  task: string;
  status: 'completed' | 'failed' | 'not_configured' | 'disabled' | 'unavailable';
  label?: string | null;
  score?: number | null;
  score_semantics: string;
  generator_scores?: Record<string, number> | null;
  interpretation: string;
  error?: string | null;
}

export interface EvidenceItem {
  id: string;
  category: 'ai_generation' | 'deepfake' | 'metadata' | 'compression_analysis' | 'provenance' | 'visual_assessment' | string;
  source: string;
  observation: string;
  interpretation: string;
  limitation: string;
  status: 'completed' | 'failed' | 'not_configured' | 'disabled' | 'unavailable' | string;
  details?: Record<string, unknown> | null;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: string;
  media: MediaInfo;
  ai_detection: AIDetectionResult;
  provenance: ProvenanceResult;
  investigation_scope?: {
    selected_checks: string[];
    check_statuses: Record<string, string>;
  } | null;
  metadata_forensics?: MetadataForensicsResult | null;
  spatial_anomaly_map?: SpatialAnomalyMap | null;
  external_ai_detection?: ExternalAIDetectionResult | null;
  deepfake_detection?: ExternalAIDetectionResult | null;
  evidence_items?: EvidenceItem[];
  trace_alert: TraceAlert;
  limitations: string[];
  created_at: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export interface HealthResponse {
  status: string;
  service: string;
  capabilities?: Record<string, string>;
}
