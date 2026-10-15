import React, { useState, useRef } from 'react';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];
const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

interface ImageUploaderProps {
  selectedFile: File | null;
  onFileSelect: (file: File) => void;
  onFileRemove: () => void;
  onAnalyze: (includeProvenance: boolean) => void;
  isLoading: boolean;
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  selectedFile,
  onFileSelect,
  onFileRemove,
  onAnalyze,
  isLoading,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [includeProvenance, setIncludeProvenance] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndHandleFile = (file: File) => {
    setValidationError(null);

    // Check file size
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setValidationError(`File exceeds 10 MB ceiling (${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
      return;
    }

    // Check extension and mime
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const isExtensionAllowed = ALLOWED_EXTENSIONS.includes(ext);
    const isMimeAllowed = ALLOWED_MIME_TYPES.includes(file.type);

    if (!isExtensionAllowed && !isMimeAllowed) {
      setValidationError('Unsupported format. Submit JPEG, PNG, or WebP.');
      return;
    }

    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isLoading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (isLoading) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndHandleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndHandleFile(e.target.files[0]);
    }
  };

  const handleTriggerBrowse = () => {
    if (!isLoading && fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="upload-intake-panel">
      <div className="panel-header-compact">
        <span className="panel-eyebrow">EVIDENCE INTAKE</span>
        <h2 className="panel-title">Media Verification</h2>
      </div>

      {validationError && (
        <div className="forensic-notice notice-error" role="alert">
          <span className="notice-icon" aria-hidden="true">✕</span>
          <span className="notice-text">{validationError}</span>
        </div>
      )}

      {!selectedFile ? (
        <div
          className={`intake-dropzone ${isDragging ? 'dropzone-active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleTriggerBrowse}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleTriggerBrowse();
            }
          }}
          aria-label="Upload evidence image. Drag and drop file here or click to browse."
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
            style={{ display: 'none' }}
          />

          <div className="dropzone-target-crosshair" aria-hidden="true">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              <circle cx="12" cy="12" r="9" strokeWidth="1" strokeDasharray="2 2" />
            </svg>
          </div>

          <div className="dropzone-instructions">
            <span className="dropzone-primary-action">Select evidence image</span>
            <span className="dropzone-secondary-text">or drag and drop file into intake area</span>
          </div>

          <div className="dropzone-specs">
            <span className="spec-tag">JPEG</span>
            <span className="spec-tag">PNG</span>
            <span className="spec-tag">WEBP</span>
            <span className="spec-divider">•</span>
            <span className="spec-tag">MAX 10 MB</span>
          </div>
        </div>
      ) : (
        <div className="intake-staging-card">
          <div className="staging-split">
            <div className="staging-media-frame">
              <img
                src={URL.createObjectURL(selectedFile)}
                alt="Selected evidence preview"
                className="staging-media-img"
              />
            </div>

            <div className="staging-meta-dossier">
              <div className="dossier-entry">
                <span className="dossier-label">FILENAME</span>
                <span className="dossier-value font-mono" title={selectedFile.name}>
                  {selectedFile.name}
                </span>
              </div>

              <div className="dossier-row-dual">
                <div className="dossier-entry">
                  <span className="dossier-label">FILE SIZE</span>
                  <span className="dossier-value font-mono">{formatFileSize(selectedFile.size)}</span>
                </div>
                <div className="dossier-entry">
                  <span className="dossier-label">FORMAT</span>
                  <span className="dossier-value font-mono">
                    {selectedFile.type || selectedFile.name.split('.').pop()?.toUpperCase() || 'UNKNOWN'}
                  </span>
                </div>
              </div>

              <div className="dossier-provenance-option">
                <label className="forensic-checkbox-label">
                  <input
                    type="checkbox"
                    checked={includeProvenance}
                    onChange={(e) => setIncludeProvenance(e.target.checked)}
                    disabled={isLoading}
                    className="forensic-checkbox"
                  />
                  <span className="checkbox-content">
                    <strong className="checkbox-title">Inspect C2PA Content Credentials</strong>
                    <span className="checkbox-desc">
                      Examines embedded provenance manifests for cryptographic signatures.
                    </span>
                  </span>
                </label>
              </div>

              <div className="staging-action-bar">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={onFileRemove}
                  disabled={isLoading}
                >
                  Replace File
                </button>

                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => onAnalyze(includeProvenance)}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <span className="btn-loading-state">
                      <span className="spinner-hairline" aria-hidden="true" />
                      Inspecting Media...
                    </span>
                  ) : (
                    'Run Forensic Inspection'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
