# Financial Reporting Review Assistant

A browser-based review assistant for **Chartered Accountants** and **Financial Reporting Review Board (FRRB)** technical
reviewers. It reviews draft financial statements and annual reports against **Indian Accounting Standards (Ind AS)**,
**Accounting Standards (AS)**, **Schedule III** (Divisions I, II and III) and the **Companies Act, 2013**, and produces
evidence-based review observations in the format of an FRRB Technical Review report.

**Live application:** https://frrb-review-assistant.streamlit.app

---

## Review methodology

The assistant is designed to think like a financial reporting reviewer, not to run through a checklist.

1. **Accuracy over quantity** - an observation is raised only when a deviation is substantiated by the financial statements.
2. **Applicability first** - before any check, the assistant establishes from the company's own figures and disclosures
   whether the item, transaction or disclosure exists. A nil or absent item is recorded as "Not applicable", never reported
   (for example: no capital work-in-progress -> no CWIP ageing observation).
3. **Evidence for every observation** - each observation cites its location (sheet / page, row, caption) and the amounts
   relied on. Ind AS / AS requirements are quoted from the paragraph text of the notified standards.
4. **No checklist observations** - the absence of "negative statements" (benami property, crypto currency, wilful defaulter,
   struck-off companies, layers of companies) is not reported, because those disclosures are required only where the
   situation exists.
5. **Holistic cross-verification** - the strongest observations come from comparing one part of the financial statements with
   another: face vs notes, ratio table vs its workings, related-party note vs balances, ageing schedules vs other notes,
   deferred tax movement, EPS recomputation, periods presented and spreadsheet errors.
6. **Classification** - every observation is classified as **Non-compliance**, **Inconsistency**, **Disclosure gap**,
   **Potential concern** or **Requires verification**.

### Entity profile detected from the statements
The framework (Ind AS / AS), Schedule III division, private / public / listed status (from the CIN), reporting date,
rounding unit and small company / Small and Medium-sized Company (SMC) status are read from the financial statements
themselves. If the sidebar selection differs, the assistant shows the difference and, by default, uses the detected profile,
so that statutory exemptions (for example the cash flow statement exemption for small companies under Section 2(40), or the
SMC relaxations under AS 20 and AS 15) are applied correctly.

---

## Outputs

1. **Financial Reporting Review Points Sheet** (on screen and as an Excel download)
   - *Review Observations* - S. No., Title, Sub Title, View of the Reviewer, Matter contained in the Financial Statements
     (evidence and location), Exact Technical Requirement(s), Nature, Significance, Basis, Suggested correction.
   - *Checks & Applicability* - every check performed, whether it was applicable, the basis from the financial statements,
     and the result.
   - *Entity Profile* - the profile detected from the statements.

2. **Draft Financial Statements (Yellow Highlights)** - the uploaded Excel workbook is returned **in its own format**
   (sheets, layout, fonts, number formats and formulas retained). The lines each observation relies on are highlighted in
   yellow with a cell comment; where a disclosure is genuinely missing, draft wording is inserted into the relevant note in
   yellow, with amounts left as `[___]` for management to complete. A *Yellow Changes Index* sheet lists every change.

---

## Optional AI review (Google Gemini)

Without an API key the application runs entirely on the deterministic review engine. With a Gemini API key
(model `gemini-2.5-flash`), the AI looks for additional matters. Its output is accepted only if:
- every extract it quotes is found verbatim in the uploaded statements,
- every amount it relies on appears in the statements,
- it is not a bare checklist point, and
- it does not duplicate an observation already raised.

AI suggestions that fail these tests are rejected and listed separately. When a key is used, extracts of the financial
statements are sent to Google.

---

## Project structure

```
app.py                         Streamlit web application
core/
  fs_model.py                  Structured model of the statements; detects the entity profile
  review_engine.py             Applicability-gated, evidence-based checks and the applicability log
  ai_reviewer.py               Optional Gemini review with evidence validation
  knowledge_base.py            Paragraph lookup in the Ind AS / AS knowledge base; citation verification
  fs_marker.py                 Marks the entity's own workbook in yellow (Draft Financial Statements output)
  excel_generator.py           Review Points Sheet workbook (FRRB Technical Review layout)
  pdf_extractor.py             Reads Excel workbooks and text-based PDFs; detects scanned PDFs
  applicability.py             Sidebar profile validation (Companies (Ind AS) Rules, 2015; Schedule III)
  frrb_library.py              ICAI FRRB precedents shown in the Technical Reference Library tab
  rules_engine.py, ai_analyzer.py, schedule_iii_viewer.py, reference_matcher.py
                               Earlier versions, not used by the application (kept for reference and their unit tests)
knowledge_base/
  standards_paragraphs.json    Paragraph-level text of the notified Ind AS and AS
sample_data/                   Sample draft statements and annual reports (Excel and PDF)
tests/                         Unit tests
requirements.txt
```

---

## Installation

Requires Python 3.10 or later.

```powershell
pip install -r requirements.txt
streamlit run app.py
```

The application opens at `http://localhost:8501`.

To enable the optional AI review, enter a Gemini API key in the sidebar under **AI Model Configuration**, or set it before
launching:

```powershell
$env:GEMINI_API_KEY="your-gemini-api-key"
streamlit run app.py
```

---

## Using the application

1. **Sidebar** - select the entity profile (company type, listing status, framework, Schedule III division, financial year).
   The sidebar validates the combination (for example, a listed company cannot report under AS / Division I).
2. **Select review mode** - Option A (draft statements before finalisation) or Option B (published annual report).
3. **Output Required** - choose the Review Points Sheet or the Draft Financial Statements (Yellow Highlights).
4. **Upload** the financial statements (Excel `.xlsx` / `.xlsm`, or a text-based PDF).
5. Review the **entity profile detected from the financial statements** and confirm it.
6. Click **Run FRRB Compliance Review**.
7. Review the observations (filter by nature, search), the **Checks & applicability** tab, and download the Excel output.

### Demonstration with the sample files
- `sample_data/Sample_Draft_FS_Option_A.xlsx` - a Balance Sheet that does not balance (total assets 11,060 vs total equity
  and liabilities 10,810), together with disclosure gaps that apply to the figures presented (trade payables ageing, CWIP
  ageing, promoter shareholding).
- `sample_data/Sample_Compliant_FS_Negative_Test.xlsx` - largely compliant statements; the only point raised is that a cash
  flow statement was not located in the uploaded file (classified as *Requires verification*).

---

## Scope and limitations

- **Excel workbooks** receive the full set of cross-verification checks. **PDF annual reports** are read and reviewed, but
  amounts are less reliably extracted from PDF layouts, so fewer cross-checks can be performed; scanned (image) PDFs are not
  supported.
- The assistant supports, and does not replace, the reviewer's professional judgement. Observations classified as
  *Potential concern* or *Requires verification* call for follow-up rather than a conclusion.
- The Draft Financial Statements output may take several seconds for large workbooks (for example, workbooks with many links
  to other workbooks).

---

## Tests

```powershell
python -m unittest discover tests
```

17 tests covering the profile validation rules, document extraction and scanned-PDF detection, the earlier rule set, and the
Excel outputs.
