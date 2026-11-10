# SME GSTAT AppealKit v0.6.2 - Independent QA Plan

This QA pack is deliberately separate from the application. It does not modify
the production HTML, JavaScript, CSS, source PDFs, or generated filing set.

## Release gate

v0.6.2 should not be released merely because a PDF downloads. A release candidate
passes only when the tests below confirm that the preview, final PDF, index,
chronology, edited page selection and annexure-reference report all describe the
same paper book.

## Severity

- **BLOCKER** — missing/duplicated evidence page, preview/final mismatch, corrupt
  output, wrong index destination or silent text truncation.
- **MAJOR** — incorrect chronology page reference, wrong annexure mapping,
  unstable multi-volume split, or page edit not reflected everywhere.
- **MINOR** — unclear hint, optional field presentation, visual alignment that
  does not hide or overwrite information.

## Test matrix

### 1. Multi-volume planning

1. Generate one volume just below its limit.
2. Add one source page and confirm a stable two-volume split.
3. Use a document larger than one volume; confirm Part 1/Part 2 entries, no page
   omission and no duplication.
4. Repeat with cover/index/chronology enabled and disabled.
5. Confirm every volume stays within the selected limit and printed numbering
   remains continuous according to the selected pagination scope.
6. Confirm the complete master index is repeated in each volume and highlights
   only that volume's entries.

### 2. Dynamic master index

1. Use particulars of 1, 2, 5, 10 and 20 wrapped lines.
2. Use long annexure labels such as `Annexure A-12(a)(iii)`.
3. Confirm rows grow, never overlap, never split across pages and never truncate.
4. Confirm the case-title line, volume marker and `Index page x of y` do not
   overwrite each other.
5. Confirm every entry's printed range and link target match the final content.

### 3. Editable chronology

1. Create chronology from dated and undated documents.
2. Add/delete/move rows; add/delete/rename optional columns.
3. Sort by date, then return to manual order.
4. Include chronology in the paper book and then exclude it.
5. Confirm chronology page ranges recalculate after page edits and volume splits.
6. A blank or invalid date must remain reviewable and must never be silently
   guessed. Use the visible hint `DD-MMM-YYYY`.

### 4. Page editing

1. Select a range, e.g. pages 2–5; confirm only those four pages are included.
2. Reorder pages `4,1,3,2`; confirm content, thumbnails, index and final PDF use
   that exact order.
3. Remove and restore a page; reset the document.
4. Split and merge a document without changing the original source file.
5. Repeat on rotated and digitally signed PDFs. Editing a signed source must show
   a warning and retain the original signed file separately.
6. Reject invalid ranges (`0`, reversed range, out-of-range page, duplicate page
   unless duplication is explicitly chosen) in plain language.

### 5. Exact preview consistency

1. Generate the preview, record its build/fingerprint, then generate final output
   without changes. Page count, dimensions, rotations, text, annotations, stamps,
   index destinations and pagination must match.
2. Change any material setting after preview. The tool must mark the preview as
   out of date and offer refresh; the warning should not be confusing.
3. Test continuous scrolling, previous/next, go-to-page, zoom, fit width/page,
   volume selector and annexure navigation.
4. Previewing must not silently download or finalise the filing set.

### 6. Annexure-reference checker

1. Detect `A-1`, `A/1`, `Annexure A-1`, `Exhibit P-3`, ranges and page citations.
2. Avoid false matches in dates, order numbers, GSTINs and quoted case citations.
3. Report: matched, cited but missing, present but not cited, duplicate annexure,
   possible wrong page, and unreadable source.
4. Checks are optional and non-blocking.
5. Any suggested renumbering must be reviewable. Never overwrite the original
   appeal draft and never silently change legal text.

## Required reconciliation controls

For each final run retain an internal page map with:

`source hash | source page | edit position | annexure | volume | physical page | printed page`

The following must reconcile to zero:

- missing source pages selected for inclusion;
- duplicate source pages not deliberately duplicated;
- index ranges not matching content;
- chronology ranges not matching content;
- broken internal links;
- preview/final page-map differences;
- silently truncated subject, particulars or annexure text.

## Usability acceptance

- Default screen remains simple; advanced controls are collapsed or optional.
- Optional blank fields do not block generation.
- Only unreadable input, invalid page selection or impossible generation is a
  blocking error.
- Hints use examples such as `26-Nov-2024`, `2021-22`, and `A-1`.
- Warnings use common language and state what the user can do next.

## v0.6 focused scenarios

1. Select `1-3, 7`, `all`, `odd` and `even`; reject zero, reversed and out-of-range values with plain text.
2. After moving selected pages, confirm the selection remains linked to original-page identity.
3. Test every bulk action with adjacent and non-adjacent selections, then Undo and Reset.
4. For each preview jump, confirm both the selected volume and exact physical page.
5. Generate the same case in Final and Draft modes. Only Draft may contain `DRAFT - FOR REVIEW`.
6. Set an artificially small MB guide and confirm the actual-size warning appears without blocking output.
7. Confirm actual PDF byte counts appear in the audit manifest.
8. At 760 px and 480 px widths, confirm the compact header and horizontally scrollable workflow remain usable.
9. Confirm optional filing controls are collapsed by default and unticked reminders never block generation.

## v0.6.2 focused scenarios

### Optional Prepared by and subject-layout regression

1. Leave “Show Prepared by” off while retaining “Indirect Tax Team” in the field; confirm no visible line and no PDF Author metadata.
2. Select it with a custom value; confirm the line appears exactly once and metadata matches.
3. Select it with a blank value; confirm no empty label is printed and a plain warning appears.
4. Reproduce the reported sparse two-word intermediate line; confirm it remains naturally aligned and does not stretch.
5. Paste one continuous 300+ character reference; confirm every glyph stays within the cover and master-index margins.
6. Insert two subject paragraphs; confirm both paragraph-ending lines remain naturally aligned.
7. Populate long Appellant, Respondent, Bench and Order fields; confirm the subject is not omitted or placed over the footer.
8. Repeat in Small, Normal and Large modes and inspect rendered PNGs, extracted text and word coordinates.

1. Generate the same cover in Small, Normal and Large; confirm all text remains inside the page and the size visibly changes.
2. Use a long multi-line subject; confirm every complete line except the final line is justified and no words overlap.
3. Confirm ISO input `2026-08-06` prints as `06-Aug-2026`.
4. Drag the first document to the end, the last to the start and one document between two rows; verify index and pagination follow the new order.
5. Confirm Up/Down buttons still work for users who do not use dragging.
6. With three main documents, confirm labels are exactly `1, 2, 3, A1, A2, A3` and reapply after drag.
7. Check `Anx1`, `Anx12`, `Anx123`, `Annexure A-12`, `A/12` and `A12`; no shorter reference may be extracted from a longer one.
