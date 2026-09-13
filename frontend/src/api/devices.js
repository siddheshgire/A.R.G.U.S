import { request } from './client';

export async function listDevices(params = {}) {
  const query = new URLSearchParams();
  if (params.limit) query.append('limit', params.limit);
  if (params.offset !== undefined) query.append('offset', params.offset);

  const qs = query.toString();
  return request(`/api/v1/devices${qs ? `?${qs}` : ''}`);
}

export async function resetDeviceTamper(deviceId) {
  return request(`/api/v1/devices/${deviceId}/reset-tamper`, {
    method: 'POST',
  });
}
