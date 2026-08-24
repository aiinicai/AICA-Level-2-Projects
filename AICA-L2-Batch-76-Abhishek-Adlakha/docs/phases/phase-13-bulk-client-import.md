# Phase 13 — Bulk client import from a spreadsheet

**Status: not started. Deferred by the owner on 2026-08-21.**

Raised while completing the client registry work. Deliberately separated rather than bolted on,
because a half-built importer that writes unvalidated rows into a live client register is worse
than no importer at all.

## What is being asked for

An administrator should be able to add many clients at once by uploading a spreadsheet, instead of
creating them one at a time:

1. Download a template spreadsheet with the expected columns and an example row.
2. Fill it in offline and upload it through the Clients screen.
3. See what the system found — what will be created, what looks like a duplicate, what is wrong —
   **before** anything is written.
4. Approve it, and only then have the clients created.

## Why this is not a small change

The one-time migration importer already in the repository is not this feature. It is a command run
by hand, against one known workbook, whose shape was studied beforehand and whose rules were agreed
with the owner row by row. This asks for something an administrator drives from a browser, against
a file nobody has seen, with no chance to study it first.

The difference is validation and reversibility, not file parsing.

## Scope

- **Template**: a generated `.xlsx` with the columns the importer accepts, an example row, and
  notes explaining each column. Generated from the same definition the parser uses, so the two
  cannot drift apart.
- **Upload**: an authenticated, size-limited upload accepting `.xlsx` and `.csv`. Reject anything
  else on content, not on file extension alone.
- **Staging and preview**: parse into `import.import_runs`, `import.client_import_results` and
  `import.import_issues`, which already exist for exactly this purpose. Show the administrator a
  summary and a per-row list before any client record is created.
- **Duplicate detection** against the 493 clients already loaded, and within the uploaded file
  itself: PAN, GSTIN, TAN, client code and close name matches.
- **Apply**: one transaction, an `ImportRun` recorded, per-row results, and a client code allocated
  from the configured prefix sequence for every new client.
- **Audit**: who uploaded what, when, how many rows, and what the outcome was.

## What already exists and should be reused

| Piece | Where | Note |
|---|---|---|
| Spreadsheet reading without macro execution | `tools/Practice.WorkbookProfiler` | Already proven read-only against the source workbook |
| Client shaping and merge rules | `tools/Practice.ClientImporter/ImportPlan.cs` | Encodes the owner's BIZ-003 and BIZ-004 decisions and is covered by tests |
| Staging tables | `import` schema | `import_runs`, `client_import_results`, `import_issues`, already migrated |
| Client code allocation | `src/Practice.Api/Clients/ClientCodeSequence.cs` | Configurable prefix plus serial; gaps are never reused |
| Issue and severity vocabulary | `ck_import_issues_severity` | Values are title case: `Info`, `Warning`, `Error` |

## Decisions needed before building

1. **Which columns are mandatory in the template?** Client name is clearly required. Whether PAN,
   constitution or GSTIN are mandatory changes how many rows a typical upload rejects.
2. **What happens to a row that matches an existing client?** Skip it, update the existing record,
   or hold it for the administrator to decide per row. Updating silently is the dangerous option.
3. **Partial apply or all-or-nothing?** If 90 of 100 rows are clean, does the administrator get the
   90 and a report on 10, or nothing until the file is corrected?
4. **Who may do this?** `clients.create` is the obvious permission, but a bulk load is a different
   risk from adding one client, and may deserve its own.

## Acceptance criteria

- Uploading the template unchanged, with no data rows, is accepted and creates nothing.
- A file with a duplicate PAN against an existing client is reported before apply, not after.
- Nothing is written to `clients` until the administrator approves the preview.
- Re-uploading the same file does not silently create a second copy of every client.
- Every created client has a code from the configured sequence, and no code is reused.
- A malformed or oversized file produces a clear message rather than a 500.
- The uploaded file itself is treated as confidential: not committed, not logged, not retained
  beyond what the import needs.

## Risks

- **Silent duplication** is the main one. The one-time importer guards against it with the source
  SHA-256; an equivalent guard is needed here.
- **Unvalidated updates.** If the answer to decision 2 is "update existing", a bad upload could
  overwrite good client data in bulk. That path needs the same care as a migration, including a
  backup taken first.
- **Client codes** are allocated from a shared sequence. A failed bulk apply must not leave gaps
  that look like deleted clients, or worse, reuse numbers.
