import React from 'react';

interface HeaderProps {
  isBackendHealthy: boolean | null;
}

export const Header: React.FC<HeaderProps> = ({ isBackendHealthy }) => {
  return (
    <header className="trace-header">
      <div className="trace-header-inner">
        <div className="trace-header-brand">
          <div className="trace-wordmark">
            <span className="trace-wordmark-acronym">T.R.A.C.E.</span>
            <span className="trace-brand-divider" aria-hidden="true">/</span>
            <span className="trace-brand-tag">FORENSICS</span>
          </div>
          <span className="trace-header-subtitle">
            Tampering Recognition, Authentication &amp; Content Evidence
          </span>
        </div>

        <div className="trace-header-controls">
          <div className="trace-system-status" title="API Backend Connectivity Status">
            <span
              className={`status-indicator-dot ${
                isBackendHealthy === true
                  ? 'status-dot-online'
                  : isBackendHealthy === false
                  ? 'status-dot-offline'
                  : 'status-dot-pending'
              }`}
              aria-hidden="true"
            />
            <span className="status-indicator-label">
              {isBackendHealthy === true
                ? 'CORE ONLINE'
                : isBackendHealthy === false
                ? 'CORE OFFLINE'
                : 'CONNECTING'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
