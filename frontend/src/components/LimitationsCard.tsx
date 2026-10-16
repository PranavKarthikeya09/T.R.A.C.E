import React from 'react';

interface LimitationsCardProps {
  limitations: string[];
}

export const LimitationsCard: React.FC<LimitationsCardProps> = ({ limitations }) => {
  return (
    <div className="editorial-evidence-panel">
      <div className="panel-header-row">
        <div>
          <span className="panel-eyebrow font-mono">INTEGRITY SAFEGUARDS</span>
          <h3 className="panel-title">Methodological Boundaries</h3>
        </div>
      </div>

      <div className="panel-inner-body">
        <p className="limitations-lead">
          Automated heuristic detections and forensic indicators are constrained by technical boundaries:
        </p>

        <ul className="limitations-list">
          {limitations.map((item, idx) => (
            <li key={idx} className="limitations-item">
              <span className="limitations-bullet" aria-hidden="true">—</span>
              <span className="limitations-text">{item}</span>
            </li>
          ))}
        </ul>

        <div className="incident-reporting-box">
          <div className="reporting-copy">
            <span className="reporting-eyebrow font-mono">INCIDENT REPORTING</span>
            <p className="reporting-text">
              If this media is associated with extortion, impersonation, or financial fraud, submit evidence through authorized legal enforcement channels.
            </p>
          </div>
          <a
            href="https://cybercrime.gov.in/"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary-restrained font-mono"
          >
            cybercrime.gov.in ↗
          </a>
        </div>
      </div>
    </div>
  );
};
