/**
 * API client configuration and fetch wrapper with automatic JWT header injection.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const token = localStorage.getItem('floodpath_token');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      errorDetail = response.statusText || errorDetail;
    }

    if (response.status === 401) {
      localStorage.removeItem('floodpath_token');
      localStorage.removeItem('floodpath_user');
      window.dispatchEvent(new CustomEvent('floodpath:auth_error', { detail: errorDetail }));
    }
    const error = new Error(errorDetail);
    (error as Error & { status: number }).status = response.status;
    throw error;
  }

  return response.json() as Promise<T>;
}
