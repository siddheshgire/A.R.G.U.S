import { request } from './client';

export async function listAlerts(params = {}) {
  const query = new URLSearchParams();
  if (params.status) query.append('status', params.status);
  if (params.severity) query.append('severity', params.severity);
  if (params.limit) query.append('limit', params.limit);
  if (params.offset !== undefined) query.append('offset', params.offset);

  const qs = query.toString();
  return request(`/api/v1/alerts${qs ? `?${qs}` : ''}`);
}

export async function updateAlert(alertId, updateData) {
  return request(`/api/v1/alerts/${alertId}`, {
    method: 'PATCH',
    body: JSON.stringify(updateData),
  });
}
