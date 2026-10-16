interface InvestigationScope {
  selected_checks: string[];
  check_statuses: Record<string, string>;
}

interface InvestigationScopeCardProps {
  scope?: InvestigationScope | null;
}

const labels: Record<string, string> = {
  visual_assessment: 'Visual assessment',
  ai_generation: 'AI-generation detection',
  deepfake: 'Deepfake detection',
  metadata: 'Image metadata',
  spatial_analysis: 'Spatial analysis (ELA)',
  provenance: 'C2PA / content provenance',
};

export function InvestigationScopeCard({ scope }: InvestigationScopeCardProps) {
  if (!scope) return null;
  const entries = Object.entries(scope.check_statuses);
  const selected = new Set(scope.selected_checks);
  const requested = entries.filter(([id]) => selected.has(id));
  const notRequested = entries.filter(([id]) => !selected.has(id));

  return (
    <section className="investigation-scope-card" aria-labelledby="investigation-scope-title">
      <div className="investigation-scope-heading">
        <span className="section-kicker font-mono">EXAMINATION SCOPE</span>
        <h2 id="investigation-scope-title">What was examined</h2>
        <p>Selection records the request; each status below records the backend outcome.</p>
      </div>
      <div className="investigation-scope-columns">
        <div>
          <h3 className="font-mono">SELECTED</h3>
          {requested.length ? <ul>{requested.map(([id, status]) => <li key={id}><span>{labels[id] ?? id}</span><span className="scope-status font-mono">{status.replace(/_/g, ' ')}</span></li>)}</ul> : <p>No checks recorded.</p>}
        </div>
        <div>
          <h3 className="font-mono">NOT PERFORMED</h3>
          {notRequested.length ? <ul>{notRequested.map(([id]) => <li key={id}><span>{labels[id] ?? id}</span><span className="scope-status font-mono">NOT REQUESTED</span></li>)}</ul> : <p>All listed checks were selected.</p>}
        </div>
      </div>
    </section>
  );
}
