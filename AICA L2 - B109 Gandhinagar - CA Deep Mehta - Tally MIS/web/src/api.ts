import { useQuery, type UseQueryOptions } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { useCompany } from './state';

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

/** All mutations send X-Requested-With (server-side CSRF check); cookies are same-origin only. */
export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; raw?: BodyInit; contentType?: string } = {}): Promise<T> {
  const headers: Record<string, string> = { 'X-Requested-With': 'mis' };
  let body: BodyInit | undefined;
  if (opts.raw !== undefined) {
    body = opts.raw;
    headers['Content-Type'] = opts.contentType ?? 'application/octet-stream';
  } else if (opts.body !== undefined) {
    body = JSON.stringify(opts.body);
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(path, { method: opts.method ?? (body ? 'POST' : 'GET'), headers, body, credentials: 'same-origin' });
  if (res.status === 401 && !path.startsWith('/api/auth')) {
    window.dispatchEvent(new Event('mis:unauthorized'));
  }
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, data?.error ?? `Request failed (${res.status})`);
  return data as T;
}

/** Query string carrying the global filters (from, to, compare, costCentre). */
export function useFilterQuery(extra: Record<string, string | undefined> = {}): string {
  const [sp] = useSearchParams();
  const p = new URLSearchParams();
  for (const k of ['from', 'to', 'compare', 'costCentre']) {
    const v = sp.get(k);
    if (v) p.set(k, v);
  }
  for (const [k, v] of Object.entries(extra)) if (v !== undefined && v !== '') p.set(k, v);
  return p.toString();
}

/** Company-scoped GET with the global filters applied. */
export function useCompanyQuery<T = any>(path: string, extra: Record<string, string | undefined> = {}, opts: Partial<UseQueryOptions<T>> = {}) {
  const { companyId } = useCompany();
  const qs = useFilterQuery(extra);
  const url = `/api/c/${companyId}${path}${qs ? `?${qs}` : ''}`;
  return useQuery<T>({ queryKey: [url], queryFn: () => api<T>(url), enabled: !!companyId, staleTime: 60_000, ...opts });
}

export function exportUrl(companyId: number, report: string, qs: string, format: 'csv' | 'xlsx') {
  return `/api/c/${companyId}/export/${report}?${qs}${qs ? '&' : ''}format=${format}`;
}
