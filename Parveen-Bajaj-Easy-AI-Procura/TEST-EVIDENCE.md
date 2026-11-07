# Verification evidence

Export preparation: 7 November 2026.

Command executed against the source project: `bunx vitest run src/lib/*.test.ts`

Result: **53 tests passed across 7 test files**.

| Test file | Passed tests |
| --- | ---: |
| supplier-notice.test.ts | 11 |
| pwa.test.ts | 5 |
| install.test.ts | 10 |
| quotes.test.ts | 2 |
| master-import.test.ts | 9 |
| csv.test.ts | 9 |
| spreadsheet.test.ts | 7 |

Previous browser verification demonstrated a mapped CSV item import saving its unit correctly, with the temporary record removed afterwards. Excel tests verify numeric receipt quantities and units. The export has not been independently deployed or replayed against a new database. Populated supplier-portal checks, complete procurement end-to-end verification and the broader security review remain pending. This evidence is not a claim of production certification.

Note: the automated test files themselves were removed from this trimmed package to fit the 100-file upload limit; the results above were recorded before removal.
