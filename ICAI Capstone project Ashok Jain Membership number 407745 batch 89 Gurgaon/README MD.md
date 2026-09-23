**ICAI AI LEVEL 2  |  CAPSTONE PROJECT**

# **Vendor Financial Health \& Credit Assessment**

User Manual

|**Submitted by**|CA Ashok Jain Membreship no  407745 ,<br>email --jain.ashokmba@gmail.com|
|-|-|
|**Programme**|ICAI AI Level 2 Certification|
|**Branch**|Gurugram|
|**Batch**|89|
|**Built with**|Lovable (AI application builder)|
|**Version**|1.0|



#### **Application access**

**Link:** <u>https://vendorfni</u> -eval.lovable.app/dashboard **User ID:** AI@ICAI.Org **Password:** 123456

## Sample financials also there in the folder

Video Link and application access both <u>https://vendorfni</u> -eval.lovable.app User ID AI@ICAI.Org Password 123456 Video Link https://drive.google.com/fle/d/1IXRRdexOR1XczdSvyDqBUnXs2jMfvaJ8/view?i <u>usp=sharing</u>

https://drive.google.com/drive/folders/1ZBZF31CCIgIsc0vjhZwMlb9xF197Q\_X3?usp=sharing

Vendor Financial Health \& Credit Assessment  |  User Manual  |  CA Ashok Jain, Batch 89  |  Page 1

## **1. Introduction**

### **1.1 Purpose of this manual**

This manual explains, step by step, how to sign in to and use the Vendor Financial Health \& Credit Assessment application. It is written for the ICAI evaluation panel and for finance, credit-control and procurement users.

### **1.2 The problem the application solves**

Whenever a new vendor is registered, or an existing vendor is reviewed, the finance team must decide the credit limit and credit period to be allowed. For a new vendor these are set for the first time; for an existing vendor they are reset.

The team often lacks specialist expertise to analyse the profit and loss account, balance sheet, notes to accounts and other information supplied in PDF, Excel, Word or other forms, and manual analysis takes a great deal of time.

### **1.3 What the application does**

* Accepts vendor documents (PDF, Excel, Word, CSV, text and images) and identifies the vendor from them.
* Captures the reported figures with a source reference and lets a finance user review and correct them.
* Calculates 25 financial ratios, prepares a SWOT analysis and red flags, and gives a vendor score out of 100.
* Recommends a credit limit and credit period using transparent rules, which the finance user can approve, modify or hold.
* Produces a 26-section Vendor Evaluation Report, downloadable as PDF, Word, Excel and PowerPoint, with all amounts in INR crore.

### **1.4 Design principles**

* **AI reads, code calculates:** documents are read with AI, but every ratio, score and limit is calculated by fixed formulas in the application. Missing figures are never invented; the application shows "Insufficient information available for this analysis".
* **Human in the loop:** extracted figures can be corrected, and the final credit decision is made by an authorised person. Any change to the recommendation needs a recorded reason.
* **Decision support only:** the output is not a credit rating, audit opinion or final credit approval.

## **2. Accessing the Application**

|**Item**|**Details**|
|-|-|
|**Application link**|https://vendorfin-eval.lovable.app/dashboard|
|**User ID**|AI@ICAI.Org|
|**Password**|123456|
||Finance User (can upload documents, run assessments, review|
|**Account type**|results, generate and download reports; report storage is unlimited<br>for this login)|
|**Browsers**|Latest Google Chrome, Microsoft Edge, Mozilla Firefox or Safari|



Vendor Financial Health \& Credit Assessment  |  User Manual  |  CA Ashok Jain, Batch 89  |  Page 2

|**Item**|**Details**|
|-|-|
|**Internet**|A working internet connection is required|



### **2.1 Signing in**

1. Open the application link in a web browser.
2. Enter the User ID and Password from the table above on the sign-in screen.
3. Select the sign-in button. The Dashboard opens.

**Note:** There is no public self-registration; only an administrator can create user accounts. The credentials above are for evaluation. To end a session, use Sign out at the top right.

## **3. Screens and Navigation**

The left-hand menu is the main way to move around. Administrator pages appear only for administrator accounts, so they are not visible to the evaluation login.

|**Menu item**|**What it is for**|
|-|-|
|**Dashboard**|Portfolio summary of vendors, assessments, risk distribution, credit<br>exposure and report storage usage.|
|**Vendors**|List of vendors identified from uploaded documents. Select a vendor<br>name to open its own dashboard with period-by-period comparison.|
|**New Assessment**|The guided 13-step workflow: upload, process, review, analyse, decide<br>and report.|
|**Assessment History**|All previous assessments. Select a row to reopen it.|
|**Reports**|Saved reports. Select a row to read the report on screen or download<br>it again.|
|**Analytics**|Analytical views across assessments.|
|**My Storage**|Your report storage: reports used against the allowance.|
|**Settings**|Application settings available to your account.|



*Administrator-only pages (for reference): User Management, Report Quotas, Scoring Configuration, Credit Rules and Audit Logs. See Section 10.*

## **4. The Dashboard**

The Dashboard is the landing page after sign-in and gives a portfolio-level view.

|**Item**|**Meaning**|
|-|-|
|**Vendors and assessments**|How many vendors have been assessed and how many assessments<br>are complete.|
|**Risk distribution**|How vendors are spread across risk bands. Bands appear once an<br>administrator has configured score thresholds.|
|**Credit exposure**|Credit limits extended across the portfolio.|



Vendor Financial Health \& Credit Assessment  |  User Manual  |  CA Ashok Jain, Batch 89  |  Page 3

|**Item**|**Meaning**|
|-|-|
|**Report storage**|Reports used against the allowance for your account.|



## **5. Running an Assessment: Step by Step**

Open New Assessment from the menu. A Workflow panel on the left lists the 13 steps and shows where you are. The vendor does not need to be typed in: the vendor name and details are taken from the documents.

### **Stage 1: Ingest (steps 1 and 2)**

1. **Upload documents.** Select Browse files, or drag and drop. Upload the Balance Sheet, Profit \& Loss account, Cash Flow Statement, notes to accounts, auditor’s report and schedules. Permitted formats: PDF, XLS, XLSX, CSV, DOC, DOCX, TXT, PNG, JPG, JPEG; maximum 20 MB per file. Several files are processed together as one assessment.
2. **Optional requested credit.** Before the first upload you may enter the requested credit limit and requested credit period in days. Then select Upload.
3. **Process documents.** Select Process documents. Each document is read and identified (for example Balance Sheet, P\&L, Cash Flow, Notes, Auditor’s Report). The application reports documents read, figures captured and reporting periods found, the units applied (such as lakh or crore) and any missing information or unreadable files. A “Vendor identified from documents” card shows the vendor details found.

### **Stage 2: Verify (steps 3 and 4)**

1. **Review extracted data.** The captured figures are shown in an editable table by financial period, each with its source reference. Figures that need attention are marked for verification.
2. **Confirm corrections.** Correct any figure the reader captured wrongly, then confirm. Corrections are kept separate from the extracted value and are recorded in the audit trail. Confirming unlocks the analysis.

### **Stage 3: Analyse (steps 5 to 8)**

1. **Financial analysis and ratios.** 25 ratios are calculated. Each shows its formula, current and previous value, trend, interpretation and risk indication.
2. **SWOT and red flags.** Strengths, weaknesses, opportunities and threats are listed, marked as document fact, calculated or analytical observation. Red flags show severity, observation, financial impact, evidence and what the reviewer should look at.
3. **Vendor score.** A score out of 100 is shown with each component, its weight, result, component score, explanation and evidence.

### **Stage 4: Decide (steps 9 to 11)**

1. **Credit recommendation.** The System Recommendation shows a credit limit, credit period and confidence, with the basis used.
2. **Finance review and decision.** Choose Approve, Modify or Hold. If you modify the recommendation you must give a reason for the override. The final decision is stored separately from the system recommendation.

### **Stage 5: Report (steps 12 and 13)**

1. **Generate report.** Generate the Vendor Evaluation Report. Reports count against your storage allowance.

Vendor Financial Health \& Credit Assessment  |  User Manual  |  CA Ashok Jain, Batch 89  |  Page 4

2. **Download.** Download in PDF, Word, Excel or PowerPoint. Every report ends with a plainlanguage summary that a non-finance reader can follow.

**Tip:** Upload complete statements, including notes to accounts and the auditor’s and directors’ reports, for the fullest assessment. If a statement is missing, the application lists what is missing and lowers the confidence of the recommendation.

## **6. Vendors, History and Reports**

### **6.1 Compare periods for a vendor**

In Vendors, select a vendor name to open its dashboard: score, credit limit and a period-by-period comparison. Choose two periods (for example FY2026 and FY2025) to see every figure and ratio side by side with the change. A search box finds a specific figure, such as revenue or current ratio.

### **6.2 Reopen and re-download**

In Assessment History or Reports, select any row to reopen that company’s assessment. The report can be read on screen, including the SWOT analysis, and downloaded again in any format without uploading the documents again.

## **7. Try It: Sample Financial Statements**

A fictional two-year sample, ABC Limited (FY 2024-25 and FY 2025-26), is supplied as ABC\_Ltd\_Two\_Year\_Sample\_Financials.pdf. Its figures are stated in INR lakh; the application presents them in INR crore (100 lakh = 1 crore). All identifiers in the sample are fictional. Upload it in New Assessment as described in Section 5.

### **7.1 Figures the application should capture**

|**Item**|**FY 2025-26**|**FY 2024-25**|
|-|-|-|
|**Revenue from operations**|₹125.00 Cr|₹108.00 Cr|
|**EBITDA**|₹25.80 Cr|₹21.10 Cr|
|**Profit before tax**|₹14.50 Cr|₹10.70 Cr|
|**Profit after tax**|₹10.70 Cr|₹7.90 Cr|
|**Net worth**|₹42.50 Cr|₹33.80 Cr|
|**Total debt**|₹34.00 Cr|₹35.00 Cr|
|**Trade receivables**|₹24.20 Cr|₹21.00 Cr|
|**Trade payables**|₹16.80 Cr|₹14.70 Cr|
|**Operating cash flow**|₹15.20 Cr|₹11.70 Cr|



### **7.2 Ratios you can verify**

|**Ratio**|**FY 2025-26**|**FY 2024-25**|
|-|-|-|
|**Current ratio**|1.49×|1.44×|
|**Quick ratio**|1.01×|0.96×|
|**Debt / equity**|0.80×|1.04×|



Vendor Financial Health \& Credit Assessment  |  User Manual  |  CA Ashok Jain, Batch 89  |  Page 5

|**Ratio**|**FY 2025-26**|**FY 2024-25**|
|-|-|-|
|**Interest coverage (EBIT ÷ finance**<br>**cost)**|3.38×|2.88×|
|**EBITDA margin**|20.6%|19.5%|
|**Net margin**|8.6%|7.3%|
|**Receivable days**|70.7 days|71.0 days|
|**Payable days (payables ÷ COGS ×**<br>**365)**|87.0 days|87.2 days|
|**Cash conversion cycle**|75.8 days|79.3 days|



### **7.3 Expected score and recommendation**

Applying the application’s published formulas and starting rules to the sample data gives the following. Small differences are possible if the document reader captures a figure differently; any such figure can be corrected in the review step.

|**Component**|**Weight (%)**|**Component score**|**Weighted points**|
|-|-|-|-|
|**Liquidity**|20|71.7|14.3|
|**Profitability**|20|95.7|19.1|
|**Leverage \& solvency**|20|80.0|16.0|
|**Cash flow**|15|88.3|13.2|
|**Efficiency \& working capital**|10|60.0|6.0|
|**Growth \& stability**|5|100.0|5.0|
|**Qualitative \& audit risks**|10|100.0|10.0|
|**Total vendor score**|100||83.7|



*Component scores and weighted points are rounded for display; the total is computed on the unrounded values.*

|**Credit limit bases (Cr)**|**Value**|
|-|-|
|**5% of revenue**|₹6.25 Cr|
|**10% of net worth**|₹4.25 Cr  (lowest, so used)|
|**25% of working capital**|₹4.55 Cr|
|**Score band (80 and above)**|1.00× multiplier, 60 days|
|**System recommendation**|₹4.25 Cr credit limit, 60 days, High confidence|



### **7.4 Points a reviewer should notice**

* Customer concentration: the five largest customers are about 46% of FY 2025-26 revenue and the largest about 14%.
* Receivables older than 90 days are ₹2.80 Cr (11.6% of total), of which ₹0.90 Cr is older than 180 days.

Vendor Financial Health \& Credit Assessment  |  User Manual  |  CA Ashok Jain, Batch 89  |  Page 6

* A disputed indirect-tax matter of ₹1.65 Cr is disclosed as a contingent liability, about 3.9% of net worth.
* Payable days computed from the statements are about 87 in both years, whereas management discloses 78 (FY 2025-26) and 74 (FY 2024-25). The basis of the disclosed figure should be clarified with the vendor.

The score reflects the numeric analysis. These qualitative points appear in the report narrative for the reviewer’s judgement, which is why the recommendation is advisory and requires finance approval.

## **8. How the Score and Recommendation Work**

### **8.1 Vendor score**

Each ratio is converted to a 0 to 100 score using fixed bands. A component score is the average of its ratio scores; the vendor score is the weighted average of the components. If a component cannot be calculated, its weight is left out and the remaining weights are re-based, and the recommendation confidence is lowered.

|**Component**|**Weight (%)**|**Ratios included**|
|-|-|-|
|**Liquidity**|20|Current, quick, cash ratio|
|**Profitability**|20|Gross, EBITDA, operating and net margin;<br>ROA, ROE, ROCE|
|**Leverage \& solvency**|20|Debt / equity, debt / assets, debt / EBITDA,<br>interest coverage|
|**Cash flow**|15|Operating cash flow margin, to EBITDA, to<br>debt|
|**Efficiency \& working capital**|10|Receivable, payable and inventory days;<br>asset turnover; cash conversion cycle|
|**Growth \& stability**|5|Revenue, EBITDA and PAT growth|
|**Qualitative \& audit risks**|10|Reduced by red flags: 25 points for each<br>high, 12 for each medium, 5 for each low<br>severity flag|



### **8.2 Credit limit and credit period**

The recommended limit is the lowest of three bases, multiplied by a factor set by the score band. The same band sets the credit period.

|**Score band**|**Limit multiplier**|**Credit period**|**Confidence**|
|-|-|-|-|
|**80 and above**|1.00×|60 days|High|
|**65 to 79**|0.75×|45 days|Medium|
|**50 to 64**|0.50×|30 days|Medium|
|**Below 50**|0.25×|15 days|Low|



*Bases: 5% of revenue; 10% of net worth (if positive); 25% of working capital (if positive). These are starting rules held as versioned configuration in the database, not hard-coded.*

Vendor Financial Health \& Credit Assessment  |  User Manual  |  CA Ashok Jain, Batch 89  |  Page 7

### **8.3 Red flags checked**

Negative net worth; loss-making year or continuous losses; revenue decline; high leverage (debt / equity above 2); low interest coverage (below 1.5); weak liquidity (current ratio below 1.2); negative operating cash flow; high receivable days (above 90); high dependence on short-term borrowings (above 70% of debt); and a sharp fall in net margin (5 percentage points or more).

## **9. Key Terms**

|**Term**|**Formula used in the application**|
|-|-|
|**Current ratio**|Current assets ÷ current liabilities|
|**Quick ratio**|(Current assets − inventory) ÷ current liabilities|
|**Debt / equity**|Total debt ÷ net worth|
|**Interest coverage**|EBIT ÷ finance cost|
|**EBITDA margin**|EBITDA ÷ revenue × 100|
|**Receivable days**|Trade receivables ÷ revenue × 365|
|**Payable days**|Trade payables ÷ cost of goods sold × 365|
|**Cash conversion cycle**|Receivable days + inventory days − payable days|
|**ROCE**|EBIT ÷ (net worth + total debt) × 100|



*No industry benchmark is applied; the application states “Industry benchmark not configured” rather than inventing one.*

## **10. Administrator Functions (Reference)**

These pages are available only to administrator accounts and are not visible to the evaluation login.

* **User Management:** create users; edit a user’s name, email, role, access and report download allowance; disable a user; delete a profile completely.
* **Report Quotas:** set the default number of stored reports (default 4) or a different limit, or unlimited, for each user.
* **Scoring Configuration and Credit Rules:** view the active weights, limit bases and score bands.
* **Audit Logs:** review recorded actions such as uploads, corrections, overrides, report generation and deletions.
* **Company data:** an administrator can delete a vendor together with its uploaded documents, figures, assessments and reports.

## **11. Data Protection**

* Documents are held in private storage, accessible only to authorised users.
* Access is role-based (Admin, Finance, Viewer) and enforced in the database with row-level security.
* Key actions are written to an audit log.

Vendor Financial Health \& Credit Assessment  |  User Manual  |  CA Ashok Jain, Batch 89  |  Page 8

## **12. Troubleshooting**

|**Issue**|**What to try**|
|-|-|
|**Cannot sign in**|Re-enter the User ID and Password exactly as given; check Caps<br>Lock; refresh the page and retry.|
|**Page does not load**|Check the internet connection and use an up-to-date browser;<br>try another browser.|
|**File will not upload**|Check the file type (PDF, Excel, Word, CSV, text or image) and<br>that it is under 20 MB and not password-protected.|
|**No figures captured**|Use a clear, text-based PDF or the Excel version. Scanned images<br>can reduce accuracy. Review and correct figures in the review<br>step.|
|**Figures in the wrong scale**|Check the “Units applied” note after processing and correct any<br>figure in the review step.|
|**Storage limit message**|Your report allowance is used up. Ask an administrator to raise<br>it. (The evaluation login has unlimited storage.)|



## **13. Disclaimer and Limitations**

This assessment is a decision-support tool based on information supplied to the system. The generated financial analysis, vendor score, credit limit and credit-period recommendation should not be treated as an independent credit rating, audit opinion, or final credit approval. Final credit decisions remain subject to review and approval by authorized personnel.

* The sample financial statements are synthetic; company details, GSTIN, PAN, CIN and address in them are fictional.
* Risk bands (low, medium, high) are shown only after an administrator sets score thresholds.
* Industry benchmarks are not configured; qualitative disclosures inform the report narrative and red flags, and should be weighed by the reviewer.

#### **Prepared and submitted by CA Ashok Jain, ICAI AI Level 2, Gurugram Branch, Batch 89.**

Vendor Financial Health \& Credit Assessment  |  User Manual  |  CA Ashok Jain, Batch 89  |  Page 9

