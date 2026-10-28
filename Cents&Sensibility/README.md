# Cents \& Sensibility — Analytical Procedures \& Financial Health Assistant

**AICA Level 2 Capstone Project** · Python + Streamlit + Claude API

Cents \& Sensibility converts a company's financial statements (Excel template or PDF) into a complete SA 520 analytical-procedures workpaper, a forensic financial-health assessment (Altman Z′-Score and Beneish M-Score), AI-drafted going-concern indicators, management inquiries, MD\&A-style commentary, and a formatted Word report for the audit file.

## Quick start

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
venv\\Scripts\\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Claude API key (get one at console.anthropic.com)
copy .streamlit\\secrets.toml.example .streamlit\\secrets.toml     # Windows
# cp .streamlit/secrets.toml.example .streamlit/secrets.toml     # Mac/Linux
# then edit secrets.toml and paste your key

# 4. Run
streamlit run app.py
```

The app also runs **without** an API key: ratio analysis, forensic scores, the SA 520 variance table and a rule-based Auditor's Lens all work offline. The API key enables PDF extraction, the AI-drafted workpaper, and the narrative commentary.

## Demo walkthrough (use this as your presentation script)

1. **Data tab** → upload `sample\_data/sample\_financials.xlsx` → Parse Excel.
2. **Dashboard** → point out the Health Score gauge (Stable, \~60), the **Grey Zone** Altman Z′ and the **Possible Manipulator** Beneish flag — then open the components expander and show DSRI: receivables grew far faster than revenue. This is the "aha" moment.
3. **Ratios \& Trends** → show receivable days jumping from \~66 to \~89; move the materiality slider and watch the flag count change live.
4. **Auditor's Lens** → generate; walk through the SA 520 workpaper and the management inquiries tied to actual numbers.
5. **AI Narrative** → generate the commentary; highlight that it cites real figures.
6. **Export** → build and open the Word report.
7. **The wow moment**: upload a (pre-tested!) PDF of financials → Claude extracts → show the **Review \& Confirm** screen with the balance-sheet tie check → confirm → full analysis re-runs. Emphasise the human-in-the-loop design.

## Project structure

```
finlens/
├── app.py                      # Streamlit UI (custom navy-gold theme)
├── modules/
│   ├── data\_ingestion.py       # Canonical schema, Excel template \& parser, balance check
│   ├── ratio\_engine.py         # 29 ratios, SA 520 expectation-vs-actual variance table
│   ├── forensic\_scores.py      # Altman Z′ (private-firm), Beneish M (8-var), Health Score
│   ├── redaction.py            # Privacy layer: masking, guard, local PDF text
│   ├── branding.py             # App name in one place
│   ├── narrative\_ai.py         # Claude API: PDF extraction, Auditor's Lens, narrative
│   └── report\_export.py        # Formatted Word report (python-docx)
├── sample\_data/sample\_financials.xlsx   # 3-year demo dataset (₹ in Lakhs)
├── make\_sample\_data.py         # Regenerates the sample dataset
├── .streamlit/                 # Theme config + secrets template
└── requirements.txt
```

## Technical highlights (for your report / viva)

* **Document intelligence**: PDF financials are extracted by Claude (`claude-sonnet-4-6`) directly into a strict JSON schema — no brittle table-parsing rules; handles digital and clean scanned PDFs.
* **Human-in-the-loop**: extracted figures appear in an editable review grid with an automatic Balance Sheet tie check (Assets = Equity + Liabilities, 0.5% tolerance) before any analysis runs.
* **SA 520 logic**: prior-year figures form the expectation basis; a user-set materiality threshold flags variances, which flow into the AI workpaper prompt.
* **Forensic models**: Altman Z′ private-firm variant (appropriate for Indian private companies); Beneish M with all 8 indices — TATA uses a working-capital accrual proxy since a cash-flow statement is not an input (disclosed in the UI).
* **Graceful degradation**: every AI feature has an offline rule-based fallback, so the live demo never depends on connectivity.
* **Prompt engineering**: structured JSON output contracts, role framing ("audit manager in an Indian CA firm"), grounding rule ("do not recompute; cite these numbers") to prevent hallucinated figures.

## Limitations (state these — evaluators reward candour)

* AI outputs are drafts requiring professional review; forensic scores are screening indicators, not conclusions.
* Beneish TATA is approximated without a cash-flow statement.
* Extraction accuracy on poor-quality scans is limited; the Excel template is the assured path.
* Schedule III mapping is simplified to 25 canonical line items.

## Cost \& deployment

* One full analysis run (extraction + lens + narrative) costs only a few rupees in API usage.
* Deploys free on Streamlit Community Cloud (add the API key under app Settings → Secrets). Use only anonymised/dummy data on any public deployment.

## Excel workbook with notes 

Besides the fixed Excel template and PDFs, you can upload **your own multi-sheet workbook**: Balance Sheet, P\&L, notes to accounts on separate sheets, or a trial balance. All sheets are read on your computer; you tick the sheets to use, review the (redacted) text, approve, and Claude maps it into the 25-line schema using the notes for break-ups. The usual Review \& Confirm screen with the balance-sheet tie check follows. Try `sample\_data/sample\_workbook\_with\_notes.xlsx` (regenerate with `make\_sample\_workbook.py`). Limits: `.xls` must be re-saved as `.xlsx`; formulas must have calculated values saved; very large ledgers should be left unticked.

## 🔒 Privacy layer 

Cents \& Sensibility can mask who the client is **before** anything reaches the Claude cloud.

* **Privacy mode** (sidebar toggle, ON by default): the entity name, directors, other organisations and addresses you list in the **🔒 Privacy** tab are replaced by tokens such as `\[ENTITY\_1]`, `\[PERSON\_2]` on your computer. PAN, GSTIN, CIN, TAN, DIN, ISIN, UDIN, firm registration no., membership no., e-mail, phone, URL and PIN code are detected by pattern.
* **Line rules**: any line containing a trigger word (DIN, CIN, PAN, GSTIN, Address, Registered Office, Phone, Email… fully editable) is deleted whole, plus the next line if the label ends with a colon.
* **PDFs**: the file is never uploaded. Text is read locally (pypdf) from the pages you choose, redacted, shown to you for review/edit, and only the approved text is sent. Scanned PDFs (no text layer) are refused in Privacy mode.
* **Egress guard**: the exact outgoing prompt is re-scanned; if any registered term survives, the call is blocked and the offline Auditor's Lens is used.
* **Restore**: tokens in the AI's answer are replaced by the real names locally.
* **Limits**: redaction is *not* anonymisation — figures can still identify a company to an informed reader. Always read the preview. For the most sensitive work use Excel + offline Lens (no API key).

Run the tests: `python -m unittest discover -s tests -v`

