import { request } from './client';

export async function getDashboardMetrics() {
  return request('/api/v1/analytics/dashboard');
}
