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
    <div className="editorial-evidence-panel">
      <div className="panel-header-row">
        <div>
          <span className="panel-eyebrow font-mono">AUDIT TRAIL</span>
          <h3 className="panel-title">Inspection Traceability &amp; Score Semantics</h3>
        </div>
        <span className="panel-engine-stamp font-mono">ID: {analysisId.substring(0, 8)}</span>
      </div>

      <div className="editorial-table-grid font-mono">
        <div className="grid-meta-cell">
          <span className="meta-k">ANALYSIS SESSION ID</span>
          <span className="meta-v selectable-text">{analysisId}</span>
          <span className="meta-hint">Unique audit trail identifier</span>
        </div>

        <div className="grid-meta-cell">
          <span className="meta-k">RECORDED TIME (UTC)</span>
          <span className="meta-v">{formattedDate}</span>
          <span className="meta-hint">Server ingestion timestamp</span>
        </div>

        <div className="grid-meta-cell">
          <span className="meta-k">REPORTED SCORE</span>
          <span className="meta-v">
              {detection.score !== null ? `${detection.score}` : 'Not provided'}
          </span>
          <span className="meta-hint">
            {detection.score_semantics || 'No score semantics returned.'}
          </span>
        </div>

        <div className="grid-meta-cell">
          <span className="meta-k">CONTAINER SPECIFICATION</span>
          <span className="meta-v text-truncate" title={media.filename}>
            {media.filename}
          </span>
          <span className="meta-hint">Media type: {media.type.toUpperCase()}</span>
        </div>
      </div>
    </div>
  );
};
