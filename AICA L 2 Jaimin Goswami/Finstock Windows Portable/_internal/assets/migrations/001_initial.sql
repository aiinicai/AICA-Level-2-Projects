CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE data_sources(
 id TEXT PRIMARY KEY, name TEXT NOT NULL, adapter TEXT NOT NULL, url TEXT NOT NULL DEFAULT '',
 kind TEXT NOT NULL DEFAULT 'Regulatory', authority TEXT NOT NULL DEFAULT '', country TEXT NOT NULL DEFAULT '',
 enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN(0,1)), interval_seconds INTEGER NOT NULL DEFAULT 900 CHECK(interval_seconds>=60),
 status TEXT NOT NULL DEFAULT 'Not Configured', last_attempt TEXT, last_success TEXT, next_attempt TEXT,
 last_error TEXT NOT NULL DEFAULT '', failures INTEGER NOT NULL DEFAULT 0, config TEXT NOT NULL DEFAULT '{}',
 terms_url TEXT NOT NULL DEFAULT '', rights_note TEXT NOT NULL DEFAULT '', checkpoint TEXT
);
CREATE TABLE event_definitions(id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, category TEXT NOT NULL);
CREATE TABLE economic_indicators(id TEXT PRIMARY KEY REFERENCES event_definitions(id), country TEXT, authority TEXT, unit TEXT, series_key TEXT);
CREATE TABLE companies(id TEXT PRIMARY KEY, name TEXT NOT NULL, isin TEXT);
CREATE TABLE exchange_listings(id TEXT PRIMARY KEY, company_id TEXT NOT NULL REFERENCES companies(id), exchange TEXT, symbol TEXT, isin TEXT);
CREATE TABLE events(
 id TEXT PRIMARY KEY, definition_id TEXT NOT NULL REFERENCES event_definitions(id),
 kind TEXT NOT NULL CHECK(kind IN('Economic','Corporate','Regulatory')), title TEXT NOT NULL,
 country TEXT NOT NULL DEFAULT '', category TEXT NOT NULL, authority TEXT NOT NULL DEFAULT '',
 company TEXT NOT NULL DEFAULT '', symbol TEXT NOT NULL DEFAULT '', isin TEXT NOT NULL DEFAULT '', exchange TEXT NOT NULL DEFAULT '',
 importance TEXT NOT NULL, status TEXT NOT NULL, sample INTEGER NOT NULL CHECK(sample IN(0,1)),
 scheduled_at TEXT, published_at TEXT, effective_at TEXT, deadline_at TEXT, record_date TEXT, ex_date TEXT,
 date_confirmed INTEGER NOT NULL, series_key TEXT NOT NULL DEFAULT '', reporting_period TEXT NOT NULL DEFAULT '',
 payload TEXT NOT NULL, fingerprint TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL, retrieved_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX events_schedule ON events(scheduled_at);
CREATE INDEX events_publication ON events(published_at);
CREATE INDEX events_kind_country ON events(kind,country,category);
CREATE INDEX events_company ON events(isin,symbol,company);
CREATE INDEX events_series ON events(series_key,reporting_period);
CREATE TABLE source_records(
 source_id TEXT NOT NULL REFERENCES data_sources(id), external_id TEXT NOT NULL,
 event_id TEXT NOT NULL REFERENCES events(id), source_url TEXT NOT NULL, source_updated_at TEXT,
 retrieved_at TEXT NOT NULL, fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(source_id,external_id)
);
CREATE TABLE event_revisions(
 id INTEGER PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id), revision INTEGER NOT NULL,
 source_id TEXT NOT NULL REFERENCES data_sources(id), recorded_at TEXT NOT NULL,
 source_updated_at TEXT, payload TEXT NOT NULL, changed_fields TEXT NOT NULL, UNIQUE(event_id,revision)
);
CREATE TABLE economic_observations(
 id INTEGER PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id), revision INTEGER NOT NULL,
 series_key TEXT NOT NULL, reporting_period TEXT, role TEXT NOT NULL, value_text TEXT, value_decimal TEXT,
 unit TEXT, source_id TEXT NOT NULL, recorded_at TEXT NOT NULL,
 UNIQUE(event_id,revision,role)
);
CREATE INDEX observations_series ON economic_observations(series_key,reporting_period,recorded_at);
CREATE TABLE corporate_announcements(event_id TEXT PRIMARY KEY REFERENCES events(id), company_id TEXT REFERENCES companies(id), document_hash TEXT);
CREATE TABLE regulatory_notices(event_id TEXT PRIMARY KEY REFERENCES events(id), notice_number TEXT, supersedes_external_id TEXT);
CREATE TABLE original_documents(id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id), source_id TEXT NOT NULL, url TEXT NOT NULL, sha256 TEXT);
CREATE TABLE duplicate_candidates(id INTEGER PRIMARY KEY, event_a TEXT NOT NULL REFERENCES events(id), event_b TEXT NOT NULL REFERENCES events(id), reason TEXT NOT NULL, decision TEXT NOT NULL DEFAULT 'Pending', UNIQUE(event_a,event_b));
CREATE TABLE knowledge_articles(id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, kind TEXT NOT NULL, definition TEXT NOT NULL, importance TEXT NOT NULL, frequency TEXT NOT NULL, sources TEXT NOT NULL, reviewed_at TEXT NOT NULL);
CREATE TABLE watchlists(id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL);
CREATE TABLE watchlist_members(watchlist_id TEXT NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE, member TEXT NOT NULL, PRIMARY KEY(watchlist_id,member));
CREATE TABLE user_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE notification_rules(id TEXT PRIMARY KEY,name TEXT NOT NULL,enabled INTEGER NOT NULL CHECK(enabled IN(0,1)), filters TEXT NOT NULL, offsets TEXT NOT NULL, triggers TEXT NOT NULL, grace_seconds INTEGER NOT NULL CHECK(grace_seconds>=0), include_samples INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE notification_jobs(
 id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id), rule_id TEXT REFERENCES notification_rules(id),
 trigger TEXT NOT NULL, generation TEXT NOT NULL, offset_seconds INTEGER NOT NULL DEFAULT 0,
 due_at TEXT NOT NULL, expires_at TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'Pending',
 created_at TEXT NOT NULL, sent_at TEXT, opened_at TEXT, last_error TEXT NOT NULL DEFAULT '', attempts INTEGER NOT NULL DEFAULT 0,
 title TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(event_id,trigger,generation,offset_seconds)
);
CREATE INDEX notification_due ON notification_jobs(state,due_at);
CREATE TABLE notification_attempts(id INTEGER PRIMARY KEY,job_id TEXT NOT NULL REFERENCES notification_jobs(id),attempted_at TEXT NOT NULL,outcome TEXT NOT NULL,detail TEXT);
CREATE TABLE ingestion_logs(id INTEGER PRIMARY KEY,source_id TEXT NOT NULL REFERENCES data_sources(id),started_at TEXT NOT NULL,completed_at TEXT,mode TEXT NOT NULL,inserted INTEGER NOT NULL DEFAULT 0,updated INTEGER NOT NULL DEFAULT 0,duplicates INTEGER NOT NULL DEFAULT 0,rejected INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'Running');
CREATE TABLE ingestion_errors(id INTEGER PRIMARY KEY,run_id INTEGER NOT NULL REFERENCES ingestion_logs(id),row_number INTEGER NOT NULL,message TEXT NOT NULL,record_ref TEXT NOT NULL DEFAULT '');

