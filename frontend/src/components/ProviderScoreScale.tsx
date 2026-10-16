import type { FC } from 'react';

interface ProviderScoreScaleProps {
  score?: number | null;
  semantics: string;
  status: string;
}

export const ProviderScoreScale: FC<ProviderScoreScaleProps> = ({ score, semantics, status }) => {
  const hasValidScore = status === 'completed'
    && typeof score === 'number'
    && Number.isFinite(score)
    && score >= 0
    && score <= 1;

  if (!hasValidScore) {
    return (
      <p className="provider-score-unavailable">
        {status === 'completed' ? 'No numeric score returned.' : 'A score is not available for this check status.'}
      </p>
    );
  }

  const value = score as number;
  const semanticsLabel = semantics.replace(/_/g, ' ');

  return (
    <figure
      className="provider-score-figure"
      aria-label={`${semanticsLabel}: provider returned ${value.toFixed(4)} on a scale from 0 to 1.`}
    >
      <figcaption className="provider-score-caption">
        <span className="provider-score-label font-mono">PROVIDER-REPORTED {semanticsLabel.toUpperCase()}</span>
        <span className="provider-score-value">{(value * 100).toFixed(1)}%</span>
      </figcaption>
      <div className="provider-score-axis" role="img" aria-label={`Provider score ${value.toFixed(4)} on a scale from 0 to 1`}>
        <div className="provider-score-track" aria-hidden="true">
          <span className="provider-score-fill" style={{ width: `${value * 100}%` }} />
          {[0, 25, 50, 75, 100].map((tick) => (
            <span key={tick} className="provider-score-tick" style={{ left: `${tick}%` }} />
          ))}
          <span className="provider-score-marker" style={{ left: `${value * 100}%` }} />
        </div>
        <div className="provider-score-endpoints font-mono" aria-hidden="true">
          <span>0</span><span>0.5</span><span>1</span>
        </div>
      </div>
      <p className="provider-score-note">Provider scale only; this result is independent of other checks.</p>
    </figure>
  );
};
