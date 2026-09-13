/**
 * A.R.G.U.S. — Centralized API Client
 * Wraps browser fetch with automatic JWT injection, unified error parsing,
 * and session expiration interception.
 */

const BASE_URL = ''; // Proxied via Vite to http://localhost:8000

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
  };

  let response;
  try {
    response = await fetch(endpoint, config);
  } catch (err) {
    throw new ApiError(0, 'Unable to connect to A.R.G.U.S. API Gateway. Please verify the backend server is active.');
  }

  // Handle Session Expiration
  if (response.status === 401) {
    localStorage.removeItem('argus_token');
    localStorage.removeItem('argus_user');
    window.dispatchEvent(new CustomEvent('argus:unauthorized'));
    const data = await response.json().catch(() => ({}));
    throw new ApiError(401, data.detail || 'Your session has expired. Please log in again.');
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let detail = 'An unexpected server error occurred.';
    if (data && data.detail) {
      if (Array.isArray(data.detail)) {
        // FastAPI / Pydantic validation error list
        detail = data.detail.map((e) => e.msg || e.message).join(', ');
      } else {
        detail = data.detail;
      }
    } else if (data && data.error && data.error.message) {
      detail = data.error.message;
    }
    throw new ApiError(response.status, detail, data);
  }

  return data;
}
