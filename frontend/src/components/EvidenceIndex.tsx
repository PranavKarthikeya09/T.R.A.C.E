import type { AnalysisResponse } from '../types/api';

interface EvidenceIndexProps {
  analysis: AnalysisResponse;
}

const statusLabel = (status: string | null | undefined): string => {
  if (!status) return 'Not returned';

  switch (status) {
    case 'completed': return 'Completed';
    case 'failed': return 'Failed';
    case 'unavailable': return 'Unavailable';
    case 'not_configured': return 'Not configured';
    case 'disabled': return 'Disabled';
    case 'not_requested': return 'Not checked';
    case 'not_found': return 'Completed · none found';
    default: return status.replace(/_/g, ' ');
  }
};

const statusClass = (status: string | null | undefined): string => {
  if (status === 'completed' || status === 'verified' || status === 'not_found') return 'index-status--complete';
  if (status === 'failed' || status === 'invalid' || status === 'tampered') return 'index-status--failed';
  return 'index-status--incomplete';
};

export const EvidenceIndex: React.FC<EvidenceIndexProps> = ({ analysis }) => {
  const entries = [
    { id: 'examination-image', label: 'Source image', description: 'Uploaded image and file details', status: 'available' },
    { id: 'visual-assessment', label: 'Visual assessment', description: 'Qualitative model observations', status: analysis.ai_detection?.status },
    { id: 'ai-generation', label: 'AI-generation detection', description: 'Independent provider check', status: analysis.external_ai_detection?.status },
    { id: 'deepfake', label: 'Deepfake detection', description: 'Face-manipulation check', status: analysis.deepfake_detection?.status },
    { id: 'metadata', label: 'Metadata', description: 'Container and EXIF fields', status: analysis.metadata_forensics?.status },
    { id: 'ela-analysis', label: 'ELA / spatial analysis', description: 'Compression residual visualization', status: analysis.spatial_anomaly_map?.status },
    { id: 'provenance', label: 'Provenance', description: 'Content credentials and signatures', status: analysis.provenance?.status },
    ...(analysis.evidence_items?.length ? [{ id: 'structured-evidence', label: 'Structured evidence', description: `${analysis.evidence_items.length} recorded observation${analysis.evidence_items.length === 1 ? '' : 's'}`, status: 'completed' }] : []),
    { id: 'methodology', label: 'Methodology & limitations', description: 'Scope and interpretive boundaries', status: 'available' },
  ];

  return (
    <nav className="evidence-index" aria-labelledby="evidence-index-title">
      <div className="evidence-index-heading">
        <span className="section-kicker font-mono">RECORD GUIDE / 02</span>
        <h2 id="evidence-index-title">Evidence index</h2>
        <p>Jump to a finding. Status describes whether a check ran; it does not establish authenticity.</p>
      </div>
      <ol className="evidence-index-list">
        {entries.map((entry, index) => (
          <li key={entry.id}>
            <a className="evidence-index-link" href={`#${entry.id}`}>
              <span className="evidence-index-number font-mono">{String(index + 1).padStart(2, '0')}</span>
              <span className="evidence-index-copy">
                <span className="evidence-index-name">{entry.label}</span>
                <span className="evidence-index-description">{entry.description}</span>
              </span>
              <span className={`evidence-index-status font-mono ${statusClass(entry.status)}`}>
                {statusLabel(entry.status)}
              </span>
              <span className="evidence-index-arrow" aria-hidden="true">↗</span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
};
