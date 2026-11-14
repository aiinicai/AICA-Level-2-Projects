// Supabase Edge Function (Deno), daily via pg_cron with the x-cron-secret header (see 0011_alerts_push_email.sql).
// 1) queue_due_alerts() adds today's alerts (same rules as the app).  2) New alerts go to the client's admins:
//    • phone notification (Web Push, standard VAPID keys — no third-party service) to every device they switched on;
//    • e-mail through the firm's own SMTP account (any provider: Google Workspace, Zoho, Microsoft 365, …).
// Either channel is skipped, and the alert stays in the app, when its settings are not configured.
// Not yet run against live push/e-mail services — see PENDING.md.
import { createClient } from 'npm:@supabase/supabase-js@2.46.1';
import webpush from 'npm:web-push@3.6.7';
import nodemailer from 'npm:nodemailer@6.9.16';

const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
const env = (k: string) => Deno.env.get(k) ?? '';
const APP = env('APP_URL') || 'https://vouchr.app';

const pushOn = !!(env('VAPID_PUBLIC_KEY') && env('VAPID_PRIVATE_KEY') && env('VAPID_SUBJECT'));
if (pushOn) webpush.setVapidDetails(env('VAPID_SUBJECT'), env('VAPID_PUBLIC_KEY'), env('VAPID_PRIVATE_KEY'));
const mailOn = !!(env('SMTP_HOST') && env('SMTP_USER') && env('SMTP_PASS') && env('SMTP_FROM'));
const mailer = mailOn ? nodemailer.createTransport({ host: env('SMTP_HOST'), port: Number(env('SMTP_PORT') || 465), secure: Number(env('SMTP_PORT') || 465) === 465,
  auth: { user: env('SMTP_USER'), pass: env('SMTP_PASS') } }) : undefined;
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));

Deno.serve(async (req) => {
  if (!env('CRON_SECRET') || req.headers.get('x-cron-secret') !== env('CRON_SECRET')) return new Response('forbidden', { status: 403 });
  const { data: run } = await db.from('job_runs').insert({ job: 'alerts_daily' }).select('id').single();
  const errors: string[] = [];
  const { data: queued, error: qErr } = await db.rpc('queue_due_alerts');
  if (qErr) errors.push(`queue: ${qErr.message}`);

  const since = new Date(Date.now() - 7 * 864e5).toISOString();
  const { data: alerts } = await db.from('notifications').select('id, client_id, kind, severity, title, body')
    .or('push_sent_at.is.null,email_sent_at.is.null').gte('created_at', since).not('ref', 'is', null).limit(500);
  let pushed = 0, mailed = 0;
  for (const a of alerts ?? []) {
    const { data: admins } = await db.from('profiles').select('id, email, email_alerts').eq('client_id', a.client_id).eq('role', 'client_admin').eq('active', true);
    const ids = (admins ?? []).map((u) => u.id);
    if (pushOn && ids.length) {
      const { data: subs } = await db.from('push_subscriptions').select('id, endpoint, p256dh, auth').in('user_id', ids);
      for (const s of subs ?? []) {
        try {
          await webpush.sendNotification({ endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } },
            JSON.stringify({ title: a.title, body: a.body ?? '', url: '/alerts', tag: a.kind }), { TTL: 86400 });
          pushed++;
        } catch (e) {
          const code = (e as { statusCode?: number }).statusCode;
          if (code === 404 || code === 410) await db.from('push_subscriptions').delete().eq('id', s.id); // device unsubscribed
          else errors.push(`push ${a.id}: ${String(e).slice(0, 150)}`);
        }
      }
    }
    if (mailOn) {
      for (const u of (admins ?? []).filter((x) => x.email && x.email_alerts)) {
        try {
          await mailer!.sendMail({ from: env('SMTP_FROM'), to: u.email!, subject: `Vouchr: ${a.title}`,
            text: `${a.title}\n${a.body ?? ''}\n\nOpen Vouchr: ${APP}/alerts\n\nYou can switch these e-mails off in Vouchr → Alerts.`,
            html: `<p><b>${esc(a.title)}</b></p><p>${esc(a.body ?? '')}</p><p><a href="${APP}/alerts">Open Vouchr</a></p><p style="color:#666;font-size:12px">You can switch these e-mails off in Vouchr → Alerts.</p>` });
          mailed++;
        } catch (e) { errors.push(`mail ${a.id}: ${String(e).slice(0, 150)}`); }
      }
    }
    // marked as handled for each channel that is set up, so an alert is not sent again tomorrow
    await db.from('notifications').update({ ...(pushOn ? { push_sent_at: new Date().toISOString() } : {}), ...(mailOn ? { email_sent_at: new Date().toISOString() } : {}) }).eq('id', a.id);
  }
  if (errors.length) await db.from('system_events').insert({ level: 'warn', component: 'push', message: errors.slice(0, 5).join(' | ').slice(0, 500) });
  await db.from('job_runs').update({ finished_at: new Date().toISOString(), ok: errors.length === 0, rows_processed: (queued as number) ?? 0, error: errors.join('\n').slice(0, 2000) || null }).eq('id', run?.id);
  return new Response(JSON.stringify({ queued, pushed, mailed, push: pushOn, email: mailOn, errors: errors.length }), { headers: { 'Content-Type': 'application/json' } });
});
