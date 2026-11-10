import type { DatasetKind, Engagement, EngagementState, FirmDetails, LogEntry, Row, Supplier } from './types';

async function call<T>(method: string, url: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`api${url}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error('Cannot reach the app server. Is the GSTR-2B Recon Suite window still open?');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { error?: string }).error || `Server error ${res.status}`);
  return data as T;
}

export interface BlockedInput {
  gstin: string;
  invKey: string;
  inv: string;
  name: string;
  date: string;
  taxable: number;
  igst: number;
  cgst: number;
  sgst: number;
  catId: string;
  catLbl: string;
  sec: string;
  reason: string;
  origin: 'auto' | 'manual';
}

export const api = {
  health: () => call<{ ok: boolean; driver: string; dbPath: string }>('GET', '/health'),
  listEngagements: () => call<Engagement[]>('GET', '/engagements'),
  createEngagement: (e: Partial<Engagement>) => call<Engagement>('POST', '/engagements', e),
  updateEngagement: (id: number, e: Partial<Engagement>) => call<Engagement>('PUT', `/engagements/${id}`, e),
  deleteEngagement: (id: number) => call<{ ok: true }>('DELETE', `/engagements/${id}`),
  state: (id: number) => call<EngagementState>('GET', `/engagements/${id}/state`),
  saveDatasets: (id: number, fileName: string, sets: Partial<Record<DatasetKind, Row[]>>) =>
    call<{ ok: true }>('PUT', `/engagements/${id}/datasets`, { fileName, sets }),
  clearDatasets: (id: number, kinds: DatasetKind[]) => call<{ ok: true }>('DELETE', `/engagements/${id}/datasets?kinds=${kinds.join(',')}`),
  addBlocked: (id: number, items: BlockedInput[]) => call<{ added: number }>('POST', `/engagements/${id}/blocked`, { items }),
  setBlockedActive: (id: number, bid: number, active: boolean) => call<{ ok: true }>('PUT', `/engagements/${id}/blocked/${bid}`, { active }),
  setRemark: (id: number, key: string, text: string) => call<{ ok: true }>('PUT', `/engagements/${id}/remarks`, { key, text }),
  logs: (id: number) => call<LogEntry[]>('GET', `/engagements/${id}/logs`),
  log: (id: number, tag: string, message: string) => call<{ ok: true }>('POST', `/engagements/${id}/logs`, { tag, message }),
  suppliers: () => call<Supplier[]>('GET', '/suppliers'),
  saveSupplier: (s: Partial<Supplier> & { gstin: string }) => call<Supplier>('PUT', `/suppliers/${encodeURIComponent(s.gstin)}`, s),
  firm: () => call<Partial<FirmDetails>>('GET', '/settings/firm'),
  saveFirm: (f: FirmDetails) => call<FirmDetails>('PUT', '/settings/firm', f),
};
