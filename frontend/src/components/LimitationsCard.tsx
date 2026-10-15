import React from 'react';

interface LimitationsCardProps {
  limitations: string[];
}

export const LimitationsCard: React.FC<LimitationsCardProps> = ({ limitations }) => {
  return (
    <div className="forensic-card limitations-panel">
      <div className="card-header-bar">
        <div>
          <span className="card-eyebrow">INTEGRITY SAFEGUARDS</span>
          <h3 className="card-title">Methodological Boundaries</h3>
        </div>
      </div>

      <div className="limitations-body">
        <p className="limitations-intro">
          Automated heuristic detections are subject to the following technical and legal constraints:
        </p>

        <ul className="limitations-bullet-list">
          {limitations.map((item, idx) => (
            <li key={idx} className="limitations-list-item">
              <span className="limitations-marker" aria-hidden="true">—</span>
              <span className="limitations-text-content">{item}</span>
            </li>
          ))}
        </ul>

        <div className="incident-reporting-callout">
          <div className="callout-text-group">
            <span className="callout-heading">INCIDENT REPORTING</span>
            <p className="callout-desc">
              If this media is associated with extortion, impersonation, or financial fraud, submit evidence through authorized legal enforcement channels.
            </p>
          </div>
          <a
            href="https://cybercrime.gov.in/"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary-compact font-mono"
          >
            cybercrime.gov.in ↗
          </a>
        </div>
      </div>
    </div>
  );
};
