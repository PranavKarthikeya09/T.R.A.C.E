import React from 'react';
import type { ExternalAIDetectionResult } from '../types/api';
import { ProviderScoreScale } from './ProviderScoreScale';

interface SightengineCardProps {
  externalAi?: ExternalAIDetectionResult | null;
  requested?: boolean;
}

export const SightengineCard: React.FC<SightengineCardProps> = ({ externalAi, requested = true }) => {
  if (!externalAi || externalAi.status === 'not_configured' || externalAi.status === 'disabled') {
    const isUnconfigured = externalAi?.status === 'not_configured';
    const isNotReturned = !externalAi;
    return (
      <div className="editorial-evidence-panel">
        <div className="panel-header-row">
          <div>
            <span className="panel-eyebrow font-mono">AI-GENERATION ASSESSMENT</span>
            <h3 className="panel-title">Sightengine GenAI Detection</h3>
          </div>
          <span className="editorial-badge font-mono badge--inconclusive">
            {isNotReturned ? (requested ? 'NOT RETURNED' : 'NOT REQUESTED') : isUnconfigured ? 'NOT CONFIGURED' : 'DISABLED'}
          </span>
        </div>
        <div className="panel-inner-body font-mono">
          <p className="sightengine-unconfigured-text">
            {externalAi?.interpretation || (isNotReturned
              ? requested ? 'The API response did not include an AI-generation provider result.' : 'AI-generation detection was not selected for this examination.'
              : isUnconfigured
                ? 'Sightengine external AI-generation detection is not configured. Configure the provider in the backend environment to enable external evaluation.'
                : 'Sightengine external AI-generation detection is disabled for this analysis.')}
          </p>
        </div>
        <div className="panel-footer-disclaimer">
          <span className="disclaimer-title font-mono">PROVIDER NOTE:</span>
          <span className="disclaimer-copy">
            External detection is an optional secondary verification signal and does not affect local metadata or compression anomaly analysis.
          </span>
        </div>
      </div>
    );
  }

  const isFailed = externalAi.status === 'failed';
  const isUnavailable = externalAi.status === 'unavailable';

  const formatClassification = (label?: string | null) => {
    if (isFailed) {
      return {
        title: 'Inspection failed',
        badgeClass: 'badge--caution',
        statusLabel: 'FAILED',
      };
    }
    if (isUnavailable) {
      return { title: 'Provider unavailable', badgeClass: 'badge--inconclusive', statusLabel: 'UNAVAILABLE' };
    }
    const cleanLabel = (label || '').toLowerCase();
    if (cleanLabel === 'likely_ai_generated') {
      return {
        title: 'Likely AI-Generated',
        badgeClass: 'badge--caution',
        statusLabel: 'HIGH AI PROBABILITY',
      };
    } else if (cleanLabel === 'low_probability_ai_generated') {
      return {
        title: 'Low AI Probability',
        badgeClass: 'badge--notice',
        statusLabel: 'LOW AI PROBABILITY',
      };
    } else {
      return {
        title: cleanLabel ? `Returned label: ${cleanLabel.replace(/_/g, ' ')}` : 'No categorical label returned',
        badgeClass: 'badge--inconclusive',
        statusLabel: cleanLabel ? 'UPSTREAM LABEL' : 'LABEL NOT RETURNED',
      };
    }
  };

  const config = formatClassification(externalAi.label);

  // Filter meaningful generator scores (>= 0.05) to avoid cluttering with 0.001 background noise
  const meaningfulGenerators = externalAi.generator_scores
    ? Object.entries(externalAi.generator_scores)
        .filter(([, val]) => typeof val === 'number' && val >= 0.05)
        .sort(([, a], [, b]) => b - a)
    : [];

  return (
    <div className="editorial-evidence-panel">
      {/* Panel Header */}
      <div className="panel-header-row">
        <div>
          <span className="panel-eyebrow font-mono">AI-GENERATION ASSESSMENT</span>
          <h3 className="panel-title">Sightengine GenAI Detection</h3>
        </div>
        <div className="panel-badge-group">
          <span className="panel-engine-stamp font-mono">{externalAi.provider}</span>
          <span className={`editorial-badge font-mono ${config.badgeClass}`}>
            {config.statusLabel}
          </span>
        </div>
      </div>

      <div className="panel-inner-body">
        {/* Metric and Evaluation Grid */}
        <ProviderScoreScale score={externalAi.score} semantics={externalAi.score_semantics} status={externalAi.status} />
        <div className="editorial-table-grid provider-result-grid font-mono">
          <div className="grid-meta-cell">
            <span className="meta-k">DETECTOR TASK</span>
            <span className="meta-v">AI-Generated Image Detection</span>
            <span className="meta-hint">Pixel synthesis analysis</span>
          </div>

          <div className="grid-meta-cell">
            <span className="meta-k">CATEGORICAL LABEL</span>
            <span className="meta-v">{config.title}</span>
            <span className="meta-hint">Categorical label returned by provider</span>
          </div>

          <div className="grid-meta-cell">
            <span className="meta-k">VERIFICATION STATUS</span>
            <span className="meta-v">{externalAi.status.toUpperCase()}</span>
            <span className="meta-hint">Provider API resolution</span>
          </div>
        </div>

        {/* Narrative Findings & Interpretation */}
        <div className="assessment-observations-block">
          <span className="field-label font-mono">FINDINGS &amp; INTERPRETATION</span>
          <p className="observations-prose">{externalAi.interpretation}</p>
        </div>

        {/* Generator-Specific Associations (if returned and meaningful) */}
        {meaningfulGenerators.length > 0 && (
          <div className="editorial-markers-strip">
            <span className="markers-label font-mono">
              DETECTOR-INDICATED GENERATOR ASSOCIATIONS
            </span>
            <div className="generator-scores-grid font-mono">
              {meaningfulGenerators.map(([genName, genScore]) => (
                <div key={genName} className="generator-score-cell">
                  <span className="gen-name">{genName.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className="gen-score">{(genScore * 100).toFixed(1)}%</span>
                  <div className="gen-progress-track">
                    <div
                      className="gen-progress-fill"
                      style={{ width: `${Math.min(100, Math.max(0, genScore * 100))}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <p className="generator-caveat font-mono">
              <strong>Caveat:</strong> These scores reflect detector similarity patterns to specific model distributions. They do not establish provenance or prove which tool created the image.
            </p>
          </div>
        )}

        {/* Error Callout if Failed */}
        {(isFailed || isUnavailable) && externalAi.error && (
          <div className="editorial-error-strip font-mono">
            <strong>PROVIDER ERROR:</strong> {externalAi.error}
          </div>
        )}
      </div>

      {/* Forensic Disclaimer */}
      <div className="panel-footer-disclaimer">
        <span className="disclaimer-title font-mono">BOUNDARY SAFEGUARD:</span>
        <span className="disclaimer-copy">
          Sightengine evaluates statistical generative synthesis artifacts. A low AI probability does not confirm an image is an unmanipulated original photograph; manual splicing, object insertion, or retouching must be corroborated with Error Level Analysis and container metadata.
        </span>
      </div>
    </div>
  );
};
