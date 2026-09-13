import { request } from './client';

export async function getHealth() {
  return request('/health');
}

export async function getReadiness() {
  return request('/ready');
}
