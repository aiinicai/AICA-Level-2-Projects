// Supabase Edge Function (Deno): runs the shared AI tasks (../_shared/ai/tasks.ts) for signed-in users.
//   POST { task, ctx, files?: [{mime, data(base64)}], expenseIds?: [id] }   (or a pg_cron call with x-cron-secret for norms_scan)
// Guard rails: GEMINI_API_KEY only here · role per task · per-client daily cap · trusted masters (heads, TDS table) loaded from
// the database, not taken from the browser · bills fetched from Drive only after an RLS check · every call logged with tokens.
import { createClient } from 'npm:@supabase/supabase-js@2.46.1';
import { gfetch } from '../_shared/google.ts';
import { DEFAULT_MODELS, runTask, TASKS, type InlineFile, type TaskName } from '../_shared/ai/tasks.ts';

const admin = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
const KEY = Deno.env.get('GEMINI_API_KEY');
const MODELS = { heavy: Deno.env.get('GEMINI_MODEL') ?? DEFAULT_MODELS.heavy, fast: Deno.env.get('GEMINI_MODEL_FAST') ?? DEFAULT_MODELS.fast };
const DAILY_CAP = Number(Deno.env.get('AI_DAILY_LIMIT_PER_CLIENT') ?? 200);

const b64 = (buf: ArrayBuffer) => { let s = ''; const u = new Uint8Array(buf); for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000)); return btoa(s); };
const istToday = () => new Date(Date.now() + 5.5 * 3600 * 1000).toISOString().slice(0, 10);

Deno.serve(async (req) => {
  const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, content-type, apikey, x-client-info' };
  if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
  const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status, headers: { ...cors, 'Content-Type': 'application/json' } });
  if (!KEY) return json({ error: 'AI is not configured on the server' }, 503);
  // free-tier content may be used by Google to improve its products — never send real client data on it
  if (Deno.env.get('GEMINI_TIER') !== 'paid') return json({ error: 'AI needs the paid Gemini tier for client data' }, 503);

  const body = await req.json().catch(() => ({}));
  const task = body.task as TaskName;
  const def = TASKS[task];
  if (!def) return json({ error: 'Unknown task' }, 400);
  const isCron = !!Deno.env.get('CRON_SECRET') && req.headers.get('x-cron-secret') === Deno.env.get('CRON_SECRET');
  const user = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_ANON_KEY')!, { global: { headers: { Authorization: req.headers.get('Authorization') ?? '' } } });
  const uid = isCron ? undefined : (await user.auth.getUser()).data.user?.id;
  const { data: me } = uid ? await user.from('profiles').select('id, role, client_id').eq('id', uid).eq('active', true).maybeSingle() : { data: null };
  if (!isCron && !me) return json({ error: 'Not signed in' }, 401);
  if (isCron ? task !== 'norms_scan' : !def.roles.includes(me!.role)) return json({ error: 'Not allowed for your role' }, 403);

  const ctx = (body.ctx ?? {}) as Record<string, unknown>;
  // DPDP: the user must have agreed to AI, and the client company must not have switched AI off (0008_dpdp_consent.sql)
  if (!isCron) {
    const { data: uc } = await admin.from('consents').select('purposes, withdrawn_at, valid_until').eq('scope', 'user').eq('user_id', me!.id).order('accepted_at', { ascending: false }).limit(1).maybeSingle();
    if (!uc || uc.withdrawn_at || !uc.purposes?.ai || (uc.valid_until && uc.valid_until < istToday())) return json({ error: 'You have not agreed to AI assistance.' }, 403);
  }
  const clientId = me?.role === 'super_admin' ? (ctx.clientId as string | undefined) : me?.client_id;
  if (clientId) {
    const { data: ok } = await user.from('clients').select('id').eq('id', clientId).maybeSingle();
    if (!ok && !isCron) return json({ error: 'Not allowed for this client' }, 403);
    const since = `${istToday()}T00:00:00+05:30`;
    const { count } = await admin.from('ai_reviews').select('id', { count: 'exact', head: true }).eq('client_id', clientId).gte('created_at', since);
    if ((count ?? 0) >= DAILY_CAP) return json({ error: 'Daily AI limit reached for this client' }, 429);
    const { data: cc } = await admin.from('consents').select('purposes, withdrawn_at').eq('scope', 'client').eq('client_id', clientId).order('accepted_at', { ascending: false }).limit(1).maybeSingle();
    if (cc && (cc.withdrawn_at || !cc.purposes?.ai)) return json({ error: 'This company has switched AI assistance off.' }, 403);
  }

  // trusted masters come from the database, never from the browser
  if (task === 'analyse_invoice' || task === 'norms_scan') {
    const [{ data: heads }, { data: rates }] = await Promise.all([
      admin.from('expense_heads').select('name'),
      admin.from('tds_rates').select('code, description, act_reference, rate_pct, threshold_single, threshold_aggregate, no_pan_rate_pct, effective_from, effective_to, verified')
    ]);
    ctx.heads = (heads ?? []).map((h: { name: string }) => h.name);
    ctx.tdsTable = rates ?? [];
  }
  if (task === 'norms_scan') {
    const { data: last } = await admin.from('ai_reviews').select('created_at').eq('task', 'norms_scan').eq('ok', true).order('created_at', { ascending: false }).limit(1).maybeSingle();
    ctx.since = last?.created_at?.slice(0, 10) ?? new Date(Date.now() - 100 * 86400000).toISOString().slice(0, 10);
  }

  // files: either sent inline (a new bill not yet saved) or fetched from Drive for saved bills the user may see (RLS)
  let files: InlineFile[] = Array.isArray(body.files) ? body.files : [];
  const ids: string[] = Array.isArray(body.expenseIds) ? body.expenseIds : [];
  if (ids.length) {
    files = [];
    for (const id of ids.slice(0, 2)) {
      const { data: e } = await user.from('expenses').select('id, client_id, drive_file_id').eq('id', id).maybeSingle();
      if (!e?.drive_file_id) return json({ error: 'Bill file not found' }, 404);
      const res = await gfetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(e.drive_file_id)}?alt=media&supportsAllDrives=true`);
      if (!res.ok) return json({ error: 'Could not read the bill from Drive' }, 502);
      files.push({ mime: res.headers.get('content-type') ?? 'application/octet-stream', data: b64(await res.arrayBuffer()) });
    }
  }

  try {
    const r = await runTask(KEY, MODELS, task, ctx, files, istToday());
    await admin.from('ai_reviews').insert({ client_id: clientId ?? null, expense_id: ids[0] ?? null, task, model: r.model, result: r.result, input_tokens: r.inTok, output_tokens: r.outTok, ok: true, created_by: me?.id ?? null });
    await admin.from('api_usage').insert({ provider: 'ai', client_id: clientId ?? null, endpoint: task, ok: true });
    if (task === 'norms_scan') {
      const items = (r.result as { items: { area: string; title: string; detail: string; source_url: string; verified: boolean; problems: string[] }[] }).items;
      for (const it of items) {
        await admin.from('compliance_findings').insert({ area: it.area || 'other', kind: 'ai_suggestion', title: `AI: ${it.title}`.slice(0, 300),
          detail: `${it.detail}\n${it.verified ? 'Checks passed' : `NEEDS CHECK — ${it.problems.join(', ')}`}: ${it.source_url || 'no source'}`, sources: (r.result as { sources: unknown }).sources });
      }
    }
    return json(r);
  } catch (err) {
    await admin.from('ai_reviews').insert({ client_id: clientId ?? null, expense_id: ids[0] ?? null, task, model: MODELS.heavy, ok: false, error: String(err).slice(0, 500), created_by: me?.id ?? null });
    await admin.from('system_events').insert({ level: 'error', component: 'ai_assist', client_id: clientId ?? null, message: String(err).slice(0, 500) });
    return json({ error: 'AI could not complete this — nothing was changed. The rule-based checks still apply.' }, 502);
  }
});
