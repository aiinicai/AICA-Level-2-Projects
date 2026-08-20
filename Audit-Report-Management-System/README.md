# Audit Report Generator – Stage 5
## Entity Classification & Applicability Engine

Stage 5 builds on the working Stage 4 application and adds a professional-review
classification/applicability layer.

### Main capabilities

- Entity form classification for corporate and non-corporate entities.
- Corporate SMC screening under Companies (Accounting Standards) Rules, 2021.
- Companies Act "Small Company" screening under section 2(85), with effective-date
  driven thresholds.
- CARO 2020 applicability screening.
- Section 143(3)(i) IFC reporting screening for private companies.
- Cash-flow / AS 3 screening.
- Current ICAI non-company AS classification: MSME vs Large, effective for periods
  beginning on/after 1 April 2024.
- Legacy ICAI Level I/II/III/IV calculation retained for historical-report
  reference; it is NOT treated as the current 2024+ classification.
- Initial AS applicability/relaxation flags for AS 3, AS 17, AS 18, AS 19, AS 22,
  AS 24, AS 28 and AS 29 for current non-company MSME analysis.
- Professional override for classification.
- Professional final conclusion override for every applicability item.
- Rationale/notes for overrides.
- Optional, explicit application of final Small Company conclusion back to the
  Engagement Master. It is NOT automatic.
- Persistence in Excel:
  - CLASSIFICATION_RESULTS
  - APPLICABILITY_RESULTS

### Important design principle

The system is a decision-support and drafting aid, not an autonomous legal conclusion
engine. System results are recommendations. The CA must review and can override
each result.

### Current-rule notes

1. ICAI revised non-company classification from the former four levels to two
   categories (MSMEs and Large entities) for accounting periods commencing on or
   after 1 April 2024. The earlier Level I-IV terminology is retained in Stage 5
   only for historical/reference purposes.
2. The Companies Act small-company threshold is effective-date driven. For dates
   from 1 December 2025 onward, the prescribed limits are ₹10 crore paid-up capital
   and ₹100 crore turnover, subject to the other statutory exclusions. Earlier
   periods use the then-prevailing limits.
3. CARO 2020 and section 143(3)(i) have separate thresholds and exclusions. The
   application does not infer them from "Small Company" status alone.

### Installation

1. Extract the ZIP to a new folder.
2. Delete `.venv` if present.
3. Run `run_windows.bat`.
4. Open `http://127.0.0.1:5000`.

No lxml/python-docx/PDF dependency is introduced.

### Stage 5 workflow

Engagements → Classify / Applicability

1. Enter/review entity and financial facts.
2. Review system classification.
3. Review system applicability.
4. Override where professional judgement requires.
5. Record rationale.
6. Save.
7. Optionally tick "Apply final Small Company conclusion to Engagement Master".

### Stage 5 intentionally does not yet

- Generate a full CARO clause-by-clause checklist.
- Generate 143(3) clause-by-clause checklist.
- Generate Schedule III checklist.
- Generate complete AS compliance checklist.
- Automatically rewrite audit report wording.
- Automatically change the approved Word master template.

Those functions are planned for subsequent stages.


## Stage 5 Fix v2 – Optional Client/Engagement and CA Overrides

- Existing Client is optional. If selected, it supplies defaults only.
- Existing Engagement is optional. If selected, it supplies defaults only.
- Values changed by the CA on the New Audit Report screen are authoritative and are not overwritten during review/generation.
- ClientID and EngagementID are carried into the Review/Generate request for traceability.
- A report can be generated without selecting either Existing Client or Existing Engagement, provided all mandatory current-report fields are completed.
