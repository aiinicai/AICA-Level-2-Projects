# Lovable test: can the app produce the desired result?

Use only the file dpdp_inventory_test.csv. Every name and value is synthetic. Never load real client records.

## Test 1: Import (Document Centre > spreadsheet import)
Upload dpdp_inventory_test.csv and map the seven columns.

Expected:
- 15 data rows read.
- 12 imported.
- 3 rejected, each with a clear reason:
  - Row 10 (blank activity): "Processing activity is required"
  - Row 12 (blank department): "Department is required"
  - Row 14 (duplicate of row 1): "already exist; no record was overwritten"
- The existing records are unchanged after the import.

Pass if all three rejections are shown and nothing is silently dropped.

## Test 2: Sensitive data is flagged (the important DPDP test)
Expected: rows containing health information (rows 5, 10), a PAN or salary (row 6), a card number (row 13), bank account details (rows 2, 6), facial images (row 3) or photographs of students (row 8) are flagged as sensitive or special-category data, and shown for legal review.

Today the importer has no such flag. If it doesn't flag them, mark this FAIL. That is a gap to build, not a test error.

## Test 3: Nothing is decided for you
Expected: the lawful ground is "Not yet assessed" for every row, and the tool never picks one. Retention text such as "Seven years (to be confirmed)" is kept exactly as written, not turned into a date.

## Test 4: Mapping
Rename the columns in the file, or reorder them. The mapping step should still find each field. Missing a required column should block the import with a clear message.

## Test 5: Exports
From the imported records, download:
- Excel: opens, with the 12 records, seven columns, and the report information sheet.
- PDF: contains all 12 records, tables don't cut words in half, and it shows the disclaimer.
- CSV: 12 rows, same values as on screen.

## Test 6: Searching, editing, deleting
- Search "Student" returns the matching rows only.
- Edit a record, refresh the page: the change is kept (today it is lost on refresh, which is a known limit).
- Delete asks for confirmation.

## Test 7: Wording
No page says "compliant", "certified" or "guaranteed". Legal references show "Needs legal review".

## Scoring
- Tests 1, 3, 4, 5, 6, 7 pass: the existing app behaves as specified.
- Test 2 fails: the DPDP-specific logic is not built yet. Ask Lovable to add it (I can write that prompt).
- Test 6 refresh fails: data is not saved. Expected until the database is connected.

Record each result: PASS, FAIL or NOT TESTED, with the screen message in quotes.
