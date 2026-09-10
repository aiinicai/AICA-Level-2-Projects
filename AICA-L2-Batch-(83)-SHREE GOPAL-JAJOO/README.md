# LC Analyser

An enterprise-grade desktop tool (Tkinter GUI with a modern blue theme) that takes a text-based PDF copy of a Letter of Credit / Documentary Credit, validates the LC, and produces an offline clause-by-clause summary and compliance analysis you can review, edit, save to an integrated SQLite database, and export to Word or PDF.

The analysis is produced entirely **offline by a rule-based engine** built around SWIFT MT700 field tags and UCP 600 checklist logic - no AI/API calls and no internet access required.

---

## Key Features

1. **Modern Blue Theme UI**:
   - Deep Navy, Midnight Blue, and Royal Blue tones with clear visual hierarchy.
   - Live KPI status dashboard showing point counts across verdicts (*In Order*, *Requires Amendment*, *Needs Clarification*, *Informational*).
   - Dual-tab navigation: **📄 LC Analysis & Workspace** and **🗄️ Saved Analysis & Database Search**.
   - Adjustable clause & document viewer with instant clipboard copy.

2. **Integrated SQLite Database Persistence (`database.py`)**:
   - Stores complete LC metadata, original document text, clause points, rule notes, user verdicts, and remarks.
   - Auto-saves new analyses and enables manual syncing/updating.
   - Zero-configuration portable database (`lc_database.db`).

3. **Multi-Criteria Search & Historical Retrieval**:
   - Search past analyses by:
     - **LC Number (Documentary Credit Number)**
     - **Issuer Bank / Issuer Name**
     - **LC Amount / Currency**
     - **Beneficiary Name**
     - **General Search Term**
   - 1-click **Load into Workspace** to continue reviewing, updating verdicts, or generating documents from saved work.
   - Quick export of Finalized Word summaries and Amendment Request letters directly from history.

4. **100% Preserved Core Logic & Verification Output**:
   - Zero change to parsing, rules engine evaluations, or exported Word/PDF formatting.

---

## 1. Setup (one-time)

1. Make sure Python 3.9+ is installed (Tkinter and SQLite ship with standard python.org distributions).
2. Open a command prompt in this folder and install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

## 2. Running the App

```bash
python main.py
```

### Running Self-Checks & Tests

- **Core Rule Engine Test**: `python smoke_test.py`
- **Database CRUD & Search Test**: `python test_database.py`
- **Full GUI & DB Integration Test**: `python test_gui_and_database.py`

---

## 3. How to Use It

### Workspace Tab (`📄 LC Analysis & Workspace`)
1. **Select LC Copy (PDF)**: Choose a text-based PDF.
2. **Select LC Type**: **Draft LC** or **Issued / Transmitted LC**.
3. **Click "Run Analysis"**: The pipeline validates the LC, extracts fields, applies UCP 600 rules, renders all clause rows, and auto-saves the analysis to the database.
4. **Review the Sections**:
   - **Main Summary**: Credit number, parties, amount, availability, dates, shipment conditions, and date cross-checks.
   - **Goods / Services Covered**: Description of goods.
   - **Documents Required**: 8 sub-categories (LR/BL, COO, Invoice & Packing List, Bill of Exchange, Certifications & Inspections, Insurance, Intimation/Communication, Other).
   - **Charges & Other Conditions**: Bank charges, reimbursement, confirmation.
5. **Interactive Review**:
   - Select verdicts with radio buttons (*Correct / In Order*, *Requires Amendment*, *Needs Clarification*, *Informational*). Live KPI cards update instantly.
   - Add custom notes in "Your Remarks".
   - Click **👁 View** to read the exact verbatim text in the right-hand viewer.
6. **Save to Database**: Click **💾 Save to Database** at any time to commit your updated verdicts and remarks.
7. **Download & Finalize**:
   - **⬇ Download Analysis**: Export complete section-wise analysis to Word (.docx) or PDF.
   - **📋 Finalized Summary (Word)**: Export summary grouped into three verdict tables for formal sign-off.
   - **✉ Amendment Letter (Word)**: Generates a formal amendment request letter to the Applicant for points marked *Requires Amendment*, including typed remarks and auto-filled party details.

### Database Tab (`🗄️ Saved Analysis & Database Search`)
1. Filter saved records by **LC Number**, **Applicant Bank**, **LC Amount**, **Beneficiary Name**, or general keyword.
2. Select any record to:
   - **📂 Load into Workspace**: Open all clauses, remarks, and document text back in the analysis tabs.
   - **📋 Export Final Summary**: Export Word summary without re-running analysis.
   - **✉ Export Amendment Letter**: Generate amendment letter directly from saved state.
   - **🗑️ Delete Record**: Remove old records with confirmation.

---

## 4. Project Files

| File                       | Purpose                                                                 |
|----------------------------|--------------------------------------------------------------------------|
| `main.py`                  | Modern Blue GUI entry point (`python main.py`)                          |
| `database.py`              | SQLite database persistence, metadata extraction, search & retrieval   |
| `models.py`                | Data structures (`ClausePoint`, `AnalysisResult`, etc.)                 |
| `pdf_extract.py`           | Text-based PDF extraction (`pypdf`)                                     |
| `lc_parser.py`             | LC gating checks & SWIFT tag tokenizer                                  |
| `rules_engine.py`          | Offline rule-based analysis engine (UCP 600 checklist logic)             |
| `exporter.py`              | Word (`python-docx`) and PDF (`reportlab`) exporters                     |
| `smoke_test.py`            | Core rule-engine self-check                                              |
| `test_database.py`         | Database unit tests                                                      |
| `test_gui_and_database.py` | Full GUI and database integration test suite                             |
