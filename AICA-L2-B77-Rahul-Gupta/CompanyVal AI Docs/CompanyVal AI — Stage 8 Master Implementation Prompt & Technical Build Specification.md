# MASTER IMPLEMENTATION PROMPT FOR CLAUDE FABLE

## PROJECT

Build a complete, functional, presentation-ready web application named:

# **CompanyVal AI**
### **AI-Assisted Business Valuation**

Tagline:

**Upload. Understand. Question. Simulate. Value.**

This is an ICAI AICA Level 2 capstone project demonstrating the practical application of:

- Artificial Intelligence
- Multimodal document understanding
- Python financial-data extraction
- Adaptive AI questioning
- Deterministic financial rules
- Business valuation
- Scenario simulation
- Explainable AI
- Professional AI-assisted reporting

The application must be a **real working prototype**, not merely static UI screens.

---

# 1. ABSOLUTE UI REQUIREMENT

I will provide finalized CompanyVal AI UI mockups for:

1. Dashboard
2. New Valuation
3. Financials
4. AI Interview
5. Valuations
6. Simulation Lab
7. AI Insights
8. Reports
9. Settings

## These screenshots are the visual source of truth.

Do **NOT** redesign them.

Do **NOT**:

- change the theme;
- introduce dark blue/navy backgrounds;
- introduce green as the main brand colour;
- change card proportions unnecessarily;
- substitute another design system;
- alter sidebar layout;
- remove the professional dashboard style;
- simplify major screens into generic forms;
- create placeholder pages.

Maintain the finalized professional style:

- white/light background;
- very subtle cool-grey surface;
- professional medium-blue primary accent;
- dark navy typography;
- soft mint/teal for positive indicators;
- pale orange for warnings;
- pale red for risks;
- restrained purple only where appropriate;
- thin borders;
- soft shadows;
- rounded cards;
- generous white space;
- clean financial SaaS appearance.

The UI should feel like a premium professional financial analytics platform rather than a consumer app.

---

# 2. GLOBAL APPLICATION LAYOUT

Maintain this structure throughout the application.

## Left Sidebar

CompanyVal AI logo

Navigation:

- Dashboard
- New Valuation
- Financials
- AI Interview
- Valuations
- Simulation Lab
- AI Insights
- Reports
- Settings

Bottom section:

- User avatar
- User name
- Role
- Valuation Readiness widget
- Copyright

---

## Top Header

Include:

- Page title
- Short contextual subtitle
- Active company selector
- `+ New Valuation`
- Notification icon
- Help icon

---

## Footer Strip

Retain the same visual footer language used in the approved UI:

- AI Powered Intelligence
- Verified Accuracy
- Explainable Valuation
- Scenario Simulation
- Professional Reports

---

# 3. TECHNOLOGY STACK

Use:

## Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui where appropriate
- Lucide React icons
- Recharts for charts
- React Router
- React Hook Form
- Zod validation
- TanStack Query

Do not use excessive external UI libraries that interfere with visual fidelity.

---

## Backend

Use:

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL

Allow SQLite as a simple local-development fallback.

---

## Python Financial & Document Libraries

Use:

- PyMuPDF (`fitz`)
- PyMuPDF4LLM
- pandas
- NumPy
- openpyxl for Excel files
- Pillow where image processing is required

Optional extraction fallback:

- pdfplumber

Use OCR **only when the PDF genuinely contains no usable native text**.

---

# 4. PROJECT ARCHITECTURE

Organise approximately as:

```text
companyval-ai/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── features/
│   │   ├── charts/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   └── styles/
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── document/
│   │   │   ├── financial/
│   │   │   ├── valuation/
│   │   │   ├── interview/
│   │   │   ├── ai/
│   │   │   └── reporting/
│   │   ├── rules/
│   │   ├── prompts/
│   │   ├── templates/
│   │   ├── utils/
│   │   └── main.py
│   │
│   ├── migrations/
│   ├── tests/
│   └── requirements.txt
│
├── storage/
│   ├── uploads/
│   ├── rendered_pages/
│   └── reports/
│
├── .env.example
├── docker-compose.yml
└── README.md
```

Keep components modular.

Do not create one massive frontend component or one massive Python file.

---

# 5. COMPLETE USER FLOW

The principal workflow must be:

```text
Create Valuation
        ↓
Upload Last 3 Years Financial Statements
        ↓
Python Document Extraction
        ↓
Render Relevant PDF Pages
        ↓
Multimodal Gemini Verification
        ↓
Python ↔ AI Reconciliation
        ↓
Accounting Validation
        ↓
Human Review & Approval
        ↓
Lock Historical Financial Data
        ↓
Financial Analysis
        ↓
Rules Engine
        ↓
Adaptive AI Interview
        ↓
Normalisation & Assumption Review
        ↓
Valuation Engine
        ↓
DCF + Market Multiple + Adjusted NAV
        ↓
Simulation Lab
        ↓
AI Insights
        ↓
AI-Assisted Professional Report
```

---

# 6. NEW VALUATION MODULE

Allow creation of a valuation case containing:

- Company Name
- Industry
- Entity Type
- Valuation Date
- Currency
- Units
- Country
- Purpose of Valuation
- Promoter Holding
- Number of Shares
- Optional notes

Valuation-purpose examples:

- Internal Management Assessment
- Fund Raising
- Investment Assessment
- Strategic Planning
- Acquisition Analysis
- Other

Use a guided stepper corresponding to the approved mockup.

---

# 7. FINANCIAL DOCUMENT UPLOAD

Allow:

- PDF
- XLSX
- XLS

Support three financial years.

Example:

```text
FY 2023-24
FY 2024-25
FY 2025-26
```

Also allow a single PDF containing comparative statements.

---

# 8. PDF DOCUMENT INTELLIGENCE PIPELINE

The PDF system is a major part of the project.

Do not simply upload the document to an LLM and trust its answer.

Implement a **dual verification architecture**.

---

## 8.1 Step 1 — File Validation

When a file is uploaded:

- validate MIME type;
- validate extension;
- validate maximum file size;
- assign document UUID;
- calculate SHA-256 hash;
- store original filename;
- store upload timestamp;
- associate with valuation case.

---

## 8.2 Step 2 — Native PDF Inspection

Use PyMuPDF.

Extract:

- page count;
- native text;
- blocks;
- tables where detectable;
- images;
- coordinates where useful.

Determine whether the PDF:

- contains digital text; or
- is substantially scanned.

---

## 8.3 Step 3 — Structured Extraction

Use:

- PyMuPDF;
- PyMuPDF4LLM;
- pandas.

Identify probable:

- Balance Sheet;
- Statement of Profit & Loss;
- Cash Flow Statement;
- Notes to Accounts.

Capture:

- line-item name;
- period;
- amount;
- page;
- source document;
- extraction method.

---

# 9. HIGH-RESOLUTION PAGE VERIFICATION

This requirement is mandatory.

For relevant financial-statement pages:

1. Render PDF pages as high-resolution PNG images using PyMuPDF.
2. Prefer approximately 180–220 DPI for normal verification.
3. Keep the rendered page linked to its original PDF page.
4. Send relevant page images to the multimodal AI together with Python-extracted values.

Do not send every page unnecessarily.

Detect candidate financial pages first.

---

# 10. PYTHON + AI DUAL VERIFICATION

The architecture must be:

```text
                  Original PDF
                      │
             ┌────────┴────────┐
             ▼                 ▼
      Python Extraction    Page Rendering
             │                 │
             │                 ▼
             │          Gemini Vision
             │                 │
             └────────┬────────┘
                      ▼
               Reconciliation
```

Gemini is acting as a **verification layer**, not the sole extractor.

---

# 11. GEMINI VISUAL VERIFICATION SCHEMA

Send:

- page image;
- source page number;
- extracted financial values;
- known period;
- expected JSON schema.

Gemini should return structured data approximately like:

```json
{
  "page": 18,
  "statement_type": "profit_and_loss",
  "items": [
    {
      "metric": "revenue",
      "label_seen": "Revenue from Operations",
      "python_value": 124500000,
      "visual_value": 124500000,
      "status": "verified",
      "confidence": 0.98
    }
  ]
}
```

Possible status:

```text
verified
difference
not_visible
ambiguous
```

Never permit Gemini to fabricate an amount when the value is not visible.

---

# 12. EXTRACTION RECONCILIATION

Compare:

```text
Python Value
vs
Gemini Verified Value
```

Status logic:

### VERIFIED

Exact match or acceptable formatting-equivalent match.

### NEEDS REVIEW

Material mismatch.

### LOW CONFIDENCE

Visual or structural ambiguity.

### MISSING

Required metric was not identified.

Display discrepancies in the Financials UI.

Example:

```text
Other Income

Python       ₹36.20 Lakh
AI Verified  ₹38.20 Lakh

Status: Needs Review
```

Allow user to select/edit the authoritative number.

Store the user's decision in the audit trail.

---

# 13. FINANCIAL DATA MUST BECOME IMMUTABLE AFTER APPROVAL

When review is complete, show:

**Lock Verified Financials**

After locking:

- original extracted numbers remain stored;
- verification values remain stored;
- approved values remain stored;
- AI cannot silently alter historical figures.

Unlocking should require an explicit user action.

---

# 14. CANONICAL FINANCIAL SCHEMA

Normalise different financial-statement labels.

Example:

```text
Sales
Turnover
Revenue
Revenue from Operations
Operating Revenue
```

map internally to:

```text
revenue
```

---

## Profit & Loss

At minimum:

- revenue
- other_income
- material_cost
- employee_cost
- other_operating_expenses
- EBITDA
- depreciation
- EBIT
- finance_cost
- PBT
- tax
- PAT

---

## Balance Sheet

At minimum:

- share_capital
- reserves
- net_worth
- fixed_assets
- investments
- inventory
- receivables
- cash
- other_current_assets
- total_assets
- long_term_borrowings
- short_term_borrowings
- trade_payables
- other_liabilities
- total_liabilities

---

## Cash Flow

At minimum:

- CFO
- CFI
- CFF
- capex
- opening_cash
- closing_cash

---

# 15. INDIAN FINANCIAL NUMBER HANDLING

Correctly support:

- ₹
- INR
- Lakhs
- Crores
- Thousands
- Millions
- Indian comma notation

Examples:

```text
1,25,00,000
₹1.25 Cr
125 Lakhs
```

Normalise internally to absolute numeric INR.

Store:

- original displayed value;
- unit;
- normalised numeric value.

---

# 16. ACCOUNTING VALIDATION ENGINE

Implement deterministic validation.

Examples:

## Balance Sheet

```text
Total Assets ≈ Equity + Liabilities
```

Use sensible rounding tolerance.

---

## Profit

```text
PBT - Tax ≈ PAT
```

---

## Cash Flow

```text
Opening Cash
+ Net Cash Movement
≈ Closing Cash
```

---

## Comparative Values

Compare the previous year's amount appearing in a current-year financial statement against the actual prior-year statement.

Flag meaningful discrepancies.

---

## Sign Validation

Correctly understand:

```text
(1,250)
```

as a negative number where accounting context requires it.

---

# 17. FINANCIAL ANALYTICS ENGINE

All calculations must be done in Python.

Calculate:

- revenue growth;
- revenue CAGR;
- EBITDA growth;
- EBITDA margin;
- EBIT margin;
- PAT margin;
- ROE;
- ROCE;
- current ratio;
- quick ratio where possible;
- debt/equity;
- debt/EBITDA;
- asset turnover;
- receivable days;
- inventory days;
- payable days;
- cash conversion cycle;
- CFO/PAT;
- capex/revenue;
- earnings volatility;
- revenue volatility;
- debt trend;
- working-capital trend.

The AI may explain calculations.

The AI must **not perform the authoritative calculations**.

---

# 18. RULES ENGINE

Create a configurable deterministic rules engine.

Do not scatter rules across frontend components.

Keep them centrally defined.

Example structure:

```python
Rule(
    code="REV_GROWTH_HIGH",
    metric="revenue_growth",
    operator=">",
    threshold=0.25,
    severity="high",
    action="investigate_growth_sustainability"
)
```

---

# 19. INITIAL CAPSTONE RULE SET

These are product rules, not statutory valuation standards.

### Revenue

```text
IF YoY Revenue Growth > 25%
THEN investigate growth sustainability
```

```text
IF Revenue Decline > 10%
THEN investigate decline and recovery
```

---

### EBITDA

```text
IF EBITDA Margin changes > 3 percentage points
THEN investigate margin movement
```

---

### Cash Conversion

```text
IF CFO / PAT < 0.70
THEN investigate earnings-to-cash conversion
```

---

### Debt

```text
IF Debt / Equity > 1.50
THEN investigate leverage/refinancing
```

---

### Receivables

```text
IF Receivable Days increase > 20%
THEN investigate collections
```

---

### Exceptional Items

```text
IF Non-Recurring Item > 10% of EBITDA
THEN investigate normalisation
```

---

### Customer Concentration

```text
IF Largest Customer Revenue > 25%
THEN flag concentration risk
```

---

# 20. AI INTERVIEW ENGINE

This is not a generic chatbot.

Use:

```text
Verified Financial Data
+
Calculated Ratios
+
Triggered Rules
+
Previous User Answers
+
Missing Valuation Inputs
        ↓
Question Planner
        ↓
Next Best Question
```

---

# 21. QUESTION PRIORITISATION

Use a deterministic priority concept such as:

```text
Materiality
×
Valuation Impact
×
Uncertainty
=
Question Priority
```

Priority levels:

- Critical
- High
- Medium
- Low

The interview should not ask unnecessary questions.

Target approximately:

**8–15 substantive questions for a normal capstone case**, while allowing more where genuinely necessary.

---

# 22. QUESTION CATEGORIES

Support:

- Business Overview
- Growth & Revenue
- Profitability
- Customers
- Operations
- Working Capital
- Capital Structure
- Management
- Competition
- Industry
- Capex
- Business Risks
- Litigation
- Related Parties
- Forecast & Outlook
- Normalisation

---

# 23. QUESTION TYPES

Support:

- yes/no;
- single choice;
- multiple choice;
- text;
- currency;
- numeric;
- percentage;
- slider/range.

---

# 24. ADAPTIVE FOLLOW-UP EXAMPLE

If:

```text
Revenue Growth = 44%
```

ask:

> What principally contributed to the substantial increase in revenue during FY 2025-26?

Possible answers:

- New customers
- Price increase
- New geography
- New product/service
- One-time order
- Acquisition
- Other

If user selects:

**One-time order**

ask:

> Approximately what amount of FY 2025-26 revenue arose from this one-time order?

Then ask:

> Do you expect similar orders to recur regularly?

The answer may create a proposed normalisation adjustment.

---

# 25. AI QUESTION JSON

Require structured output.

Example:

```json
{
  "question_id": "GROWTH_004",
  "category": "growth",
  "priority": "high",
  "reason": "Revenue growth materially exceeds historical trend.",
  "trigger_rule": "REV_GROWTH_HIGH",
  "question": "What principally contributed to FY 2025-26 revenue growth?",
  "type": "single_choice",
  "options": [
    "New customers",
    "Price increase",
    "New geography",
    "New product",
    "One-time order",
    "Acquisition",
    "Other"
  ],
  "valuation_impact": [
    "revenue_forecast",
    "growth_sustainability"
  ]
}
```

Do not parse arbitrary prose when structured output can be used.

---

# 26. HUMAN-IN-THE-LOOP ASSUMPTIONS

AI can:

- identify issues;
- explain data;
- recommend an assumption;
- suggest normalisation.

AI cannot silently change anything.

Example UI:

```text
Revenue Growth Assumption

Current             18%
AI Recommendation   13%

Reason:
Recent growth included a non-recurring order.

[Keep 18%]
[Accept 13%]
[Enter Another Value]
```

Only an explicitly accepted value becomes authoritative.

---

# 27. AI INTERVIEW STOP CONDITION

Interview may finish when:

```text
No unresolved critical/high-priority questions
AND
Essential valuation assumptions are available
AND
Material normalisation items are addressed
AND
Material risks are covered
```

Display:

```text
AI Interview Complete
Valuation Readiness: 94%
Proceed to Valuation
```

---

# 28. VALUATION READINESS SCORE

Use an explainable score.

Recommended structure:

```text
Financial Data Completeness     25%
Financial Verification          20%
Forecast Inputs                 20%
Business Interview              20%
Risk Information                15%
                              ─────
                               100%
```

This is a **readiness/completeness score**.

Do not label it as “AI accuracy”.

---

# 29. NORMALISATION ENGINE

Allow explicit adjustments such as:

- one-time revenue;
- exceptional expenses;
- non-recurring income;
- promoter remuneration adjustment;
- unusual legal expenses;
- extraordinary losses;
- abnormal related-party amounts.

Keep:

```text
Reported
Adjustment
Normalised
Reason
Source
Approved By User
```

---

# 30. VALUATION ENGINE — PRINCIPLE

All authoritative valuation numbers are calculated in Python.

Never ask Gemini:

> “What is this company worth?”

Instead Gemini receives the engine results and explains them.

---

# 31. DCF VALUATION

Implement a 5-year FCFF model.

For each projected year calculate approximately:

```text
Revenue
↓
EBITDA
↓
Depreciation
↓
EBIT
↓
Tax
↓
NOPAT
+
Depreciation
-
Capex
-
Increase in Net Working Capital
=
FCFF
```

---

# 32. DCF FORMULAE

Core:

```text
NOPAT = EBIT × (1 - Tax Rate)
```

```text
FCFF =
NOPAT
+ Depreciation
- Capex
- Change in NWC
```

Present value:

```text
PV(FCFFt) = FCFFt / (1 + WACC)^t
```

Terminal value:

```text
TV =
FCFF(n+1)
────────────
WACC - g
```

Enterprise value:

```text
EV =
Σ PV(FCFF)
+
PV(Terminal Value)
```

Equity value:

```text
Equity Value =
Enterprise Value
- Debt
+ Cash & Cash Equivalents
```

Per-share value:

```text
Equity Value / Diluted Shares
```

---

# 33. WACC

Allow WACC to be:

- manually entered;
- generated from individual assumptions where sufficient information exists.

If components are available:

```text
WACC =
E/(D+E) × Ke
+
D/(D+E) × Kd × (1-T)
```

Do not invent:

- beta;
- risk-free rate;
- equity-risk premium;
- borrowing cost.

If unavailable, require explicit assumptions.

---

# 34. MARKET MULTIPLE VALUATION

Support:

- EV/EBITDA
- P/E
- EV/Revenue

Multiples can originate only from:

- administrator-configured demo industry data;
- user-entered values;
- an explicitly connected benchmark data source in future.

Gemini must never invent comparable-company multiples.

Example:

```text
Enterprise Value =
Normalised EBITDA × EV/EBITDA Multiple
```

Then adjust debt/cash to obtain equity value.

---

# 35. ADJUSTED NAV

Allow adjustments to:

- land;
- building;
- plant;
- investments;
- inventory;
- receivables;
- intangible assets;
- contingent liabilities;
- other assets/liabilities.

Calculate:

```text
Adjusted Asset Value
-
Outside Liabilities
=
Adjusted Net Asset Value
```

Maintain an adjustment schedule.

---

# 36. CENTRAL ESTIMATE

Avoid unexplained AI weighting.

Default deterministic methodology weights:

```text
DCF                50%
Market Multiple    30%
Adjusted NAV       20%
```

Allow administrator/user adjustment.

Validate that:

```text
Total Weight = 100%
```

Calculate:

```text
Central Estimate =
Σ(Method Value × Method Weight)
```

Clearly show the weighting.

If only one method is selected, its value becomes the central estimate.

---

# 37. INDICATIVE VALUATION RANGE

For the core capstone implementation:

```text
Lower Bound =
Lowest selected methodology value

Upper Bound =
Highest selected methodology value
```

Keep scenario ranges separately identified.

Do not hide the methodology used to calculate the range.

---

# 38. VALUATION SCREEN

Match the approved mockup.

Include:

- Indicative Valuation Range
- Central Estimate
- Valuation Confidence
- Last Updated
- Valuation Readiness

Method cards:

- DCF
- Market Multiple
- Adjusted NAV

Also include:

- Method Comparison
- Sensitivity Analysis
- Risk Highlights
- Recent Valuation Runs
- Key Assumptions

Every major number should have:

**View Details**

or equivalent drill-down.

---

# 39. VALUATION CONFIDENCE

Keep it distinct from Valuation Readiness.

Valuation Confidence may consider:

- method agreement;
- data verification;
- forecast completeness;
- sensitivity;
- normalisation completeness.

Do not claim statistical accuracy.

Use terminology such as:

```text
High Confidence
Moderate Confidence
Low Confidence
```

and explain the basis.

---

# 40. SIMULATION LAB

This is a major wow-factor module.

Match the approved UI.

Provide live controls for:

- Revenue Growth
- EBITDA Margin
- WACC
- Terminal Growth Rate
- EV/EBITDA Multiple
- Capex where appropriate
- Working-Capital assumption where appropriate

When sliders move:

- calculate immediately;
- display changed company value;
- display absolute impact;
- display percentage impact.

Do not call Gemini every time a slider moves.

This must be local/backend deterministic calculation.

---

# 41. SCENARIOS

Support:

### Bear Case

More conservative assumptions.

### Base Case

Accepted valuation assumptions.

### Bull Case

More optimistic assumptions.

Display:

```text
Bear
Base
Bull
```

with valuation comparison.

Allow saved named scenarios.

---

# 42. SENSITIVITY ANALYSIS

Include:

- WACC vs Terminal Growth heat map;
- Tornado chart;
- assumption impact table.

For example:

```text
+2% Revenue Growth
→ +₹0.28 Cr

+2% EBITDA Margin
→ +₹0.22 Cr

-1% WACC
→ +₹0.17 Cr
```

Values must come from actual recalculation.

---

# 43. EXPLAINABILITY ENGINE

Provide:

**Why this valuation?**

Include major:

### Positive Drivers

- Revenue Growth
- EBITDA Margin
- Cash Generation
- Low Leverage
- Recurring Revenue

### Negative Drivers

- Concentration
- Working Capital
- Promoter Dependency
- Margin Volatility
- Regulatory Risk

Also identify:

**Most Sensitive Assumption**

and quantify its impact.

---

# 44. AI INSIGHTS MODULE

Match the approved screen.

Sections:

- Overall Business Quality
- AI-Generated Key Insights
- Positive Drivers
- Risk Flags
- Earnings Quality
- Business Strengths
- Assumption Review
- Explainability Highlights
- Recommended Next Actions

AI-generated insights must always be based on stored data.

Do not generate generic filler.

---

# 45. AI PROVIDER

Default provider:

```text
Google Gemini
```

Default model:

```text
Gemini 3.6 Flash
```

Create a provider adapter architecture so the model can be changed later without changing the financial engine.

Example:

```python
class AIProvider:
    verify_document(...)
    generate_question(...)
    interpret_answer(...)
    generate_report(...)
```

---

# 46. DIFFERENT AI TASKS

Separate prompts/services for:

1. Document Verification
2. Question Generation
3. Answer Interpretation
4. Risk/Insight Explanation
5. Final Report Generation

Do not use one giant universal prompt.

---

# 47. API KEY SECURITY — CRITICAL

The browser must never call Gemini directly.

Correct architecture:

```text
React PWA
    ↓
FastAPI
    ↓
Gemini
```

Never:

```text
React
    ↓
Gemini API
```

---

# 48. API KEY STORAGE

In Settings:

User enters API key.

Backend:

1. validates key;
2. tests connection;
3. encrypts key;
4. stores encrypted value;
5. never returns original key again.

Frontend thereafter displays:

```text
Gemini API Key

••••••••••••••••••••

Connected
```

Buttons:

- Test Connection
- Replace Key

Do not include:

**Show API Key**

after it has been saved.

---

# 49. ENCRYPTION

Use a server-side encryption key loaded from environment variables.

For example:

```text
COMPANYVAL_MASTER_KEY=
```

Use a well-supported encryption library such as Python `cryptography`.

Do not:

- commit API keys;
- commit encryption keys;
- include secrets in JavaScript;
- put secrets in localStorage;
- write keys to logs.

---

# 50. SETTINGS SCREEN

Maintain approved layout.

Sections:

### AI Configuration

- Provider
- Model
- API Key status
- Temperature
- Structured Output
- Visual Verification
- AI Final Report

For extraction/verification, use a low-variance configuration.

---

### Report Generation

- Language
- Default template
- Currency presentation
- Include charts
- Include source references

---

### Profile

- Name
- Role
- Email
- Time zone
- Date format
- Number format

---

### Preferences

- Default valuation methodology
- Default WACC/discount assumptions
- Auto-save

Do not include unnecessary enterprise settings in the capstone.

---

# 51. FINAL AI REPORT GENERATION

AI receives only structured authoritative data.

Input should include:

```text
Company Profile
+
Verified Historical Financials
+
Ratios
+
Normalisation Adjustments
+
Interview Answers
+
Accepted Forecast Assumptions
+
Key Risks
+
DCF Results
+
Market Multiple Results
+
NAV Results
+
Scenario Results
+
Sensitivity Results
```

---

# 52. CRITICAL REPORT SYSTEM RULE

The final-report AI prompt must contain:

> All numerical financial and valuation results supplied to you are authoritative outputs from CompanyVal AI's deterministic financial engine. You may explain, contextualise and compare them, but you must not alter, recalculate, fabricate or substitute any financial or valuation value.

---

# 53. FINAL REPORT SECTIONS

Generate:

1. Cover
2. Executive Summary
3. Company Profile
4. Documents Analysed
5. Historical Financial Performance
6. Financial Ratio Analysis
7. Earnings Quality
8. Normalisation Adjustments
9. Business Assessment
10. AI Interview Findings
11. Key Risks
12. Valuation Assumptions
13. DCF Valuation
14. Market Multiple Valuation
15. Adjusted NAV
16. Method Comparison
17. Sensitivity Analysis
18. Scenario Analysis
19. Explainability / Key Value Drivers
20. Indicative Valuation Range
21. Conclusion
22. Assumptions
23. Disclaimer
24. Appendices / Data Sources

---

# 54. REPORT GENERATION ENGINE

Create professional HTML/CSS report templates.

PDF export should:

- preserve charts;
- preserve page breaks;
- include page numbers;
- include CompanyVal AI branding;
- include valuation date;
- include confidentiality footer;
- include assumptions and disclaimer.

Use a reliable HTML-to-PDF workflow.

Keep report-generation code isolated so another PDF renderer can be substituted later.

---

# 55. REPORT DISCLAIMER

Include clear wording that the system produces an:

**AI-assisted indicative valuation simulation based on supplied financial information and user assumptions.**

Do not present the output as:

- a statutory valuation;
- registered valuer certificate;
- fairness opinion;
- audit opinion.

State that professional judgement and applicable regulatory requirements may be necessary for formal purposes.

---

# 56. DATABASE — CORE TABLES

Implement at least:

```text
users
companies
valuation_cases
documents
document_pages
financial_periods
financial_line_items
extraction_results
verification_results
normalisation_adjustments
ratios
rules
rule_triggers
interview_sessions
interview_questions
interview_answers
valuation_assumptions
valuation_runs
valuation_method_results
scenario_runs
ai_insights
reports
ai_call_logs
app_settings
audit_logs
```

Use relational integrity.

---

# 57. FINANCIAL LINE ITEM AUDITABILITY

A financial amount should be traceable.

Store approximately:

```json
{
  "metric": "revenue",
  "period": "FY2025-26",
  "approved_value": 124500000,
  "unit": "INR",
  "source_document_id": "...",
  "source_page": 18,
  "python_value": 124500000,
  "ai_visual_value": 124500000,
  "verification_status": "verified",
  "confidence": 0.98
}
```

Where practical also retain:

- original label;
- original displayed amount;
- bounding-box/source context.

---

# 58. AUDIT LOG

Track important actions:

- upload;
- extraction;
- verification;
- manual correction;
- financial lock/unlock;
- assumption accepted/rejected;
- valuation run;
- scenario run;
- report generated;
- API setting changed.

Do not log sensitive API keys.

---

# 59. BACKEND API STRUCTURE

Provide REST endpoints broadly such as:

```text
/api/auth/
/api/companies/
/api/valuations/
/api/documents/
/api/financials/
/api/interview/
/api/assumptions/
/api/valuation-engine/
/api/scenarios/
/api/insights/
/api/reports/
/api/settings/
```

Include automatic FastAPI OpenAPI documentation.

---

# 60. IMPORTANT API OPERATIONS

Examples:

```text
POST /api/valuations
GET  /api/valuations/{id}

POST /api/valuations/{id}/documents
POST /api/documents/{id}/process

GET  /api/valuations/{id}/financials
POST /api/valuations/{id}/financials/approve
POST /api/valuations/{id}/financials/lock

POST /api/valuations/{id}/interview/start
GET  /api/valuations/{id}/interview/next
POST /api/valuations/{id}/interview/answer

GET  /api/valuations/{id}/assumptions
PUT  /api/valuations/{id}/assumptions

POST /api/valuations/{id}/calculate
POST /api/valuations/{id}/simulate

GET  /api/valuations/{id}/insights

POST /api/valuations/{id}/reports
GET  /api/reports/{id}/download

POST /api/settings/ai/test
PUT  /api/settings/ai
```

Use appropriate REST semantics.

---

# 61. PROCESSING STATUS

Document processing can take time.

Implement statuses:

```text
uploaded
reading
extracting
rendering
ai_verifying
reconciling
awaiting_review
verified
locked
failed
```

Frontend must display real progress.

Do not fake completion immediately.

---

# 62. ERROR HANDLING

Provide useful errors for:

- encrypted PDF;
- corrupt PDF;
- unsupported spreadsheet;
- no financial statements detected;
- missing year;
- AI connection failure;
- Gemini rate limit;
- malformed AI response;
- extraction mismatch;
- calculation failure.

The application should not crash.

---

# 63. AI FAILURE MUST NOT BREAK THE CORE APP

If Gemini is unavailable:

- preserve uploaded files;
- preserve Python extraction;
- allow manual review;
- display clear AI verification error;
- allow retry.

The deterministic valuation engine should remain independent.

---

# 64. SECURITY

Implement:

- server-side validation;
- safe file names;
- random internal storage names;
- MIME validation;
- upload-size limit;
- SQL injection protection through ORM;
- no secrets in frontend;
- CORS configuration;
- environment-based secrets;
- password hashing if login is included;
- access control by valuation case where relevant.

For a capstone, keep authentication simple but secure.

---

# 65. NO HARDCODED DEMO NUMBERS IN LIVE CALCULATIONS

It is acceptable to provide seed/demo data.

However:

- dashboard results;
- valuation results;
- ratios;
- charts;
- readiness;
- insights;

must update from backend data when a valuation case is processed.

Do not hardcode UI screenshots' example values as application logic.

The screenshots demonstrate **design**, not authoritative financial results.

---

# 66. DEMO MODE

Include a seed demo case:

```text
ABC Food Pvt. Ltd.
```

with realistic three-year illustrative financial data.

The demo case should support the full journey:

```text
Upload / Seed
→ Verify
→ Interview
→ Calculate
→ Simulate
→ Report
```

Clearly treat demo figures as illustrative.

---

# 67. FRONTEND STATE

Persist:

- selected company;
- active valuation case;
- interview progress;
- approved financials;
- assumptions;
- scenario values;
- last valuation run.

Reloading the page should not reset the valuation.

---

# 68. RESPONSIVE DESIGN

Primary target:

**Laptop/Desktop presentation**

The exact desktop UI is most important.

Also support:

- tablet;
- usable mobile fallback.

Do not compromise desktop fidelity in an attempt to make the desktop layout behave like mobile.

---

# 69. ACCESSIBILITY

Use:

- keyboard-accessible controls;
- accessible form labels;
- logical heading hierarchy;
- readable contrast;
- tooltips where financial terminology needs explanation.

---

# 70. CHARTS

Use professional financial charts.

Possible Recharts components:

- LineChart
- BarChart
- AreaChart
- Pie/Donut
- Radar where justified

Sensitivity heat map can be implemented with a styled grid if more suitable.

Avoid excessive decorative charts.

---

# 71. WOW FACTOR

The wow factor should come from intelligence and usability rather than animation gimmicks.

Implement:

### Financial Extraction Journey

Real-time states showing:

```text
Reading Document
Detecting Statements
Extracting Tables
Visual Verification
Validating Totals
```

### Dual Verification

Show:

```text
Python Extracted
AI Verified
Status
Confidence
Source Page
```

### Why Am I Asking This?

Every material AI question explains its trigger.

### Live Simulation

Sliders immediately recalculate value.

### Why This Valuation?

Explain key value drivers.

### Source Traceability

Click a financial amount and show its source document/page where possible.

These should be signature capabilities.

---

# 72. DO NOT OVERUSE AI

Gemini should be used where semantic intelligence genuinely adds value:

- document visual validation;
- natural-language financial interpretation;
- adaptive question drafting;
- answer classification;
- qualitative insight generation;
- professional narrative generation.

Use Python for:

- extraction pipeline;
- calculations;
- ratios;
- thresholds;
- rules;
- weighting;
- valuation;
- sensitivity;
- scenarios.

---

# 73. TESTING

Create meaningful tests.

## Financial Tests

Test:

- CAGR;
- EBITDA margin;
- FCFF;
- discounting;
- terminal value;
- enterprise-to-equity bridge;
- market multiple valuation;
- NAV;
- weighted central estimate.

---

## Extraction Tests

Test:

- Indian commas;
- parentheses;
- lakh/crore conversions;
- multiple year columns;
- blank cells;
- negative values.

---

## Rules Tests

Ensure relevant rules trigger correctly.

---

## API Tests

Test key endpoints.

---

# 74. ACCEPTANCE TEST — DOCUMENT PIPELINE

Given three valid financial-statement PDFs:

The system must:

1. upload successfully;
2. detect statements;
3. extract financial data;
4. render relevant pages;
5. call AI visual verification;
6. reconcile results;
7. identify discrepancies;
8. permit user review;
9. lock approved numbers.

---

# 75. ACCEPTANCE TEST — INTERVIEW

Given a company with 44% revenue growth:

The rules engine should trigger growth investigation.

AI should:

1. formulate a contextual question;
2. explain why it is asking;
3. accept structured answer;
4. interpret answer;
5. generate follow-up where material;
6. update interview progress.

---

# 76. ACCEPTANCE TEST — VALUATION

With approved assumptions:

System must calculate:

- DCF;
- Market Multiple;
- Adjusted NAV;
- central estimate;
- indicative range;
- equity value;
- per-share value where shares exist.

All values must be reproducible from stored inputs.

---

# 77. ACCEPTANCE TEST — SIMULATION

Changing WACC must:

1. recalculate DCF;
2. update company value;
3. update impact amount;
4. update impact percentage;
5. update charts;
6. not require a Gemini call.

---

# 78. ACCEPTANCE TEST — REPORT

The generated report must:

- use actual case data;
- use authoritative valuation-engine results;
- include AI narrative;
- include charts;
- include methodology;
- include assumptions;
- include risks;
- include disclaimer;
- export to PDF.

---

# 79. CODE QUALITY REQUIREMENTS

Use:

- type hints;
- docstrings where useful;
- service layers;
- reusable React components;
- reusable Pydantic models;
- clean separation of concerns;
- central theme variables;
- central financial formulas;
- central rules;
- central AI prompts.

Avoid:

- duplicate logic;
- magic numbers;
- giant files;
- inline secrets;
- hardcoded paths.

---

# 80. CONFIGURATION

Create `.env.example`.

Include only placeholders such as:

```text
DATABASE_URL=
SECRET_KEY=
COMPANYVAL_MASTER_KEY=
UPLOAD_DIR=
REPORT_DIR=
FRONTEND_URL=
```

Do not put the Gemini API key in `.env.example` as a real key.

The actual provider key may be saved through the application Settings UI.

---

# 81. README

Provide a complete README covering:

1. Prerequisites
2. Backend installation
3. Frontend installation
4. Database setup
5. Alembic migration
6. Environment configuration
7. Running backend
8. Running frontend
9. Gemini configuration
10. Sample/demo case
11. PDF dependencies
12. Testing
13. Production-build commands

The project should be runnable by someone other than the original developer.

---

# 82. DEVELOPMENT PRIORITY

Build in this order:

## Phase 1

Project setup and UI shell.

## Phase 2

Database and valuation-case CRUD.

## Phase 3

Document upload and Python extraction.

## Phase 4

Financial reconciliation and review.

## Phase 5

Gemini visual verification.

## Phase 6

Financial analytics and rules.

## Phase 7

Adaptive AI Interview.

## Phase 8

Valuation engine.

## Phase 9

Simulation Lab.

## Phase 10

AI Insights.

## Phase 11

Professional reporting.

## Phase 12

Testing, polishing and demo seed.

Do not try to implement everything in one enormous file or one uncontrolled coding step.

---

# 83. IMPLEMENTATION BEHAVIOUR FOR CLAUDE

Before writing code:

1. inspect all attached CompanyVal AI mockups carefully;
2. derive a reusable design system;
3. map every screen to components;
4. map backend entities;
5. map routes and workflows;
6. create the project structure.

Then implement module-by-module.

If visual details conflict with assumptions in this prompt:

**the attached finalized UI screenshots control visual appearance, while this specification controls functionality and architecture.**

If a screenshot contains an obvious demo-data inconsistency, correct the data logic without unnecessarily changing the visual design.

---

# 84. IMPORTANT CORRECTION TO SETTINGS MOCKUP

If any earlier Settings visual displays another model/provider, ignore that particular model text.

Actual implementation:

```text
Provider: Google Gemini
Default Model: Gemini 3.6 Flash
```

API provider/model should remain configurable.

After the API key has been configured, never reveal the original key.

---

# 85. FINAL PRODUCT PRINCIPLES

CompanyVal AI must demonstrate:

### 1. Verified Data

Financials are extracted and independently checked.

### 2. Explainable Intelligence

Users know why AI is asking a question.

### 3. Human Control

AI recommendations require explicit acceptance.

### 4. Deterministic Valuation

Financial mathematics is performed by Python.

### 5. AI-Assisted Interpretation

AI explains rather than invents the valuation.

### 6. Scenario Intelligence

Users can understand which assumptions drive value.

### 7. Auditability

Every important financial number can be traced.

---

# 86. FINAL DEFINITION OF DONE

CompanyVal AI is complete only when a user can genuinely perform this workflow:

> Create a company valuation case → upload three years of financial statements → allow Python to extract financial information → visually verify the data through Gemini → review discrepancies → lock the historical financials → answer adaptive AI questions → approve assumptions → generate DCF, market-multiple and adjusted-NAV valuations → simulate alternative scenarios → view AI insights and explainability → generate and download a professional AI-assisted valuation report.

A visually beautiful collection of static screens alone is **not sufficient**.

The financial engine, document engine, AI orchestration, user workflow and report generation must function end-to-end.

---

# 87. FINAL DEVELOPMENT COMMAND

Build **CompanyVal AI — AI-Assisted Business Valuation** as a complete, modular, production-quality capstone prototype following this specification and the attached finalized UI references.

Prioritise:

**correct financial logic → data integrity → explainability → working AI integration → visual fidelity → polish.**

Do not introduce unnecessary complexity that prevents completion of the capstone.

The final implementation should be sufficiently reliable and visually impressive for a live ICAI AICA Level 2 project demonstration.