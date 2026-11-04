// Supabase Edge Function (Deno). Scheduled quarterly by pg_cron (see 0002_platform_ops.sql).
// 1) Fetch each watched official page, normalise text, SHA-256 it, compare with last quarter.
// 2) Raise findings for changed / unreachable pages, unverified masters and the quarterly checklist.
// It NEVER edits tax masters — a CA reviews findings and edits masters by hand (audit-logged).
import { createClient } from 'npm:@supabase/supabase-js@2.46.1';

const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);

async function sha256(text: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

// Strip scripts/styles/tags/whitespace so cosmetic changes (ads, timestamps in markup) matter less.
function normalise(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

Deno.serve(async (req) => {
  // scheduled job: only pg_cron (with the shared secret) may run it — the anon key in the app is public
  if (!Deno.env.get('CRON_SECRET') || req.headers.get('x-cron-secret') !== Deno.env.get('CRON_SECRET')) return new Response('forbidden', { status: 403 });
  const trigger = new URL(req.url).searchParams.get('manual') ? 'manual' : 'schedule';
  const { data: run } = await db.from('compliance_runs').insert({ trigger }).select().single();
  const findings: Record<string, unknown>[] = [];
  let checked = 0, changed = 0, failed = 0;

  const { data: sources } = await db.from('compliance_sources').select('*').eq('active', true);
  for (const src of sources ?? []) {
    try {
      const res = await fetch(src.url, { headers: { 'User-Agent': 'Vouchr-ComplianceWatch/0.1' }, signal: AbortSignal.timeout(20000) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const text = normalise(await res.text());
      const hash = await sha256(text);
      checked++;
      const now = new Date().toISOString();
      if (src.last_hash && src.last_hash !== hash) {
        changed++;
        findings.push({
          run_id: run.id, source_id: src.id, area: src.area, kind: 'source_changed',
          title: `${src.name} has changed since last check`,
          detail: `Open ${src.url} and review new notifications/circulars. Excerpt: ${text.slice(0, 600)}`
        });
        await db.from('compliance_sources').update({ last_hash: hash, last_checked_at: now, last_changed_at: now }).eq('id', src.id);
      } else {
        await db.from('compliance_sources').update({ last_hash: hash, last_checked_at: now }).eq('id', src.id);
      }
    } catch (err) {
      failed++;
      findings.push({ run_id: run.id, source_id: src.id, area: src.area, kind: 'source_unreachable',
        title: `Could not check ${src.name}`, detail: String(err) });
    }
  }

  const { data: unverified } = await db.from('tds_rates').select('code, rate_pct').eq('verified', false);
  if (unverified?.length) {
    findings.push({ run_id: run.id, area: 'tds', kind: 'unverified_master',
      title: `${unverified.length} TDS rates not yet verified by CA`,
      detail: unverified.map((r) => `${r.code} (${r.rate_pct}%)`).join(', ') });
  }
  for (const [area, title, detail] of [
    ['due_dates', 'Quarterly review: TDS & GST due dates', 'Confirm TDS deposit due date, Form 140 due dates, GSTR-2B generation date.'],
    ['rcm', 'Quarterly review: RCM categories', 'Check CBIC rate notifications for changes to reverse-charge services.'],
    ['itc', 'Quarterly review: Section 17(5) blocked credits', 'Check CGST Act amendments affecting blocked credits.'],
    ['forms', 'Quarterly review: Form 140 file format (RPU/FVU version)', 'Check for a new FVU version before the next quarterly statement.']
  ]) findings.push({ run_id: run.id, area, kind: 'review_due', title, detail });

  if (findings.length) await db.from('compliance_findings').insert(findings);
  const status = failed === 0 ? 'ok' : checked === 0 ? 'failed' : 'partial';
  await db.from('compliance_runs').update({ finished_at: new Date().toISOString(), sources_checked: checked, changes_found: changed, status }).eq('id', run.id);
  await db.from('job_runs').insert({ job: 'compliance_quarterly', finished_at: new Date().toISOString(), ok: status !== 'failed', rows_processed: findings.length });
  if (failed) await db.from('system_events').insert({ level: 'warn', component: 'compliance_watch', message: `${failed} source(s) unreachable` });

  return new Response(JSON.stringify({ status, checked, changed, findings: findings.length }), { headers: { 'Content-Type': 'application/json' } });
});
