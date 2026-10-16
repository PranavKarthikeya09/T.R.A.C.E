import React, { useState, useRef } from 'react';
import { InvestigationConfiguration, type InvestigationCheckId } from './InvestigationConfiguration';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];
const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

interface ImageUploaderProps {
  selectedFile: File | null;
  previewUrl: string | null;
  imageDimensions: { width: number; height: number } | null;
  onFileSelect: (file: File) => void;
  onFileRemove: () => void;
  onAnalyze: (checks: InvestigationCheckId[]) => void;
  isLoading: boolean;
  capabilities: Record<string, string>;
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  selectedFile,
  previewUrl,
  imageDimensions,
  onFileSelect,
  onFileRemove,
  onAnalyze,
  isLoading,
  capabilities,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndHandleFile = (file: File) => {
    setValidationError(null);
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setValidationError(`File exceeds 10 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
      return;
    }
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const isExtensionAllowed = ALLOWED_EXTENSIONS.includes(ext);
    const isMimeAllowed = ALLOWED_MIME_TYPES.includes(file.type);
    if (!isExtensionAllowed && !isMimeAllowed) {
      setValidationError('Unsupported format. Please submit JPEG, PNG, or WebP.');
      return;
    }
    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isLoading) setIsDragging(true);
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
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="editorial-intake-card">
      {validationError && (
        <div className="intake-notice notice-error font-mono" role="alert">
          <span className="notice-icon" aria-hidden="true">✕</span>
          <span className="notice-text">{validationError}</span>
        </div>
      )}

      {!selectedFile ? (
        <div
          className={`intake-dropzone-stage ${isDragging ? 'is-dragging' : ''}`}
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
          aria-label="Submit an image for forensic examination. Click or drag a file here."
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
            style={{ display: 'none' }}
          />

          <div className="dropzone-center-content">
            <div className="dropzone-symbol" aria-hidden="true">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14m7-7H5" />
              </svg>
            </div>
            <div className="dropzone-headline-group">
              <span className="dropzone-callout">Select an image for forensic examination</span>
              <span className="dropzone-subcallout">or drag and drop file into this examination zone</span>
            </div>
            <div className="dropzone-spec-chips font-mono">
              <span className="spec-chip">JPEG</span>
              <span className="spec-chip">PNG</span>
              <span className="spec-chip">WebP</span>
              <span className="spec-chip-rule">|</span>
              <span className="spec-chip">Max 10 MB</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="intake-staged-stage">
          <div className="staged-preview-cell">
            <img
              src={previewUrl ?? ''}
              alt="Intake evidence thumbnail"
              className="staged-thumbnail-img"
            />
          </div>

          <div className="staged-info-cell">
            <div className="staged-meta-grid font-mono">
              <div className="staged-meta-item">
                <span className="staged-meta-k">FILE NAME</span>
                <span className="staged-meta-v text-truncate" title={selectedFile.name}>
                  {selectedFile.name}
                </span>
              </div>
              <div className="staged-meta-item">
                <span className="staged-meta-k">FILE SIZE</span>
                <span className="staged-meta-v">{formatFileSize(selectedFile.size)}</span>
              </div>
              <div className="staged-meta-item">
                <span className="staged-meta-k">FORMAT</span>
                <span className="staged-meta-v">
                  {selectedFile.type || selectedFile.name.split('.').pop()?.toUpperCase() || 'Unknown'}
                </span>
              </div>
              <div className="staged-meta-item">
                <span className="staged-meta-k">DIMENSIONS</span>
                <span className="staged-meta-v">
                  {imageDimensions ? `${imageDimensions.width} × ${imageDimensions.height} px` : 'Reading image…'}
                </span>
              </div>
            </div>

            <div className="staged-actions-row">
              <button
                type="button"
                className="btn btn-secondary-restrained font-mono"
                onClick={onFileRemove}
                disabled={isLoading}
              >
                Remove File
              </button>
            </div>
          </div>
        </div>
      )}
      {selectedFile && <InvestigationConfiguration capabilities={capabilities} isLoading={isLoading} onStart={onAnalyze} />}
    </div>
  );
};
