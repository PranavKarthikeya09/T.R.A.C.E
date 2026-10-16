import React from 'react';
import type { ExternalAIDetectionResult } from '../types/api';
import { ProviderScoreScale } from './ProviderScoreScale';

interface DeepfakeCardProps {
  deepfake?: ExternalAIDetectionResult | null;
  requested?: boolean;
}

export const DeepfakeCard: React.FC<DeepfakeCardProps> = ({ deepfake, requested = true }) => {
  if (!deepfake || deepfake.status === 'not_configured' || deepfake.status === 'disabled') {
    const isUnconfigured = deepfake?.status === 'not_configured';
    const isNotReturned = !deepfake;
    return (
      <div className="editorial-evidence-panel">
        <div className="panel-header-row">
          <div>
            <span className="panel-eyebrow font-mono">FACIAL MANIPULATION ASSESSMENT</span>
            <h3 className="panel-title">Sightengine Deepfake Detection</h3>
          </div>
          <span className="editorial-badge font-mono badge--inconclusive">
            {isNotReturned ? (requested ? 'NOT RETURNED' : 'NOT REQUESTED') : isUnconfigured ? 'NOT CONFIGURED' : 'DISABLED'}
          </span>
        </div>
        <div className="panel-inner-body font-mono">
          <p className="sightengine-unconfigured-text">
            {deepfake?.interpretation ||
              (isNotReturned
                ? requested ? 'The API response did not include a deepfake detection result.' : 'Deepfake detection was not selected for this examination.'
                : isUnconfigured
                  ? 'Sightengine deepfake detection is not configured. Configure the provider to enable optional face-swap inspection.'
                  : 'Sightengine deepfake detection is disabled for this analysis.')}
          </p>
        </div>
        <div className="panel-footer-disclaimer">
          <span className="disclaimer-title font-mono">DETECTOR NOTE:</span>
          <span className="disclaimer-copy">
            Deepfake detection is an independent, optional capability that addresses face-swap manipulation on prominent faces. It is distinct from whole-image generative AI synthesis detection.
          </span>
        </div>
      </div>
    );
  }

  const isFailed = deepfake.status === 'failed';
  const isUnavailable = deepfake.status === 'unavailable';

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
    if (cleanLabel === 'likely_deepfake') {
      return {
        title: 'Likely Deepfake / Manipulated Face',
        badgeClass: 'badge--caution',
        statusLabel: 'ELEVATED DEEPFAKE RISK',
      };
    } else if (cleanLabel === 'low_probability_deepfake') {
      return {
        title: 'Low Deepfake Probability',
        badgeClass: 'badge--notice',
        statusLabel: 'LOW MANIPULATION RISK',
      };
    } else {
      return {
        title: cleanLabel ? `Returned label: ${cleanLabel.replace(/_/g, ' ')}` : 'No categorical label returned',
        badgeClass: 'badge--inconclusive',
        statusLabel: cleanLabel ? 'UPSTREAM LABEL' : 'LABEL NOT RETURNED',
      };
    }
  };

  const config = formatClassification(deepfake.label);

  return (
    <div className="editorial-evidence-panel">
      {/* Panel Header */}
      <div className="panel-header-row">
        <div>
          <span className="panel-eyebrow font-mono">FACIAL MANIPULATION ASSESSMENT</span>
          <h3 className="panel-title">Sightengine Deepfake Detection</h3>
        </div>
        <div className="panel-badge-group">
          <span className="panel-engine-stamp font-mono">{deepfake.provider}</span>
          <span className={`editorial-badge font-mono ${config.badgeClass}`}>
            {config.statusLabel}
          </span>
        </div>
      </div>

      <div className="panel-inner-body">
        {/* Metric and Evaluation Grid */}
        <ProviderScoreScale score={deepfake.score} semantics={deepfake.score_semantics} status={deepfake.status} />
        <div className="editorial-table-grid provider-result-grid font-mono">
          <div className="grid-meta-cell">
            <span className="meta-k">DETECTOR TASK</span>
            <span className="meta-v">Deepfake Face Swap Inspection</span>
            <span className="meta-hint">Target: Prominent facial features</span>
          </div>

          <div className="grid-meta-cell">
            <span className="meta-k">CATEGORICAL LABEL</span>
            <span className="meta-v">{config.title}</span>
            <span className="meta-hint">Categorical label returned by provider</span>
          </div>

          <div className="grid-meta-cell">
            <span className="meta-k">VERIFICATION STATUS</span>
            <span className="meta-v">{deepfake.status.toUpperCase()}</span>
            <span className="meta-hint">Provider API resolution</span>
          </div>
        </div>

        {/* Narrative interpretation */}
        <div className="assessment-observations-block">
          <span className="field-label font-mono">FINDINGS &amp; INTERPRETATION</span>
          <p className="observations-prose">{deepfake.interpretation}</p>
        </div>

        {/* Error Callout if Failed */}
        {(isFailed || isUnavailable) && deepfake.error && (
          <div className="editorial-error-strip font-mono">
            <strong>PROVIDER ERROR:</strong> {deepfake.error}
          </div>
        )}
      </div>

      {/* Forensic Disclaimer */}
      <div className="panel-footer-disclaimer">
        <span className="disclaimer-title font-mono">SCOPE SAFEGUARD:</span>
        <span className="disclaimer-copy">
          Deepfake detection evaluates photographic faces for signs of identity substitution or face-swapping. A low score does not imply the image is authentic or unmanipulated: non-facial alterations, full generative synthesis, or text insertions must be inspected through separate forensic layers.
        </span>
      </div>
    </div>
  );
};
