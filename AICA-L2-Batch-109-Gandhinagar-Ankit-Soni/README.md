# Balance Confirmation Generator

Desktop application (Python / PyQt6) that prepares audit balance confirmation
letters, sends them from the auditor's own mailbox, reads the replies through a
Google Apps Script bridge, and produces the reconciliation reports.

## Layout

- `balance_confirmation_generator.py` - the application, assembled as a single file
- `src/parts/` - the source parts the single file is assembled from
- `src/assemble.sh` - rebuilds the single file from the parts (run after any change)
- `src/tests/` - automated tests (Python and Node)
- `bridge/` - Google Apps Script bridge (`Code.gs`, `appsscript.json`)
- `docs/` - set-up guides

## Never commit

Client balances, letters, signed slips, replies, passwords, or the bridge feed
address (it contains the access key). See `.gitignore`.
