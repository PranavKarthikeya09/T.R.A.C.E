import React from 'react';
import type { AIDetectionResult } from '../types/api';

interface AnalysisResultsProps {
  detection: AIDetectionResult;
}

export const AnalysisResults: React.FC<AnalysisResultsProps> = ({ detection }) => {
  const formatLabel = (label: string) => {
    switch (label.toLowerCase()) {
      case 'potential_manipulation':
        return {
          title: 'Potential Media Manipulation',
          badgeClass: 'label-badge-caution',
          rationale:
            'The inspection observed visual artifacts, boundary inconsistencies, or rendering textures characteristic of generative synthesis or digital editing.',
        };
      case 'authentic':
        return {
          title: 'Authentic Photographic Appearance',
          badgeClass: 'label-badge-authentic',
          rationale:
            'No conspicuous generative or manipulation artifacts were flagged in this inspection. This does not confirm ground-truth capture authenticity.',
        };
      case 'inconclusive':
      default:
        return {
          title: 'Inconclusive Finding',
          badgeClass: 'label-badge-inconclusive',
          rationale:
            'Visual cues were subtle, degraded, or ambiguous. The model could not reach a confident heuristic assessment.',
        };
    }
  };

  const labelConfig = formatLabel(detection.label);

  return (
    <div className="forensic-card assessment-panel">
      <div className="card-header-bar">
        <div>
          <span className="card-eyebrow">AUTOMATED VISION INSPECTION</span>
          <h3 className="card-title">Qualitative Model Assessment</h3>
        </div>
        <div className="model-id-tag font-mono">
          <span className="model-id-label">ENGINE:</span>
          <span className="model-id-value">{detection.model_id}</span>
        </div>
      </div>

      <div className="assessment-classification-row">
        <div className="classification-box">
          <span className="box-meta-label">CLASSIFICATION</span>
          <div className="classification-value-group">
            <span className={`classification-badge font-mono ${labelConfig.badgeClass}`}>
              {labelConfig.title}
            </span>
            <span className="heuristic-tag">Heuristic</span>
          </div>
          <p className="classification-rationale">{labelConfig.rationale}</p>
        </div>
      </div>

      <div className="observations-box">
        <div className="observations-header-compact">
          <span className="box-meta-label">VISUAL OBSERVATIONS &amp; ANOMALY LOG</span>
        </div>

        <div className="observations-content font-mono-subtle">
          <p className="observations-text">
            {detection.interpretation || 'No narrative observations were returned for this image.'}
          </p>
        </div>

        <div className="forensic-disclaimer-note">
          <span className="disclaimer-indicator" aria-hidden="true">NOTE:</span>
          <span className="disclaimer-copy">
            Machine-generated qualitative visual impressions. They describe observable features (geometry, lighting coherence, texture transitions) and must not be treated as certified evidence.
          </span>
        </div>
      </div>
    </div>
  );
};
