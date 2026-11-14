-- AI assist (Google Gemini API via the `ai-assist` Edge Function). Nothing here runs unless the firm adds a key.
-- Rules: AI output is a SUGGESTION stored for review; it never edits expenses, vendors or tax masters by itself.
-- Use a PAID Gemini tier for client documents: on the free tier Google may use submitted content to improve its products.

insert into api_providers (code, provider, secret_name, free_quota_monthly, unit_cost_inr, enabled, notes)
values ('ai', 'Google Gemini API', 'GEMINI_API_KEY', null, null, false,
        'Paid tier only for client data. Model set by GEMINI_MODEL secret. Search grounding billed per query beyond the free monthly allowance — check current pricing before enabling.')
on conflict (code) do nothing;

-- One row per AI call: what was asked, the structured answer, tokens used (for per-client cost reports).
create table ai_reviews (
  id            uuid primary key default gen_random_uuid(),
  client_id     uuid references clients(id),
  expense_id    uuid references expenses(id),
  task          text not null check (task in ('read_bill', 'voice_entry', 'analyse_invoice', 'reco_message', 'bank_match', 'narration',
                                         'hsn_suggest', 'ask_data', 'mis_commentary', 'notice_summary', 'compare_bills', 'norms_scan')),
  model         text not null,
  result        jsonb,
  sources       jsonb,               -- web pages the model cited (norms_scan)
  input_tokens  int,
  output_tokens int,
  ok            boolean not null,
  error         text,
  created_by    uuid references profiles(id),
  created_at    timestamptz not null default now()
);
create index ai_reviews_client_day on ai_reviews (client_id, created_at);
alter table ai_reviews enable row level security;
-- readable by the CA firm and by that client's admins; written only by the Edge Function (service role)
create policy ai_reviews_read on ai_reviews for select using (app_role() = 'super_admin' or (app_role() = 'client_admin' and client_id = app_client()));

-- AI-found rule changes land in the same compliance inbox the CA already works from
alter table compliance_findings drop constraint if exists compliance_findings_kind_check;
alter table compliance_findings add constraint compliance_findings_kind_check
  check (kind in ('source_changed', 'review_due', 'unverified_master', 'source_unreachable', 'ai_suggestion'));
alter table compliance_findings add column if not exists sources jsonb;

-- Schedule (only after the key is added and the CA has approved AI use). Monthly, a day after the page-change watch slot:
-- select cron.schedule('ai-norms-monthly', '0 7 2 * *',
--   $$ select net.http_post(url := 'https://<ref>.functions.supabase.co/ai-assist',
--        headers := jsonb_build_object('Content-Type','application/json','x-cron-secret','<CRON_SECRET>'),
--        body := jsonb_build_object('task','norms_scan')) $$);
