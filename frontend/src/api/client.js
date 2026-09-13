/**
 * A.R.G.U.S. — Centralized API Client
 * Wraps browser fetch with automatic JWT injection, unified error parsing,
 * and session expiration interception.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

function getErrorDetail(data, fallback) {
  if (!data) return fallback;
  if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg || item.message || String(item)).join(', ');
  if (typeof data.detail === 'string') return data.detail;
  if (data.error?.message) return data.error.message;
  return fallback;
}

export class ApiError extends Error {
  constructor(status, detail, data = null) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail));
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

export async function request(endpoint, options = {}) {
  const token = localStorage.getItem('argus_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
    signal: options.signal,
  };

  let response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, config);
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError(0, 'Unable to connect to the A.R.G.U.S. API gateway. Verify that the backend is running.');
  }

  // Handle Session Expiration
  if (response.status === 401) {
    localStorage.removeItem('argus_token');
    localStorage.removeItem('argus_user');
    window.dispatchEvent(new CustomEvent('argus:unauthorized'));
    const data = await response.json().catch(() => ({}));
    throw new ApiError(401, getErrorDetail(data, 'Your session has expired. Please sign in again.'), data);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(response.status, getErrorDetail(data, `Request failed with status ${response.status}.`), data);
  }

  return data;
}
