import { useState } from 'react';
import type { SpatialAnomalyMap } from '../types/api';

interface ForensicImageViewerProps {
  previewUrl: string | null;
  spatialMap?: SpatialAnomalyMap | null;
  filename: string;
  spatialAnalysisRequested?: boolean;
}

type ViewMode = 'original' | 'overlay' | 'heatmap';

export const ForensicImageViewer: React.FC<ForensicImageViewerProps> = ({
  previewUrl,
  spatialMap,
  filename,
  spatialAnalysisRequested = true,
}) => {
  const hasHeatmap = Boolean(
    spatialMap &&
    spatialMap.status === 'completed' &&
    spatialMap.heatmap_data_uri
  );

  const [viewMode, setViewMode] = useState<ViewMode>(hasHeatmap ? 'overlay' : 'original');
  const [opacity, setOpacity] = useState<number>(0.65);
  const [useGrayscale, setUseGrayscale] = useState<boolean>(false);

  const activeHeatmapUri = useGrayscale && spatialMap?.grayscale_data_uri
    ? spatialMap.grayscale_data_uri
    : spatialMap?.heatmap_data_uri ?? null;

  const stats = spatialMap?.residual_statistics;

  return (
    <div className="editorial-viewer-panel">
      {/* Viewer Header */}
      <div className="viewer-top-bar">
        <div className="viewer-title-group">
          <span className="viewer-eyebrow font-mono">EXHIBIT A — SPATIAL ANOMALY WORKSPACE</span>
          <span className="viewer-active-view-name">
            {viewMode === 'original' && 'Source Input Media'}
            {viewMode === 'overlay' && 'Blended Residual Overlay'}
            {viewMode === 'heatmap' && (useGrayscale ? 'Grayscale Compression Residuals' : 'Thermal Compression Heatmap')}
          </span>
        </div>

        {/* View mode toggle controls */}
        <div className="viewer-mode-selector" role="group" aria-label="Viewer display mode">
          {(['original', 'overlay', 'heatmap'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              aria-pressed={viewMode === mode}
              aria-label={`Show ${mode === 'heatmap' ? 'ELA heatmap' : mode === 'overlay' ? 'blended ELA overlay' : 'original image'}`}
              disabled={mode !== 'original' && !hasHeatmap}
              className={`viewer-mode-tab font-mono ${viewMode === mode ? 'is-active' : ''}`}
              onClick={() => setViewMode(mode)}
            >
              {mode.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Controls Bar for Overlay and Palette */}
      {hasHeatmap && viewMode !== 'original' && (
        <div className="viewer-toolbar">
          {viewMode === 'overlay' && (
            <div className="toolbar-control-group">
              <label htmlFor="opacity-slider" className="toolbar-label font-mono">
                OVERLAY OPACITY
              </label>
              <input
                id="opacity-slider"
                type="range"
                min="0"
                max="100"
                value={Math.round(opacity * 100)}
                onChange={(e) => setOpacity(Number(e.target.value) / 100)}
                className="editorial-range-slider"
              />
              <span className="toolbar-val font-mono">{Math.round(opacity * 100)}%</span>
            </div>
          )}

          <div className="toolbar-control-group">
            <span className="toolbar-label font-mono">COLORMAP</span>
            <div className="toolbar-btn-pair font-mono">
              <button
                type="button"
                className={`toolbar-btn ${!useGrayscale ? 'is-active' : ''}`}
                onClick={() => setUseGrayscale(false)}
              >
                Thermal
              </button>
              <button
                type="button"
                className={`toolbar-btn ${useGrayscale ? 'is-active' : ''}`}
                onClick={() => setUseGrayscale(true)}
                disabled={!spatialMap?.grayscale_data_uri}
              >
                Grayscale
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Technical Forensic Canvas Stage — Dark stage exception strictly confined to image view */}
      <div className="viewer-canvas-stage">
        {!previewUrl ? (
          <div className="canvas-empty-state font-mono">Image preview unavailable</div>
        ) : (
          <div className="canvas-viewport">
            <img
              src={previewUrl}
              alt={`Source media exhibit: ${filename}`}
              className={`canvas-layer-base ${viewMode === 'heatmap' ? 'is-hidden' : ''}`}
            />
            {hasHeatmap && activeHeatmapUri && viewMode !== 'original' && (
              <img
                src={activeHeatmapUri}
                alt={useGrayscale ? 'Grayscale ELA residual map' : 'Thermal ELA heatmap'}
                className="canvas-layer-overlay"
                style={{ opacity: viewMode === 'overlay' ? opacity : 1.0 }}
              />
            )}
          </div>
        )}

        {!hasHeatmap && (
          <div className="canvas-unavailable-notice font-mono">
            {spatialMap?.status && spatialMap.status !== 'completed'
              ? `Error Level Analysis ${spatialMap.status.replace(/_/g, ' ')}`
              : spatialMap ? 'Error Level Analysis map not available' : spatialAnalysisRequested ? 'Error Level Analysis result not returned' : 'Spatial analysis was not requested'}
          </div>
        )}
      </div>

      {!hasHeatmap && spatialMap?.error && (
        <details className="viewer-technical-disclosure">
          <summary>View ELA processing details</summary>
          <p>{spatialMap.error}</p>
        </details>
      )}

      {/* Downsampling notice */}
      {spatialMap?.is_downsampled && (
        <div className="viewer-info-banner font-mono">
          <span className="info-banner-badge">DOWNSAMPLED</span>
          <span className="info-banner-text">
            Map: {spatialMap.visualization_width}×{spatialMap.visualization_height} px; source: {spatialMap.input_width}×{spatialMap.input_height} px.
          </span>
        </div>
      )}

      {/* Residual statistics table */}
      {hasHeatmap && stats && (
        <details className="viewer-technical-disclosure">
          <summary>Technical measurements</summary>
          <div className="viewer-stats-table font-mono">
            <div className="stat-cell">
              <span className="stat-label">ALGORITHM</span>
              <span className="stat-value">Error Level Analysis</span>
            </div>
            <div className="stat-cell">
              <span className="stat-label">REF. QUALITY</span>
              <span className="stat-value">Q = {spatialMap.jpeg_quality}</span>
            </div>
            <div className="stat-cell">
              <span className="stat-label">MEAN RESIDUAL</span>
              <span className="stat-value">{stats.mean_residual?.toFixed(2) ?? 'N/A'} / 255</span>
            </div>
            <div className="stat-cell">
              <span className="stat-label">MAX RESIDUAL</span>
              <span className="stat-value">{stats.max_residual?.toFixed(1) ?? 'N/A'} / 255</span>
            </div>
            <div className="stat-cell">
              <span className="stat-label">STD DEVIATION</span>
              <span className="stat-value">{stats.std_residual?.toFixed(2) ?? 'N/A'}</span>
            </div>
            <div className="stat-cell">
              <span className="stat-label">NORMALIZATION</span>
              <span className="stat-value">{spatialMap.scale_factor?.toFixed(1) ?? '1.0'}× ({spatialMap.normalization_method})</span>
            </div>
          </div>
        </details>
      )}

      {/* Keep the key limitation visible; disclose the longer method note progressively. */}
      <div className="viewer-footer-disclaimer">
        <span className="disclaimer-title font-mono">ELA LIMITATION</span>
        <span className="disclaimer-copy">
          Compression differences can occur naturally. This visualization does not prove manipulation.
        </span>
      </div>
      <details className="viewer-technical-disclosure viewer-method-details">
        <summary>How to interpret this visualization</summary>
        <p>
          Error Level Analysis compares compression degradation with a standardized reference. High-contrast edges, complex texture, and repeated resaves can produce elevated residuals; interpret this view alongside the source image and other independent evidence.
        </p>
      </details>
    </div>
  );
};
