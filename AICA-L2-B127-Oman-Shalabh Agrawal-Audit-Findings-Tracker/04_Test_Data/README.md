# Test data

All content is dummy text marked `[SAMPLE]`. There is no real audit, client or personal data.

| File | Purpose |
| --- | --- |
| `sample_findings_import.xlsx` | 584 dummy findings (30 to 50 for each of the 14 departments) in the 14 agreed import columns. Use it for the Excel import test. |
| `import_with_errors.xlsx` | 7 rows with deliberate mistakes. Expected: 2 imported, 5 rejected (unknown department, bad date, duplicate serial number, bad risk level, bad auditor type). |
| `import_missing_column.xlsx` | A file without the "Risk level" column. Expected: the whole file is refused. |
| `sample_users.csv` | The 30 test users (Audit Admin, Management, and two per department) with the dummy test password. |
| `sample_full_register.xlsx` | What the system holds after "Load sample data": current status, the wide layout (one block per follow-up date), and the follow-up history. Shows what the outputs look like. |
| `generate_test_data.py` | Creates all the files above. Run `python generate_test_data.py` in this folder. |

The target dates in the sample files are set relative to the day the files were created, so the ageing buckets shift a little if the files are imported much later. The "Load sample data" button inside the app always uses the current date.
