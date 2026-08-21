# Backup and restore

`scripts/backup.py` writes a timestamped zip to `data/backups/` and prunes
archives older than 30 days.

```bash
python scripts/backup.py           # create, then prune
python scripts/backup.py --list    # show what exists
```

Each archive holds three things:

```
database/auditcraft.db     the whole database
documents/…                the generated document tree
content/…                  the clause repository as it stood
```

The clause repository is included deliberately. Restoring a database without
the YAML that produced its documents would leave you unable to reprint them.

The database is copied with SQLite's own `backup` API rather than a file
copy. Under WAL journalling a plain copy can capture a database mid-write and
produce an archive that restores to a corrupt file.

---

## Restoring

**Stop the application first.** Restoring under a running server will
produce a database that disagrees with the connections already open.

1. **Take a backup of the current state**, even if you believe it is broken.
   A failed restore onto an un-backed-up database is unrecoverable.

   ```bash
   python scripts/backup.py
   ```

2. **Unpack the archive** somewhere outside `data/`:

   ```bash
   mkdir restore-tmp
   cd restore-tmp
   unzip ../data/backups/auditcraft-20260815-143000.zip
   ```

3. **Move the current data aside** rather than deleting it:

   ```bash
   mv data/auditcraft.db data/auditcraft.db.before-restore
   mv data/clients data/clients.before-restore
   ```

4. **Put the restored files in place:**

   ```bash
   cp restore-tmp/database/auditcraft.db data/auditcraft.db
   cp -r restore-tmp/documents/. data/clients/
   ```

   If the clause repository also needs restoring, compare
   `restore-tmp/content/` against `content/` before overwriting — the
   repository is version-controlled, so git is usually the better source.

5. **Bring the schema up to date.** An older backup may predate a migration:

   ```bash
   python -m alembic upgrade head
   ```

6. **Verify before announcing success:**

   ```bash
   python run.py
   ```

   Then check `/health` reports the expected `template_version` and clause
   count, open a finalised engagement, and **reprint one document** — it
   should match its recorded SHA-256. That check is the point of storing the
   hash.

7. Once verified, remove the `.before-restore` copies.

---

## What a backup does not protect against

A backup restores state; it does not restore *correctness*. If a wrong clause
body was in force when documents were generated, restoring reproduces the
wrong documents faithfully. Statutory content problems are fixed by
correcting the YAML and issuing a revision, not by restoring.
