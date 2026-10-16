import type { AnalysisResponse } from '../types/api';

interface FindingsSummaryProps {
  analysis: AnalysisResponse;
}

const displayStatus = (status: string | null | undefined): string => {
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
  if (status === 'completed' || status === 'verified' || status === 'not_found') return 'status-completed';
  if (status === 'failed' || status === 'invalid' || status === 'tampered') return 'status-failed';
  return 'status-pending';
};

export const FindingsSummary: React.FC<FindingsSummaryProps> = ({ analysis }) => {
  const checks = [
    { id: 'visual-assessment', label: 'Visual assessment', status: analysis.ai_detection?.status },
    { id: 'ai-generation', label: 'AI-generation detection', status: analysis.external_ai_detection?.status },
    { id: 'deepfake', label: 'Deepfake detection', status: analysis.deepfake_detection?.status },
    { id: 'metadata', label: 'Metadata inspection', status: analysis.metadata_forensics?.status },
    { id: 'provenance', label: 'Provenance', status: analysis.provenance?.status },
    { id: 'ela-analysis', label: 'ELA / compression', status: analysis.spatial_anomaly_map?.status },
  ];

  return (
    <section className="findings-summary" aria-labelledby="findings-summary-title">
      <div className="findings-summary-lead">
        <span className="summary-eyebrow font-mono">INVESTIGATION SUMMARY</span>
        <h2 id="findings-summary-title">What the analysis returned</h2>
        <p>{analysis.trace_alert.message}</p>
        <p className="summary-operational-note">
          Analysis status: <strong>{displayStatus(analysis.status)}</strong>. Processing status is not a conclusion about image authenticity.
        </p>
      </div>
      <ul className="summary-checks" aria-label="Analysis check statuses">
        {checks.map(({ id, label, status }) => (
          <li key={label}>
            <a
              href={`#${id}`}
              className={`summary-check ${statusClass(status)}`}
              aria-label={`View ${label} evidence. Status: ${displayStatus(status)}.`}
            >
              <span className="summary-check-label">{label}</span>
              <span className="summary-check-status font-mono">{displayStatus(status)}</span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
};
