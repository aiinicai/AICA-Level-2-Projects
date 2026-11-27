# IncentiveIQ India V7.4
ICAI Level 2 AI project | CA Prasun Jain

A Streamlit decision-support prototype for industrial incentive research, source-grounded answers, state comparisons and illustrative investment appraisal. Directory covers 36 jurisdictions; functional screenshots cover UP, Maharashtra and Gujarat only.

## Run locally
1. Install Python 3.10+ and extract the repository.
2. Run `python -m pip install -r requirements.txt` and `python -m streamlit run app.py` (or double-click START.bat on Windows).
3. For local AI, install Ollama, run `ollama pull qwen2.5:1.5b`, ensure Ollama is running, then use Check Ollama connection. Fast modes do not require Ollama.
4. For scanned PDFs install Tesseract and follow OCR_SETUP.txt.
5. In Live research, select state, fetch official HTTPS URLs or import PDFs. UP and historical Maharashtra have default URLs; Gujarat requires a source URL or upload. Reuse your existing policy_cache locally if available; it is not included.

## Demo question
What are the stamp duty exemption or reimbursement benefits available under the industrial policy of the selected state?

## Architecture
Browser-assisted discovery → HTTPS fetch / PDF upload → layout text or OCR → per-state JSON cache → ranked excerpts and targeted rule extraction → optional Ollama evidence selection → source-linked display / Excel export. Finance calculations use independent illustrative assumptions.

## Testing
Run `python TESTS.py`. All bundled synthetic and mocked regression assertions passed in the packaging environment. User screenshots show three-state V7.4 output and local AI connection; no independent live policy or Windows end-to-end test was performed here.

## Limitations
Maharashtra 2019 is historical; Gujarat OCR is provisional. Source extracts are not legal entitlements. No automatic amendment reconciliation, universal table parser or verified nationwide policy coverage. Uploaded provenance is unverified. PDF limit 20 MB / 250 pages; OCR default 30 scanned pages. Local AI selects excerpts, not rates.

## Repository
app.py: UI; panindia.py: sources/cache; ocr66.py: OCR; answer*.py and stamp74.py: targeted extraction; local73.py: Ollama; comparison69.py / comparison70.py: comparison; finance70.py: financial model; TESTS.py: regression tests. See docs/ and evidence/. README.txt retains original version history.
