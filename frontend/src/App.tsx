import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ImageUploader } from './components/ImageUploader';
import { AlertBanner } from './components/AlertBanner';
import { AnalysisResults } from './components/AnalysisResults';
import { ProvenanceCard } from './components/ProvenanceCard';
import { LimitationsCard } from './components/LimitationsCard';
import { AnalysisMetadata } from './components/AnalysisMetadata';
import { ApiService } from './services/api';
import type { AnalysisResponse } from './types/api';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);

  // Probe backend health on startup and periodically
  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        const health = await ApiService.checkHealth();
        if (isMounted) {
          setIsBackendHealthy(health.status === 'ok');
        }
      } catch {
        if (isMounted) {
          setIsBackendHealthy(false);
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setErrorMessage(null);
  };

  const handleFileRemove = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setErrorMessage(null);
  };

  const handleAnalyze = async (includeProvenance: boolean) => {
    if (!selectedFile) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await ApiService.analyzeImage(selectedFile, includeProvenance);
      setAnalysisResult(response);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'An unexpected error occurred during inspection.';
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setAnalysisResult(null);
    setErrorMessage(null);
  };

  return (
    <div className="trace-app-container">
      <Header isBackendHealthy={isBackendHealthy} />

      <main className="trace-main-workspace">
        {errorMessage && (
          <div className="forensic-notice notice-error" role="alert">
            <div className="notice-icon-box">✕</div>
            <div className="notice-body">
              <strong className="notice-heading">Inspection Failed</strong>
              <p className="notice-detail">{errorMessage}</p>
            </div>
            <button
              type="button"
              className="btn-notice-dismiss"
              onClick={() => setErrorMessage(null)}
              aria-label="Dismiss error notice"
            >
              ×
            </button>
          </div>
        )}

        {!analysisResult ? (
          <section className="intake-workspace-section" aria-label="Evidence Intake">
            <ImageUploader
              selectedFile={selectedFile}
              onFileSelect={handleFileSelect}
              onFileRemove={handleFileRemove}
              onAnalyze={handleAnalyze}
              isLoading={isLoading}
            />
          </section>
        ) : (
          <section className="dossier-report-section" aria-label="Forensic Investigation Report">
            {/* Report Top Command Bar */}
            <div className="report-command-bar">
              <button
                type="button"
                className="btn btn-secondary-compact font-mono"
                onClick={handleReset}
              >
                ← INTAKE NEW EVIDENCE
              </button>
              <div className="report-reference-stamp font-mono">
                <span className="stamp-label">CASE:</span>
                <span className="stamp-ref">{analysisResult.analysis_id.substring(0, 12)}</span>
                <span className="stamp-divider">|</span>
                <span className="stamp-file text-truncate" title={analysisResult.media.filename}>
                  {analysisResult.media.filename}
                </span>
              </div>
            </div>

            {/* Structured Report Layout */}
            <div className="dossier-grid-layout">
              {/* Evidence Asset Column */}
              <aside className="dossier-evidence-column">
                <div className="evidence-panel">
                  <div className="evidence-panel-header">
                    <span className="evidence-header-label">EXHIBIT A // SUBMITTED MEDIA</span>
                  </div>

                  <div className="evidence-viewer-frame">
                    {previewUrl ? (
                      <img
                        src={previewUrl}
                        alt="Submitted evidence asset"
                        className="evidence-img"
                      />
                    ) : (
                      <div className="evidence-placeholder">Image preview unavailable</div>
                    )}
                  </div>

                  <div className="evidence-manifest-table font-mono">
                    <div className="manifest-row">
                      <span className="manifest-key">ASSET NAME</span>
                      <span className="manifest-val text-truncate" title={analysisResult.media.filename}>
                        {analysisResult.media.filename}
                      </span>
                    </div>
                    <div className="manifest-row">
                      <span className="manifest-key">MEDIA TYPE</span>
                      <span className="manifest-val">{analysisResult.media.type.toUpperCase()}</span>
                    </div>
                    <div className="manifest-row">
                      <span className="manifest-key">PROVENANCE</span>
                      <span className="manifest-val">{analysisResult.provenance.status.toUpperCase()}</span>
                    </div>
                    <div className="manifest-row">
                      <span className="manifest-key">ANALYSIS TIME</span>
                      <span className="manifest-val">
                        {new Date(analysisResult.created_at).toISOString().substring(11, 19)} UTC
                      </span>
                    </div>
                  </div>
                </div>
              </aside>

              {/* Findings & Evaluation Column */}
              <div className="dossier-findings-column">
                {/* 1. Primary Forensic Alert */}
                <div className="dossier-block">
                  <AlertBanner alert={analysisResult.trace_alert} />
                </div>

                {/* 2. Qualitative Model Assessment */}
                <div className="dossier-block">
                  <AnalysisResults detection={analysisResult.ai_detection} />
                </div>

                {/* 3. Provenance & Limitations Dual Grid */}
                <div className="dossier-dual-row">
                  <ProvenanceCard provenance={analysisResult.provenance} />
                  <LimitationsCard limitations={analysisResult.limitations} />
                </div>

                {/* 4. Traceability & Metadata Grid */}
                <div className="dossier-block">
                  <AnalysisMetadata
                    detection={analysisResult.ai_detection}
                    media={analysisResult.media}
                    analysisId={analysisResult.analysis_id}
                    createdAt={analysisResult.created_at}
                  />
                </div>
              </div>
            </div>
          </section>
        )}
      </main>

      <footer className="trace-footer">
        <div className="footer-inner">
          <div className="footer-brand-line font-mono">
            <strong>T.R.A.C.E.</strong> // TAMPERING RECOGNITION, AUTHENTICATION &amp; CONTENT EVIDENCE
          </div>
          <p className="footer-disclaimer-text">
            Digital media forensics inspection workstation. Qualitative assessments and heuristic indicators represent algorithmic estimates and do not constitute certified legal chain-of-custody evidence.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
