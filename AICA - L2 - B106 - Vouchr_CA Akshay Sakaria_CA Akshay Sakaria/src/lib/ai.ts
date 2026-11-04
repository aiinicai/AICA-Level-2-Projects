// Browser side of AI assist. The Gemini key never reaches the browser:
//   • live (Supabase connected, VITE_AI_ENABLED=true) → `ai-assist` Edge Function
//   • local testing (`npm run dev`, GEMINI_API_KEY in .env.local) → the dev server's /__ai proxy
//   • otherwise AI is off and every screen says why. Rule-based checks work in all cases.
// Every answer has passed the truth checks in supabase/functions/_shared/ai/truth.ts before it gets here.
import { useEffect, useState } from 'react';
import { supabase } from './backend';
import { todayIso } from './dates';
import type { Fact } from '../../supabase/functions/_shared/ai/truth.ts';
import type { TaskName } from '../../supabase/functions/_shared/ai/tasks.ts';
import type { Role } from '../data/types';
import { useStore } from '../data/store';
import { aiAllowed } from './consent';

export type { Fact, TaskName };
export interface AiStatus { enabled: boolean; mode: 'server' | 'local' | 'off'; reason: string; model?: string; freeTier?: boolean }
export interface AiResult<T> { result: T; doubts: string[]; needsHumanCheck: boolean; model: string }

let probe: Promise<AiStatus> | undefined;
export function getAiStatus(): Promise<AiStatus> {
  if (supabase) return Promise.resolve(import.meta.env.VITE_AI_ENABLED === 'true'
    ? { enabled: true, mode: 'server', reason: '' }
    : { enabled: false, mode: 'off', reason: 'AI is not switched on for this firm yet.' });
  if (!import.meta.env.DEV) return Promise.resolve({ enabled: false, mode: 'off', reason: 'AI is off in this demo. It runs on the server once a paid Gemini API key is added.' });
  probe ??= fetch('/__ai').then((r) => r.json()).then((j: { ready: boolean; model: string; paid?: boolean }) => (j.ready
    ? { enabled: true, mode: 'local' as const, reason: '', model: j.model, freeTier: !j.paid }
    : { enabled: false, mode: 'off' as const, reason: 'Local AI test: add GEMINI_API_KEY to .env.local and restart the app.' }))
    .catch(() => ({ enabled: false, mode: 'off' as const, reason: 'AI is off in this demo. It runs on the server once a paid Gemini API key is added.' }));
  return probe;
}

/** AI availability for this user: server/proxy ready AND DPDP consent — the user agreed to AI and the company has not switched it off. */
export function useAiStatus(): AiStatus {
  const { s: st, me, clientId } = useStore();
  const [s, setS] = useState<AiStatus>({ enabled: false, mode: 'off', reason: 'Checking AI…' });
  useEffect(() => { let live = true; getAiStatus().then((x) => live && setS(x)); return () => { live = false; }; }, []);
  const allowed = me ? aiAllowed(st.consents, me.id, clientId, todayIso()) : { ok: false, reason: 'Not signed in' };
  return s.enabled && !allowed.ok ? { ...s, enabled: false, reason: allowed.reason ?? '' } : s;
}

const toB64 = (b: Blob) => new Promise<string>((resolve, reject) => {
  const r = new FileReader();
  r.onload = () => resolve(String(r.result).split(',')[1] ?? '');
  r.onerror = () => reject(r.error);
  r.readAsDataURL(b);
});

/** Gemini's audio list has webm/ogg/m4a; Safari records "audio/mp4" (an m4a container). */
const mimeOf = (b: Blob) => (b.type.startsWith('audio/mp4') ? 'audio/m4a' : b.type.split(';')[0] || 'application/octet-stream');

export async function runAi<T>(task: TaskName, role: Role, ctx: Record<string, unknown>, opts: { files?: Blob[]; expenseIds?: string[] } = {}): Promise<AiResult<T>> {
  const st = await getAiStatus();
  if (!st.enabled) throw new Error(st.reason);
  const files = await Promise.all((opts.files ?? []).map(async (f) => ({ mime: mimeOf(f), data: await toB64(f) })));
  if (st.mode === 'local') {
    const res = await fetch('/__ai', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task, role, ctx, files, today: todayIso() }) });
    const j = await res.json();
    if (!res.ok) throw new Error(j.error ?? `AI error ${res.status}`);
    return j;
  }
  const { data, error } = await supabase!.functions.invoke('ai-assist', { body: { task, ctx, files: opts.expenseIds?.length ? [] : files, expenseIds: opts.expenseIds } });
  if (error) throw new Error(error.message);
  return data;
}

/** Use a fact only when it passed every check. */
export const sure = <T,>(f?: Fact<T> | null): T | undefined => (f && f.certainty === 'certain' && f.value !== null ? f.value : undefined);
