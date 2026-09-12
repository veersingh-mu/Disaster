/**
 * API client configuration and fetch wrapper with automatic JWT header injection.
 */

export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const customUrl = localStorage.getItem('floodpath_api_url');
    if (customUrl) return customUrl.replace(/\/$/, '');
  }
  return (
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    'http://localhost:8000'
  ).replace(/\/$/, '');
}

export function setCustomApiUrl(url: string | null): void {
  if (typeof window === 'undefined') return;
  if (!url) {
    localStorage.removeItem('floodpath_api_url');
  } else {
    localStorage.setItem('floodpath_api_url', url.trim().replace(/\/$/, ''));
  }
  window.dispatchEvent(new CustomEvent('floodpath:api_url_changed'));
}

export const API_BASE_URL = getApiBaseUrl();

export interface ApiFetchError extends Error {
  status?: number;
  isNetworkError?: boolean;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;
  const token = typeof window !== 'undefined' ? localStorage.getItem('floodpath_token') : null;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const netErr: ApiFetchError = new Error(
      err instanceof Error ? err.message : 'Network request failed'
    );
    netErr.isNetworkError = true;
    throw netErr;
  }

  if (!response.ok) {
    let errorDetail = 'Request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      errorDetail = response.statusText || errorDetail;
    }

    if (response.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('floodpath_token');
        localStorage.removeItem('floodpath_user');
        window.dispatchEvent(new CustomEvent('floodpath:auth_error', { detail: errorDetail }));
      }
    }
    const error: ApiFetchError = new Error(errorDetail);
    error.status = response.status;
    throw error;
  }

  return response.json() as Promise<T>;
}

