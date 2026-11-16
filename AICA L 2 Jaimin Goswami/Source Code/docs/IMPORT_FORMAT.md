# Event import format

UTF-8 CSV with headers, a JSON array, or {"sample":true,"events":[...]} are accepted. The bundled sample files are complete examples. CSV is read as strings; empty cells do not become numeric zeros. File imports suppress new-publication alerts.

Required fields: kind (Economic, Corporate, Regulatory), title, category, and at least one of scheduled_at / published_at / effective_at / deadline_at. Non-sample rows require source_url. Choose the import source in the dialog; it overrides source_id in the file.

Strongly recommended: stable external_id. Without it, a deterministic fallback uses source URL, title, type, issuer and reporting period. Supply explicit external IDs for reliable revisions when titles change.

Common fields: country, authority, importance (Unknown/Low/Medium/High), status (Scheduled/Tentative/Published/Updated/Postponed/Cancelled), summary, source_url, document_url, source_updated_at, source_timezone, date_confirmed, sample, verification.

Dates: scheduled_at, published_at, effective_at, deadline_at, record_date, ex_date. Use YYYY-MM-DD for date-only records, or ISO timestamps with offset, e.g. 2026-11-13T18:00:00+05:30. An offset-free exact time is accepted only with a known source_timezone. Ambiguous/nonexistent DST local times are rejected; provide an offset. Estimated schedules must set date_confirmed=false or status=Tentative.

Economic fields: indicator, series_key, reporting_period, previous, forecast, actual, revised, provider_forecast, unit. Define series_key to include methodology/basis where relevant (for example headline/core, YoY/MoM, seasonally adjusted/unadjusted and base year). Charts additionally require matching units and never combine sample and source records. Forecast is the supplied consensus/forecast; provider_forecast is distinct. revised is retained exactly as the provider supplies it; do not infer which historical period it revises.

Corporate fields: company, symbol, isin, exchange, reporting_period, document_hash (optional verified SHA-256). Exact cross-source grouping requires matching ISIN, category, reporting period and document_hash. Without that evidence, matching issuer/title disclosures remain separate candidates. Do not supply arbitrary document hashes to force merges.

Regulatory fields: notice_number, supersedes_external_id. Effective dates and deadlines are separate. Source-supplied relationships are retained; the app does not infer legal supersession.

sample must be true for invented/test data. The import dialog can force all rows to sample; embedded sample=true is never demoted by the file-import workflow. Demo examples use fictional issuers and fabricated readings. They are not sourced market observations.

Optional source_reference_kind=feed identifies an RSS record whose individual filing URL is missing; source_url then points to the actual official feed. The interface explicitly labels this distinction. Do not claim the feed URL is the missing filing.

Unknown columns are ignored. Invalid rows are rejected individually, with run ID, row number and error recorded. Successfully validated rows remain committed. Imports over 100 MB must be split. Original documents remain external references; no automatic PDF copying is performed.
