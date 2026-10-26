# Video script (about 5–6 minutes, face + screen)

Record in one take with your face visible, then screen share. Upload as YouTube *unlisted* or Google Drive (anyone with link).

**0:00 – Introduction (face).** "I am CA Somarajan PK, M.No 235612, AICA Level 2 Batch 98, Ernakulam. My capstone is an AI-powered bank reconciliation and audit assistant."

**0:30 – Problem (face).** Monthly reconciliation is repetitive; duplicates and keying errors hide among near-matches; sign-off is rarely recorded.

**1:15 – Demo, steps 1–2 (screen).** Run `run_project.bat`. Show the stepper. Click Load demo data (or Pull from Tally using the mock). Select the bank. Add the statement.

**2:15 – Demo, steps 3–4 (screen).** Run reconciliation. Show dashboard, matched entries with rule and confidence, reconciling items, BRS, exceptions, proposed entries.

**3:45 – Demo, step 5 (screen).** Show export locked. Approve or reject each entry, enter reviewer name and remarks, export. Open the Excel file and show the Approval sheet and BRS.

**4:45 – Technical explanation (screen, code).** Show `tally_extract.py` (XML request), `recon_engine.py` (matching layers), the server-side approval check in `tool_server.py`, and the tests passing.

**5:30 – Honest limits and close (face).** Synthetic data only; Tally pull tested on mock XML; CSV statements only. "AI does the matching, the CA makes the call. Thank you."

Before recording: confirm no real client data is visible on screen.
