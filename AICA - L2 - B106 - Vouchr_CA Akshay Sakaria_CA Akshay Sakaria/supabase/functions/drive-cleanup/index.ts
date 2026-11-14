// Supabase Edge Function (Deno), nightly via pg_cron with the x-cron-secret header.
// A bill / challan file is uploaded to Drive before its record is saved. If the save never happens (failed, phone lost
// signal, app closed), the file is left "staged". After 24 hours with no record using it, this moves the file to
// Drive's TRASH (recoverable there for 30 days — nothing is permanently deleted here) and removes the staged row.
import { createClient } from 'npm:@supabase/supabase-js@2.46.1';
import { gfetch } from '../_shared/google.ts';

const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
const allDrives = () => (Deno.env.get('GOOGLE_SHARED_DRIVE_ID') ? '?supportsAllDrives=true' : '');

Deno.serve(async (req) => {
  if (!Deno.env.get('CRON_SECRET') || req.headers.get('x-cron-secret') !== Deno.env.get('CRON_SECRET')) return new Response('forbidden', { status: 403 });
  const { data: run } = await db.from('job_runs').insert({ job: 'drive_cleanup' }).select('id').single();
  const { data: orphans, error } = await db.from('orphan_documents').select('id, client_id, drive_file_id, drive_path').limit(200);
  let trashed = 0;
  const errors: string[] = [];
  for (const d of orphans ?? []) {
    try {
      const res = await gfetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(d.drive_file_id)}${allDrives()}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ trashed: true })
      });
      if (!res.ok && res.status !== 404) throw new Error(`Drive HTTP ${res.status}`);
      await db.from('documents').delete().eq('id', d.id).eq('staged', true);
      await db.from('system_events').insert({ level: 'info', component: 'drive_upload', client_id: d.client_id, message: `Unused upload moved to Drive trash: ${d.drive_path}` });
      trashed++;
    } catch (e) { errors.push(`${d.drive_path}: ${String(e).slice(0, 200)}`); }
  }
  await db.from('job_runs').update({ finished_at: new Date().toISOString(), ok: !error && errors.length === 0, rows_processed: trashed, error: error?.message ?? (errors.join('\n') || null) }).eq('id', run?.id);
  return new Response(JSON.stringify({ trashed, errors }), { headers: { 'Content-Type': 'application/json' } });
});
