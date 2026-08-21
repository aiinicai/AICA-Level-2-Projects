# Architecture

One idea holds the system together: **statutory wording is data, not code.**
Everything else follows from that.

```
content/*.yaml  ──loader──▶  ClauseSet  ──resolve──▶  node tree  ──▶  HTML
     ▲                                       ▲                   └──▶  DOCX
     │                                       │
  the only place              engagement_response (EAV)
  statute lives                + child record tables
```

## Layers

| Package | Responsibility |
|---|---|
| `app/clauses/` | Load YAML, validate it, select a variant, interpolate |
| `app/core/` | Pure engines: applicability, carry-forward, comparison, consistency, snapshot, formatting, validators, permissions |
| `app/models/` | SQLAlchemy schema (§5) |
| `app/services/` | Orchestration: client, engagement, document, review, export, excel |
| `app/render/` | `base.py` node tree; `html.py` and `docx.py` are thin adapters |
| `app/routers/` | HTTP only — no business rules |

`app/core` is deliberately free of database and clock. `compute()` in
`applicability.py` takes a value object and returns a frozen dataclass, so
the same inputs always give the same answer and the reasoning is testable
without fixtures.

## Five invariants worth knowing

**No statutory sentence in Python.** Enforced by
`tests/test_no_hardcoded_text.py`, which also fails on any string literal
over 120 characters inside `app/render/` — the place boilerplate would
otherwise accumulate.

**`when` expressions never reach `eval`.** Conditions are parsed to an AST
and walked against a whitelist. Otherwise editing a YAML file would be
arbitrary code execution on the firm's LAN.

**Client master data is never updated in place.** A change closes the
current `client_profile` row and opens a new one, so a document finalised
last year keeps printing the address it was signed with. A partial unique
index on `is_current` is the database-level backstop.

**A finalised document reprints from its own snapshot.** `document_instance`
stores the frozen payload and a SHA-256 of the rendered text. Reprinting
reads the snapshot, never current data, and the hash makes "byte-identical"
checkable rather than merely claimed.

**SQLite transactions are made real.** The pysqlite driver does not emit
`BEGIN` for DML, so statements would otherwise autocommit and `SAVEPOINT`
would never nest. `app/db.py::_fix_pysqlite_transactions` applies
SQLAlchemy's documented fix. Without it, versioning a client profile is not
atomic: a failure between closing the old row and inserting the new one would
leave a client with no current profile.

## Known gaps, recorded rather than hidden

**§7's applicability inputs cannot decide everything.** `compute()` returns
ten flags from six profile facts. Twelve conditional clauses in the Clause
Register depend on facts the input list does not carry — whether the company
has branches, subsidiaries, or inventory; whether it is a Nidhi company;
whether independent directors, an NRC or a vigil mechanism are required;
whether it crosses the Rule 5(2) remuneration thresholds. `cost_records` and
`cfs_required` therefore report *"must be set on the client"* rather than
guessing. Either the profile grows those fields or those clauses route
through a second mechanism — which is what §7 exists to prevent.

**Every applicability threshold is a derivation.** See
`content/applicability_rules.yaml`. All are marked `needs_review: true` and a
test fails if any is presented as settled.

**HTMX and Alpine are not vendored.** §1 names them; fetching them is a
download decision for the firm. `app/static/autosave.js` provides the same
behaviour with no dependency, and every control degrades to a plain form.

**Four of the six documents have no clauses yet.** The repository holds six
sample clauses across two documents. Phase 2 authors the rest from the
approved Clause Register. The audit pack names what is missing rather than
shipping a set that quietly lacks the MRL and the Directors' Report.
