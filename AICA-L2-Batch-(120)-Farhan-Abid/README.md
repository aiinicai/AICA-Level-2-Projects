# Smart Ledger Anomaly \& System-Override Detector

**ICAI AICA Level 2 Capstone Project (Proposal B)**
Participant: Farhan Abid | Batch: (120) - Abu Dhabi

🎥 **Video walkthrough:** https://drive.google.com/file/d/16tM9IiGG27OWVBXce\_fF09Gnyca5W0B\_/view?usp=drive\_link

📝 **Prompts used:** see [PROMPTS.md](PROMPTS.md)

## Business problem

Traditional audit sampling can miss unusual journal entries, such as weekend overrides by privileged users, duplicate postings, round-number estimates, entries just under approval limits, and period-end manual journals. This tool tests **100% of ledger lines** and drafts a Management Letter from the findings.

## How it works (multi-agent pipeline)

```
CSV ledger -> Agent 1 Detector -> Agent 2 Investigator (LLM tool-calling) -> Agent 3 Letter Drafter (LLM) -> Word / Excel
```

|Agent|Role|
|-|-|
|**Agent 1 - Detector**|Pandas pipeline: 12 anomaly tests, monthly **variance analysis**, Benford first-digit test, risk score per journal|
|**Agent 2 - Investigator**|**LLM tool-calling loop**: the LLM (Groq, model `openai/gpt-oss-120b`) calls Python tools (`list\\\_flagged\\\_journals`, `get\\\_journal\\\_lines`, `get\\\_user\\\_activity`, `get\\\_account\\\_variance`, `record\\\_finding`) to gather evidence and records a finding per journal. Rule-based fallback if no LLM.|
|**Agent 3 - Letter Drafter**|Feeds the extreme anomalies to the LLM, which drafts the **Management Letter**. Template fallback if no LLM.|

### Tests and analytics performed

1. Weekend postings (higher severity for privileged users)
2. Large round-number amounts
3. Duplicate entries across journals
4. Large manual journals at period end (cut-off risk)
5. Statistical outliers (log-scale z-score per account)
6. Amounts just below the approval limit (split-invoice indicator)
7. Large manual entries by privileged/override users
8. Override or manual journals with no approver, or approved by the person who posted them
9. After-hours postings (22:00 to 05:00)
10. Back-dated or future-dated entries (posting date vs entry date)
11. Debit-credit imbalance within a journal
12. Large manual entries by a user who rarely posts
13. Variance analysis: monthly net movement per account vs its own average (z-score + materiality)
14. Benford's Law first-digit analysis (chi-square)

Tests 8 to 12 use the optional columns `Posting\\\_Time`, `Approved\\\_By`, `Override` and `Entry\\\_Date`. If a ledger does not have them, those tests are skipped automatically.

Large files: the analytics are vectorised pandas; about 340,000 ledger lines are processed in roughly 10 seconds.

## Rubric mapping (Level 2 Capstone, 30 marks)

|Parameter (marks)|Requirement|Where in this project|
|-|-|-|
|Python \& Agentic Logic (10)|Code execution, conditional loops, LLM tool-calling|`app.py` sections 2 and 4: pandas analytics; 3 agents and an orchestrator; a **tool-calling loop** with conditional exit, risk-based escalation, retries and offline fallback|
|API \& Backend Architecture (10)|Successful connection to endpoints|`app.py` section 1: live HTTPS calls to the **Groq API** (`/openai/v1/chat/completions`, with tool definitions); rate-limit handling and retries; *Test LLM connection* button; Word/Excel generation in section 5|
|UI Deployment \& Walkthrough (10)|Streamlit dashboard verified via video|`app.py` section 6 (Streamlit dashboard) + video link above|

## Setup (Windows)

1. Install Python 3.13 or newer from python.org (tick **Add python.exe to PATH**).
2. Run the app, either way:

   * Double-click `run.bat`, or
   * Open `app.py` in **IDLE** and press **F5**, or
   * Type `python app.py` in a terminal opened inside this folder.

On the **first run, `app.py` installs the libraries it needs by itself** (internet needed), then the app opens in your browser at http://localhost:8501. Use **Chrome** if another browser shows a blank page. Keep the black window open while using the app. Alternative: `pip install -r requirements.txt` then `streamlit run app.py`.

The sample ledger is built into the app: tick "Use the built-in sample ledger" and click **Run analysis**. No files to prepare.

### The LLM (Groq API)

The app works fully **offline** without any key. To use the LLM:

1. Create a free API key at console.groq.com (the key starts with `gsk\\\_`).
2. In the sidebar, open **LLM API key**, set **Provider = Groq**, paste the key and press Enter. Leave **Model name** empty (default `openai/gpt-oss-120b`).
3. Click **Test LLM connection** (expect "connection OK"), then **Run analysis**.

The key is kept only while the app is open and is never saved to disk. Alternatively copy `.env.example` to `.env` and set `LLM\\\_PROVIDER=groq` and `GROQ\\\_API\\\_KEY=...`. Grok (xAI), OpenAI, Anthropic and local Ollama are also supported through the same settings. **Never commit your `.env` file or share your key.**

Notes: the free Groq plan has a token-per-minute limit, so the app waits and retries when asked to, and the LLM investigates 4 journals by default (adjustable in the sidebar). The remaining journals are analysed by the offline rules. If the API is unavailable, everything falls back to offline rules and templates.

## Tests

```bash
python -m unittest discover -s tests -v
```

12 tests. They use a scripted fake LLM, so they need no API key. They verify the detectors, the tool-calling loop, rate-limit retries and the fallbacks.

## Input format

CSV with columns: `JE\\\_ID, Posting\\\_Date, Account\\\_Code, Account\\\_Name, Description, Debit, Credit, User`. Optional columns: `Source` (value `Manual` for manual journals), `Posting\\\_Time` (HH:MM:SS), `Approved\\\_By`, `Override` (Y/N) and `Entry\\\_Date`.

## Sample data

The app builds a synthetic ledger (about 3,450 lines) with planted anomalies, so results are reproducible. All data is fictional. The same ledger is saved in `sample\\\_data/sample\\\_general\\\_ledger.csv`, and a button in the app downloads it too.

## Limitations

Flags are indicators, not conclusions. Auditor judgment is required, and the Management Letter is a draft for review. LLM output can be wrong and must be checked.

## Files

```
sample\\\_data/              sample\\\_general\\\_ledger.csv (the built-in sample, ready to upload)
app.py                    ALL the code (6 sections: LLM client, detectors, sample data, agents, export, UI)
run.bat                   Optional Windows launcher
requirements.txt          Library list (app.py also installs these itself on first run)
.env.example              Optional API settings (copy to .env)
tests/test\\\_pipeline.py    Unit tests (mocked LLM)
VIDEO\\\_SCRIPT.md           Walkthrough script
PROMPTS.md                Prompts used with the AI assistant
```

