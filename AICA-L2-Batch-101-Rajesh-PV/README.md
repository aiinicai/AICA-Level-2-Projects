# Judgement Insights Analyser

**AICA Level 2 Capstone Project** — an AI-assisted desktop application that turns a judgment (court or tribunal order) into a structured, **source-checked** summary, stores it in a searchable **precedent register** for the litigation team, compares rulings, and sends reviewed summaries to **clients and employees**.

> **Disclaimer:** Output is AI-generated for research and knowledge-management purposes and is **not legal advice**. Every summary passes deterministic checks and a human approval step, but must still be verified against the original judgment by a qualified professional before anyone relies on it.

---

## Contents

1. [The problem](#the-problem)
2. [What the app does](#what-the-app-does)
3. [Technology and architecture](#technology-and-architecture)
4. [How reliability is handled](#how-reliability-is-handled)
5. [Requirements and installation](#requirements)
6. [Gemini API key setup](#gemini-api-key-setup)
7. [Using the application](#using-the-application)
8. [Precedent register](#precedent-register)
9. [Emailing clients and the team](#emailing-clients-and-the-team)
10. [Reliability test kit](#reliability-test-kit)
11. [Privacy considerations](#privacy-considerations)
12. [Configuration](#configuration)
13. [Running the tests](#running-the-tests)
14. [Troubleshooting](#troubleshooting)
15. [Project structure](#project-structure)

---

## The problem

A tax litigation team reads many tribunal and High Court orders every month. Each one is long; the relevant holding is often a few paragraphs. Summaries are written by hand, stored in personal folders and rarely found again. When AI is used to summarise, two new risks appear: the AI may **misquote or invent** a citation, date or figure, and it may **not give the same answer twice**.

## What the app does

| Step | What happens | Who / what does it |
|---|---|---|
| 1. Upload | Judgment PDF is read locally; numbered paragraphs are detected and marked `[Para N]` | Python (PyMuPDF) |
| 2. Analyse | 14-section structured report: facts, issues, arguments, provisions, reasoning, order, ratio, obiter, precedents, implications, key insights, points for consideration. Long judgments are processed section by section | Google Gemini |
| 3. Source Check | Every quotation, citation, section, date, amount and paragraph reference in the report is looked up in the judgment text and marked *Found / Close / Not found* | Python (no AI) |
| 4. Consistency Check | The key facts are extracted **twice** independently and compared field by field; where they disagree the reviewer chooses the correct value in Review & Approve | Gemini x2 + Python comparison |
| 5. Review & Approve | The reviewer edits any section, chooses between the two AI runs where they disagree, confirms the citation (optional online lookup with sources), acknowledges the Source Check and approves. **Nothing can be saved, printed, exported, registered or emailed before approval** | Human |
| 6. Register | The confirmed summary is saved to the **precedent register** with court, date, AY, sections, issues, outcome, in whose favour, ratio, tags, scores and a copy of the PDF. A reviewer marks it **Verified** | SQLite database |
| 7. Compare | Two register entries on the same issue are compared: where they agree, where they conflict, forum and weight | Gemini + human review |
| 8. Communicate | Two email versions - a **client** version and a **team** version (with paragraph references and the register reference) - sent to Clients, Employees or Both after approval; client emails only for **Verified** entries | Outlook / Gmail / any SMTP / .eml |

Exports (after approval only): one **Save ▾** button - Word (.docx), PDF, text (.txt) or data (.json); register to Excel.

**Clean, client-ready output.** Word, PDF and email output start with *Generated on*, *Case* and *Citation* (from the judgment; if it is unreported, the app shows the case number, forum and date, or a citation the reviewer accepted from the online lookup). The review labels (`[Court Finding]`, `[AI Observation]`, `[AI Generated]`), page numbers, technical details (model, processing mode, source file), quality checks and the AI footer are **not** printed. Text is justified.

**Why paragraph numbers and not page numbers?** The same order is published by the official site, Taxmann, TaxTMI and others, each with different page numbers. Paragraph numbers are part of the order itself and are the same in every copy, so the app cites `para 12` only.

## Technology and architecture

| Layer | Technology | Why |
|---|---|---|
| Front end | **CustomTkinter** (Python desktop GUI) | Runs on the user's PC; no web server to secure; judgments stay local |
| Back end / logic | **Python 3.10+** modules (`judgment_analyzer/`) | PDF reading, paragraph detection, Source Check, consistency comparison, exports, email |
| AI | **Google Gemini API** via the official `google-genai` SDK (default model `gemini-3.8-flash`; `gemini-3.5-flash` also works) | Report writing, key-fact extraction (JSON mode), comparison of rulings |
| Database | **SQLite** (`precedent_register.db`, built into Python) | Zero-install, single file; can sit in a shared OneDrive/SharePoint/network folder |
| PDF | **PyMuPDF**; optional **Tesseract OCR** for scanned pages | Fast local text extraction |
| Exports | **python-docx**, **reportlab**, **openpyxl** | Word, PDF and Excel outputs |
| Email | **Outlook COM** (pywin32) on Windows, **smtplib** for Gmail / Microsoft 365 / Zoho / any SMTP, or **.eml** files | Works with the firm's existing mailboxes |
| Secrets | **keyring** (Windows Credential Manager / macOS Keychain / Linux Secret Service) | API key and email App Password are never stored in plain text |
| Hosting / distribution | **Desktop application distributed through GitHub** (source + launcher scripts). No cloud server: the only network calls are to the Gemini API and the chosen mail server | Privacy, zero hosting cost |
| Tests | **pytest** (no network; Gemini and the mail server are faked) | Repeatable verification |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the data-flow diagram and module map.

## How reliability is handled

**Will the AI give the same output if the same judgment is analysed twice?** Not word for word - this is a known property of large language models, even at low "temperature". The app is therefore designed so that **no single AI run is trusted**:

1. **Consistency Check** - key facts are extracted twice and compared by Python; any disagreement must be resolved by the reviewer in Review & Approve before anything can be saved or emailed.
2. **Source Check** - quotations, citations, sections, dates, amounts and paragraph references are verified against the judgment text by deterministic code (same answer every time).
3. **Human approval** - nothing reaches a client or the register as *Verified* without a named reviewer.
4. **Measured, not claimed** - the [reliability test kit](#reliability-test-kit) produces agreement and accuracy percentages on your own test set of judgments.

Why not run the full report several times and pick the best? "Best" needs a judge - using another AI run to judge only moves the problem, and three full reports triple the time and free-tier quota. The app repeats the **short, checkable** part (key facts) and leaves judgement to the reviewer. Full discussion: [docs/RELIABILITY.md](docs/RELIABILITY.md).

**Temperature.** For Gemini 3.x models the app uses the model's default temperature, following Google's Gemini 3 developer guide, which recommends keeping the default (1.0) because lower values can cause looping or degraded output. Older models use 0.2. (Setting `temperature_mode` - see Configuration.)

## Requirements

| Item | Version / notes |
|---|---|
| Python | **3.10 or newer** (tested on 3.12 and 3.13) |
| Tkinter | Included with python.org installers for Windows and macOS. On Linux: `sudo apt install python3-tk` |
| Tesseract OCR | *Optional.* Needed only for scanned PDFs (see below) |
| Internet | Required for the Gemini API |
| Gemini API key | Free or paid, from Google AI Studio |

### Installing Tesseract OCR (for scanned PDFs only)

- **Windows:** install the UB Mannheim build from <https://github.com/UB-Mannheim/tesseract/wiki>. The app finds the default location (`C:\Program Files\Tesseract-OCR\tesseract.exe`) automatically, as well as per-user installs. If the app still shows "OCR program not installed", click **Locate installed OCR…** and pick `tesseract.exe`. The **Get OCR (free)** button opens the download page.
- **macOS:** `brew install tesseract` (and `brew install tesseract-lang` for more languages).
- **Debian/Ubuntu:** `sudo apt install tesseract-ocr`. Language packs are installed separately, e.g. `sudo apt install tesseract-ocr-hin`.

OCR reads **English** only. The language is fixed so that it cannot be set to one whose language data isn't installed, which would make OCR fail.

## Installation

```bash
# 1. Extract the ZIP and open a terminal in the extracted folder
cd "Judgement Insights Analyser"

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

**Recommended:** on Windows, double-click `run_windows.bat`; on macOS or Linux, run `./run_mac_linux.sh`. Extract the ZIP first; don't run the launcher from inside it.

- **First launch:** the launcher creates a private Python environment in your user profile and installs the packages. This takes a few minutes, once.
  - Windows: `%USERPROFILE%\.JudgmentInsightAnalyzer\venv` (deliberately not under AppData: Microsoft Store Python redirects AppData writes into its own package folder). If that location cannot be used, it falls back to a `.venv` folder inside the app folder.
  - macOS / Linux: `~/Library/Application Support/...` or `~/.local/share/...`
- **Later launches:** the app starts straight away. This includes after you replace the app folder with a newer version.
- **Reinstalls:** packages are installed again only if something is missing or `requirements.txt` changes.

## Gemini API key setup

1. Go to <https://aistudio.google.com/apikey>, sign in, and click **Create API key**.
2. Start the app and paste the key into **Gemini API Settings → API key**. The field is masked; tick **Show** to check what you typed.
3. Click **Test API Key**. A green tick confirms that both the key and the selected model work.
4. *Optional:* tick **Remember key securely on this computer**. The key is stored in your operating system's credential vault: Windows Credential Manager, macOS Keychain, or Linux Secret Service. It is never written to a plain-text file by the app. Click **Forget Saved Key** to remove it.

**Alternative:** copy `.env.example` to `.env` and set `GEMINI_API_KEY=...`. The app reads it at start-up. Keep `.env` private.

> The source code contains no API key. Do not commit your `.env` file to version control. It is already listed in `.gitignore`.

### Choosing a model

The default model is `gemini-3.8-flash`. On the date of the Google *Models* and *Deprecations* pages checked for this release (Oct 2026), it was a stable model that Google recommended for new projects. Other suggestions in the list are `gemini-3.6-flash`, `gemini-3.5-flash-lite` (faster and cheaper) and `gemini-3.1-pro-preview`.

Model availability changes over time. Click **↻ (Refresh models)** to load the models your key can actually use, or type any model ID into the box. If Google retires a model, choose a newer one. The app reports "model not found" rather than failing silently.

## Running the application

```bash
python main.py
```

Settings are saved automatically to your user profile:

| OS | Location |
|---|---|
| Windows | `%USERPROFILE%\.JudgmentInsightAnalyzer\data\` (not under AppData, so the files are visible to Excel even with Microsoft Store Python; data from earlier versions is copied here automatically) |
| macOS | `~/Library/Application Support/JudgmentInsightAnalyzer/` |
| Linux | `~/.config/JudgmentInsightAnalyzer/` |

Log files are kept in the `logs` subfolder of that location. They record processing steps and errors only. They never contain document text, and API keys are redacted.

## Using the application

1. **Upload Judicial Decision PDF.** (Try `examples/Fictitious_Sample_ITAT_Order.pdf` - an invented order made for demonstrations.)
2. Enter and test your API key; pick a model (**↻** loads the models your key can use).
3. Options: OCR mode, **Paragraph references**, **Process long judgments in parts**, **Double-check key facts** (the key facts are read twice by the AI and compared; any difference is shown for you to choose).
4. **Analyze Judgment.** The status line says *Analysis complete*, or lists what needs checking.
5. Review the tabs: Full Report, Summary, Legal Analysis, Key Insights, Points for Consideration and **Source Check** (items not found in the judgment are listed first, with the Consistency Check field by field).
6. **✎ Edit this tab** to correct the AI's wording (keep the `## ` heading lines). The Source Check re-runs after every edit. **Source Check** lists every quotation, citation, section, date, amount and paragraph number the AI wrote that could not be found in the judgment: open the judgment, check each one, and correct or delete it in the report.
7. **✔ Review & Approve** - confirm the key facts (where the two AI runs disagree, pick Run 1, Run 2 or type the value), confirm or look up the citation, tick that the Source Check items were checked, optionally save to the precedent register with tags, and enter your name. Only now are Save and Email enabled. (The approval saves to the register; there is no separate register button.) Any later edit cancels the approval.
8. **📚 Register** (header button) - search, open, verify, compare, export.
9. **✉ Email** - send the client and/or team version (see below).

## Supported PDF types

| Type | Support |
|---|---|
| Text-based PDFs (downloaded from court websites, SCC Online, Manupatra, Indian Kanoon, eLitigation, CanLII, BAILII, etc.) | Full support |
| Scanned / image-only PDFs | Supported through Tesseract OCR. Accuracy depends on scan quality. |
| Mixed PDFs (some pages scanned) | Supported. OCR is applied only to the pages that need it. |
| Password-protected PDFs | Not supported. Remove the password first. |
| Corrupted, empty or non-PDF files | Rejected with a clear message |
| Files over the size limit (default 200 MB) | Rejected |

OCR can misread names, numbers and citations. Always check critical details against the original.

## How long judgments are processed

- A document of up to about 400,000 characters (roughly 100k tokens) is sent in **one request**. Before sending, the app also checks the model's reported input-token limit and switches to sections if the document would use more than 75% of it.
- Larger documents, or any document when **Always process section by section** is on, are handled in four steps:
  1. The text is split into **sections of whole pages** (default 60,000 characters) with a short overlap, so findings that cross a boundary are kept.
  2. Gemini takes **loss-averse notes** for each section under fixed headings: facts, issues, arguments, provisions, precedents, findings, orders, obiter and unclear text. Exact citations, dates, amounts and page references are preserved, and key holdings are quoted.
  3. If the combined notes are still very large, they are merged hierarchically.
  4. The final report is written from all section notes, plus the judgment's **opening and closing pages verbatim**, so that case details and the operative order are never paraphrased away.
- If Gemini reports that a single request is too large, the app automatically switches to section-by-section processing.

## Precedent register

- **Search** by words (case name, issue, tag, citation, ratio, AY), by **section** with **Either Act / 1961 Act / 2025 Act** (exact: `68` does not match `168`), by status and by outcome.
- **Two Acts:** sections of the Income-tax Act, 1961 and the Income-tax Act, 2025 are stored separately. The 1961 Act has no section above 298, so a higher number is always a 2025 Act section; for lower numbers the app checks which Act the judgment names next to the section and flags doubtful cases for the reviewer.
- **Update details…** corrects or completes an entry later: citation (once reported - online search available), names, assessment year, sections, outcome, tags, and any of the 14 analysis sections (e.g. Important Precedents Cited). Items the reviewer asked to correct are marked in red. The corrected text is checked against the stored judgment PDF before saving. Who updated it is recorded.
- **Return for correction** - the reviewer ticks the items to correct and adds a note.
- **Search as you type**: the list filters while you type; **Clear filters** shows everything again.
- **Two-level sign-off (maker / checker):**

| Step | Who | Where | Result |
|---|---|---|---|
| Review & Approve | Preparer | Main window | Output can be saved / emailed; entry saved to the register as **Draft** |
| Mark verified | Reviewer (ideally a different, senior person; the app warns if it is the same person) | Register | **Verified** - the team may rely on it |
| Return for correction | Reviewer | Register | **Returned**, with the reason |
| Update details | Preparer | Register | Back to **Draft** for the reviewer |

Correcting anything other than the citation or tags on a Verified entry puts it back to Draft, because the checked content has changed. Deleting and re-analysing is needed only if the analysis is unusable.
- **Open summary** shows the key facts, scores and full report; **Open PDF** opens the stored copy of the judgment; **Save as Word**.
- **Mark verified…** records the reviewer's name and time. Draft entries should not be relied on.
- **Email** - send a register entry to clients / the team in the same email window (not for entries returned for correction).
- **Compare 2 selected** - select two rulings (Ctrl+click): Gemini produces a structured comparison (snapshot, common issue, facts, holdings, agreement, conflict, precedential weight, guidance, points to verify), exportable to Word.
- **Export to Excel** for MIS or sharing.
- **Same judgment twice:** the PDF's SHA-256 fingerprint is checked on saving. If it is already in the register you can link to the existing (verified) entry instead of creating a second, different summary.
- **Location:** on first use the app asks where to keep the register (this computer, or a folder you choose) and shows the full path in the header badge. **Change location…** can point every PC to one file in a shared OneDrive / SharePoint-synced / network folder. SQLite handles short writes from a few users, but it is not a multi-user server: let one reviewer do most of the saving and verifying, and keep backups.

## Emailing clients and the team

**Recipients.** Two separate lists - **Clients** and **Employees** - each with its own *Template* (`Client_list_template.xlsx`, `Employee_list_template.xlsx`) and *Load…* button. Columns: *Name*, *Email ID*, optional *Salutation*, *Company*, *Consent* (`No` = never email). Choose **Send to: Clients / Employees / Both**. Loaded lists are **saved on this computer** and reappear the next time the email window opens; load a new file to replace a list, or click **Forget** to delete it.

**Two versions,** edited side by side:

| | Client version | Team version (employees) |
|---|---|---|
| Default sections | Case details, executive summary, practical implications | Case details, summary, issues, final order, ratio, key insights |
| Labels `[Court Finding]` / `[AI Observation]` | Shown in the editor (green / red, bold) for review; **never** in the sent email | Same |
| Page references | Removed | Removed |
| Extra | Optional closing note | Register reference, optional closing note |

Emails are HTML: bold headings, proper bullets, justified text, no `##` markers.

**Who may receive what.** Each group always receives its own version - the app never swaps them. Client emails are allowed only when the register entry is **Verified**; the Team version may go to employees while it is Draft. Before approval the app checks for team material in the Client version (team subject or opening, register reference), client opening in the Team version, colleagues in the client list and outsiders in the employee list (by the firm's email domain).

**Approval gate.** Approval is blocked while any `[Uncertain]` point remains, while key facts the AI runs disagreed on are unconfirmed, or until the reviewer ticks that the items the Source Check could not find were checked. Changing any text or the recipient group after approval cancels the approval.

**Delivery options**

| Option | Notes |
|---|---|
| Create drafts in Outlook / Send now via Outlook | Windows with Outlook desktop installed and signed in |
| **Send via email account (Gmail / SMTP)** | Any computer. Presets for Gmail (smtp.gmail.com, 465, SSL), Microsoft 365 / Outlook.com (smtp.office365.com, 587, STARTTLS), Zoho Mail India, or your own server. **Gmail requires 2-Step Verification and an App Password** (Google Account → Security → App passwords) - your normal password will not work. Providers cap daily sending; check your provider's limits. |
| Save as .eml files | Open in any mail program and send |

**Without recipients:** *Create drafts in Outlook* and *Save as .eml files* work even with no list loaded - one email per version with an empty 'To' line and the greeting 'Dear <<Recipient name>>,', to complete in Outlook. Recipients are required only for *Send now via Outlook* and *Send via email account*. Opening the Team or Client tab switches *Send to* to that group.

**Send test to me** sends each version in use to your own address first. Every email (including tests) is recorded in `email_audit_log.csv` with the recipient group, register reference and a fingerprint of the approved content.

## Reliability test kit

`tools/reliability_eval.py` measures the app on your own set of public judgments:

```bash
python tools/reliability_eval.py --pdf-dir test_judgments --make-gold gold.xlsx      # answer-key template
# fill in gold.xlsx by reading each judgment
python tools/reliability_eval.py --pdf-dir test_judgments --runs 3 --gold gold.xlsx --out results.xlsx --full-report
```

It reports, per judgment and overall: **run-to-run agreement %** on the key facts, **accuracy %** against your answer key, and (with `--full-report`) the **Source Check %**. Put the resulting figures in your project report rather than quoting a generic accuracy claim. Use only public judgments; on the free tier Google may use requests to improve its products.

## Privacy considerations

- The PDF is read **locally**. OCR runs **locally** with Tesseract.
- The extracted **text** is sent only to Google's Gemini API (`generativelanguage.googleapis.com`) through the official SDK, and only when you click **Analyze Judgment**. The PDF file itself is never uploaded, and nothing is sent to any other service.
- The app has no telemetry. Logs stay on your computer and contain no document text.
- **How Google uses your data depends on your tier.** Per the Gemini API Additional Terms of Service (last updated 28 Apr 2026):
  - On **Unpaid Services**, Google may use submitted content to improve its products, and human reviewers may read inputs and outputs. Google advises that you not submit sensitive, confidential or personal information to Unpaid Services.
  - On **Paid Services** (a Cloud project with active billing), prompts and responses are not used to improve Google's products.
  - Review the current terms at <https://ai.google.dev/gemini-api/terms> before you process confidential or client material. Redact or anonymise where appropriate.
- Your saved API key is stored only in the OS credential vault, and only if you opt in.

- The precedent register, the stored PDF copies, the recipient list, the email audit log and the email account settings stay on your computer (or the shared folder you choose). The email password is kept only in the OS credential vault, and only if you tick *Remember*.
- Do not commit `.db` files, recipient lists, audit logs or `.env` to GitHub (they are listed in `.gitignore`).

## Configuration

The app always runs a detailed analysis. Advanced settings live in `settings.json` (location above); `config/settings.example.json` lists every setting.

| Setting | Default | Purpose |
|---|---|---|
| `temperature_mode` | `auto` | `auto`: model default for Gemini 3.x, `temperature` for older models. `fixed`: always `temperature` |
| `temperature` | 0.2 | Used for non-Gemini-3 models (or always, in `fixed` mode) |
| `include_para_refs` | true | Detect numbered paragraphs and cite them as (para N) |
| `consistency_check` | true | Extract key facts twice and compare |
| `register_path` | "" | Register database file ("" = app data folder) |
| `chunk_max_chars` | 60,000 | Section size for long judgments |
| `chunk_overlap_chars` | 1,500 | Context carried between sections |
| `single_pass_max_chars` | 400,000 | Larger documents are sectioned |
| `max_output_tokens` | 32,768 | Increase if output is truncated |
| `request_timeout_s` | 300 | Per request |
| `max_retries` | 4 | Exponential backoff on rate limits, 5xx errors and timeouts |
| `max_file_size_mb` | 200 | Upload limit |
| `tesseract_cmd` | (auto) | Path to `tesseract.exe` if installed in a non-standard folder |

The environment variable `GEMINI_MODEL` overrides the model.

## Running the tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover PDF handling, chunking, response parsing, exports, settings and keys, Gemini error handling, the analysis pipeline, client emails, and the review features: paragraph detection, Source Check, Consistency Check, temperature handling, the precedent register, comparison prompts, recipient groups, the team email version and SMTP delivery. They make **no network calls** and need **no API key**.

## Troubleshooting

| Problem | Solution |
|---|---|
| `Tkinter is not available` | Linux: `sudo apt install python3-tk`. Windows and macOS: reinstall Python from python.org. |
| "Packages are not installed" even after `pip install` | Your `pip` belongs to a different Python than the one opening the app (common on Windows). Easiest fix: double-click `run_windows.bat`, or click **Yes** when the app offers to install the packages itself. Manual fix: run the exact command shown in the error, `"<path shown>\python.exe" -m pip install -r requirements.txt`. |
| "Installed but failed to load" | Run the `--force-reinstall` command shown in the message. If it mentions a DLL on Windows, install the latest Microsoft Visual C++ Redistributable (x64). |
| `run_windows.bat` installs packages every time | Use the latest version of the app, whose launcher keeps its environment in your user profile. Also make sure you run it from an extracted folder, not from inside the ZIP. |
| `run_windows.bat` shows an install error | Read the message in the window. A corporate proxy blocking pypi.org is the usual cause. |
| "Gemini rejected the API key" | Re-copy the key from AI Studio. Check it has not been deleted or restricted. |
| "Model ... was not found" | Click **↻** to load available models, or choose another model |
| Rate limit / quota message | The status line says which limit was hit. **Per-minute:** the app waits as long as Google asks and retries automatically. For large judgments, turn on **Always process section by section**. **Daily:** resets at midnight Pacific time (early afternoon IST); switch model meanwhile. **No quota for this model:** your key has no free-tier allowance for that model; pick another with **↻** or enable billing. Your exact limits are shown in Google AI Studio. |
| "Could not reach the Gemini API" | Check your internet connection, VPN or corporate proxy. The SDK respects the `HTTPS_PROXY` environment variable. |
| "Gemini declined ... safety policy" | Some content may be blocked. Try another model or analyse a smaller extract. |
| "PDF appears to be scanned ... Tesseract not found" | Click **Get OCR (free)**, install, restart the app. If it's still not found, use **Locate installed OCR…** |
| "OCR language data ... not installed" | The English data was not installed with Tesseract. Reinstall Tesseract with default options. |
| "password-protected" | Open the PDF with its password and print or save it to a new, unprotected PDF |
| Output says it was truncated | Turn on **Always process section by section**, or ask an administrator to raise `max_output_tokens` |
| Some sections show "Not provided in the AI response" | Re-run the analysis, or try a stronger model (e.g. a Pro model) |
| Non-Latin text shows as boxes in exported PDF | The exporter uses Arial or DejaVu Sans if available. Export to Word instead for scripts these fonts lack, such as Devanagari, Tamil or Japanese. |
| "Key not saved: No secure credential store" | Linux without a keyring service. Install `gnome-keyring`, or use a `.env` file. |
| Gmail: "The email server rejected the login" | Turn on 2-Step Verification in your Google Account, create an **App Password** and paste that 16-character password (not your normal Gmail password). |
| Gmail: sign-in fails although the password works in the browser | Apps cannot use your normal Gmail password. Turn on 2-Step Verification, create an **App Password** at myaccount.google.com/apppasswords and paste those 16 letters. The app warns if the password is not 16 letters. |
| Gmail: connection test shows `sign in: SMTPServerDisconnected` after the greeting succeeded | The connection is cut when the password is sent. Gmail itself would reply 'Username and Password not accepted' to a wrong password, so this is almost always email-scanning software or a company firewall. Look at the *certificate* line (not Google = intercepted) and the *Security software running* line. Turn off outgoing-mail (SMTP) / SSL email scanning in that product or add an exception for the app (Python), or test on a mobile hotspot to rule out the office network. Also confirm 2-Step Verification is on and you pasted the 16-letter App Password of the same Gmail account. Meanwhile use **Create drafts in Outlook**. |
| Microsoft 365: login rejected | Some organisations switch off password (SMTP AUTH) sign-in. Ask IT, or use **Outlook** delivery on Windows. |
| Test sign-in fails | A connection-test window shows each step (server lookup, port, secure handshake, greeting, sign-in) with OK / FAIL and what it means. Copy it to IT if needed. |
| "Could not connect to smtp..." / `SMTPServerDisconnected` | The connection was closed **before** the password was checked, so it is a network block, not a wrong password. The app tries port 465 (SSL) and then 587 (STARTTLS) automatically. If both fail: antivirus "email shield", office firewall or VPN is blocking mail ports - try a mobile hotspot to confirm, then ask IT to allow smtp.gmail.com on 465/587, or use Outlook delivery. |
| "The register file could not be opened" | The shared folder is offline or the file is damaged. Use **Change location…** in the register, or restore the .db file from backup. |
| Approval blocked: "AI runs disagreed" | In **Review & Approve**, pick Run 1 or Run 2 (or type the value) for each field marked in red. |
| Anything else | Check the log file in the settings folder `logs` directory |

## Project structure

```
Judgement Insights Analyser/
├── main.py                     # entry point (environment checks, logging, GUI start)
├── judgment_analyzer/
│   ├── config.py               # settings, validation, temperature policy, register location
│   ├── key_store.py            # secure storage of the API key and email password (keyring)
│   ├── logging_setup.py        # rotating logs with API-key redaction
│   ├── pdf_processor.py        # PDF validation, text extraction, OCR fallback
│   ├── paragraphs.py           # numbered-paragraph detection and [Para N] markers
│   ├── chunker.py              # page-aware sectioning for long judgments
│   ├── prompts.py              # system instruction and report / section / consolidation prompts
│   ├── gemini_client.py        # google-genai wrapper: errors, retries, JSON mode, cancellation
│   ├── analyzer.py             # pipeline: extract → analyse → Source Check → Consistency Check
│   ├── response_parser.py      # Markdown report → 14 canonical sections
│   ├── verifier.py             # Source Check (deterministic)
│   ├── consistency.py          # key facts (always), double-check, fallback from report/judgment
│   ├── sections_act.py         # Income-tax Act 1961 vs 2025 section sorting
│   ├── citation_lookup.py      # optional web lookup of a reported citation
│   ├── repository.py           # SQLite precedent register, Excel export
│   ├── compare.py              # comparison of two rulings
│   ├── exporter.py             # plain text, Word and PDF export
│   ├── email_composer.py       # client and team versions, review checks, rendering
│   ├── audience_check.py       # client/team content and recipient mix-up checks
│   ├── recipients.py           # client / employee lists: import, templates, saved lists
│   ├── mailer.py               # Outlook, SMTP (Gmail etc.) + diagnosis, .eml, audit log (CSV + Excel)
│   └── ui/
│       ├── app.py              # main window
│       ├── register_ui.py      # Review & Approve, register, update details, return, compare
│       ├── email_dialog.py     # email window (groups, two versions, approval, delivery)
│       ├── widgets.py          # cards and the Markdown results viewer
│       └── theme.py            # colours and fonts
├── tools/reliability_eval.py   # reliability test kit
├── docs/                       # architecture, reliability, video script, development notes, build prompt, GitHub guide
├── examples/                   # fictitious sample order for demonstrations
├── assets/                     # logo and icon
├── config/settings.example.json
├── tests/                      # pytest suite (no network)
├── requirements.txt / requirements-dev.txt
├── .env.example / .gitignore / LICENSE
└── run_windows.bat / run_mac_linux.sh
```

## Putting it on GitHub and rebuilding it

- **GitHub:** step-by-step guide in [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md) (GitHub Desktop or command line) and course submission in [`docs/GITHUB_SUBMISSION.md`](docs/GITHUB_SUBMISSION.md).
- **Build prompt:** [`docs/BUILD_PROMPT.md`](docs/BUILD_PROMPT.md) is a consolidated specification that an AI coding agent can use to rebuild this application.

## Licence

MIT - see [`LICENSE`](LICENSE).

## Credits

Prepared as the AICA Level 2 (ICAI) capstone project. The application was designed by the author and built with the help of AI coding assistants, as encouraged by the course; the author reviewed the design, the prompts and the tests. Sample data in `examples/` is fictitious.
