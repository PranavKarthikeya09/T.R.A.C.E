import type { AnalysisResponse, ApiErrorResponse, HealthResponse } from '../types/api';

/**
 * Service handling all API communication with the T.R.A.C.E. FastAPI backend.
 */
export class ApiService {
  /**
   * Resolve API base URL: respects VITE_API_BASE_URL when deployed,
   * falling back to relative '/api/v1' for local development via Vite proxy.
   */
  private static get apiBase(): string {
    const customBase = import.meta.env.VITE_API_BASE_URL;
    if (customBase && typeof customBase === 'string' && customBase.trim() !== '') {
      const clean = customBase.trim().replace(/\/+$/, '');
      return clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`;
    }
    return '/api/v1';
  }

  /**
   * Check whether the backend API service is reachable.
   */
  static async checkHealth(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${this.apiBase}/health`);
      if (!response.ok) {
        throw new Error(`Health check returned status ${response.status}`);
      }
      const health: HealthResponse = await response.json();
      try {
        const capabilitiesResponse = await fetch(`${this.apiBase}/capabilities`);
        if (capabilitiesResponse.ok) {
          const payload: { capabilities?: Record<string, string> } = await capabilitiesResponse.json();
          health.capabilities = payload.capabilities ?? {};
        }
      } catch {
        // A capability catalog failure should not mark the health endpoint offline.
      }
      return health;
    } catch {
      throw new Error('Unable to connect to T.R.A.C.E. API backend. Ensure the backend server is running.');
    }
  }

  /**
   * Submit an image for visual manipulation inspection.
   * Uses multipart/form-data with browser-generated boundary.
   */
  static async analyzeImage(file: File, selection: boolean | string[] = false): Promise<AnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (Array.isArray(selection)) {
      formData.append('selected_checks', JSON.stringify(selection));
    } else {
      formData.append('include_provenance', String(selection));
    }

    let response: Response;
    try {
      response = await fetch(`${this.apiBase}/analyze/image`, {
        method: 'POST',
        // Important: Do NOT manually set Content-Type header so browser attaches multipart boundary
        body: formData,
      });
    } catch {
      throw new Error('Network error: Could not connect to the analysis backend. Check connection or server status.');
    }

    if (!response.ok) {
      let errorMessage = `Analysis request failed (HTTP ${response.status})`;
      try {
        const errorData: ApiErrorResponse = await response.json();
        if (errorData?.error?.message) {
          errorMessage = errorData.error.message;
        }
      } catch {
        // Response was not JSON
        if (response.status === 503) {
          errorMessage = 'The detection model is currently unavailable or unconfigured on the server.';
        } else if (response.status === 413) {
          errorMessage = 'The uploaded image exceeds the maximum supported file size (10 MB).';
        } else if (response.status === 415) {
          errorMessage = 'The uploaded file format is unsupported. Please upload a JPEG, PNG, or WebP image.';
        } else if (response.status === 422) {
          errorMessage = 'The uploaded file could not be decoded as a valid image stream.';
        }
      }
      throw new Error(errorMessage);
    }

    try {
      const data: AnalysisResponse = await response.json();
      return data;
    } catch {
      throw new Error('Invalid response structure received from the analysis backend.');
    }
  }
}
