// POST multipart: file, clientId, folder ("Vouchr/<Client>/FY 2026-27/Bills").
// Checks the caller may act for that client, files the document in Google Drive, logs usage and errors.
import { createClient } from 'npm:@supabase/supabase-js@2.46.1';
import { ensureFolderPath, uploadFile } from '../_shared/google.ts';

const admin = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
const MAX = 15 * 1024 * 1024;
const ALLOWED = /^(image\/(jpeg|png|webp|heic)|application\/pdf|application\/json|text\/csv|text\/plain)$/;

Deno.serve(async (req) => {
  const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, content-type, apikey, x-client-info' };
  if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
  const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status, headers: { ...cors, 'Content-Type': 'application/json' } });

  // who is calling? (RLS-aware client with the user's JWT)
  const user = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_ANON_KEY')!, { global: { headers: { Authorization: req.headers.get('Authorization') ?? '' } } });
  const form = await req.formData();
  const file = form.get('file');
  const clientId = String(form.get('clientId') ?? '');
  const folder = String(form.get('folder') ?? '');
  if (!(file instanceof File)) return json({ error: 'No file' }, 400);
  if (file.size > MAX) return json({ error: 'File larger than 15 MB' }, 413);
  if (!ALLOWED.test(file.type)) return json({ error: `File type ${file.type} not allowed` }, 415);
  // the user must be able to see this client (RLS), and the folder must be this client's folder
  const { data: client } = await user.from('clients').select('id, name').eq('id', clientId).maybeSingle();
  if (!client) return json({ error: 'Not allowed for this client' }, 403);
  if (!folder.startsWith('Vouchr/') || folder.includes('..')) return json({ error: 'Bad folder' }, 400);

  const t0 = Date.now();
  try {
    const folderId = await ensureFolderPath(folder);
    const up = await uploadFile(folderId, file.name, file);
    // Bills and challans are attached to a record by save_bill_document / the tds_challans trigger; until then they are
    // "staged", and drive-cleanup moves a staged file to Drive's trash if no record uses it within 24 hours.
    const kind = folder.split('/').find((p) => ['Bills', 'TDS Challans', 'Bank Statements', 'GSTR-2B', 'Branding'].includes(p));
    if (kind) {
      const sha = [...new Uint8Array(await crypto.subtle.digest('SHA-256', await file.arrayBuffer()))].map((b) => b.toString(16).padStart(2, '0')).join('');
      await admin.from('documents').upsert({ client_id: clientId, fy_label: /FY (\d{4}-\d{2})/.exec(folder)?.[1] ?? null, kind, drive_file_id: up.id,
        drive_path: `${folder}/${file.name}`, web_view_link: up.webViewLink, sha256: sha, staged: kind === 'Bills' || kind === 'TDS Challans' }, { onConflict: 'client_id,sha256', ignoreDuplicates: true });
    }
    await admin.from('api_usage').insert({ provider: 'drive', client_id: clientId, endpoint: 'upload', ok: true, latency_ms: Date.now() - t0 });
    return json({ fileId: up.id, webViewLink: up.webViewLink });
  } catch (err) {
    await admin.from('system_events').insert({ level: 'error', component: 'drive_upload', client_id: clientId, message: String(err).slice(0, 500) });
    await admin.from('api_usage').insert({ provider: 'drive', client_id: clientId, endpoint: 'upload', ok: false, latency_ms: Date.now() - t0, error: String(err).slice(0, 300) });
    return json({ error: 'Upload to Google Drive failed — the file is kept on the device and will retry.' }, 502);
  }
});
