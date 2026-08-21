# AuditCraft

Statutory audit documentation for a Chartered Accountancy firm, under the
Companies Act, 2013 and Indian GAAP.

A staff member answers a set of questions once. AuditCraft assembles the
auditor's report, its annexures, the Board's Report and the letters from those
same answers, so the documents in a file cannot contradict one another. It runs
on one computer or on the firm's own LAN. It has no network endpoints and
nothing leaves the machine.

Built as an AICA Level 2 capstone project.

---

## What it produces

Seven documents, each assembled clause by clause from the same set of answers:

| Document | Issued by | When |
|---|---|---|
| Independent Auditor's Report | The firm | Always |
| Annexure A — CARO 2020 | The firm | When CARO applies |
| Annexure B — Internal Financial Controls | The firm | When s.143(3)(i) reporting applies |
| Management Representation Letter | The company | Always |
| Engagement Letter | The firm | Always |
| Board's Report | The company | Always — abridged under Rule 8A for a small company or OPC |
| Annexure A to the Board's Report — Form MGT-9 | The company | Always |

A small company or an OPC receives neither CARO nor the IFC annexure, so its
set is five documents rather than seven. The number follows the client, not the
tool.

## The idea the design rests on

**Statutory wording is data, not code.** All of it lives in `content/` as YAML —
208 clauses, each carrying its own id, paragraph number, statutory reference,
effective dates, applicability flags and the set of answers it accepts. A
manager can read a clause, diff it, and correct it in a text editor without
touching Python.

This is enforced rather than intended. `tests/test_no_hardcoded_text.py` fails
the build if statutory prose appears in a `.py` file, and it is not marked
`xfail` or skipped.

Each clause carries variants selected by a `when` expression — `value ==
'qualified'`, `is_listed_company`, and so on. **Those expressions never reach
`eval`.** They are parsed to an AST and walked against a whitelist that permits
comparisons, `and`/`or`/`not`, `in` and named variables, and nothing else.
Without that, editing a YAML file would be arbitrary code execution.

## What the tool decides, and what it refuses to decide

Applicability is settled once per engagement and every document reads the same
determination. Flags come in three kinds, and the distinction is deliberate:

- **Computed** — inferred from the client's profile. Whether Rule 8 or Rule 8A
  governs the Board's Report follows from the company class.
- **Declared** — stated by the auditor, never inferred. CARO, internal financial
  controls, CSR, internal audit and secretarial audit. The engine does not guess
  at them from figures, and until one is answered the workspace says so and the
  clauses that depend on it are held back.
- **Derived** — the strict inverse of another flag, so a company cannot be
  determined abridged by the engine and full on the page.

Every determination shows its reasoning on `/engagements/{id}/applicability`,
and can be overruled with a recorded reason.

**Nothing is asserted from silence.** An unanswered question leaves its clause
out and blocks export; it never falls through to a default that says something
about the client. A Board's Report drafted before the opinion is settled does
not tell the directors their audit report was qualified, and a CARO annexure for
a company that granted no loans reports paragraph 3(iii)(b) to (f) as not
applicable rather than opining that the terms of loans that do not exist were
not prejudicial.

## The file, from open to issue

1. **Master data.** Client, company class, framework, directors and key
   managerial personnel. The profile is versioned (slowly changing dimension,
   type 2): a change opens a new version with an effective date and a reason,
   and last year's finalised documents go on reading the version they were
   signed against.
2. **The workspace.** One tab per document. Answers save as you go, and each
   document carries an index of its sections marking what is still outstanding.
3. **Roll forward.** Opening next year carries the answers over — and every
   carried answer arrives *unconfirmed*. Carried forward is not the same as
   verified for this year, and export waits until someone has looked.
4. **Review.** Findings, review comments, and a validation gate that reports
   every unanswered question, empty table, missing explanation and unresolved
   placeholder, plus contradictions across documents.
5. **Finalise.** Against a UDIN, one way. A finalised year is read-only;
   corrections go through Create Revision.
6. **Generate.** Each issued document is registered with a version number, a
   SHA-256 of its content and a frozen snapshot of every input, so reprinting it
   next year reproduces the same bytes rather than rebuilding it from today's
   master data.

Drafts can be printed on the firm's letterhead at any point before finalisation.
They carry a **DRAFT FOR DISCUSSION — NOT AN ISSUED DOCUMENT** stamp, which is
the only thing standing between a half-finished file on firm paper and something
that reads like a signed report.

## Running it

```bash
python -m venv .venv
.venv/Scripts/activate      # Windows;  source .venv/bin/activate elsewhere
pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
python scripts/seed.py
python run.py
```

Or `run.bat` (Windows) / `./run.sh`, which do all of the above.

Then open:

- <http://127.0.0.1:8000/> — the dashboard
- `/admin/firm` — set the firm's own name, FRN, address, signing partners and logo
- `/engagements/2` — the workspace for the seeded engagement
- `/engagements/2/applicability` — every flag with the reasoning behind it
- `/engagements/2/validation` — findings, review comments, finalisation
- `/health` — template version, clauses loaded, and anything flagged for review

`scripts/seed.py` creates a placeholder firm and a demo client. **Nothing about
any firm is hard-coded** — name, FRN, address, place of signature, letterhead
logo and document font are all set on Admin → Firm & Partners, and several firms
can share one installation.

If port 8000 is busy, set `AUDITCRAFT_PORT` in `.env`.

### A packaged build

`AuditCraft.spec` builds a single Windows executable with PyInstaller:

```bash
python -m PyInstaller AuditCraft.spec --noconfirm
```

The .exe carries the clause repository, templates and migrations inside it, and
keeps its database under `%LOCALAPPDATA%\AuditCraft` — never beside the
executable, which may sit on a read-only share. A colleague receives one file
and double-clicks it.

## Checks

```bash
python -m pytest
python -m pytest --cov=app/core --cov=app/clauses --cov=app/render
python -m ruff check app tests scripts run.py
python -m black --check app tests scripts run.py
python -m mypy app/core app/clauses app/render
```

**930 tests pass.** Coverage on the core packages is 93%. `mypy` runs
`--strict` on `app/core`, `app/clauses` and `app/render`.

Two things about how the tests are written, because they shaped the code:

**Machinery is tested against a small fixture repository** in
`tests/fixtures/content/`, separate from the real one in `content/`. "Does the
export pipeline work" and "is the real repository fit to sign" are different
questions and are kept apart.

**The rules are swept, not listed.** Rather than asserting that one clause
behaves, the suite asks the whole repository a question — no document may end
unsigned, no clause may keep an adverse catch-all variant, no schedule may
compute a sub-total from a line below it, no index entry may point at a field
that is not on the page. A rule written that way covers the clause somebody adds
next month.

## Where things live

| Path | What |
|---|---|
| `content/` | **The clause repository.** Statutory wording lives here as YAML and nowhere else. |
| `content/manifest.yaml` | `template_version`, stamped into every generated document, and the document → clause map. |
| `content/applicability_rules.yaml` | Every threshold and exemption, with its statutory reference and effective dates. |
| `app/clauses/` | Clause model, YAML loader, restricted expression evaluator. |
| `app/core/` | Applicability engine, consistency rules, Indian number formatting, snapshotting. |
| `app/render/base.py` | A neutral node tree. The HTML and DOCX renderers both consume it, so neither holds its own copy of document text. |
| `app/services/` | Engagement workspace, document assembly, export and issuance. |
| `alembic/` | Database migrations. |
| `docs/` | Architecture, schema, content-authoring guide, and a decision log. |

`docs/GATE_A_DECISIONS.md` records 80 decisions — what was changed, what it
replaced, and what went wrong to prompt it. Most entries exist because the
firm's own audit team found something in review.

## Known limitations, stated plainly

**There is no login.** This is a single-user local build at the firm's
instruction: anyone who can open the application can use all of it.

What that costs, said plainly because the screens do not show it: nothing stops
the person who prepared a file from approving and finalising it, UDIN entry is
not reserved to a partner, and the change log records *what* changed and *when*
but not *who*. It is a change history, not evidence of review.

The gates that do not depend on identity all hold — the status sequence, zero
blocking findings before review, zero open comments before approval, one-way
finalisation, and Create Revision as the only way back. If attribution is wanted
later without passwords, a "who are you?" selector feeding the actor field is
the whole change.

**Scope.** Indian GAAP only; Ind AS is out of scope. The tool prepares
documentation — it does not audit anything, and it does not check the figures
it is given.

**Consolidated financial statements** are supported only so far as the Board's
Report and CARO 3(xxi) require. A group audit is not the target.
