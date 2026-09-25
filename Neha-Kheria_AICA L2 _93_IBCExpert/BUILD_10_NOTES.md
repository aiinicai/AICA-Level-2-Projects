# IBC EXPERT — BUILD 10 NOTES

Build 10 completes two pending security/operations milestones: scheduled encrypted local backups with safe retention, and the runtime outbound-network guard.

## Scheduled local backup
- Default: enabled, daily, 20 scheduled backups retained.
- Default schedule initializes on first authenticated use and is due one day later.
- Backups run only while the offline application is in authenticated use because the encrypted backup key is derived from the authenticated local master key.
- Manual backups are never removed by scheduled retention.
- Retention deletes only files that resolve inside the application-owned backup directory and marks the corresponding database record `DELETED`.
- Schedule, last run, next due, last attempt and error state are persisted locally in the `settings` table.

## Offline network guard
- Python runtime connections to non-loopback IP destinations are blocked before connection.
- External DNS/name resolution is blocked.
- Loopback access required by FastAPI/PyWebView remains allowed.
- Internet integrations are still unavailable even if the configuration flag is manually changed.
- The first-run dependency bootstrap remains outside the runtime guard so missing packages can still be installed during setup when internet installation is required; offline wheelhouse remains supported.

## Data location
The SQLite database, encrypted document vault, backup files, configuration and other application state remain under the local application data root on the computer. No automatic web data import or database update exists in this build.
