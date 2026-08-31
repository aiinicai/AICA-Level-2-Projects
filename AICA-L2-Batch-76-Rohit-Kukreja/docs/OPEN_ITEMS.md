# Open items

Written 17 August 2026, at the end of a working session. Everything here is
known and unfinished rather than forgotten.

## ~~1. Creating a client is not covered end to end~~ — CLOSED 17 Aug 2026

Seven cases in `tests/test_new_client.py` pass, none skipped.

The cause was in the test, not the application, and is worth remembering:
the payload was built as a **list of 2-tuples**, which httpx does not
form-encode when passed as `data=`. The body arrived empty, `request.form()`
saw nothing, and the route reported "Missing CSRF token" — a message that read
like a CSRF fault and was nothing of the kind. Repeated field names go in as
`{"director_name": [...]}`.

## ~~2. Partner management is not built~~ — CLOSED 17 Aug 2026

`add_partner`, `update_partner` and `signing_partners` in
`app/services/client.py`; `POST /admin/partners` and
`POST /admin/partners/{partner_id}`; editable rows plus an add form on the
firm screen. Eleven tests in `tests/test_partners.py`.

**There is no delete.** A partner named on a document already issued must stay
findable, so leaving the firm sets `active = False`, and `signing_partners`
excludes them from the signature block.

## ~~3. Multiple CA firms is not built~~ — CLOSED 17 Aug 2026

`create_firm`, `all_firms`, `active_firm` and `ACTIVE_FIRM_COOKIE` in
`app/services/client.py`; `POST /admin/firms` and `POST /admin/firms/switch`;
a firm picker in the sidebar that appears once there is more than one firm; a
firms table with per-firm client counts on the admin screen. `search_clients`,
`dashboard_tiles` and `recent_engagements` all take `firm_id`. Eleven tests in
`tests/test_multi_firm.py`.

**The active firm is a working filter, not access control.** There is no
login, so a client belonging to another firm is still reachable by its own URL.
That is asserted deliberately by
`test_switching_is_not_access_control`, and stated on the admin page itself, so
nobody later mistakes the picker for a permission boundary. If it ever needs to
be a boundary, the single-user decision has to be revisited first.

Two bugs found and fixed while building it: `/admin/firm` was editing and
listing the partners of the FIRST firm rather than the active one, and
`needs_review` referenced a session it never received.

## ~~4. Carry-forward covers only two documents~~ — CLOSED 17 Aug 2026

`DOCUMENT_CATEGORIES` was hard-coded to the auditor's report and the CARO
annexure. It is now `document_categories(clause_set)`, derived from the
manifest, so a document added there appears automatically.

This was a **defect against the approved register**, not an open design
question: every document already carries per-clause `carry_forward` policies
the register approved — 46 clauses marked `prompt` across the MRL, IFC annexure
and Board's Report — and the document-level gate silently overrode all of them.
A 32-clause representation letter was being re-answered from scratch each year.

The engagement letter is excluded on purpose, in `NEVER_CARRIED` with its
reason: Gate C decision 18 requires a fresh letter every year.

## ~~5. `bdr.directors.kmp` is typed, not computed~~ — CLOSED 17 Aug 2026

The clause now uses `director_changes_in_year`, a **computed** entity with no
table, derived from the client's director register by
`app.services.engagement._director_changes_in_year`. Read-only in the
workspace, which says so and points at the client screen instead.

`COMPUTED_CHILD_ROWS` is the general mechanism; `is_computed()` tells the
template not to offer add or delete. The old `bdr_director_change` table is
unused and documented as such — **dropping it is a separate migration**, not
bundled here, because a table that may hold a firm's data should not be deleted
in passing.

---

# Nothing else is outstanding

Every item raised in this project has been closed. What remains is not
engineering:

- **Gate D** — the parallel run against three real FY 2024-25 clients,
  comparing AuditCraft's output against what the firm actually issued. No test
  substitutes for it.
- **Reading the clause wording.** Gate A was signed off as a blanket
  instruction rather than a clause-by-clause read; `gate_a_pack/` remains the
  way to do it properly, and `content/manifest.yaml` records honestly how the
  sign-off happened.
- **The firm's own Word template** still carries the "Emphasis of Matter (if
  there are any qualifications...)" line, which conflates two different things.
  This tool does not reproduce it and cannot fix it.

## Housekeeping done 17 Aug 2026

- `bdr_director_change` dropped by migration `0006_drop_bdr_director_change`,
  after confirming it held no rows. Separated from the change that made it
  redundant on purpose: making a table redundant and destroying it are
  different decisions.
- The FY 2026-27 roll-forward test engagement removed, with its six answers and
  four child rows. **Done with direct SQL, because the application has no
  delete path for an engagement by design (§18.6)** — and recorded in
  `audit_log` with that reason, so the removal is not silent. If engagements
  ever need deleting as a feature, it needs a service, a confirmation and a
  refusal on anything finalised.
- The three `data/*.bak` migration backups deleted, after confirming the
  application reads the migrated database correctly.
