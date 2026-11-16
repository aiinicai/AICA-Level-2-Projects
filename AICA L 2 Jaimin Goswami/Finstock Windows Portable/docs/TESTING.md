# Validation and reproducible acceptance

The latest deterministic test run on 13 November 2026 passed **60 tests** using Python 3.12.14 on Windows. Run `python -m pytest -q` in the documented development environment. Tests use isolated temporary databases and fixed clocks; no paid API account or live market response is needed.

| Acceptance area | Evidence |
|---|---|
| Economic, corporate and regulatory events | CSV/JSON validation, shared queries, source references and subtype records |
| Past/present/future search | Date and timezone filters, category/company/authority filters, escaped search text |
| Definitions and values | GUI knowledge/detail checks, missing/zero preservation, exact decimal parsing |
| Historical changes | Stable identities, append-only revisions/observations and compatible-series charts |
| Timezones | Six worldwide zones, date boundaries, ambiguous/nonexistent DST times and date-only preservation |
| Custom notifications | Editable filters, custom intervals, watchlists, sample opt-in and overlapping rules |
| Scheduled/unscheduled alerts | Fixed-clock dispatch, first-sync suppression, new/material-update events |
| Duplicate prevention | Reimport identity, conservative cross-source merge, notification job uniqueness |
| Rescheduling/cancellation | Obsolete jobs cancelled; replacements generated; cancelled events suppressed |
| Offline/restart | SQLite backup/reopen, overdue expiry and uncertain-dispatch recovery |
| Source failures | HTTP 401/403/429/500, malformed responses, missing credentials and preserved checkpoints |
| Navy desktop interface | Automated navigation through all ten pages and four views; saved screenshots |
| Windows packaging | Separate frozen backend and offscreen GUI smoke reports accompany the release |

Official SEBI, RBI press, RBI notifications, NSE announcements and NSE circulars were exercised against their real RSS endpoints. Dated outcomes are in live-source-test-report.json and source-probe.json. No authenticated Trading Economics call was made; its mapping and failures are tested with controlled responses. BSE is an authorized file-import route.

## Packaged checks

The delivered EXE passed both checks on this Windows 11 workstation: frozen backend imported 82 synthetic records, SQLite integrity returned `ok`, timezone conversion matched IST, and native notification dependencies imported; the frozen GUI constructed its 1600×940 main window offscreen and exited successfully. See packaged-test-report.json. A conflicting ICU library discovered during packaging was excluded so Qt resolves the Windows 11 operating-system API.

Run `FinstockEventScope.exe --smoke-test --data-dir <empty-test-folder>` and inspect smoke-report.json and the exit status. This verifies bundled data resources, imports, SQLite integrity, samples and timezone conversion. `--ui-smoke-test` additionally constructs the packaged main window using Qt's offscreen platform and writes ui-smoke-report.json. Neither proves native screen rendering or OS notification visibility.

## Manual checks remaining

Native desktop automation was stopped by the user during inspection. A real visible toast and its activation were therefore not verified. The automated notification engine and native delivery implementation are separate from this remaining Windows UI check. Use Notification Settings > Simulate reminder in 10s, keep the app running, inspect Submitted/Failed status, then click the toast and verify the correct event opens. Repeat after minimizing to the tray. Windows Do Not Disturb may suppress visible presentation.

Also perform a clean Windows 11 machine test without Python, a prolonged sleep/resume test, and a deployment pilot under the intended organization's policies. The build is unsigned. Packaging on this workstation is not a substitute for those release checks.
