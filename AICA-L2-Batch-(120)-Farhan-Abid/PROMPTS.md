# Prompts used (AI-assisted development log)

Consolidated prompt in Input -> Process -> Output format

This is a cleaned-up prompt that matches the final project. The log above shows the actual messages I typed.

```
You are a senior Python developer and a Chartered Accountant with audit experience. I need a Python based
web application (Streamlit) for my ICAI AICA Level 2 Capstone (Proposal B) which can perform the following
tasks. Test every journal entry in a general ledger and draft a Management Letter.

1. Load the ledger
   INPUT:   User uploads a CSV general ledger (large files allowed) with columns JE\_ID, Posting\_Date,
            Account\_Code, Account\_Name, Description, Debit, Credit, User, Source (optional).
   PROCESS: Validate the columns, parse dates, convert amounts to numbers, create one Amount column.
   OUTPUT:  A clean table, plus counts of ledger lines and journals. Clear error if a column is missing.

2. Anomaly tests (pandas)
   INPUT:   The clean ledger and user settings (approval limit, privileged users, thresholds).
   PROCESS: Run these tests: weekend postings (higher severity for privileged users), large round-number
            amounts, duplicate entries across journals, large manual journals at period end,
            statistical outliers (log-scale z-score per account), amounts just below the approval
            limit, and large manual entries by privileged users.
   OUTPUT:  A list of flagged ledger lines with test name, severity and reason.

3. Variance analysis
   INPUT:   The clean ledger.
   PROCESS: Calculate the net movement per account per month and compare it with that account's own
            monthly average (variance %, z-score, minimum materiality).
   OUTPUT:  A variance table with the material deviations flagged.

4. Benford's Law test
   INPUT:   All amounts of 10 or more.
   PROCESS: Compare first-digit frequencies with Benford's expected frequencies; calculate chi-square
            against the 5% critical value (15.51).
   OUTPUT:  A digit table, a chart, and a conforms / deviates result.

5. Risk scoring (Agent 1 - Detector)
   INPUT:   All flags from tasks 2 to 4.
   PROCESS: Give points per severity (High 3, Medium 2, Low 1), count each test once per journal,
            and add up a score per journal.
   OUTPUT:  Journals ranked by risk score.

6. Investigation (Agent 2 - Investigator, LLM tool-calling)
   INPUT:   The ranked journals.
   PROCESS: The LLM (Groq API, model openai/gpt-oss-120b) calls Python tools in a loop: list\_flagged\_journals,
            get\_journal\_lines, get\_user\_activity, get\_account\_variance, record\_finding. Stop when all
            findings are recorded or after a maximum number of rounds. Escalate CRITICAL / HIGH /
            MODERATE by score. If no API key or the API fails, use rule-based investigation.
   OUTPUT:  A finding per journal: rating, short assessment, recommended audit procedures.

7. Management Letter (Agent 3 - Letter Drafter)
   INPUT:   The most extreme anomalies, Benford result and material variances.
   PROCESS: Send them to the LLM to draft a formal Management Letter (intro, numbered findings with
            observation and recommendation, closing note that it is a draft). Use a template if the
            LLM is not available.
   OUTPUT:  Editable letter text.

8. Dashboard (Streamlit)
   INPUT:   User clicks "Run analysis" after uploading a CSV or choosing the sample ledger.
   PROCESS: Show metrics, flagged journals, charts, Benford, variance, the letter, and an agent log
            that shows how the agents handed work to each other and how many LLM tool calls were made.
   OUTPUT:  An easy-to-use dashboard with a "Test LLM connection" button.

9. Export
   INPUT:   The letter and the findings.
   PROCESS: Create the files with python-docx and openpyxl.
   OUTPUT:  Management\_Letter\_Draft.docx and Anomaly\_Findings.xlsx (findings, flagged lines,
            variance, agent log).

Technical requirements:
1. Use Python with pandas, Streamlit, openpyxl, python-docx and requests.
2. Name the application "Smart Ledger Anomaly \& System-Override Detector".
3. It must work offline with no API key. The LLM is optional.
4. Read the API key and provider only from a .env file. Never put keys in the code.
5. Handle large CSV files quickly (hundreds of thousands of lines).
6. Include requirements.txt, planted anomalies in the sample ledger, unit tests that use a
   fake LLM, a README with a video link placeholder, and a .gitignore that excludes .env.
7. Use the Groq API (free tier) for the LLM; also support Grok (xAI). Handle rate limits and malformed tool calls with retries. Put ALL the code in one file, app.py, with clearly marked sections. Auto-install the required libraries once on first run when run as a .py script (skip this if packaged as an .exe), and make it runnable from IDLE (F5). Include a built-in sample ledger and let me paste the API key in the sidebar.
8. Name the folder AICA-L2-Batch-(120)-Farhan-Abid and keep it under 100 files and 100 MB.
9. Code should be safe, simple and ready to run.

Generate the Python code as per the above specifications.
```

## 

