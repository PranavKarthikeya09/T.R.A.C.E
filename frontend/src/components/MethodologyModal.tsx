import React, { useEffect } from 'react';

interface MethodologyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MethodologyModal: React.FC<MethodologyModalProps> = ({ isOpen, onClose }) => {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="editorial-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="methodology-modal-title"
    >
      <div className="editorial-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-top-bar">
          <div className="modal-title-stack">
            <span className="modal-eyebrow font-mono">INVESTIGATIVE STANDARD &amp; GOVERNANCE</span>
            <h2 id="methodology-modal-title" className="modal-title">
              Forensic Principles &amp; Integrity Safeguards
            </h2>
          </div>
          <button
            type="button"
            className="modal-close-trigger font-mono"
            onClick={onClose}
            aria-label="Close methodology modal"
          >
            ✕
          </button>
        </div>

        <div className="modal-scroll-body">
          <div className="modal-prose-section">
            <h3 className="section-subhead">1. Scope of Investigation</h3>
            <p>
              T.R.A.C.E. operates on a foundational forensic axiom: <strong>evidence informs, but automated tools do not issue judicial verdicts</strong>. We do not synthesize distinct analytical indicators into an arbitrary single "authenticity percentage" or issue binary "REAL" / "FAKE" proclamations.
            </p>
          </div>

          <div className="modal-framework-grid">
            <div className="framework-box">
              <span className="framework-tag font-mono">01 // VISION HEURISTIC</span>
              <h4 className="framework-title">Qualitative Model Assessment</h4>
              <p className="framework-desc">
                Vision backbones evaluate rendering coherence, anatomy, perspective consistency, and texture artifacts characteristic of generative models. They provide qualitative visual impressions, not mathematical proof.
              </p>
            </div>

            <div className="framework-box">
              <span className="framework-tag font-mono">02 // COMPRESSION ANOMALY</span>
              <h4 className="framework-title">Error Level Analysis (ELA)</h4>
              <p className="framework-desc">
                ELA measures differences in compression degradation between an input image and a standardized recompressed reference. It identifies compression differentials, but high-contrast edges and complex textures naturally exhibit elevated residuals.
              </p>
            </div>

            <div className="framework-box">
              <span className="framework-tag font-mono">03 // CONTAINER AUDIT</span>
              <h4 className="framework-title">Metadata &amp; EXIF Inspection</h4>
              <p className="framework-desc">
                Container headers may document hardware or editing software signatures. However, metadata is routinely stripped by messaging apps and social media, and can be forged. Absence of EXIF does not indicate forgery.
              </p>
            </div>

            <div className="framework-box">
              <span className="framework-tag font-mono">04 // CRYPTOGRAPHIC ORIGIN</span>
              <h4 className="framework-title">C2PA Content Credentials</h4>
              <p className="framework-desc">
                C2PA manifests can carry signed provenance assertions, but this application does not currently parse manifests or verify signatures. Provenance inspection therefore reports unavailable; missing credentials would not establish tampering.
              </p>
            </div>
          </div>

          <div className="modal-safeguard-callout font-mono">
            <strong>DIRECTIVE:</strong> High-risk determinations (such as legal proceedings, journalistic verification, or fraud investigations) require corroborating chain-of-custody documentation and independent multi-source verification.
          </div>
        </div>

        <div className="modal-bottom-bar">
          <button
            type="button"
            className="btn btn-primary-editorial font-mono"
            onClick={onClose}
          >
            Acknowledge &amp; Return
          </button>
        </div>
      </div>
    </div>
  );
};
