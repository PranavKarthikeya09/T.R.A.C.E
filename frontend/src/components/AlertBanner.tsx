import React from 'react';
import type { TraceAlert } from '../types/api';

interface AlertBannerProps {
  alert: TraceAlert;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ alert }) => {
  const getAlertConfig = (level: string) => {
    switch (level) {
      case 'caution':
        return {
          category: 'PRIMARY FORENSIC ALERT',
          verdict: 'CAUTION // ANOMALIES DETECTED',
          containerClass: 'alert-level-caution',
          tagClass: 'verdict-tag-caution',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          ),
          scope: 'Automated inspection observed visual characteristics consistent with synthetic or modified media.',
        };
      case 'info':
        return {
          category: 'PRIMARY FORENSIC ALERT',
          verdict: 'NOTICE // NO PROMINENT ANOMALIES',
          containerClass: 'alert-level-notice',
          tagClass: 'verdict-tag-notice',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ),
          scope: 'Inspection did not identify significant visual manipulation patterns. Absence of evidence is not proof of authenticity.',
        };
      case 'inconclusive':
      default:
        return {
          category: 'PRIMARY FORENSIC ALERT',
          verdict: 'INCONCLUSIVE // AMBIGUOUS SIGNALS',
          containerClass: 'alert-level-inconclusive',
          tagClass: 'verdict-tag-inconclusive',
          icon: (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3m.08 4h.01" />
            </svg>
          ),
          scope: 'Visual indicators were subtle or contradictory. The system could not assign a confident heuristic label.',
        };
    }
  };

  const config = getAlertConfig(alert.level);

  return (
    <div className={`forensic-verdict-banner ${config.containerClass}`} role="alert">
      <div className="verdict-banner-header">
        <div className="verdict-header-left">
          <span className="verdict-icon-box">{config.icon}</span>
          <div className="verdict-titles">
            <span className="verdict-category-label">{config.category}</span>
            <span className={`verdict-tag font-mono ${config.tagClass}`}>{config.verdict}</span>
          </div>
        </div>
        <span className="verdict-scope-badge">HEURISTIC REPORT</span>
      </div>

      <div className="verdict-banner-body">
        <p className="verdict-message-text">{alert.message}</p>
        <p className="verdict-subtext">{config.scope}</p>
      </div>
    </div>
  );
};
