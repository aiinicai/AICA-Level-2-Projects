# NCE Tool – Tally to ICAI Non-Corporate Entity Financial Statements

**AICA Level 2 – Capstone Project**
**Participant:** CA Praveen Kumar Nahata | **Batch:** 94

## The problem

Audits of proprietorships, partnership firms, LLPs, HUFs and trusts need financial statements in the format of the ICAI Guidance Note for Non-Corporate Entities (NCE). Clients give a Tally trial balance or a T-shaped Balance Sheet and P&L. Converting these into the NCE format (Balance Sheet, Statement of Profit & Loss and Notes, with previous-year figures) is manual, slow and error-prone – often several hours per client.

## The solution

**NCE Tool** is an offline Windows application, built with Claude (AI-assisted development), that:

1. Reads the previous-year and current-year trial balances **directly from Tally via ODBC** (or from Excel files already exported).
2. Maps every ledger to the correct NCE note and line item using rules for Tally groups, keywords and common Tally typos.
3. Writes **one fully formula-linked Excel workbook**: Review, Details, Balance Sheet, Statement of P&L, Notes 1–26, Disclosures, Trial Balance (with drop-downs), Workings and Lists.
4. Lets the CA correct any mapping through drop-downs – every figure updates automatically.
5. Lists all assumptions and warnings on a **Review** sheet so nothing is hidden.

Time per client: about 5 minutes instead of hours.

## AICA Level 2 learnings applied

| Module | How it is used |
|---|---|
| Module 1–2: AI Agents, Claude Skills & Agentic Workspaces | Tool built with Claude Cowork; the build process is packaged as a reusable **Claude Skill** (`Claude_Skill/SKILL.md`) |
| Module 6: Python Fundamentals | Entire tool is in Python (`openpyxl`, `pypdf`, `pyodbc`, `tkinter` GUI) |
| Module 9: AI-Driven Workflow Automation | One-click flow: Tally → trial balances → ICAI-format Excel |
| Module 10: Agentic AI & Tally integration | Live data extraction from Tally (ODBC / HTTP port 9000) |
| Prompt engineering | Detailed master prompt (`Prompt/`) that lets any AI rebuild the tool with the same rules and acceptance tests |

## Folder contents

| Path | What it is |
|---|---|
| `NCE_Tool/nce_tool.py` | The application (GUI + command line); ICAI template embedded |
| `NCE_Tool/run_nce_tool.bat` | Double-click launcher for Windows (installs libraries on first run) |
| `NCE_Tool/run_nce_tool.command` | Launcher for Mac |
| `NCE_Tool/README.txt` | User manual and changelog |
| `Prompt/Prompt_v2.5_Build_NCE_Tool_and_Tally_Extract.md` | Master prompt used to build the tool with AI |
| `Claude_Skill/SKILL.md` | Claude Skill that packages the build workflow |
| `NCE Financials Builder Guide.pdf` | Illustrated guide |

## How to run

1. Install Python 3.9+ (tick "Add python.exe to PATH").
2. Double-click `NCE_Tool/run_nce_tool.bat`.
3. Tab 1 – choose *Extract from Tally* (Tally open, ODBC on port 9000) or *Use files I already have*.
4. Tab 2 – enter client details. Tab 3 – click **Create NCE financial statements**.
5. Open the generated `NCE_<Client>_FY<year>.xlsx` and read the **Review** sheet first.

## Data privacy

The tool runs fully offline – no client data leaves the computer. No client data is included in this repository; example names are dummies.
