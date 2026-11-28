# Backup and restore

## What is in a backup
One ZIP file `IPT_backup_<date>_<kind>.zip` with:
- `ipt.db` – the whole database (all companies, years, invoices, mappings, reconciliations, audit trail), copied
  with SQLite's online-backup method so it is consistent even while IPT is open;
- `Companies/…` – the original invoice files, GSTR-2B files and purchase registers;
- `backup.json` – when and by whom.

Every backup is checked right after it is made (checksum + SQLite integrity check). "Verify selected" repeats the
check later; a backup file that was changed or damaged is reported.

## Settings (Settings & Backup page, admin)
- **Backup folder** – default `IPT_DATA\Backups`. Choose a OneDrive / Google Drive / pen-drive folder so a copy is
  outside this computer.
- **Automatic backup** – Off / Daily / Weekly. It runs in the background when IPT is opened and a backup is due.
- **Keep automatic backups** – older automatic backups are deleted; manual backups are never deleted by IPT.

## Restore (admin)
1. Settings & Backup → select a backup → **Restore selected…** (or **Restore from a file…** for a ZIP copied from
   elsewhere) → confirm.
2. IPT checks the backup, then makes a **safety backup of today's data**, and prepares the restore.
3. Close IPT and open it again. The restore is applied before the database opens. The data it replaced is kept in
   `Backups\replaced_by_restore_<date>` – nothing is deleted.

If anything fails, the current data is not touched and the message says why.

## Upgrades
Before upgrading the database structure, IPT copies `ipt.db` to `ipt.before-migration-<date>.db` automatically.
