import { request } from './client';

export async function login(username, password) {
  return request('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function register(userData) {
  return request('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(userData),
  });
}

export async function getMe() {
  return request('/api/v1/auth/me');
}
