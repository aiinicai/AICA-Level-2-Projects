PHASE 1 — Data model, config, and the hash-chained audit log.

Read AGENTS.md and ARCHITECTURE.md in the working directory first. They are authoritative.
Section 3.2 of ARCHITECTURE.md defines the data model. Build exactly that.

Create these files:

## 1. `src/amg/config.py`
Env-driven settings loaded via python-dotenv (`.env` if present, else process env).
Expose a frozen dataclass `Settings` with a module-level `get_settings()` (cached).
Fields, with the defaults from `.env.example`:
- `llm_provider` (default "gemini"), `gemini_api_key`, `gemini_model` (default "gemini-3.7-flash")
- `embed_provider` (default "voyage"), `voyage_api_key`, `voyage_model` (default "voyage-4-lite")
- `contextual_top_k` (int, default 6) — this is the P0 hard cap
- `contradiction_min_confidence` (float, default 0.60)
- `checker_strictness` (str, default "balanced"; one of lenient|balanced|strict)
- `export_passphrase` (default "capstone-demo-2026")
- `db_path` (default "amg_memory.db")
Also a `resolved_llm_provider()` / `resolved_embed_provider()` that downgrade to "stub"/"local"
when the corresponding API key is absent, so the rest of the code never has to check keys.

## 2. `src/amg/models.py`
Pydantic v2 models and enums mirroring the schema. At minimum:
- `SourceType` enum: `user_stated`, `ai_inferred`
- `MemoryStatus` enum: `active`, `flagged_conflict`, `superseded`, `deleted`
- `AssertionType` enum: `direct_self_statement`, `hypothetical`, `third_party`, `quoted`
- `EventType` enum: `write`, `write_rejected`, `contextual_read`, `full_export`, `update`, `delete`, `access_denied`
- `TrustTier` enum: `stated` (highest), `confirmed_inference`, `unconfirmed_inference` (lowest)
- `Memory` dataclass/model with every field from ARCHITECTURE.md 3.2 `memories`
- `AuditEvent` model with every field from `audit_log`
- `CandidateFact` — what the maker proposes: `content`, `subject_key`, `category`,
  `assertion_type`, `source_type`, `inferred_from_content` (optional str — the text of the
  sibling fact in the same turn it was inferred from; see note below)
- `CheckerVerdict` — `approved: bool`, `reason_code: str`, `notes: str`
- `EntailmentVerdict` — `contradicts: bool`, `confidence: float`, `reason: str`

IMPORTANT on `derived_from` parentage: because the maker may only read the current turn's user
text (hard rule 2), an `ai_inferred` memory's parent is always another candidate fact extracted
from the SAME turn. Example: user says "I'm strictly vegetarian" -> direct fact
"User is strictly vegetarian" plus inferred fact "User likely avoids leather products", whose
parent is the vegetarian fact. Model it that way.

## 3. `src/amg/db.py`
Plain `sqlite3` (no ORM). Provide:
- `connect(db_path) -> sqlite3.Connection` with `row_factory = sqlite3.Row` and
  `PRAGMA foreign_keys = ON`.
- `init_schema(conn)` — CREATE TABLE IF NOT EXISTS for all four tables from ARCHITECTURE.md 3.2:
  `memories`, `embeddings`, `derived_from`, `audit_log`. Use the exact field names from the spec.
  `memories.embedding_id` is an FK to `embeddings.id`. `derived_from` has
  (`memory_id`, `parent_memory_id`) both FKs to `memories.id`, PK on the pair.
  `audit_log` needs `id`, `event_type`, `memory_id` (nullable), `actor`, `timestamp`,
  `detail` (TEXT, JSON), `prev_row_hash`, `row_hash`.
  Index `memories.subject_key` and `memories.status`.
- `reset_db(db_path)` — drop the file and re-init. Used by tests and the demo harness.
- Timestamps: store as ISO-8601 UTC strings. Provide a `utc_now_iso()` helper. Do NOT use
  `datetime.utcnow()` (deprecated) — use `datetime.now(timezone.utc)`.

## 4. `src/amg/audit.py`
This is the heart of Phase 1. Module docstring must state it enforces P0 rules 1 and 8.

- `compute_row_hash(event_type, memory_id, actor, timestamp, detail_json, prev_row_hash) -> str`
  SHA-256 hex over a canonical, deterministic serialization of exactly those fields. Canonical
  means: JSON with `sort_keys=True`, `separators=(",", ":")`, explicit "" for None. Document the
  exact preimage format in a comment — a reviewer must be able to recompute a hash by hand.
- `append_event(conn, event_type, actor, detail: dict, memory_id=None) -> int`
  Reads the current last row's `row_hash` as `prev_row_hash` (genesis = 64 zeros), computes
  `row_hash`, inserts. Must be safe under a transaction.
- `verify_chain(conn) -> ChainVerification` where ChainVerification is a small model with
  `valid: bool`, `rows_checked: int`, `broken_at_row_id: int | None`, `reason: str`.
  Walks every row in id order, recomputes each hash, checks linkage to the previous row.
- `SAFE_DETAIL_KEYS` — an explicit allowlist of keys permitted in `detail`. Include things like
  `subject_key`, `category`, `source_type`, `trust_tier`, `assertion_type`, `status`,
  `content_sha256`, `field_changed`, `reason_code`, `result_count`, `top_k`, `provider`,
  `gate`, `cascade_count`, `dependent_ids`. NOT content, NOT any free text that could carry it.
- `assert_detail_safe(detail: dict)` — raises `AuditDetailViolation` if any key is outside the
  allowlist. `append_event` calls this. This turns hard rule 1 into something the code enforces
  rather than something a comment requests.
- `content_fingerprint(text) -> str` — SHA-256 hex of the content, for tamper-evidence without
  storing content.

## 5. `tests/test_phase1.py`
pytest, must pass offline with no keys. Cover:
- schema creates cleanly; all four tables and expected columns exist
- appending N events produces a chain that `verify_chain` reports valid
- **tamper test 1**: UPDATE an audit row's `detail` directly via SQL -> `verify_chain` returns
  invalid and identifies the right row
- **tamper test 2**: DELETE a middle audit row -> `verify_chain` returns invalid (chain linkage break)
- **tamper test 3**: modify a row's `row_hash` -> detected
- `assert_detail_safe` rejects a disallowed key (e.g. `{"content": "..."}`) and
  `append_event` refuses to write it
- genesis row has prev_row_hash of 64 zeros
- `compute_row_hash` is deterministic across calls and sensitive to every input field

## Constraints
- Python 3.11. Type hints on all public functions.
- stdlib `hashlib` only for hashing — no new dependency.
- No LLM or network calls anywhere in Phase 1.
- Do not create files outside the ones listed plus `src/amg/__init__.py`,
  `src/amg/providers/__init__.py`, `src/amg/demo/__init__.py`, `tests/__init__.py` as needed.

## Finish by
Running `python -m pytest tests/ -q` and pasting the real output. If anything fails, fix it and
re-run until green. Then print a one-paragraph summary of what you built and any decision you had
to make that the spec left open.
