import { request } from './client';

export async function assessTransaction(payload) {
  return request('/api/v1/transactions/assess', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getTransactionDetail(txId) {
  return request(`/api/v1/transactions/${txId}`);
}

export async function listTransactions(params = {}) {
  const query = new URLSearchParams();
  if (params.limit) query.append('limit', params.limit);
  if (params.offset !== undefined) query.append('offset', params.offset);
  if (params.type) query.append('type', params.type);
  if (params.decision) query.append('decision', params.decision);
  if (params.min_risk !== undefined && params.min_risk !== '') query.append('min_risk', params.min_risk);
  if (params.max_risk !== undefined && params.max_risk !== '') query.append('max_risk', params.max_risk);

  const qs = query.toString();
  return request(`/api/v1/transactions${qs ? `?${qs}` : ''}`);
}
