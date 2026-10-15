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

export interface AnalysisResponse {
  analysis_id: string;
  status: string;
  media: MediaInfo;
  ai_detection: AIDetectionResult;
  provenance: ProvenanceResult;
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
}
