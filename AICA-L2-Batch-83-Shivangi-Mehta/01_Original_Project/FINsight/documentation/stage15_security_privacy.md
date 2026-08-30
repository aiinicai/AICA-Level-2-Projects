# Stage 15 — Security, Privacy & Offline-First Hardening

Status: **Complete.** Audit-first, then hardening, then verification, exactly as instructed. No Accounting/Audit/Tax/Unified Review/Query business logic was modified. No database schema change was made or required.

---

## 1. Security Reconnaissance

A full source-level review was performed before any code was changed, covering: the Flask application factory (`app/__init__.py`), every blueprint/route, session handling, the database engine/ORM layer, every SQL/ORM query, file upload handling and storage, evidence handling, the (placeholder) export path, logging, configuration/environment variables, debug settings, error handling, static file serving, every frontend template/form/hidden field/URL parameter, all JavaScript, all dependencies, and the filesystem layout (upload directory, path construction, filename handling). Findings are organized below by the exact section numbers the governing instruction requested.

---

## 2. Network / Offline Findings

**No outbound network call exists anywhere in FinSight's own source.** A static scan (now a permanent regression test, `test_no_outbound_network_call_in_application_source`) searched every `.py` and `.js` file for `requests.*`, `urllib.request`, `httpx.`, `aiohttp.`, `socket.socket(`, `fetch(`, and `XMLHttpRequest` — none found, with one confirmed false-positive excluded and documented (`frontend/static/js/api.js` is a 3-line, code-free stub whose only content is a comment reading "Thin fetch() wrapper — stub."). `app/mapping/structure_detector.py` contains the literal word "requests" only inside a docstring sentence ("...between two different uploads that happen to share a filename... requests."), not the Python `requests` library.

`requirements.txt` does not list `requests`, `httpx`, or `aiohttp` at all — the only reference to `requests` in the whole repository is a *commented-out* line reserved for a future, explicitly-opt-in AI feature (see section 3).

`wsgi_lan.py` contains the literal string `http://` twice, both in human-readable docstring/print text describing the LAN URL a user would type into their own browser — not a call FinSight makes.

---

## 3. External API Findings

No AI provider integration exists. `app/ai/` contains only two `__init__.py` files with planning-stage docstrings for a future, explicitly opt-in Stage 16 feature ("AI adapter package — populated in Stage 16... must never be called implicitly"). `app/ai/providers/disabled_provider.py` and `external_api_provider.py` — the files those docstrings describe — **do not exist yet**. The only live code is `app/api/ai_bp.py`, a stub blueprint whose one route (`/api/ai/ping`) returns a static `{"status": "stub", "area": "ai", "enabled": false}` and calls nothing else.

A static scan for `OpenAI`, `Anthropic`, `Claude`, `Gemini`, `Google AI`, `Perplexity`, `API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` across all application source found **zero matches** (`test_no_external_ai_provider_wired_up`). `Config.AI_ENABLED` defaults to `False` and nothing in the codebase reads it to make an external call.

---

## 4. File Upload Review

`app/services/upload_service.py`'s `_build_stored_path()` was already sound before this stage: it runs every filename through Werkzeug's `secure_filename()` (stripping directory separators and unsafe characters), adds a timestamp+random suffix, and — critically — resolves the final path and confirms with `os.path.commonpath()` that it still sits inside the engagement's own subfolder before anything is written, raising `ValueError` if not. `app/upload/validation.py` restricts uploads to exactly `.csv`/`.xlsx` (legacy `.xls` deliberately excluded — it would need the unapproved `xlrd` package). `MAX_CONTENT_LENGTH` is wired to Flask/Werkzeug at the WSGI layer, rejecting an oversized upload before it's read into memory (pre-existing 413 handler). No route anywhere in the app calls `send_file`/`send_from_directory` — uploaded files are read server-side for parsing only, never streamed back to a browser, eliminating a whole class of download-based path-traversal risk. This posture is now covered by a permanent regression suite (7 tests) rather than resting on manual review alone.

---

## 5. Path Traversal Review

Tested directly against `_build_stored_path()` and via full HTTP upload round-trips with the exact hostile filenames the governing instruction listed (`../../../test.txt`, `..\..\test.txt`, `../../app.py`, `/etc/passwd`, `C:\temp\test.txt`, `test;rm.txt`, `test<script>.csv`) — every resolved stored path stayed confined to the uploading engagement's own subfolder of `DATA_INPUT_DIR`, and no traversal payload ever escaped it. A full-HTTP test additionally confirmed a real application source file (`app/__init__.py`) is byte-for-byte unchanged after an upload deliberately crafted to target it by relative path.

---

## 6. Engagement Isolation Review

FinSight has no user-account model (confirmed — see section 3 of the completion table and the code search in section 11) — there is one person per local install, so "isolation" here means what it must mean for a single-user tool: switching the *current engagement* must never let one engagement's data leak into another's view. This was already correctly enforced for the object-scoped screens before this stage (`mapping_bp.py`/`validation_bp.py`'s `_get_engagement_scoped_upload()`, `exceptions_bp.py`'s explicit `engagement_id` match, `review_bp.py`'s `get_finding()` engagement-scoped lookup) — confirmed, not assumed, with 6 new end-to-end tests: creating real data under "Engagement A", switching to "Engagement B", and confirming Engagement B's Working Paper, Finding Detail, Mapping, Data Quality, Findings Centre, and Query Centre routes/listings never expose or 404-leak Engagement A's records.

One deliberate exception, by design rather than oversight: `/engagement/<id>/profile` and `/engagement/<id>/applicability` accept any valid engagement id regardless of which one is "current" — this is intentional (the Engagements list screen links directly to any engagement's own profile/applicability without first switching to it), not a gap, since there is no ownership boundary to cross in a single-user local tool.

---

## 7. IDOR Review

Every route that accepts an object id was reviewed: `/engagement/<id>/*` (see section 6's note), `/data/mapping/<file_id>/`, `/data/quality/<file_id>/` (both engagement-scoped, pre-existing), `/exceptions/<exception_id>/` (engagement-scoped, pre-existing since Stage 13), `/review/findings/<module>/<finding_id>` (engagement-scoped via `get_finding()`, pre-existing since Stage 12). No route was found that trusts an object id without checking it against the current engagement where that check matters. No code or schema change was required — this stage added tests that prove the existing design, rather than new enforcement code.

---

## 8. SQL Injection Review

No raw SQL, no `.format()`/`%`/f-string query building, no `sqlalchemy.text()`, and no dynamic `ORDER BY`/filter-clause construction from user input exist anywhere in `app/services/` or `app/models/` — every query is a parameterized `select()...where()` ORM call, and every search/filter feature (Query Centre search, Findings Centre filters) does its matching in **Python**, not SQL (`query_service.list_queries()`'s `needle in (...).lower()` pattern). This is structural, not incidental — there is no code path where injection syntax could reach the database as anything other than an inert string value. Verified empirically, not just by inspection: `'`, `"`, `;`, `--`, `OR 1=1`, and `'; DROP TABLE engagements; --` were submitted through the Query Centre search box, the Findings Centre filters, and the New Engagement form — every request returned a normal 200/302, and the `engagements` table was confirmed intact afterward in every case.

---

## 9. XSS Review

Flask's Jinja autoescaping is on (the framework default for `.html` templates — confirmed no `autoescape=False` anywhere, and confirmed no template uses `|safe` or `Markup()` **except one new, deliberate, reviewed exception**: `csrf_field()` in `app/security/csrf.py`, which emits a hidden `<input>` built entirely from a server-generated random hex token — never user input — see section 13). `<script>alert("test")</script>` was submitted as an entity name and as Working Paper reviewer notes; both rendered back as literal, inert text (`&lt;script&gt;...`), never as an executable tag, confirmed in the actual rendered HTML by 3 new tests.

---

## 10. CSRF Review

**Before this stage:** no CSRF protection existed anywhere. This was already recorded, disclosed, and deliberately deferred — `wsgi_lan.py`'s own docstring already documented it as a "MANDATORY PRE-LAN REQUIREMENT... deliberately NOT added now... belongs immediately before [LAN mode]" (the stage numbering in that comment is stale — it predates the current renumbering — but the substance is exactly this stage's job).

**Implemented:** a plain synchronizer-token check (`app/security/csrf.py`), standard-library only (`secrets` + the existing Flask session) — no new dependency, since Flask-WTF was never on the approved package list. Every GET response mints (or reuses) a per-session random token; `{{ csrf_field() }}` renders it as a hidden field into every one of the app's 13 `<form method="post">` blocks (confirmed complete by a new regression test that scans every template and fails if any POST form is missing the field); a `before_request` hook rejects any POST/PUT/PATCH/DELETE whose submitted token doesn't match the session's, with a friendly 400 page, before the view function runs. `CSRF_ENABLED` defaults to `True` for the real application (both `run.py` and `wsgi_lan.py` use it) and is turned off only in `TestConfig`, mirroring Flask-WTF's own well-established `WTF_CSRF_ENABLED = False` test convention — chosen specifically so the ~150 pre-existing HTTP tests across 11 files did not all need to be individually retrofitted to scrape and resubmit a token, while real enforcement is still exercised directly and completely by 6 new tests using a separate config with it explicitly re-enabled (missing token rejected, correct token accepted, wrong token rejected, GET never blocked).

This did **not** require a major authentication/session redesign — Flask's session mechanism has been in place since Stage 5 — so it proceeded without a STOP, per the governing instruction's own framing of when a STOP is required.

---

## 11. Session / Secret Review

No authentication exists (confirmed — no `password`, `login`, `authenticate`, or `current_user` anywhere in `app/`); the session holds exactly two keys: `current_engagement_id` (Stage 5) and the new `_csrf_token` (this stage). `SECRET_KEY` reads from `FINSIGHT_SECRET_KEY` with a documented development-only fallback; `wsgi_lan.py` already refuses to start if that fallback is still in effect (a pre-existing, correct guard, unchanged). `SESSION_COOKIE_HTTPONLY = True` and `SESSION_COOKIE_SAMESITE = "Lax"` were added explicitly to `config.py` (Flask already defaults `HTTPONLY` to `True`; stating it in source makes the decision visible rather than resting on an unstated framework default). `SESSION_COOKIE_SECURE` was deliberately left at its default `False` — this app is served over plain HTTP by design (no TLS termination exists anywhere in the stack), so `Secure` would silently break every session cookie rather than add protection; documented here as a conscious decision, not an oversight, and revisited automatically if HTTPS is ever added.

`run.py`'s dev launcher previously hard-coded `debug=True`. Flask's interactive debugger, when enabled, lets anyone who can reach an error page execute arbitrary Python via the browser once they have the console PIN — a real risk to default to on, even though this launcher only binds to `127.0.0.1`. Changed to default off, with an explicit opt-in (`FINSIGHT_DEV_DEBUG=true python run.py`) for local development. `wsgi_lan.py` never enabled debug mode and is unchanged.

---

## 12. Error Handling

Flask/Werkzeug's own default behavior already never shows a traceback, SQL query, filesystem path, or environment variable for a generic 500 when `app.debug` is `False` (i.e., always, outside the explicit local dev opt-in above). This stage adds `400`/`403`/`404`/`500` handlers (`app/__init__.py`) that render FinSight's own styled `error.html` with a plain-English message instead of Werkzeug's bare default page — e.g. the CSRF-rejection message reads "Your session appears to have expired, or this form was submitted from an unexpected source. Please go back, refresh the page, and try again." rather than any protocol-level text. Verified directly: neither a 404 nor a CSRF-triggered 400 response contains the word "Traceback", a `File "` frame marker, or this repository's own absolute path.

---

## 13. Logging Review

`app/utils/logging_config.py` is unchanged — a plain rotating file handler with no business-data logging of any kind. A static scan (`test_no_application_code_logs_reviewer_or_financial_content`) confirmed no `logger.*()`/`log.*()` call anywhere in the codebase references `reviewer_notes`, `evidence_description`, `evidence_reference`, `file_bytes`, or `management_response`. In fact, **no application code calls `app.logger` at all today** — the only thing written to `logs/finsight.log` is whatever Flask/Werkzeug itself logs (request lines: method, path, status — not request bodies), which is a data-minimal posture by default rather than something this stage had to add.

---

## 14. Database Exposure Review

The SQLite file lives at `database/finsight.db`, entirely outside `frontend/static/` (Flask's only file-serving route, `/static/<path>`, is rooted at `frontend/static/` and cannot reach it). Directly probing `/database/finsight.db`, `/.env`, and `/static/../database/finsight.db`-style traversal attempts all returned 404/400 with no file content and no `SECRET_KEY` string present in the response — confirmed by 6 new tests. `database/finsight.db`, `data/input/*`, `data/processed/*`, `data/output/*`, and `logs/` were already correctly listed in `.gitignore` before this stage (confirmed, not added).

---

## 15. Static File Exposure Review

Only `frontend/static/css/`, `frontend/static/js/` are served, and both were confirmed reachable exactly as intended (`/static/css/design-system.css`, `/static/js/forms.js` → 200) while nothing outside that directory is reachable through it (section 14).

---

## 16. Dependency Review

| Package | Version | Reason | Security relevance |
|---|---|---|---|
| Flask | >=3.0,<4.0 | Web framework | Core; kept current within the approved major version |
| SQLAlchemy | >=2.0,<3.0 | ORM | Parameterized queries only — see section 8 |
| alembic | >=1.13,<2.0 | Migrations | Not installable in this sandbox (pre-existing, disclosed gap); no change |
| pandas | >=2.2,<3.0 | CSV/XLSX parsing | Local file parsing only, no network |
| openpyxl | >=3.1,<4.0 | XLSX parsing | Local only |
| reportlab | >=4.1,<5.0 | **Unused** — Reports (`reports_bp.py`) is still a placeholder | No current relevance; revisit when Reports is actually built |
| pydantic | >=2.6,<3.0 | **Unused** — no import of it exists anywhere in `app/` today | No current relevance |
| waitress | >=3.0,<4.0 | LAN mode WSGI server | Pure-Python, no C extension attack surface |
| python-dotenv | >=1.0,<2.0 | **Unused** — `load_dotenv()` is never called anywhere | Low: a declared-but-inert dependency, not a risk itself, but worth trimming for a leaner packaged build (Stage 17) |
| pytest / pytest-cov | dev-only | Test suite | Not shipped in a real deployment; a future EXE-packaging stage should confirm dev deps are excluded from that build |

No unnecessary networking package (`requests`, `httpx`, `aiohttp`, etc.) is installed. No dependency was upgraded or added this stage.

---

## 17. Debug/Production Configuration

`run.py` (local dev, loopback-only) now defaults `debug=False`, opt-in via `FINSIGHT_DEV_DEBUG=true` (section 11). `wsgi_lan.py` (the actual LAN-facing launcher) never enabled Flask's debug mode and already refuses to start on the development `SECRET_KEY` fallback — both pre-existing, correct, and unchanged. `TestConfig` is unambiguously test-only (`TESTING = True`, in-memory DB, `CSRF_ENABLED = False`) and is never the default for either launcher.

---

## 18. Security Fixes Made

- **CSRF protection** implemented app-wide (section 10) — the one item the codebase itself had already flagged as required before LAN mode.
- **`SESSION_COOKIE_HTTPONLY`/`SESSION_COOKIE_SAMESITE`** set explicitly (section 11) — small, safe, zero-dependency defense-in-depth.
- **`run.py` debug mode** defaulted off instead of hard-coded on (section 11).
- **`PRAGMA foreign_keys=ON`** enabled for every SQLite connection (`app/extensions.py`) — SQLite does not enforce declared `ForeignKey` constraints by default; every current delete in the codebase already goes through SQLAlchemy's own cascade-aware relationships in the correct order, so this is additive safety with no behavior change, confirmed by the full existing test suite still passing unmodified.
- **Custom `400`/`403`/`404`/`500` error pages** (section 12) replacing Werkzeug's bare defaults with FinSight's own styled, plain-English messaging.
- **Reports placeholder copy** — out of scope for this stage; unchanged from Stage 14.

No rule logic, schema, migration, or query business logic was touched by any of the above.

---

## 19. Remaining Limitations

- **No genuine multi-user authentication exists**, by design (Blueprint decision, not a Stage 15 gap) — "engagement isolation" in this report means current-engagement-context isolation for a single local user, not a multi-tenant security boundary. A real LAN deployment with more than one person accessing the same running instance (Stage 16) will need to revisit this explicitly, as `wsgi_lan.py`'s own docstring already flags ("a single shared optional-password gate, not multi-user accounts").
- **No database-at-rest encryption.** SQLite stores data in plaintext on local disk; anyone with filesystem access to the machine (or its backups) can read `database/finsight.db` directly. This is a genuine limitation, documented here rather than solved with an invented encryption scheme this stage was explicitly told not to build.
- **`SESSION_COOKIE_SECURE` is `False`** because the app is plain HTTP by design — see section 11.
- **No true network-namespace-isolated test was run** — outbound raw-socket connectivity to an external host was confirmed blocked in this sandbox by default (see section 20), and the full application/workflow suite passed under that condition, but this is not the same as a dedicated `unshare`/firewall-rule test built for this purpose. Stated honestly rather than claimed as more than it is.
- **`reportlab`, `pydantic`, `python-dotenv` are declared but unused** (section 16) — not a security risk today, worth trimming before EXE packaging.
- **Dev-only test dependencies** (`pytest`, `pytest-cov`) should be confirmed excluded from any future packaged EXE build (Stage 17's concern, not this stage's).

---

## 20. Security Test Results

Run with the sandbox ORM shim (`PYTHONPATH=/tmp/shim_site`, `/tmp/testenv/bin/python -m pytest`):

```
637 passed, 71 warnings in 14.94s
```

(with `tests/unit/test_models.py` and `tests/unit/test_migration.py` excluded — the same 2 pre-existing, environment-only gaps disclosed in every prior stage's report: a sandbox `sqlalchemy.exc` shim gap and a missing `alembic` package, both unrelated to any Stage 15 change and re-confirmed unchanged by re-running them separately.)

New: `tests/test_stage15_security.py` — 61 tests covering every item in the governing instruction's section 24 list (offline/no-AI/no-CDN static scans, upload extension restriction, path-traversal/absolute-path protection with the exact hostile filenames specified, cannot-overwrite-application-files, 6 engagement-isolation end-to-end tests, SQL-injection-resistance with the exact payloads specified, XSS-escaping, error-response exposure, secrets-not-exposed, database/static-file exposure, evidence-reference stays a plain string with no serving route, sensitive-content-not-logged, SEBI-remains-non-executable, and CSRF enforcement itself).

Reconciliation: 576 (Stage 14 end) + 61 (new) = 637. Matches exactly. Every pre-existing Accounting (Stage 8), Audit (Stage 9), Tax (Stage 10), Unified Review (Stage 12), Query & Working Papers (Stage 13), and UX (Stage 14) test still passes unmodified.

**Real, not merely simulated, offline evidence:** this sandbox's outbound raw-socket connectivity to an external IP (`8.8.8.8:53`) was directly confirmed to time out by default — i.e., this environment is genuinely network-restricted, not merely assumed to be. The entire 637-test suite, including complete Upload → Map → Validate → Run Review → Query → Working Paper HTTP round trips, and Stage 14's real browser-driven (Playwright) visual QA pass over a fully seeded instance, ran successfully throughout every prior stage under that same restricted condition — this is genuine evidence the application does not depend on internet connectivity for normal operation, not a claim made without having actually run it that way.

---

## 21. Deployment Recommendations for Stage 16/17

- **Stage 16 (LAN mode):** CSRF protection and `SameSite=Lax` cookies are now in place, satisfying `wsgi_lan.py`'s own pre-existing pre-LAN requirement. Still needed before real multi-person LAN use: decide and implement the "single shared optional-password gate" `wsgi_lan.py`'s docstring already anticipates — this stage deliberately did not build any authentication, per the explicit instruction not to.
- **Stage 17 (EXE packaging):** confirm `pytest`/`pytest-cov` (and `reportlab`/`pydantic`/`python-dotenv` if still unused by then) are excluded from the packaged build; confirm the packaged app never runs with `FINSIGHT_DEV_DEBUG=true`; confirm `FINSIGHT_SECRET_KEY` is generated fresh per install rather than shipping the development fallback.
- **General:** document for end users that `database/finsight.db`, `data/input/`, `data/processed/`, `data/output/`, and `logs/` together constitute "the FinSight data directory" and should be backed up before moving between computers or upgrading versions (Stage 15 section 22) — no backup system was built (none exists today and none was requested), this is a documentation recommendation only.

---

## Privacy Statement Accuracy Review (section 23)

The existing footer statement — "FinSight is designed for local/offline financial data processing. Client financial data is not sent to external AI or cloud services by the application." — was re-verified against the actual code in this stage (sections 2-3 above) and remains accurate: no outbound network call and no AI provider integration exist. No stronger claim ("fully secure", "zero risk", "encrypted", "100% private") is made anywhere in the application, and none is added by this stage — `database/finsight.db` is explicitly documented above (section 19) as unencrypted at rest, so an "encrypted" claim would be false.
