import React from 'react';
import type { ProvenanceResult } from '../types/api';

interface ProvenanceCardProps {
  provenance: ProvenanceResult;
}

export const ProvenanceCard: React.FC<ProvenanceCardProps> = ({ provenance }) => {
  const formatStatus = (status: string) => {
    switch (status) {
      case 'verified':
        return { label: 'CREDENTIALS VERIFIED', badgeClass: 'prov-badge-verified' };
      case 'invalid':
        return { label: 'SIGNATURE INVALID', badgeClass: 'prov-badge-invalid' };
      case 'tampered':
        return { label: 'MANIFEST TAMPERED', badgeClass: 'prov-badge-invalid' };
      case 'not_found':
        return { label: 'NO MANIFEST FOUND', badgeClass: 'prov-badge-not-found' };
      case 'unavailable':
        return { label: 'CHECK UNAVAILABLE', badgeClass: 'prov-badge-unavailable' };
      case 'not_requested':
      default:
        return { label: 'NOT REQUESTED', badgeClass: 'prov-badge-not-requested' };
    }
  };

  const statusConfig = formatStatus(provenance.status);

  return (
    <div className="forensic-card provenance-panel">
      <div className="card-header-bar">
        <div>
          <span className="card-eyebrow">ORIGIN &amp; CREDENTIALS</span>
          <h3 className="card-title">Provenance (C2PA)</h3>
        </div>
        <span className={`status-pill font-mono ${statusConfig.badgeClass}`}>
          {statusConfig.label}
        </span>
      </div>

      <div className="provenance-body">
        {provenance.status === 'not_requested' ? (
          <div className="provenance-unrequested-state">
            <p className="provenance-status-text">
              Cryptographic origin verification was not requested for this inspection. C2PA Content Credentials and digital signatures were not evaluated.
            </p>
            <div className="provenance-safeguard-banner">
              <span className="safeguard-label">FORENSIC RULE:</span>
              <span className="safeguard-text">
                The absence of cryptographic metadata does not establish manipulation. Standard capture hardware and compression pipelines frequently strip provenance headers.
              </span>
            </div>
          </div>
        ) : provenance.checks && provenance.checks.length > 0 ? (
          <div className="provenance-checks-table">
            <div className="checks-header-row">
              <span className="checks-col-header">CHECK</span>
              <span className="checks-col-header text-right">RESULT</span>
            </div>
            {provenance.checks.map((check, idx) => (
              <div key={idx} className="check-row-item">
                <div className="check-description-block">
                  <span className="check-name font-mono">{check.name}</span>
                  {check.details && <span className="check-detail-text">{check.details}</span>}
                </div>
                <span className={`check-outcome-tag font-mono outcome-${check.status.toLowerCase()}`}>
                  {check.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="provenance-unrequested-state">
            <p className="provenance-status-text">
              Status: <strong className="font-mono">{provenance.status}</strong>. No cryptographic authenticity manifests or digital signatures were identified in this file.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
