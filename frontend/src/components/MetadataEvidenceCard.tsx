import React from 'react';
import type { MetadataForensicsResult } from '../types/api';

interface MetadataEvidenceCardProps {
  metadata?: MetadataForensicsResult | null;
  requested?: boolean;
}

export const MetadataEvidenceCard: React.FC<MetadataEvidenceCardProps> = ({ metadata, requested = true }) => {
  if (!metadata) {
    return (
      <div className="editorial-evidence-panel">
        <div className="panel-header-row">
          <div>
            <span className="panel-eyebrow font-mono">CONTAINER &amp; EXIF HEADERS</span>
            <h3 className="panel-title">Embedded Metadata Audit</h3>
          </div>
          <span className="editorial-badge font-mono badge--inconclusive">
            {requested ? 'UNAVAILABLE' : 'NOT REQUESTED'}
          </span>
        </div>
        <div className="panel-empty-message font-mono">
          {requested ? 'Container header inspection was selected but no result was returned.' : 'Container header inspection was not selected for this examination.'}
        </div>
      </div>
    );
  }

  const isFailed = metadata.status === 'failed';
  const isUnavailable = metadata.status !== 'completed' && !isFailed;
  const cameraDevice = [metadata.camera_make, metadata.camera_model].filter(Boolean).join(' ') || null;

  return (
    <div className="editorial-evidence-panel">
      {/* Header */}
      <div className="panel-header-row">
        <div>
          <span className="panel-eyebrow font-mono">CONTAINER &amp; EXIF HEADERS</span>
          <h3 className="panel-title">Embedded Metadata Audit</h3>
        </div>

        <div className="panel-badge-group">
          {isFailed ? (
            <span className="editorial-badge font-mono badge--caution">
              PARSING FAILED
            </span>
          ) : isUnavailable ? (
            <span className="editorial-badge font-mono badge--inconclusive">
              {metadata.status.replace(/_/g, ' ').toUpperCase()}
            </span>
          ) : metadata.has_exif ? (
            <span className="editorial-badge font-mono badge--notice">
              EXIF HEADERS PRESENT
            </span>
          ) : (
            <span className="editorial-badge font-mono badge--inconclusive">
              NO EXIF HEADERS
            </span>
          )}
        </div>
      </div>

      {metadata.status === 'completed' ? (
      <>
      {/* Structured Metadata Grid */}
      <div className="editorial-table-grid font-mono">
        <div className="grid-meta-cell">
          <span className="meta-k">CAPTURE DEVICE</span>
          <span className="meta-v">{cameraDevice || 'None recorded'}</span>
          <span className="meta-hint">
            {cameraDevice ? 'Hardware identifiers embedded in container' : 'Device provenance tag absent'}
          </span>
        </div>

        <div className="grid-meta-cell">
          <span className="meta-k">RECORDED TIMESTAMP</span>
          <span className="meta-v">{metadata.capture_time || 'Not specified'}</span>
          <span className="meta-hint">
            {metadata.capture_time ? 'Timestamp present in extracted fields' : 'No timestamp present in extracted fields'}
          </span>
        </div>

        <div className="grid-meta-cell">
          <span className="meta-k">SOFTWARE SIGNATURE</span>
          <span className="meta-v text-truncate" title={metadata.software || undefined}>
            {metadata.software || 'None detected'}
          </span>
          <span className="meta-hint">
            {metadata.software ? 'Software value present in extracted fields' : 'No software value present in extracted fields'}
          </span>
        </div>

        <div className="grid-meta-cell">
          <span className="meta-k">LENS PROFILE</span>
          <span className="meta-v text-truncate" title={metadata.lens_model || undefined}>
            {metadata.lens_model || 'Not recorded'}
          </span>
          <span className="meta-hint">Optical lens identifier</span>
        </div>

        <div className="grid-meta-cell">
          <span className="meta-k">ORIENTATION</span>
          <span className="meta-v">
            {metadata.orientation_description || (metadata.orientation ? `Tag ${metadata.orientation}` : 'Default (Normal)')}
          </span>
          <span className="meta-hint">Display transformation flag</span>
        </div>

        <div className="grid-meta-cell">
          <span className="meta-k">DISCOVERED TAGS</span>
          <span className="meta-v">
            {metadata.identifiable_fields.length > 0
              ? `${metadata.identifiable_fields.length} header fields discovered`
              : 'Zero header tags'}
          </span>
          <span className="meta-hint">Container header keys</span>
        </div>
      </div>
      </>
      ) : (
        <div className="panel-empty-message font-mono" role="status">
          Metadata inspection {metadata.status.replace(/_/g, ' ')}. Field values are not available for this check.
        </div>
      )}

      {metadata.status === 'completed' && <>
      {/* Noteworthy Software / Generative Markers */}
      <div className="editorial-markers-strip">
        <span className="markers-label font-mono">FORENSIC CONTEXT &amp; NOTABLE SOFTWARE MARKERS</span>
        {metadata.noteworthy_markers && metadata.noteworthy_markers.length > 0 ? (
          <div className="markers-list font-mono">
            {metadata.noteworthy_markers.map((marker, idx) => (
              <div key={idx} className="marker-row">
                <span className="marker-arrow" aria-hidden="true">▸</span>
                <span className="marker-content">{marker}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="markers-empty font-mono">
            No distinctive editing signatures or generative software markers flagged in container headers.
          </div>
        )}
      </div>
      </>}

      {/* Error Notice */}
      {isFailed && metadata.error && (
        <div className="editorial-error-strip font-mono">
          <strong>EXTRACTION ERROR:</strong> {metadata.error}
        </div>
      )}

      {/* Disclaimer */}
      <div className="panel-footer-disclaimer">
        <span className="disclaimer-title font-mono">METADATA CAVEAT:</span>
        <span className="disclaimer-copy">
          {metadata.disclaimer ||
            'Container headers and EXIF fields are routinely stripped by social platforms and messaging pipelines, and can be forged. The absence or presence of metadata does not constitute absolute proof of authenticity or manipulation.'}
        </span>
      </div>
    </div>
  );
};
