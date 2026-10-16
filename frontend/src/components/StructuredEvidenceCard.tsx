import React, { useState } from 'react';
import type { EvidenceItem } from '../types/api';

interface StructuredEvidenceCardProps {
  evidenceItems?: EvidenceItem[];
}

export const StructuredEvidenceCard: React.FC<StructuredEvidenceCardProps> = ({ evidenceItems }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});

  if (!evidenceItems || evidenceItems.length === 0) {
    return null;
  }

  const categories = [
    { id: 'all', label: 'All Evidence' },
    { id: 'ai_generation', label: 'AI Synthesis' },
    { id: 'deepfake', label: 'Deepfake' },
    { id: 'metadata', label: 'Metadata' },
    { id: 'compression_analysis', label: 'Compression / ELA' },
    { id: 'provenance', label: 'Provenance' },
    { id: 'visual_assessment', label: 'Vision Model' },
  ];

  const filteredItems = selectedCategory === 'all'
    ? evidenceItems
    : evidenceItems.filter(item => item.category === selectedCategory);

  const toggleDetails = (id: string) => {
    setExpandedDetails(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const formatStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'completed' || s === 'verified') {
      return { label: 'COMPLETED', badgeClass: 'badge--notice' };
    } else if (s === 'failed' || s === 'invalid' || s === 'tampered') {
      return { label: s.toUpperCase(), badgeClass: 'badge--caution' };
    } else if (s === 'disabled') {
      return { label: 'DISABLED', badgeClass: 'badge--inconclusive' };
    } else if (s === 'not_configured') {
      return { label: 'NOT CONFIGURED', badgeClass: 'badge--inconclusive' };
    } else {
      return { label: s.toUpperCase(), badgeClass: 'badge--inconclusive' };
    }
  };

  const getCategoryTitle = (category: string) => {
    switch (category) {
      case 'ai_generation':
        return 'AI-Generation Detection';
      case 'deepfake':
        return 'Deepfake Face Manipulation';
      case 'metadata':
        return 'Container & EXIF Metadata';
      case 'compression_analysis':
        return 'Compression & Error Level Analysis';
      case 'provenance':
        return 'Content Credentials & Provenance';
      case 'visual_assessment':
        return 'Vision Model Assessment';
      default:
        return category.replace(/_/g, ' ').toUpperCase();
    }
  };

  return (
    <div className="editorial-evidence-panel">
      {/* Panel Header */}
      <div className="panel-header-row">
        <div>
          <span className="panel-eyebrow font-mono">EXPLAINABLE EVIDENCE MATRIX</span>
          <h3 className="panel-title">Structured Forensic Observations</h3>
        </div>
        <span className="panel-engine-stamp font-mono">
          {evidenceItems.length} EXHIBITS RECORDED
        </span>
      </div>

      <div className="panel-inner-body">
        <p className="evidence-matrix-lead">
          Every forensic exhibit is structured across four verified boundaries: what was directly measured, its calibrated interpretation, its methodological limitation, and verification status. No unvalidated aggregate probability is computed.
        </p>

        {/* Filter Pills */}
        <div className="evidence-filter-row font-mono" role="tablist" aria-label="Filter evidence by category">
          {categories.map(cat => (
            <button
              key={cat.id}
              type="button"
              className={`evidence-filter-pill ${selectedCategory === cat.id ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat.id)}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Evidence Exhibits List */}
        <div className="evidence-exhibits-stack">
          {filteredItems.map(item => {
            const statusConfig = formatStatusBadge(item.status);
            const isDetailsOpen = Boolean(expandedDetails[item.id]);

            return (
              <div key={item.id} className="evidence-exhibit-card">
                {/* Exhibit Header */}
                <div className="exhibit-header-row">
                  <div className="exhibit-title-wrap">
                    <span className="exhibit-source-tag font-mono">{item.source}</span>
                    <h4 className="exhibit-category-name">{getCategoryTitle(item.category)}</h4>
                  </div>
                  <span className={`editorial-badge font-mono ${statusConfig.badgeClass}`}>
                    {statusConfig.label}
                  </span>
                </div>

                {/* 3-Facet Grid: Observation, Interpretation, Limitation */}
                <div className="exhibit-facets-grid">
                  {/* 1. Observation */}
                  <div className="facet-block facet-observation">
                    <div className="facet-label-row font-mono">
                      <span className="facet-icon">◎</span>
                      <span className="facet-name">OBSERVATION</span>
                      <span className="facet-desc">What was measured</span>
                    </div>
                    <p className="facet-content">{item.observation}</p>
                  </div>

                  {/* 2. Interpretation */}
                  <div className="facet-block facet-interpretation">
                    <div className="facet-label-row font-mono">
                      <span className="facet-icon">✦</span>
                      <span className="facet-name">INTERPRETATION</span>
                      <span className="facet-desc">What this suggests</span>
                    </div>
                    <p className="facet-content">{item.interpretation}</p>
                  </div>

                  {/* 3. Limitation */}
                  <div className="facet-block facet-limitation">
                    <div className="facet-label-row font-mono">
                      <span className="facet-icon">⚠</span>
                      <span className="facet-name">LIMITATION</span>
                      <span className="facet-desc">What remains unproven</span>
                    </div>
                    <p className="facet-content">{item.limitation}</p>
                  </div>
                </div>

                {/* Optional Structured Details Toggle */}
                {item.details && Object.keys(item.details).length > 0 && (
                  <div className="exhibit-details-drawer">
                    <button
                      type="button"
                      className="details-toggle-btn font-mono"
                      onClick={() => toggleDetails(item.id)}
                      aria-expanded={isDetailsOpen}
                    >
                      <span>{isDetailsOpen ? '▾ Hide Exhibit Parameters' : '▸ View Exhibit Parameters'}</span>
                    </button>

                    {isDetailsOpen && (
                      <div className="details-parameters-grid font-mono">
                        {Object.entries(item.details)
                          .filter(([, val]) => val !== null && val !== undefined)
                          .map(([k, v]) => (
                            <div key={k} className="parameter-item">
                              <span className="param-k">{k.replace(/_/g, ' ')}:</span>
                              <span className="param-v">
                                {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                              </span>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer Disclaimer */}
      <div className="panel-footer-disclaimer">
        <span className="disclaimer-title font-mono">EVIDENCE PRINCIPLE:</span>
        <span className="disclaimer-copy">
          Forensic indicators must be interpreted jointly in context. No individual detector score or heuristic anomaly proves authentic capture or malicious synthesis in isolation.
        </span>
      </div>
    </div>
  );
};
