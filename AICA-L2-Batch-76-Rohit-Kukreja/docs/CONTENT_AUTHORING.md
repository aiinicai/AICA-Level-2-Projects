# Authoring the clause repository

Statutory wording lives in `content/` as YAML and nowhere else. No sentence
of statute appears in a `.py` file, and `tests/test_no_hardcoded_text.py`
fails the build if one does.

This document is for a manager with a text editor. You do not need to read
Python to change what a document says.

---

## Acceptance criterion 12 — a new CARO clause, end to end, YAML only

> *"A new CARO clause can be added end to end by editing YAML only — no
> Python change, no migration."*

Here is the whole procedure. Nothing outside `content/` is touched.

### 1. Write the clause file

`content/caro_2020/clause_xvii.yaml`:

```yaml
id: caro.xvii
document: caro_2020
order: 170
number: "(xvii)"
title: "Cash Losses"
clause_ref: "CARO 2020, para 3(xvii)"
effective_from: "2021-04-01"
effective_to: null

# Set this until the wording has been checked against a primary source or a
# firm precedent. It puts the clause on the /health needs_review list and on
# the Needs-Review Clauses screen.
needs_review: true

applicability:
  requires: [caro_applicable]

input:
  key: caro.xvii
  label: "Cash losses in the current and immediately preceding financial year"
  datatype: select
  carry_forward: never          # amounts are year-specific
  mandatory: true
  options:
    - { value: none,     label: "No cash losses in either year" }
    - { value: incurred, label: "Cash losses incurred" }

variants:
  - when: "value == 'none'"
    body: >
      The Company has not incurred cash losses in the financial year and in
      the immediately preceding financial year.

  - when: "value == 'incurred'"
    body: >
      The Company has incurred cash losses in the financial year and/or in the
      immediately preceding financial year, as set out below:
    requires_narrative: true    # blocks export until an explanation is given
    severity: exception         # feeds the consistency engine
```

### 2. Add it to the manifest

`content/manifest.yaml`, under `documents.caro_2020.clauses`:

```yaml
      - caro.xvii
```

Bump `template_version` in the same file. It is stamped into every generated
document, so a document produced under old wording remains identifiable.

### 3. Restart, and re-sync the catalogue

```bash
python scripts/seed.py     # idempotent; rebuilds field_catalog from the YAML
python run.py
```

The startup self-check loads and validates the repository. A malformed file
stops the application there, with the problem named — rather than surfacing
later as a defective document.

**No migration. No Python change.** `field_catalog` is generated from the
YAML, and `engagement_response` is EAV precisely so that a new question does
not need a new column.

---

## What the loader will refuse

Authoring mistakes are caught at load, not in a signed document.

| Mistake | What happens |
|---|---|
| An option that matches no variant | Rejected: *"a dead control"*. §18.3 |
| A `select` input with no options | Rejected |
| Two clauses with the same `id` | Rejected |
| `effective_from` after `effective_to` | Rejected |
| A repeating block no variant renders | Rejected — rows would be collected and never printed |
| A `when` expression using anything but comparisons, `and`/`or`/`not`, `in` and names | Rejected |
| A carry-forward policy outside `always` / `prompt` / `never` | Rejected |

At render time, a clause whose answer matches no variant is a **hard error**,
never a silent skip. A silently skipped clause is a missing statutory
paragraph nobody notices.

---

## Writing the body text

Bodies are YAML **folded scalars** (`>`). Folding turns a single line break
into a space, so you can wrap freely. A **blank line becomes a paragraph
break** in the rendered document — that is how Rule 11(e)'s parts (i), (ii)
and (iii) render as three paragraphs rather than one block.

Interpolate values with `{{ name }}`:

`company_name` · `cin` · `registered_addr` · `fy_code` · `financial_year` ·
`fy_start_long` · `fy_end_long` · `fy_end_numeric` · `report_date_long` ·
`place` · `framework_ref`

A `{{ token }}` with no value is a **hard error**, not a blank. The
alternative is emitting the raw token into a document, and §18.4 forbids an
unresolved placeholder ever reaching an export.

Never write a bracketed instruction such as `[State the modified opinion]`.
The pre-export scan rejects it.

---

## Carry-forward policy

Set in the clause YAML, never in Python.

| Policy | Behaviour |
|---|---|
| `always` | Copied and marked reviewed. Master data only. |
| `prompt` | Copied but **unreviewed**. Amber badge; export blocked until confirmed. The default for every judgmental answer. |
| `never` | Not copied. Amounts, dates, opinions, UDIN, all narratives. |

The §6.2 never-blind-copy register is enforced by giving those fields a
`prompt` policy here — not by a second list somewhere in the code that can
drift out of step with this one.

---

## Repeating blocks

For a clause that requires a table rather than one answer:

```yaml
repeating_block:
  when: "value == 'disputed'"
  entity: statutory_due       # must be one of the child tables
  min_rows: 1
  carry_forward: prompt
  columns:
    - { key: statute, label: "Name of the Statute", datatype: text, required: true }
    - { key: amount,  label: "Amount (₹)",          datatype: amount }
```

and the variant that prints it needs `render_block: table`.

Available entities: `litigation`, `statutory_due`, `ifc_deficiency`,
`board_meeting`. A new entity **does** need a migration — that is the one
exception to "YAML only".

Amount columns render with Indian grouping (`42,60,000`), and an empty cell
renders blank, never `None`.

---

## Before you change wording in production

Changing a clause body changes what the firm signs. Bump `template_version`,
and remember that documents already generated keep their own frozen snapshot
— a reprint reproduces what was signed, not what the YAML says today.
