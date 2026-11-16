# Finstock EventScope — User manual

Start FinstockEventScope.exe from its complete distribution folder. No Python commands are needed for normal use. The first launch loads an explicitly labelled synthetic workspace; it does not connect paid feeds or imply live market coverage.

## Browse and search

Use the left navigation to open the dashboard, unified calendar, economic, corporate or regulatory views. The Historical Database starts with a Past filter. All views read the same persistent database.

Search matches titles, companies, symbols, categories, authorities and countries. Choose Sample only, Source records only, or All records. SAMPLE is visible in the event title, detail page, chart and notification. Source records can be imported or retrieved; a SOURCE label does not mean a feed is currently connected.

Use country, category, authority, importance, status and exchange filters. The time selector offers Past, Today and Upcoming based on the selected display timezone. Select Agenda, Day, Week or Month. The arrows and date picker move the calendar. Agenda has an optional date range. Calendar date prefers scheduled date, then publication, effective date and deadline. The date-basis selector also searches publication, effective, deadline, record and ex-dates; All milestones shows separately labelled entries in calendar grids.

Tables are sortable and horizontally scrollable. Agenda is paginated at 500 events; week/month at 5,000. The footer reports when additional pages exist. Dashboard category counts describe the displayed page; the total describes all matches.

Select a row or calendar item. Overview shows readings, dates, explanation and disclosure summary. History shows compatible numeric actual readings with the same series key, unit and sample/source class. Hover over a chart point for its period and reading. Changes retains previous snapshots; Sources lists original references and original timestamp strings. A provider's revised field is preserved as supplied and is not automatically treated as a revision to the current reporting period.

## Timezones and uncertain dates

Choose an IANA timezone at the top. Daylight-saving and date-boundary conversion is automatic. A source date without an established time/offset stays a date, labelled time unavailable. Do not read midnight as an invented release time. The original raw timestamp is retained in Sources.

Some official RSS feeds omit UTC offsets or use midnight placeholders. EventScope conservatively shows the source date and does not infer an exact instant from the authority's country. This limits precise time display for those feeds; detection and retrieval timestamps remain exact.

## Import CSV or JSON

Click Import events, choose a file and its source, then identify synthetic data or confirm permission to store source records. The bundled synthetic_events.csv and synthetic_events.json demonstrate the schema. Field names are documented in IMPORT_FORMAT.md.

Imports retain revisions. File imports and initial feed synchronization do not send newly detected publication alerts. Future scheduled events can still receive reminders if an enabled rule matches. Import errors are recorded under Sources & Settings > View ingestion logs.

## Watchlists

Create a watchlist and add exact company names, symbols or ISINs. Watch selected adds the selected corporate event's available identity to My watchlist. In a notification rule, watchlist membership is combined with directly entered company identifiers as alternatives. An empty selected watchlist matches nothing.

## Notification rules

Create a rule in Notification Settings. Configure countries, companies/watchlists, categories, authorities, importance and event types. Blank filters mean any. Values within one filter are alternatives; different filter dimensions combine. Specify one or more advance intervals in minutes, including decimals for short tests. There is no fixed high-importance or 30-minute restriction.

Select advance reminders, new publications and/or material updates. Sample events are excluded unless explicitly enabled. A 1,440-minute interval means 24 elapsed hours. Unknown/date-only and tentative scheduled times do not receive exact-time reminders.

The grace period determines how late a missed reminder can still be submitted. Already elapsed reminders expire; cancelled/rescheduled events cancel obsolete jobs. Overlapping rules produce one logical alert for an identical event/trigger/interval. History distinguishes Pending, Submitted, Failed, Expired, Cancelled, Suppressed and Uncertain. Submitted means Windows accepted the request, not proof it was visible or read. Do Not Disturb and notification preferences are controlled by Windows.

Click Simulate reminder in 10s to create a clearly labelled synthetic event and matching rule. Leave the application running. Click the native toast to open the associated event while EventScope is running, including in the tray. Double-click a notification-history row to open the event manually.

Closing the window normally minimizes to the system tray. The tray menu can reopen it or fully quit. Sources & Settings can change close-to-tray behaviour. Fully quitting, logging off or switching off stops monitoring. There is no Windows service or automatic start-at-login registration. Stored history remains accessible offline. Already known reminders can fire offline while the app runs, but new information cannot be detected. Restart reconciles schedules and records missed/uncertain deliveries. Cold activation after fully quitting is not implemented.

## Sources

Select a source and Configure selected. Review its terms, enable permitted local access and set the refresh interval. Then Refresh selected. Trading Economics also requires your own entitled API credential and provider country names. Credentials are stored using Windows Credential Manager, not in the database or build. Leave the credential field blank to retain the saved value.

Connected means a successful validated refresh; it does not guarantee complete coverage or instantaneous updates. Not Configured means disabled/missing access; Restricted indicates denied access; Stale identifies overdue successful refresh or throttling; Error identifies parsing/network/validation failures. Imports display Import only. Last successful refresh is retained after later failures.

SEBI, RBI press/notifications and NSE announcements/circulars use documented official RSS URLs. BSE and Indian statistical/fiscal datasets have authorized CSV/JSON import routes; no unverified private endpoint is bundled. Read SOURCE_GUIDE.md for exact limitations. The initial fetch establishes history without publication-alert flooding.

## Storage and backup

The normal data folder is %LOCALAPPDATA%\Finstock\EventScope. Back up database creates a consistent SQLite backup. To restore, fully quit EventScope, preserve the current data folder as a backup, then place the chosen backup there as eventscope.db. Do not replace a database while a monitoring process is running. Do not copy only the main database file while a WAL transaction is active; use the backup button.

Local history is not encrypted. Protect the Windows account and storage appropriately. Documents remain links; the application does not automatically download complete filings. It does not provide trading recommendations, legal conclusions or automated orders.
