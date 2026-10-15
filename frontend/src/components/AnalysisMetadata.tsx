import React from 'react';
import type { AIDetectionResult, MediaInfo } from '../types/api';

interface AnalysisMetadataProps {
  detection: AIDetectionResult;
  media: MediaInfo;
  analysisId: string;
  createdAt: string;
}

export const AnalysisMetadata: React.FC<AnalysisMetadataProps> = ({
  detection,
  media,
  analysisId,
  createdAt,
}) => {
  const formattedDate = new Date(createdAt).toISOString().replace('T', ' ').substring(0, 19) + ' UTC';

  return (
    <div className="forensic-card metadata-panel">
      <div className="card-header-bar">
        <div>
          <span className="card-eyebrow">AUDIT TRAIL</span>
          <h3 className="card-title">Inspection Traceability</h3>
        </div>
        <span className="audit-hash-badge font-mono">SHA-REF: {analysisId.substring(0, 8)}</span>
      </div>

      <div className="metadata-table-grid">
        <div className="meta-grid-item">
          <span className="meta-item-label">ANALYSIS ID</span>
          <span className="meta-item-value font-mono selectable-text">{analysisId}</span>
          <span className="meta-item-help">Unique audit session identifier</span>
        </div>

        <div className="meta-grid-item">
          <span className="meta-item-label">RECORDED TIMESTAMP</span>
          <span className="meta-item-value font-mono">{formattedDate}</span>
          <span className="meta-item-help">System receipt timestamp</span>
        </div>

        <div className="meta-grid-item">
          <span className="meta-item-label">CALIBRATED CONFIDENCE</span>
          <span className="meta-item-value font-mono">
            {detection.score !== null ? `${detection.score}` : 'None (Uncalibrated)'}
          </span>
          <span className="meta-item-help">
            {detection.score_semantics === 'not_applicable_qualitative_heuristic'
              ? 'Qualitative visual inspection; no probabilistic score.'
              : detection.score_semantics || 'Uncalibrated qualitative heuristic.'}
          </span>
        </div>

        <div className="meta-grid-item">
          <span className="meta-item-label">MEDIA SPECIFICATION</span>
          <span className="meta-item-value font-mono text-truncate" title={media.filename}>
            {media.filename}
          </span>
          <span className="meta-item-help">Type: {media.type.toUpperCase()}</span>
        </div>

        <div className="meta-grid-item">
          <span className="meta-item-label">INFERENCE BACKBONE</span>
          <span className="meta-item-value font-mono">{detection.model_id}</span>
          <span className="meta-item-help">Platform: Azure AI Foundry Vision</span>
        </div>

        <div className="meta-grid-item">
          <span className="meta-item-label">VERIFICATION INTEGRITY</span>
          <span className="meta-item-value font-mono">STRICT_PARSED</span>
          <span className="meta-item-help">Backend contract validated</span>
        </div>
      </div>
    </div>
  );
};
