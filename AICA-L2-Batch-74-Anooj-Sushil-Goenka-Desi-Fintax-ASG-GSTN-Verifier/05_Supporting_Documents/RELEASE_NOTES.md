# Desi Fintax ASG GSTN Verifier - Release 1.4.0

Prepared for **CA Anooj Sushil Goenka**  
Mobile: **9833049094** | WhatsApp: **9028593321**

## Version 1.4.0 changes

- Calculates clearly-labelled generic statutory due dates and delay days for captured GSTR-3B and GSTR-1/IFF rows.
- Captures both GSTR-3B and GSTR-1/IFF filing tables for the selected financial year.
- Adds project-wise GSTR-2A/2B import context: financial year plus Annual or a specific month.
- Keeps consolidated GSTIN totals while adding a period-wise GSTIN summary and full import log to Excel exports.
- Ignores workbook labels and instructions instead of falsely reporting them as invalid GSTINs; genuine invalid candidates show file, sheet and row.
- Automatically links the latest import FY/period to verification, while retaining editable search controls.

- Locates the GSTR3B table from its portal heading; the rows themselves do not repeat the return name.
- Parses the displayed FY, tax period, filing date and filing status columns.
- Infers Monthly/Quarterly frequency from fiscal-period spacing and labels it explicitly as inferred.

## Version 1.3.2 changes

- Matches project FY `FY 2025-26` to the GST Portal's full label `2025-2026`.
- Selects the requested portal FY by starting year before filing-table search.
- Prevents saving any verification or PDF when the requested FY or GSTR-3B rows are absent.

## Version 1.3.1 changes

- Stops cleanly after the final pending GSTIN and clears the previous selection.
- Prevents a queued portal timer event from saving the same GSTIN twice.
- Opens **Show Filing Table** only; it no longer replaces the table with current-year filing frequency.
- Requires the project FY to be selected and fails clearly if that FY is unavailable.
- Captures GSTR-3B rows cell-by-cell before saving the verification and evidence PDF.

## Version 1.3 changes

- Migrates existing databases in place without deleting client records.
- Recovers interrupted queues and keeps verified GSTINs untouched.
- Adds project queue reset, clear last-error details and reliable retry.
- Continues automatically from CAPTCHA through capture, PDF and next GSTIN.
- Adds screenshot-to-PDF fallback when Edge cannot print directly.
- Handles direct and nested GST Portal responses.

## Version 1.2 changes

- Fixed normal GST redirects from `/services/searchtp` to the authenticated search route.
- Added encrypted GST Portal login ID/password separately for every client project.
- Automatically fills the client's login ID and password; CAPTCHA remains manual.
- Permanent CAPTCHA entry and **Submit CAPTCHA & Continue** control on the software screen.
- Automatically resumes the selected GSTIN after login/CAPTCHA succeeds.
- **Retry Selected Now** clears stale state and immediately restarts an interrupted item.
- Resume checks the live browser state instead of leaving a failed item pending.
- Clear portal downtime, session expiry, redirect, timeout, CAPTCHA and page-load messages.

## Version 1.1 changes

- Simplified seven-section interface centred on the active client/project.
- Strict project isolation across dashboard, imports, queue, results and reports.
- Automatic GSTIN entry, result capture, FY selection, evidence PDF and next-queue processing.
- Hidden official-page attempt with visible Edge fallback only when the portal requires interaction.
- Clear GST Portal downtime/HTTP 503 reporting instead of an apparently stuck queue.
- Optional GSP/API settings hidden by default; no provider is needed for portal-assisted use.
- FY list from FY 2017-18 through the ongoing FY.

## Verification completed

- Nine automated core, portal-mapping, persistence, reporting, backup and project-isolation tests passed.
- GSTIN checksum validation, project-wise deduplication and invoice aggregation are covered.
- PySide6 startup smoke test covers all seven simplified sections.
- PyInstaller standalone EXE and Inno Setup installer are supplied.

## Operational qualification

The GST Portal controls CAPTCHA, login, MFA, downtime, page layout and data availability. CAPTCHA is never bypassed or solved automatically. A retained logged-in Edge session may reduce repeated prompts only where the portal permits. The official Developer Sandbox contains test/dummy data and is not treated as live taxpayer verification evidence. Live production API access requires an authorised GSP/API arrangement.

GSTR-3B filing does not independently establish invoice-wise payment of tax or ITC eligibility. Due dates and delays affected by notifications or extensions must be checked against the applicable legal period and taxpayer facts.
