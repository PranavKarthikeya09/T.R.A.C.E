import React from 'react';

interface HeaderProps {
  isBackendHealthy: boolean | null;
  onOpenMethodology: () => void;
  onNewInvestigation?: () => void;
  onViewReport?: () => void;
  hasActiveInvestigation?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  isBackendHealthy,
  onOpenMethodology,
  onNewInvestigation,
  hasActiveInvestigation,
  onViewReport,
}) => {
  return (
    <header className="editorial-masthead">
      <div className="masthead-inner">
        {/* Brand identity lockup */}
        <div className="masthead-brand">
          <div className="brand-title-row">
            <span className="brand-seal" aria-hidden="true">T</span>
            <span className="brand-wordmark">T.R.A.C.E.</span>
            <span className="brand-divider" aria-hidden="true">|</span>
            <span className="brand-acronym-expansion">
              Tampering Recognition, Authentication &amp; Content Evidence
            </span>
          </div>
            <span className="brand-descriptor">Digital image investigation</span>
        </div>

        {/* Right navigation and status */}
        <nav className="masthead-nav" aria-label="Primary navigation">
          {hasActiveInvestigation && onViewReport && (
            <button type="button" className="masthead-nav-link" onClick={onViewReport}>
              View Report
            </button>
          )}
          {hasActiveInvestigation && onNewInvestigation && (
            <button
              type="button"
              className="btn btn-primary-editorial masthead-new-button"
              onClick={onNewInvestigation}
            >
              New investigation
            </button>
          )}

          <button
            type="button"
            className="masthead-nav-link"
            onClick={onOpenMethodology}
          >
            Methodology Framework
          </button>

          <div
            className="masthead-status"
            role="status"
            aria-live="polite"
            title={
              isBackendHealthy === true
                ? 'Analysis API reachable'
                : isBackendHealthy === false
                ? 'Analysis API unreachable'
                : 'Checking analysis API…'
            }
          >
            <span
              className={`status-indicator-dot ${
                isBackendHealthy === true
                  ? 'status-dot--online'
                  : isBackendHealthy === false
                  ? 'status-dot--offline'
                  : 'status-dot--pending'
              }`}
              aria-hidden="true"
            />
            <span className="status-indicator-text font-mono">
              {isBackendHealthy === true
                ? 'API reachable'
                : isBackendHealthy === false
                ? 'API unavailable'
                : 'Checking…'}
            </span>
          </div>
        </nav>
      </div>
    </header>
  );
};
