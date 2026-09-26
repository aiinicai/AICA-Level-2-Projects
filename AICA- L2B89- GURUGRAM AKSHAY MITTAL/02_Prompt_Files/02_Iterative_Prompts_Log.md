# Prompt File 2: Iterative Prompts Log (Refinement Conversation)

After the master build prompt, the application was refined through a conversation with the AI. Each row records **my prompt** (the problem I observed as the user and Chartered Accountant), **what the AI did**, and **the outcome**. This shows the "human in the loop" approach: I tested, observed, and directed. The AI diagnosed, built and verified.

**AI tool:** Claude (Anthropic), in the Claude desktop app's Code mode. Everything the AI built was checked with automated tests and in the browser.

---

### Prompt 2: Opening the files
> "These files are not opening. getting this error as screenshot attached. where should i open these files"

- **Diagnosis:** the files were in a temporary, hidden workspace, and a folder link cannot open in the file viewer.
- **Action:** copied both projects to `C:\BRMCo`, then re-ran all tests from the new location (all passed).
- **Learning:** keep project files in a normal, permanent folder.

### Prompt 3: "Local Host is not responding"
> "is this error coming. if error, how can i resolve this" *(screenshot: the app opened from `C:/BRMCo/.../index.html`)*

- **Diagnosis:** the page was opened as a plain file. The application runs as a local web server and must be opened at `http://127.0.0.1:8000`.
- **Action:** created one-click launchers, `start_local.bat` and `start_server.bat`. On first run they set up everything automatically, start the app, and open the browser.
- **Learning:** a non-technical user needs a double-click start, not typed commands.

### Prompt 4: Demo Mode banner
> "why the local file is showing this- DEMO MODE — No entry posted to Tally"

- **Explanation:** Demo Mode is a deliberate safety feature. It simulates Tally so users can practise without touching real books.
- **Action:** gave step-by-step instructions to connect to real TallyPrime (enable the XML/ODBC port 9000, set company details, turn off Demo Mode, test the connection, sync masters).

### Prompt 5: Finding "Connection"
> "help me with step no. 5. in tally, no Connection option is visible"

- **Clarification:** "Connection" and "Master Sync" are menu items inside the BRMCo app, not inside TallyPrime. Also gave the TallyPrime path (F1 → Settings → Connectivity) in case the connection fails.

### Prompt 6: Missing ledgers, and a request for a new feature
> "This error is coming. Basically it is saying ledgers with this name is not created. Can you put the option of Masters so that ledger can be created in tally"

- **Design decision:** the original brief said never to *silently* create ledgers. The AI proposed a reviewed, human-approved creation flow, which respects that rule.
- **Action:** built a **Create Ledgers** feature:
  - It pre-fills each missing ledger with a suggested group: Customer → Sundry Debtors, Output CGST → Duties & Taxes (Central Tax), and so on.
  - It copies GSTIN and state from the Excel file.
  - The user reviews and confirms, and Tally's own result is shown for each ledger.
  - It then re-syncs the masters and lets the user re-validate the same file with one click.
  - Every step is recorded in the audit log.
- **Also advised:** for GST ledgers that already exist under different names, map the names in Settings instead of creating duplicates.
- **Tests added:** 5 (57 passing at that point).

### Prompt 7: Tally says "Voucher date is missing"
> "It is showing the error that says- voucher date is missing but voucher date is in the excel file attached and also it is coming in the application. why this error is giving by the tally"

- **Investigation:** the AI confirmed the date was present in the XML, then sent a **read-only** query to the local TallyPrime for company details and licence mode.
- **Root cause found:** TallyPrime was running in **Educational mode**, which only accepts vouchers dated the 1st, 2nd or 31st of a month. Other dates are discarded, and Tally then reports them as "missing".
- **Action:** the app now reads the licence mode and books-beginning date from Tally.
  - It warns on the Tally Connection screen.
  - Before posting, it blocks with a plain-English explanation that lists the affected vouchers, instead of Tally's confusing message.
- **Tests added:** 3 (60 passing).
- **Learning:** AI helped diagnose a real-world environment problem, not just write code.

### Prompt 8: Presentation script
> "If someone ask me to explain in 5 minutes what is this application all about... I need the script. But it should be for Lay man people"

- **Action:** wrote a 5-minute, plain-language presentation script with timings and tips for a live demo (see `05_Supporting_Documents`).

### Prompt 9: Capstone packaging
> "I have to submit this data to ICAI... project should contain in zip file... Can you prepare the zip file"

- **Action:** read ICAI's AICA Level 2 document (Annexure D: single ZIP, maximum 100 MB, a separate video link). Then assembled this organised package:
  - Project Summary (Word)
  - Prompt files
  - Example files (templates, sample inputs, and the Tally XML they produce)
  - Executable source code with one-click launchers
  - Supporting documents and the automated test results

---

## Prompt-engineering techniques used

| Technique | Where |
|---|---|
| Role prompting | "Act as a senior Python full-stack architect… with expertise in accounting automation, TallyPrime…" |
| Detailed specification | 37 numbered sections covering scope, templates, validations and workflow |
| Negative constraints | the "DO NOT DO THESE THINGS" list (no EXE, no secrets on the client, no auto-posting) |
| Design before code | "Before writing code, first provide architecture, data flow, API contract…" |
| Incremental development | "Build incrementally… at every stage keep existing functionality working" |
| Evidence-based follow-ups | screenshots of actual errors attached to the refinement prompts |
| Human-in-the-loop guardrails | preview before posting; reviewed ledger creation; demo mode |
