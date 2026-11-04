// Supabase Edge Function (Deno), nightly via pg_cron (x-cron-secret) and after a client admin is added or deactivated.
// For each client with drive_share_with_admins: give every ACTIVE client admin (with an e-mail) VIEW access to the
// Vouchr/<Client> folder, and remove access from anyone who is no longer an active admin or when sharing is turned off.
// Staff (sub-users) never get Drive access. Uses the Drive permissions API (files/{id}/permissions).
// Shared Drive: sharing with people outside the firm's Workspace must be allowed by the Workspace admin.
// Not yet run against a live Drive — see PENDING.md.
import { createClient } from 'npm:@supabase/supabase-js@2.46.1';
import { ensureFolderPath, gfetch } from '../_shared/google.ts';

const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
const all = () => (Deno.env.get('GOOGLE_SHARED_DRIVE_ID') ? '&supportsAllDrives=true' : '');
const safe = (s: string) => s.normalize('NFKD').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-').slice(0, 40) || 'file';

Deno.serve(async (req) => {
  if (!Deno.env.get('CRON_SECRET') || req.headers.get('x-cron-secret') !== Deno.env.get('CRON_SECRET')) return new Response('forbidden', { status: 403 });
  const { data: run } = await db.from('job_runs').insert({ job: 'drive_share' }).select('id').single();
  const errors: string[] = [];
  let granted = 0, removed = 0;
  const { data: clients } = await db.from('clients').select('id, name, drive_share_with_admins, drive_folder_id');
  for (const c of clients ?? []) {
    try {
      const { data: shares } = await db.from('drive_shares').select('user_id, permission_id, email').eq('client_id', c.id);
      const { data: admins } = c.drive_share_with_admins
        ? await db.from('profiles').select('id, email').eq('client_id', c.id).eq('role', 'client_admin').eq('active', true).not('email', 'is', null)
        : { data: [] as { id: string; email: string }[] };
      const want = new Map((admins ?? []).map((a) => [a.id, a.email as string]));
      if (!want.size && !(shares ?? []).length) continue;
      let folder = c.drive_folder_id as string | null;
      if (!folder) {
        folder = await ensureFolderPath(`Vouchr/${safe(c.name)}`);
        await db.from('clients').update({ drive_folder_id: folder }).eq('id', c.id);
      }
      // remove access that should no longer exist (admin deactivated, e-mail changed, or sharing turned off)
      for (const sh of shares ?? []) {
        if (want.get(sh.user_id) === sh.email) continue;
        const res = await gfetch(`https://www.googleapis.com/drive/v3/files/${folder}/permissions/${sh.permission_id}?x=1${all()}`, { method: 'DELETE' });
        if (!res.ok && res.status !== 404) throw new Error(`remove ${sh.email}: HTTP ${res.status}`);
        await db.from('drive_shares').delete().eq('client_id', c.id).eq('user_id', sh.user_id);
        removed++;
      }
      // give view access to admins who do not have it yet (no Google e-mail notification — the app tells them)
      for (const [uid, email] of want) {
        if ((shares ?? []).some((sh) => sh.user_id === uid && sh.email === email)) continue;
        const res = await gfetch(`https://www.googleapis.com/drive/v3/files/${folder}/permissions?sendNotificationEmail=false${all()}`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role: 'reader', type: 'user', emailAddress: email })
        });
        const j = await res.json();
        if (!res.ok) throw new Error(`share with ${email}: ${JSON.stringify(j).slice(0, 200)}`);
        await db.from('drive_shares').upsert({ client_id: c.id, user_id: uid, permission_id: j.id, email });
        granted++;
      }
    } catch (e) {
      errors.push(`${c.name}: ${String(e).slice(0, 200)}`);
    }
  }
  if (errors.length) await db.from('system_events').insert({ level: 'error', component: 'drive_upload', message: `Drive sharing: ${errors.slice(0, 3).join(' | ')}`.slice(0, 500) });
  await db.from('job_runs').update({ finished_at: new Date().toISOString(), ok: errors.length === 0, rows_processed: granted + removed, error: errors.join('\n') || null }).eq('id', run?.id);
  return new Response(JSON.stringify({ granted, removed, errors }), { headers: { 'Content-Type': 'application/json' } });
});
