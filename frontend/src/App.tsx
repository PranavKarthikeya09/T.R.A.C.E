import { useEffect, useRef, useState } from 'react';
import { Header } from './components/Header';
import { ImageUploader } from './components/ImageUploader';
import { AlertBanner } from './components/AlertBanner';
import { AnalysisResults } from './components/AnalysisResults';
import { ProvenanceCard } from './components/ProvenanceCard';
import { LimitationsCard } from './components/LimitationsCard';
import { AnalysisMetadata } from './components/AnalysisMetadata';
import { ForensicImageViewer } from './components/ForensicImageViewer';
import { MetadataEvidenceCard } from './components/MetadataEvidenceCard';
import { SightengineCard } from './components/SightengineCard';
import { DeepfakeCard } from './components/DeepfakeCard';
import { StructuredEvidenceCard } from './components/StructuredEvidenceCard';
import { MethodologyModal } from './components/MethodologyModal';
import { WorkflowRail } from './components/WorkflowRail';
import { FindingsSummary } from './components/FindingsSummary';
import { EvidenceIndex } from './components/EvidenceIndex';
import { InvestigationScopeCard } from './components/InvestigationScopeCard';
import type { InvestigationCheckId } from './components/InvestigationConfiguration';
import { ApiService } from './services/api';
import type { AnalysisResponse } from './types/api';
import './App.css';

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number } | null>(null);
  const previewUrlRef = useRef<string | null>(null);
  const reportRef = useRef<HTMLElement | null>(null);
  const reportHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [capabilities, setCapabilities] = useState<Record<string, string>>({});
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);

  const replacePreviewUrl = (nextUrl: string | null) => {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = nextUrl;
    setPreviewUrl(nextUrl);
  };

  useEffect(() => () => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        const health = await ApiService.checkHealth();
        if (isMounted) {
          setIsBackendHealthy(health.status === 'healthy' || health.status === 'ok');
          setCapabilities(health.capabilities ?? {});
        }
      } catch {
        if (isMounted) setIsBackendHealthy(false);
      }
    };

    void checkHealth();
    const interval = window.setInterval(() => void checkHealth(), 30000);
    return () => {
      isMounted = false;
      window.clearInterval(interval);
    };
  }, []);

  // The report only exists after state changes. Scroll and focus after React has committed it.
  useEffect(() => {
    if (!analysisResult) return;

    const frame = window.requestAnimationFrame(() => {
      reportRef.current?.scrollIntoView({
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
        block: 'start',
      });
      reportHeadingRef.current?.focus({ preventScroll: true });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [analysisResult]);

  const handleFileSelect = (file: File) => {
    const nextPreviewUrl = URL.createObjectURL(file);
    replacePreviewUrl(nextPreviewUrl);
    setSelectedFile(file);
    setImageDimensions(null);
    setErrorMessage(null);
    setAnalysisResult(null);

    const image = new Image();
    image.onload = () => {
      if (previewUrlRef.current === nextPreviewUrl) {
        setImageDimensions({ width: image.naturalWidth, height: image.naturalHeight });
      }
    };
    image.src = nextPreviewUrl;
  };

  const handleFileRemove = () => {
    replacePreviewUrl(null);
    setSelectedFile(null);
    setImageDimensions(null);
    setAnalysisResult(null);
    setErrorMessage(null);
  };

  const handleAnalyze = async (selectedChecks: InvestigationCheckId[]) => {
    if (!selectedFile || isLoading) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await ApiService.analyzeImage(selectedFile, selectedChecks);
      if (response.status !== 'completed' && response.status !== 'partial') {
        throw new Error(`The analysis service returned status “${response.status}”. Review the service status and retry.`);
      }
      setAnalysisResult(response);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'An unexpected error occurred during analysis.';
      setErrorMessage(`${message} Your selected image is still available, so you can retry or choose another file.`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    replacePreviewUrl(null);
    setSelectedFile(null);
    setImageDimensions(null);
    setAnalysisResult(null);
    setErrorMessage(null);
  };

  const goToReport = () => {
    reportRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    reportHeadingRef.current?.focus({ preventScroll: true });
  };

  return (
    <div className="trace-app-shell">
      <Header
        isBackendHealthy={isBackendHealthy}
        onOpenMethodology={() => setIsMethodologyOpen(true)}
        onNewInvestigation={handleReset}
        onViewReport={goToReport}
        hasActiveInvestigation={Boolean(analysisResult)}
      />

      <main className="trace-main-content" aria-busy={isLoading}>
        {!analysisResult ? (
          <>
            <WorkflowRail hasFile={Boolean(selectedFile)} isAnalyzing={isLoading} hasResult={false} />
            {errorMessage && (
              <div className="editorial-notice notice-error" role="alert">
                <div className="notice-icon-box font-mono" aria-hidden="true">!</div>
                <div className="notice-body">
                  <strong className="notice-title">Analysis could not be completed</strong>
                  <p className="notice-desc">{errorMessage}</p>
                </div>
              </div>
            )}

            <section className="intake-workspace" aria-labelledby="intake-title">
              <div className="intake-editorial-copy">
                <span className="hero-eyebrow-tag font-mono">
                  <span className="eyebrow-accent-square" aria-hidden="true" />
                  DIGITAL IMAGE INVESTIGATION <span className="hero-note-index">FIELD NOTE 001</span>
                </span>
                <h1 id="intake-title" className="hero-display-headline">
                  The image is<br />not the evidence.<br /><em>What we establish is.</em>
                </h1>
                <p className="hero-subheading-prose">
                  A structured examination of image integrity, AI-generation signals, metadata, and provenance. Each check stands on its own evidence and limitations.
                </p>
                <div className="hero-footnote">
                  <span className="hero-footnote-mark" aria-hidden="true">↳</span>
                  <span>Automated indicators guide closer inspection. They do not establish authenticity on their own.</span>
                </div>
              </div>

              <div className="intake-panel-column">
                <div className="intake-panel-heading">
                  <span className="section-kicker font-mono">01 / INTAKE</span>
                  <span className="intake-panel-title">Select a source image</span>
                </div>
                <ImageUploader
                  selectedFile={selectedFile}
                  previewUrl={previewUrl}
                  imageDimensions={imageDimensions}
                  onFileSelect={handleFileSelect}
                  onFileRemove={handleFileRemove}
                  onAnalyze={handleAnalyze}
                  isLoading={isLoading}
                  capabilities={capabilities}
                />
                <p className="intake-privacy-note">
                  <span className="privacy-rule" aria-hidden="true" />
                  JPEG, PNG, or WebP · maximum 10 MB<br />Submitted to the configured T.R.A.C.E. API for analysis.
                </p>
              </div>
            </section>

            <section className="capability-index" aria-labelledby="capability-title">
              <div className="section-heading-row">
                <div>
                  <span className="section-kicker font-mono">METHOD / 01—04</span>
                  <h2 id="capability-title">Read each signal in its own context.</h2>
                </div>
                <p>The record separates observations from interpretation—and makes unavailable checks visible.</p>
              </div>
              <div className="capability-ledger">
                <article><span className="capability-index-number font-mono">01</span><div><h3>Visual assessment</h3><p>Qualitative cues from the configured vision model, when available. A heuristic is not a validated forensic verdict.</p></div><span className="capability-note font-mono">MODEL OBSERVATION</span></article>
                <article><span className="capability-index-number font-mono">02</span><div><h3>Independent detectors</h3><p>AI-generation and face-swap checks address different signals and remain separate in the report.</p></div><span className="capability-note font-mono">PROVIDER RESULTS</span></article>
                <article><span className="capability-index-number font-mono">03</span><div><h3>Image structure</h3><p>Metadata and compression differences add context. Missing fields or residual patterns do not prove editing.</p></div><span className="capability-note font-mono">FILE OBSERVATIONS</span></article>
                <article><span className="capability-index-number font-mono">04</span><div><h3>Provenance</h3><p>Content credentials are checked only when requested. A signature cannot establish that a scene is truthful.</p></div><span className="capability-note font-mono">OPTIONAL CHECK</span></article>
              </div>
            </section>

            <section className="method-sequence" aria-labelledby="sequence-title">
              <div className="sequence-intro">
                <span className="section-kicker font-mono">A RECORD, NOT A VERDICT</span>
                <h2 id="sequence-title">From source file<br />to documented findings.</h2>
              </div>
              <ol className="sequence-steps">
                <li><span className="sequence-number font-mono">01</span><div><h3>Examine</h3><p>Inspect the source image and the available diagnostics.</p></div></li>
                <li><span className="sequence-number font-mono">02</span><div><h3>Interpret</h3><p>Compare independent outputs with their stated scope.</p></div></li>
                <li><span className="sequence-number font-mono">03</span><div><h3>Document</h3><p>Review the record, its sources, and what remains unknown.</p></div></li>
              </ol>
              <p className="sequence-caveat">No single score combines these checks. An unavailable result is not a negative finding.</p>
            </section>
          </>
        ) : (
          <section
            ref={reportRef}
            id="investigation-report"
            className="editorial-dossier-stage report-destination"
            aria-labelledby="report-title"
          >
            <WorkflowRail hasFile={Boolean(selectedFile)} isAnalyzing={false} hasResult />
            <div className="report-heading-block">
              <span className="section-kicker font-mono">INVESTIGATION RECORD / DOCUMENT</span>
              <div className="report-heading-row">
                <div>
                  <h1 id="report-title" ref={reportHeadingRef} tabIndex={-1} className="report-title">
                    Image examination record
                  </h1>
                  <p className="report-file-name">{analysisResult.media.filename}</p>
                </div>
                <button type="button" className="btn btn-primary-editorial report-new-button" onClick={handleReset}>
                  + New investigation
                </button>
              </div>
              <div className="report-identifiers font-mono">
                <span>RECORD <strong>{analysisResult.analysis_id}</strong></span>
                <span>RECEIVED <strong>{new Date(analysisResult.created_at).toLocaleString(undefined, { timeZone: 'UTC', dateStyle: 'medium', timeStyle: 'short' })} UTC</strong></span>
                <span>STATUS <strong>{analysisResult.status.toUpperCase()}</strong></span>
              </div>
            </div>

            <FindingsSummary analysis={analysisResult} />
            <InvestigationScopeCard scope={analysisResult.investigation_scope} />
            <EvidenceIndex analysis={analysisResult} />

            <div className="dossier-editorial-grid">
              <aside className="dossier-viewer-anchor" aria-label="Image examination">
                <div id="examination-image" className="dossier-section-label">
                  <span className="section-kicker font-mono">01 / EXAMINE</span>
                  <h2>Source image</h2>
                </div>
                <div id="ela-analysis" className="dossier-image-analysis">
                  <ForensicImageViewer
                    previewUrl={previewUrl}
                    spatialMap={analysisResult.spatial_anomaly_map}
                    filename={analysisResult.media.filename}
                    spatialAnalysisRequested={analysisResult.investigation_scope?.selected_checks.includes('spatial_analysis') ?? true}
                  />
                </div>
                <details className="asset-facts-disclosure">
                  <summary className="font-mono">File details <span aria-hidden="true">+</span></summary>
                  <dl className="asset-facts font-mono">
                    <div><dt>FILE NAME</dt><dd title={analysisResult.media.filename}>{analysisResult.media.filename}</dd></div>
                    <div><dt>FORMAT</dt><dd>{selectedFile?.type || analysisResult.media.type.toUpperCase()}</dd></div>
                    {selectedFile && <div><dt>FILE SIZE</dt><dd>{formatFileSize(selectedFile.size)}</dd></div>}
                    {imageDimensions && <div><dt>IMAGE SIZE</dt><dd>{imageDimensions.width} × {imageDimensions.height} px</dd></div>}
                    <div><dt>ANALYSIS STATUS</dt><dd>{analysisResult.status.toUpperCase()}</dd></div>
                  </dl>
                </details>
              </aside>

              <div className="dossier-findings-stack">
                <div id="findings" className="dossier-section-label">
                  <span className="section-kicker font-mono">02 / INTERPRET</span>
                  <h2>Independent findings</h2>
                </div>
                <AlertBanner alert={analysisResult.trace_alert} />
                <section id="visual-assessment" className="dossier-evidence-section" aria-label="Visual assessment">
                  <AnalysisResults detection={analysisResult.ai_detection} />
                </section>
                <section id="ai-generation" className="dossier-evidence-section" aria-label="AI-generation detection">
                  <SightengineCard externalAi={analysisResult.external_ai_detection} requested={analysisResult.investigation_scope?.selected_checks.includes('ai_generation') ?? true} />
                </section>
                <section id="deepfake" className="dossier-evidence-section" aria-label="Deepfake detection">
                  <DeepfakeCard deepfake={analysisResult.deepfake_detection} requested={analysisResult.investigation_scope?.selected_checks.includes('deepfake') ?? true} />
                </section>
                <section id="metadata" className="dossier-evidence-section" aria-label="Metadata findings">
                  <MetadataEvidenceCard metadata={analysisResult.metadata_forensics} requested={analysisResult.investigation_scope?.selected_checks.includes('metadata') ?? true} />
                </section>

                {analysisResult.evidence_items && analysisResult.evidence_items.length > 0 && (
                  <section id="structured-evidence" className="dossier-evidence-section dossier-evidence-section--spaced" aria-label="Structured evidence">
                    <div className="dossier-section-label">
                      <span className="section-kicker font-mono">03 / SUPPORTING EVIDENCE</span>
                      <h2>Observations and context</h2>
                    </div>
                    <StructuredEvidenceCard evidenceItems={analysisResult.evidence_items} />
                  </section>
                )}
                <div className="dossier-split-row">
                  <section id="provenance" className="dossier-evidence-section" aria-label="Provenance findings">
                    <ProvenanceCard provenance={analysisResult.provenance} />
                  </section>
                  <section id="methodology" className="dossier-evidence-section" aria-label="Methodology and limitations">
                    <LimitationsCard limitations={analysisResult.limitations} />
                  </section>
                </div>
                <AnalysisMetadata
                  detection={analysisResult.ai_detection}
                  media={analysisResult.media}
                  analysisId={analysisResult.analysis_id}
                  createdAt={analysisResult.created_at}
                />
              </div>
            </div>
          </section>
        )}
      </main>

      <MethodologyModal isOpen={isMethodologyOpen} onClose={() => setIsMethodologyOpen(false)} />

      <footer className="editorial-footer">
        <div className="footer-content-wrap">
          <div className="footer-brand-title font-mono"><strong>T.R.A.C.E.</strong> / TAMPERING RECOGNITION, AUTHENTICATION &amp; CONTENT EVIDENCE</div>
          <p className="footer-disclaimer-prose">
            Automated forensic indicators are investigative aids. Review their sources, limitations, and context before drawing conclusions.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
