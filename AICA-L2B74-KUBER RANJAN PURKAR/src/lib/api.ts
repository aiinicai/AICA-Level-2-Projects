// Server API client — used when the app is served by the CMA LAN server.
// Falls back to null when unreachable (pure static/dev mode).
import type { ClientRecord } from './store';

export interface LicenseInfo {
  licensed: boolean;
  reason?: string;
  hardwareId: string;
  keyType?: 'Annual' | 'Master';
  year?: string | null;
  expiry?: string | null;
}

async function tryFetch(url: string, init?: RequestInit, timeoutMs = 3000): Promise<Response | null> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    const res = await fetch(url, { ...init, signal: ctrl.signal });
    clearTimeout(t);
    return res;
  } catch {
    return null;
  }
}

/** null → server mode unavailable (use localStorage).
 *  Long timeout: the server's first health call may run hardware queries. */
export async function serverHealth(): Promise<LicenseInfo | null> {
  const res = await tryFetch('/api/health', undefined, 12000);
  if (!res || !res.ok) return null;
  return res.json();
}

export async function apiListClients(): Promise<ClientRecord[] | null> {
  const res = await tryFetch('/api/clients');
  if (!res || !res.ok) return null;
  return res.json();
}

export async function apiSaveClient(rec: ClientRecord): Promise<'ok' | 'unlicensed' | 'offline'> {
  const res = await tryFetch(`/api/clients/${encodeURIComponent(rec.id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rec),
  });
  if (!res) return 'offline';
  if (res.status === 402) return 'unlicensed';
  return res.ok ? 'ok' : 'offline';
}

export async function apiDeleteClient(id: string): Promise<'ok' | 'unlicensed' | 'offline'> {
  const res = await tryFetch(`/api/clients/${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (!res) return 'offline';
  if (res.status === 402) return 'unlicensed';
  return res.ok ? 'ok' : 'offline';
}

export async function apiActivate(key: string): Promise<{ ok: boolean; reason?: string; keyType?: string; year?: string; expiry?: string }> {
  const res = await tryFetch('/api/license/activate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key }),
  });
  if (!res) return { ok: false, reason: 'offline' };
  return res.json();
}
