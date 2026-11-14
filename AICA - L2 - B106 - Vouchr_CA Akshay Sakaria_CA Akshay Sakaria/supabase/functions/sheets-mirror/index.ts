// Nightly (pg_cron) + on demand: mirrors each client's data into one Google Sheet per client per FY,
// kept in that client's Drive folder:  Vouchr/<Client>/FY 2026-27/Vouchr MIS — <Client> — FY 2026-27
// Tabs are fully rewritten each run (idempotent; Supabase stays the source of truth).
import { createClient } from 'npm:@supabase/supabase-js@2.46.1';
import { ensureFolderPath, gfetch } from '../_shared/google.ts';

const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
const safe = (s: string) => s.normalize('NFKD').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-').slice(0, 40) || 'file';
type Row = (string | number | null)[];

async function ensureSheet(clientId: string, clientName: string, fy: string, existing?: string): Promise<string> {
  if (existing) return existing;
  const folderId = await ensureFolderPath(`Vouchr/${safe(clientName)}/FY ${fy}`);
  const title = `Vouchr MIS — ${clientName} — FY ${fy}`;
  // create through Drive, directly inside the client's FY folder (works for OAuth accounts and Shared Drives)
  const created = await (await gfetch('https://www.googleapis.com/drive/v3/files?fields=id&supportsAllDrives=true', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: title, mimeType: 'application/vnd.google-apps.spreadsheet', parents: [folderId] })
  })).json();
  if (!created.id) throw new Error(`Could not create sheet: ${JSON.stringify(created)}`);
  await gfetch(`https://sheets.googleapis.com/v4/spreadsheets/${created.id}:batchUpdate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ requests: [
      { updateSheetProperties: { properties: { sheetId: 0, title: 'Expenses' }, fields: 'title' } },
      ...['Payments', 'Vendors', 'TDS', 'Ageing'].map((t) => ({ addSheet: { properties: { title: t } } }))
    ] })
  });
  await db.from('client_sheets').upsert({ client_id: clientId, fy_label: fy, sheet_id: created.id });
  return created.id;
}

async function writeTab(sheetId: string, tab: string, rows: Row[]) {
  await gfetch(`https://sheets.googleapis.com/v4/spreadsheets/${sheetId}/values/${encodeURIComponent(tab)}:clear`, { method: 'POST' });
  if (!rows.length) return;
  await gfetch(`https://sheets.googleapis.com/v4/spreadsheets/${sheetId}/values/${encodeURIComponent(tab)}!A1?valueInputOption=RAW`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ values: rows })
  });
}

Deno.serve(async (req) => {
  // scheduled job: only pg_cron (with the shared secret) may run it — the anon key in the app is public
  if (!Deno.env.get('CRON_SECRET') || req.headers.get('x-cron-secret') !== Deno.env.get('CRON_SECRET')) return new Response('forbidden', { status: 403 });
  const only = new URL(req.url).searchParams.get('client');
  const { data: run } = await db.from('job_runs').insert({ job: 'sheets_mirror' }).select().single();
  let rowsDone = 0;
  const failures: string[] = [];
  const { data: clients } = await db.from('clients').select('id, name').match(only ? { id: only } : {});
  for (const c of clients ?? []) {
    try {
      const { data: fys } = await db.from('expenses').select('fy_label').eq('client_id', c.id);
      for (const fy of [...new Set((fys ?? []).map((x) => x.fy_label))]) {
        const { data: link } = await db.from('client_sheets').select('sheet_id').eq('client_id', c.id).eq('fy_label', fy).maybeSingle();
        const sheetId = await ensureSheet(c.id, c.name, fy, link?.sheet_id);
        const { data: ex } = await db.from('expense_register').select('*').eq('client_id', c.id).eq('fy_label', fy).order('invoice_date');
        const { data: pay } = await db.from('payment_register').select('*').eq('client_id', c.id).eq('fy_label', fy).order('paid_on');
        const { data: ven } = await db.from('vendors').select('name, gstin, pan, pan_status, gstin_status, credit_days').eq('client_id', c.id).order('name');
        const head = (o?: Record<string, unknown>) => (o ? Object.keys(o) : []);
        const table = (list: Record<string, unknown>[] | null): Row[] => (list?.length ? [head(list[0]), ...list.map((r) => Object.values(r) as Row)] : []);
        await writeTab(sheetId, 'Expenses', table(ex));
        await writeTab(sheetId, 'Payments', table(pay));
        await writeTab(sheetId, 'Vendors', table(ven));
        rowsDone += (ex?.length ?? 0) + (pay?.length ?? 0);
      }
    } catch (err) {
      failures.push(c.name);
      await db.from('system_events').insert({ level: 'error', component: 'sheets_sync', client_id: c.id, message: String(err).slice(0, 500) });
    }
  }
  await db.from('job_runs').update({ finished_at: new Date().toISOString(), ok: failures.length === 0, rows_processed: rowsDone, error: failures.length ? `Failed: ${failures.join(', ')}` : null }).eq('id', run.id);
  return new Response(JSON.stringify({ rows: rowsDone, failures }), { headers: { 'Content-Type': 'application/json' } });
});
