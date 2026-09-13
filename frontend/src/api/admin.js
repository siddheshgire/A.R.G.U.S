import { request } from './client';

export async function getAuditLogs(params = {}) {
  const query = new URLSearchParams();
  if (params.limit) query.append('limit', params.limit);
  if (params.offset !== undefined) query.append('offset', params.offset);
  if (params.event_type) query.append('event_type', params.event_type);

  const qs = query.toString();
  return request(`/api/v1/admin/audit-logs${qs ? `?${qs}` : ''}`);
}

export async function getUsers(params = {}) {
  const query = new URLSearchParams();
  if (params.limit) query.append('limit', params.limit);
  if (params.offset !== undefined) query.append('offset', params.offset);

  const qs = query.toString();
  return request(`/api/v1/admin/users${qs ? `?${qs}` : ''}`);
}
