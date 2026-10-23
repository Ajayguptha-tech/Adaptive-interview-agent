// Adaptive Interview Intelligence API Client
// Connected to FastAPI backend via VITE_API_BASE_URL (or relative proxy)

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const isBackendConfigured = (): boolean => {
  // Always true: relative requests are forwarded to FastAPI backend via Vite proxy or reverse proxy
  return true;
};

export class ApiConnectionError extends Error {
  constructor(message = 'FastAPI backend connection is not configured. Set VITE_API_BASE_URL to connect.') {
    super(message);
    this.name = 'ApiConnectionError';
  }
}

export async function apiRequest<T>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<T | null> {
  const base = API_BASE_URL ? API_BASE_URL.replace(/\/$/, '') : '';
  const url = `${base}/${endpoint.replace(/^\//, '')}`;

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (typeof sessionStorage !== 'undefined') {
    const token = sessionStorage.getItem('interview_session_token');
    const cand = sessionStorage.getItem('interview_candidate_id');
    if (token) headers['X-Session-Token'] = token;
    if (cand) headers['X-Candidate-ID'] = cand;
  }

  // Only set Content-Type to application/json if not FormData
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error [${response.status}]: ${errorText || response.statusText}`);
  }

  return response.json();
}

/**
 * Upload multipart form data (e.g. resume document and target role)
 */
export async function apiUpload<T>(
  endpoint: string,
  formData: FormData
): Promise<T> {
  const base = API_BASE_URL ? API_BASE_URL.replace(/\/$/, '') : '';
  const url = `${base}/${endpoint.replace(/^\//, '')}`;

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error [${response.status}]: ${errorText || response.statusText}`);
  }

  return response.json();
}

/**
 * Download a binary blob (e.g. report PDF) and prompt save dialog
 */
export async function apiDownloadBlob(
  endpoint: string,
  filename: string
): Promise<void> {
  const base = API_BASE_URL ? API_BASE_URL.replace(/\/$/, '') : '';
  const token = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('interview_session_token') : null;
  const cand = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('interview_candidate_id') : null;
  const sep = endpoint.includes('?') ? '&' : '?';
  let targetEndpoint = endpoint;
  if (token && cand) {
    targetEndpoint = `${endpoint}${sep}candidate_id=${encodeURIComponent(cand)}&token=${encodeURIComponent(token)}`;
  }
  const url = `${base}/${targetEndpoint.replace(/^\//, '')}`;

  const downloadHeaders: Record<string, string> = {
    Accept: 'application/pdf, application/octet-stream',
  };
  if (token) downloadHeaders['X-Session-Token'] = token;
  if (cand) downloadHeaders['X-Candidate-ID'] = cand;

  const response = await fetch(url, {
    method: 'GET',
    headers: downloadHeaders,
  });

  if (!response.ok) {
    throw new Error(`Failed to download file [${response.status}]: ${response.statusText}`);
  }

  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(blobUrl);
}
