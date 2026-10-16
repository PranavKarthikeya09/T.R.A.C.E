import React from 'react';
import type { AIDetectionResult } from '../types/api';

interface AnalysisResultsProps {
  detection: AIDetectionResult;
}

export const AnalysisResults: React.FC<AnalysisResultsProps> = ({ detection }) => {
  if (detection.status !== 'completed') {
    const statusLabel = detection.status.replace(/_/g, ' ').toUpperCase();
    return (
      <div className="editorial-evidence-panel" role="status">
        <div className="panel-header-row">
          <div>
            <span className="panel-eyebrow font-mono">VISION MODEL ASSESSMENT</span>
            <h3 className="panel-title">Qualitative Image Analysis</h3>
          </div>
          <span className="editorial-badge font-mono badge--inconclusive">{statusLabel}</span>
        </div>
        <div className="panel-inner-body">
          <p className="observations-prose">
            {detection.interpretation || `Vision model assessment ${detection.status.replace(/_/g, ' ')}. No classification is available.`}
          </p>
        </div>
      </div>
    );
  }

  const formatLabel = (label: string) => {
    switch (label.toLowerCase()) {
      case 'potential_manipulation':
        return {
          title: 'Potential Manipulation',
          badgeClass: 'badge--caution',
          rationale: 'The inspection observed visual artifacts, boundary inconsistencies, or rendering textures characteristic of generative synthesis or digital editing.',
        };
      case 'authentic':
        return {
          title: 'Authentic Appearance',
          badgeClass: 'badge--notice',
          rationale: 'No conspicuous generative or manipulation artifacts were flagged. This observation does not confirm ground-truth capture authenticity.',
        };
      case 'inconclusive':
      default:
        return {
          title: 'Inconclusive',
          badgeClass: 'badge--inconclusive',
          rationale: 'Visual cues were subtle, degraded, or ambiguous. The model could not reach a confident heuristic assessment.',
        };
    }
  };

  const labelConfig = formatLabel(detection.label);

  return (
    <div className="editorial-evidence-panel">
      <div className="panel-header-row">
        <div>
          <span className="panel-eyebrow font-mono">VISION MODEL ASSESSMENT</span>
          <h3 className="panel-title">Qualitative Image Analysis</h3>
        </div>
        <span className="panel-engine-stamp font-mono">{detection.model_id}</span>
      </div>

      <div className="panel-inner-body">
        <div className="assessment-classification-block">
          <span className="field-label font-mono">HEURISTIC CLASSIFICATION</span>
          <div className="classification-pill-group">
            <span className={`editorial-badge font-mono ${labelConfig.badgeClass}`}>
              {labelConfig.title}
            </span>
            <span className="badge-sub-note font-mono">Uncalibrated Heuristic</span>
          </div>
          <p className="classification-rationale">{labelConfig.rationale}</p>
        </div>

        {detection.interpretation && (
          <div className="assessment-observations-block">
            <span className="field-label font-mono">FORENSIC OBSERVATIONS</span>
            <p className="observations-prose">{detection.interpretation}</p>
          </div>
        )}
      </div>

      <div className="panel-footer-disclaimer">
        <span className="disclaimer-title font-mono">METHODOLOGICAL BOUNDARY:</span>
        <span className="disclaimer-copy">
          Vision backbones evaluate rendering coherence and characteristic generative artifacts. They offer qualitative visual impressions rather than mathematical proof.
        </span>
      </div>
    </div>
  );
};
