# TenderIQ – AI-Powered Tender Intelligence Agent

TenderIQ is a simple, one-click Windows application for scraping publicly accessible tender portals, downloading tender PDF/ZIP documents, analysing them using OpenAI, and generating consolidated Excel and PDF management reports.

## Project Structure

```text
TenderIQ/
    app.py
    browser_agent.py
    tender_extractor.py
    document_analyser.py
    report_generator.py
    requirements.txt
    .env.example
    README.md
    START_TENDERIQ.bat
    downloads/
    output/
```

## Windows Installation Instructions

1. Open **Command Prompt (CMD)** inside the `TenderIQ` folder.
2. Install the required Python libraries using this single command:

```cmd
pip install streamlit playwright beautifulsoup4 pandas openpyxl pypdf openai python-dotenv reportlab
```

3. Install the Playwright Chromium browser:

```cmd
playwright install chromium
```

## Configuring Your OpenAI API Key

1. Copy `.env.example` to `.env` in the `TenderIQ` folder:

```cmd
copy .env.example .env
```

2. Open `.env` in Notepad and enter your OpenAI API key:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

> **Note:** Never hardcode your API key in source files. If `OPENAI_API_KEY` is not set, TenderIQ still extracts tender listings and downloads documents, while skipping AI analysis.

## Running TenderIQ

### Option 1: Double-click launcher
Double-click `START_TENDERIQ.bat` inside the `TenderIQ` folder.

### Option 2: Command Prompt
From inside the `TenderIQ` folder, run:

```cmd
streamlit run app.py
```

## How to Use

1. Open the TenderIQ window in your browser.
2. Paste a tender portal URL (homepage, classification/search page, search results page, or specific tender detail page).
3. Click **SCRAPE**.
4. If the portal shows a CAPTCHA or classification search form (such as on eProcure), TenderIQ pauses and keeps the browser window open with the message:
   > `CAPTCHA detected. Please solve it in the browser window.`
   - Choose **Select Classification** (if present) and solve the CAPTCHA either directly in the open Chromium browser window or in the TenderIQ input box, then click **Continue Scraping**.
5. Wait for the automatic extraction, document download, AI analysis, and report generation to finish.
6. Click **DOWNLOAD EXCEL REPORT** or **DOWNLOAD PDF SUMMARY**.

All downloaded documents are saved under `TenderIQ/downloads/` (organised by tender reference) and generated reports are saved in `TenderIQ/output/`:
- `TenderIQ_Tender_Report.xlsx` (`TENDER MASTER` and `AI TENDER SUMMARY` worksheets)
- `TenderIQ_Management_Report.pdf` (Executive Summary + per-tender pages)
