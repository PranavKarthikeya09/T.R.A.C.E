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
          label: 'Caution',
          modifierClass: 'alert-banner--caution',
        };
      case 'info':
        return {
          label: 'Information',
          modifierClass: 'alert-banner--notice',
        };
      case 'inconclusive':
      default:
        return {
          label: 'Inconclusive',
          modifierClass: 'alert-banner--inconclusive',
        };
    }
  };

  const config = getAlertConfig(alert.level);

  return (
    <div className={`editorial-alert-banner ${config.modifierClass}`} role="alert">
      <div className="alert-top-bar">
        <span className="alert-eyebrow font-mono">PRIMARY FORENSIC ASSESSMENT</span>
        <span className="alert-tag font-mono">{config.label}</span>
      </div>
      <h3 className="alert-headline">{alert.message}</h3>
      <p className="alert-scope-note">
        Automated assessment only. Review the source, scope, and limitations before drawing conclusions.
      </p>
    </div>
  );
};
