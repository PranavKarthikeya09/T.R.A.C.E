import { useMemo, useState } from 'react';

export type InvestigationCheckId = 'visual_assessment' | 'ai_generation' | 'deepfake' | 'metadata' | 'spatial_analysis' | 'provenance';
type PresetId = 'quick' | 'standard' | 'custom';

interface InvestigationConfigurationProps {
  capabilities: Record<string, string>;
  isLoading: boolean;
  onStart: (checks: InvestigationCheckId[]) => void;
}

const checkOptions: { id: InvestigationCheckId; label: string; description: string; limitation: string }[] = [
  { id: 'visual_assessment', label: 'Visual assessment', description: 'Qualitative assessment from the configured vision model.', limitation: 'A model observation, not a validated forensic verdict.' },
  { id: 'ai_generation', label: 'AI-generation detection', description: 'Sightengine analysis for statistical image-generation signals.', limitation: 'Does not identify a specific creator or prove image origin.' },
  { id: 'deepfake', label: 'Deepfake detection', description: 'Sightengine analysis for facial manipulation signals.', limitation: 'Distinct from whole-image AI-generation detection.' },
  { id: 'metadata', label: 'Image metadata', description: 'Reads available EXIF and container properties.', limitation: 'Missing metadata is not evidence of manipulation.' },
  { id: 'spatial_analysis', label: 'Spatial analysis (ELA)', description: 'Creates an exploratory compression-difference map.', limitation: 'Residual patterns are not a tamper mask or proof.' },
  { id: 'provenance', label: 'C2PA / content provenance', description: 'Requests the server provenance adapter.', limitation: 'This build has no C2PA manifest parser or cryptographic signature verifier.' },
];

const alwaysAvailable = new Set(['metadata', 'spatial_analysis']);

export function InvestigationConfiguration({ capabilities, isLoading, onStart }: InvestigationConfigurationProps) {
  const [preset, setPreset] = useState<PresetId>('quick');
  const [selected, setSelected] = useState<Set<InvestigationCheckId>>(() => new Set(['metadata']));
  const availableStandard = useMemo(() => checkOptions
    .filter((option) => option.id !== 'provenance' && (alwaysAvailable.has(option.id) || capabilities[option.id] === 'available'))
    .map((option) => option.id), [capabilities]);
  const availableQuick = useMemo(() => [
    'metadata' as const,
    ...(capabilities.visual_assessment === 'available' ? ['visual_assessment' as const] : []),
  ], [capabilities]);

  const applyPreset = (nextPreset: PresetId) => {
    setPreset(nextPreset);
    if (nextPreset === 'quick') setSelected(new Set(availableQuick));
    if (nextPreset === 'standard') setSelected(new Set(availableStandard));
  };

  const toggle = (id: InvestigationCheckId) => {
    setPreset('custom');
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const statusLabel = (id: InvestigationCheckId) => {
    const status = capabilities[id];
    if (alwaysAvailable.has(id)) return 'AVAILABLE';
    if (status === 'available') return 'AVAILABLE';
    if (status === 'disabled') return 'SERVER DISABLED';
    if (status === 'unavailable') return 'UNAVAILABLE';
    if (status === 'not_configured') return 'NOT CONFIGURED';
    return 'STATUS UNKNOWN';
  };

  return (
    <section className="investigation-config" aria-labelledby="investigation-config-title">
      <div className="investigation-config-heading">
        <span className="section-kicker font-mono">02 / CONFIGURE</span>
        <h3 id="investigation-config-title">Choose the examination scope</h3>
        <p>Select the checks to request. Provider-dependent checks may return not configured or unavailable.</p>
      </div>
      <fieldset className="investigation-presets" disabled={isLoading}>
        <legend className="font-mono">STARTING POINT</legend>
        <label><input type="radio" name="investigation-preset" checked={preset === 'quick'} onChange={() => applyPreset('quick')} /> Quick check</label>
        <label><input type="radio" name="investigation-preset" checked={preset === 'standard'} onChange={() => applyPreset('standard')} /> Standard examination</label>
        <label><input type="radio" name="investigation-preset" checked={preset === 'custom'} onChange={() => setPreset('custom')} /> Custom investigation</label>
      </fieldset>
      <div className="investigation-check-list">
        {checkOptions.map((option) => (
          <label className="investigation-check-option" key={option.id}>
            <input type="checkbox" checked={selected.has(option.id)} onChange={() => toggle(option.id)} disabled={isLoading} />
            <span className="investigation-check-copy">
              <span className="investigation-check-title">{option.label}<span className="investigation-availability font-mono">{statusLabel(option.id)}</span></span>
              <span>{option.description}</span>
              <small>{option.limitation}</small>
            </span>
          </label>
        ))}
      </div>
      <p className="investigation-scope-preview font-mono" aria-live="polite">
        REQUESTED: {selected.size ? checkOptions.filter((check) => selected.has(check.id)).map((check) => check.label).join(' · ') : 'SELECT AT LEAST ONE CHECK'}
      </p>
      <button type="button" className="btn btn-primary-editorial font-mono investigation-start" onClick={() => onStart(checkOptions.filter((check) => selected.has(check.id)).map((check) => check.id))} disabled={isLoading || selected.size === 0}>
        {isLoading ? 'Executing examination…' : 'Run selected checks'}
      </button>
    </section>
  );
}
