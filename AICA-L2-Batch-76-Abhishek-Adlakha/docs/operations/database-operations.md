# Database Operations

The database foundation separates the fixed `practice_migrator` schema owner from the fixed `practice_app` runtime role. Only their passwords are configured in `.env`. The API uses `practice_app`; the one-shot Compose `migrate` service uses `practice_migrator`. The application never migrates its database during startup. Phase 2 extends the model with `identity` and `employees` schemas while preserving that split.

## Apply migrations

macOS/Linux:

```bash
./deploy/scripts/database.sh migrate
```

Windows PowerShell:

```powershell
.\deploy\scripts\database.ps1 migrate
```

Applying an already-applied migration is safe and reports zero pending migrations.

## Create and verify a backup

macOS/Linux:

```bash
./deploy/scripts/database.sh backup
./deploy/scripts/database.sh verify-backup backups/<generated-file>.dump
```

Windows PowerShell:

```powershell
.\deploy\scripts\database.ps1 backup
.\deploy\scripts\database.ps1 verify-backup -Path backups\<generated-file>.dump
```

Restore verification creates the exact temporary database `practice_restore_verification`, restores the backup, checks the required schemas, and removes that temporary database. It never overwrites `practice_management`. A production restore into the real database is intentionally a supervised runbook action and requires a maintenance window, a pre-restore backup, an exact target check, and explicit approval.

Backups are excluded from Git and may contain confidential firm data. Store production copies in encrypted, access-controlled storage and test restoration regularly.

## Profile a workbook read-only

```bash
dotnet run --project tools/Practice.WorkbookProfiler -- "Clients List.xlsm" --output artifacts/workbook-profile.json
```

Add `--reference employees.txt` to report unmatched values in assignment-like columns. The profiler supports `.xlsx` and `.xlsm`, opens the file read-only, computes its SHA-256, and does not execute or retain macros. It produces observations only; it does not write staging or business records.
