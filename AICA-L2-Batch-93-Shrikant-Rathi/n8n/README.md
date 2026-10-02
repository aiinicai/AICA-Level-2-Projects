# LookThrough monthly monitor (n8n)

This covers AICA Level 2 Module 9, AI-driven workflow automation. Every month the family-office PC runs the policy checks and n8n does the rest: it validates the result, compares it with last month's run, keeps a history and emails the committee.

```
Family-office PC (monthly)                           n8n cloud: "LookThrough - Monthly Policy Monitor"
Monthly_Monitor.bat                                  Receive Monitor Run   (webhook, header-token auth)
  └ bridge/monitor_push.py --refresh                   → Validate Payload  (schema; rejects bad data)
      refresh prices and NAVs                          → Get Last Run      (data table lookthrough_monitor_runs)
      run the reconciled engine (MCP tools)            → Compare With Last Run (new / resolved breaches, value change)
      SHA-256 of the payload                             ├→ Log Run        (one row per run: the audit trail)
      POST ───────────────────────────────────────►      ├→ Breach Or Resolution? → Email Investment Committee (Gmail)
                                                         └→ Acknowledge Run (JSON response to the PC)
```

## Why the data is pushed from the PC

The data bridge and the portfolio data stay on the family-office PC. A cloud n8n instance cannot reach `127.0.0.1`, and the PC should not expose a port to the internet, so the PC sends its results out to n8n instead.

## Controls

- **n8n never computes a figure.** Every number comes from the engine that is reconciled against the app, and the email says so.
- **Only the PC can post.** The webhook needs a header token. The token lives in an n8n credential and in the PC's `.env` file, which git ignores.
- **Bad data is rejected.** A payload with the wrong schema, a bad date or missing tests fails validation and is not logged or emailed. Tested: all four errors are named in the rejection.
- **The recipient is fixed.** The alert address is set in the workflow and never taken from the payload.
- **Every run is recorded.** Each run writes a data-table row with the payload's SHA-256, and the PC logs n8n's response to `logs/monitor_push.jsonl`.
- **Alerts only when something matters.** An email is sent only when a policy limit is breached or a breach has been resolved. A missing figure shows as NOT COMPUTABLE, never as compliant. Warning-grade limits (fund overlap) show as ABOVE LIMIT, in amber, and are counted in the subject, but do not by themselves send an email.

## One-time setup

0. Import `lookthrough_monitor.workflow.ts` with the n8n Workflow SDK or MCP builder. Set the recipient in *Email Investment Committee* (the source file uses a placeholder address) and create a data table named `lookthrough_monitor_runs` with the columns listed in *Log Run*.

1. **Create the webhook credential.** In n8n go to *Credentials → New → Header Auth*. Name it `LookThrough monitor token`, set the header name to `X-LookThrough-Token`, and use the `LOOKTHROUGH_N8N_TOKEN` value from this folder's `.env` as the value.
2. **Attach it.** Open the workflow, click *Receive Monitor Run* and select that credential.
3. **Publish (activate) the workflow.**
4. **Test from the PC.** Run `.venv\Scripts\python.exe bridge\monitor_push.py`, or `Monthly_Monitor.bat` to refresh the data first. The console prints n8n's response.
5. **Optional: schedule it.** Use Windows Task Scheduler to run `Monthly_Monitor.bat` on the 12th of each month. AMC portfolio disclosures are normally out within ten days of month-end.

Source: `lookthrough_monitor.workflow.ts` (n8n Workflow SDK). Tested with pinned data: change detection (new breach, resolved breach, value change of +1.07 cr / +2.32%), email routing, and rejection of a malformed payload. The test runs left no rows in the data table.
