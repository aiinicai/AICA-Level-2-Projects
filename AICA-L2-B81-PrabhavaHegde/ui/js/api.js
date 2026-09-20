/**
 * The API surface. Every network call in the interface goes through here.
 *
 * All requests are same-origin to 127.0.0.1. There is no other endpoint and
 * there must never be one: the tool assesses data protection and would fail
 * its own R6 controls by sending client data anywhere.
 */

const BASE = '/api';

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function req(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, options);
  } catch {
    // The server is local, so a failure here means it has stopped, not that
    // the network is down. Say so plainly.
    throw new ApiError('The app has stopped. Start DPDP_Assessor.exe again.', 0);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (body && body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }
    } catch { /* a non-JSON error body is not worth reporting verbatim */ }
    throw new ApiError(detail, res.status);
  }
  return res.status === 204 ? null : res.json();
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const api = {
  meta:          ()               => req('/meta'),
  roleQuestions: ()               => req('/role/questions'),

  clients:       ()               => req('/clients'),
  createClient:  (b)              => req('/clients', json('POST', b)),
  client:        (s)              => req(`/clients/${s}`),
  submitRole:    (s, answers)     => req(`/clients/${s}/role`, json('POST', { answers })),

  controls:      (s)              => req(`/clients/${s}/controls`),
  saveControl:   (s, id, b)       => req(`/clients/${s}/controls/${id}`, json('PUT', b)),
  score:         (s)              => req(`/clients/${s}/score`),
  evidence:      (s)              => req(`/clients/${s}/evidence`),

  generateReport: (s, useAi)      => req(`/clients/${s}/report?use_ai=${useAi ? 'true' : 'false'}`,
                                         { method: 'POST' }),
  downloadUrl:   (s)              => `${BASE}/clients/${s}/report/download`,

  /**
   * Evidence upload. `description` is a query parameter, not a form field —
   * FastAPI treats non-Form scalars beside an UploadFile as query params.
   */
  uploadEvidence(slug, controlId, file, description = '') {
    const fd = new FormData();
    fd.append('file', file, file.name);
    const q = description ? `?description=${encodeURIComponent(description)}` : '';
    return req(`/clients/${slug}/controls/${controlId}/evidence${q}`, { method: 'POST', body: fd });
  },
};

export { ApiError };
