import React from 'react';
import type { ProvenanceResult } from '../types/api';

interface ProvenanceCardProps {
  provenance: ProvenanceResult;
}

export const ProvenanceCard: React.FC<ProvenanceCardProps> = ({ provenance }) => {
  const formatStatus = (status: string) => {
    switch (status) {
      case 'verified':
        return { label: 'CREDENTIALS VERIFIED', badgeClass: 'badge--notice' };
      case 'invalid':
      case 'tampered':
        return { label: 'MANIFEST INVALID', badgeClass: 'badge--caution' };
      case 'not_found':
        return { label: 'NO MANIFEST FOUND', badgeClass: 'badge--inconclusive' };
      case 'failed':
        return { label: 'CHECK FAILED', badgeClass: 'badge--caution' };
      case 'disabled':
        return { label: 'CHECK DISABLED', badgeClass: 'badge--inconclusive' };
      case 'not_configured':
        return { label: 'NOT CONFIGURED', badgeClass: 'badge--inconclusive' };
      case 'unavailable':
        return { label: 'CHECK UNAVAILABLE', badgeClass: 'badge--inconclusive' };
      case 'not_requested':
      default:
        return { label: 'NOT REQUESTED', badgeClass: 'badge--inconclusive' };
    }
  };

  const statusConfig = formatStatus(provenance.status);

  return (
    <div className="editorial-evidence-panel">
      <div className="panel-header-row">
        <div>
          <span className="panel-eyebrow font-mono">CONTENT CREDENTIALS (C2PA)</span>
          <h3 className="panel-title">Origin Provenance</h3>
        </div>
        <span className={`editorial-badge font-mono ${statusConfig.badgeClass}`}>
          {statusConfig.label}
        </span>
      </div>

      <div className="panel-inner-body">
        {provenance.status === 'not_requested' ? (
          <div className="provenance-not-requested font-mono">
            <p className="provenance-unrequested-text">
              C2PA inspection was not selected for this examination. No provenance conclusion was produced.
            </p>
            <div className="provenance-guideline-note">
              <strong className="guideline-k">FORENSIC RULE:</strong>
              <span className="guideline-v">
                The absence of cryptographic manifests does not indicate manipulation. Most consumer capture devices do not yet sign media credentials.
              </span>
            </div>
          </div>
        ) : provenance.status === 'disabled' || provenance.status === 'unavailable' || provenance.status === 'failed' ? (
          <div className="provenance-empty font-mono" role="status">
            {provenance.checks?.map((check) => check.details).filter(Boolean).join(' ') || `C2PA inspection is ${provenance.status}. No conclusion about manifest presence or signature validity is available.`}
          </div>
        ) : provenance.checks && provenance.checks.length > 0 ? (
          <div className="provenance-checks-grid font-mono">
            <div className="checks-header">
              <span>CHECK</span>
              <span className="text-right">RESULT</span>
            </div>
            {provenance.checks.map((check, idx) => (
              <div key={idx} className="check-item-row">
                <span className="check-item-name">{check.name}</span>
                <span className={`check-item-badge ${check.status === 'passed' ? 'badge--notice' : 'badge--caution'}`}>
                  {check.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        ) : provenance.status === 'not_found' ? (
          <div className="provenance-empty font-mono">
            No cryptographic provenance claims or C2PA manifests were discovered in container headers.
          </div>
        ) : (
          <div className="provenance-empty font-mono">
            Provenance status: {provenance.status.replace(/_/g, ' ')}. No additional check details were returned.
          </div>
        )}
      </div>

      <div className="panel-footer-disclaimer">
        <span className="disclaimer-title font-mono">PROVENANCE NOTE:</span>
        <span className="disclaimer-copy">
          This application does not currently parse C2PA manifests or verify signatures. If verification is added, a valid signature would not certify that the depicted real-world scene was truthful.
        </span>
      </div>
    </div>
  );
};
