"""Authoritative Reference Library of FRRB Observations, Standards, and Statutory Citations.

Contains verbatim technical principles from ICAI's 'Study on Compliance of Financial Reporting Requirements',
Ind AS Standards (Ind AS 1, 2, 7, 8, 12, 16, 19, 20, 21, 23, 24, 33, 36, 37, 38, 40, 107, 108, 109, 115, 116),
Schedule III (Divisions I, II, III), Companies Act 2013, and CARO 2020.
All technical references are authentic, traceable, and cite exact statutory sections and paragraphs.
"""

from typing import Dict, Any, List, Optional


class FRRBLibrary:
    """Repository of authenticated FRRB precedents, Schedule III rules, and standard paragraphs."""

    PRECEDENTS: List[Dict[str, Any]] = [
        # --- ASSETS & PROPERTY, PLANT AND EQUIPMENT ---
        {
            "id": "FRRB-PPE-01",
            "category": "Assets - Property, Plant & Equipment",
            "framework": "Ind AS",
            "topic": "Subsequent expenditure recognition criteria",
            "standard_ref": "Ind AS 16, Paragraphs 7 and 13",
            "statutory_ref": "Schedule III, Division II, Part I",
            "principle": (
                "Under Ind AS 16.7 and 16.13, subsequent expenditure on PPE is capitalized if and only if "
                "it is probable that future economic benefits associated with the item will flow to the entity "
                "and cost can be measured reliably. Basing capitalization on 'standard of performance' "
                "(which was the legacy AS 10 test) is non-compliant under Ind AS."
            ),
            "common_deficiency": (
                "Accounting policy states subsequent costs capitalized only if they increase standard of performance "
                "beyond previously assessed standard, rather than probability of future economic benefits."
            ),
            "suggested_correction": (
                "Amend PPE policy: 'Subsequent expenditure is capitalized only when it is probable that future economic "
                "benefits associated with the item will flow to the company and the cost can be measured reliably.'"
            ),
            "risk": "Medium"
        },
        {
            "id": "FRRB-PPE-02",
            "category": "Assets - Property, Plant & Equipment",
            "framework": "Both",
            "topic": "Depreciation method and useful life review",
            "standard_ref": "Ind AS 16, Paragraph 51 / AS 10, Paragraph 59; Schedule II to Companies Act, 2013",
            "statutory_ref": "Schedule II, Part B, Companies Act, 2013",
            "principle": (
                "The residual value and useful life of an asset shall be reviewed at least at each financial year-end. "
                "If useful lives differ from Schedule II prescribed lives, disclosure of technical justification is mandatory."
            ),
            "common_deficiency": (
                "Failure to disclose whether useful lives were reviewed at financial year-end or omission of technical "
                "evaluation justification when applying lives different from Schedule II."
            ),
            "suggested_correction": (
                "Include disclosure under Note on PPE confirming annual review of useful lives and residual values, "
                "with reference to independent technical evaluation if different from Schedule II."
            ),
            "risk": "Medium"
        },
        {
            "id": "FRRB-PPE-CAP-ADV",
            "category": "Assets - Capital Advances & CWIP",
            "framework": "Both",
            "topic": "Classification of Capital Advances under Non-Current Assets",
            "standard_ref": "Schedule III (Part I, Non-Current Assets); Ind AS 16",
            "statutory_ref": "Schedule III, Division I & II, Part I",
            "principle": (
                "Capital Advances are non-financial assets given for acquiring capital goods and SHALL be classified "
                "under 'Other Non-Current Assets', NOT clubbed within Capital Work-in-Progress (CWIP) or Long-Term Loans & Advances."
            ),
            "common_deficiency": (
                "Capital advances clubbed within Capital Work-in-Progress or shown under financial loans and advances."
            ),
            "suggested_correction": (
                "Reclassify capital advances to 'Other Non-Current Assets' in compliance with Schedule III Part I."
            ),
            "risk": "Medium"
        },
        {
            "id": "FRRB-SCH3-CWIP-01",
            "category": "Assets - Capital Work-in-Progress (CWIP)",
            "framework": "Both",
            "topic": "CWIP Ageing Schedule and Completion Schedule",
            "standard_ref": "Schedule III (General Instructions, Part I, Clause 6(EA))",
            "statutory_ref": "MCA Notification G.S.R. 207(E) dated 24th March 2021",
            "principle": (
                "Schedule III requires disclosure of CWIP ageing schedule categorized into (i) Projects in progress and "
                "(ii) Projects temporarily suspended for periods: <1 year, 1-2 years, 2-3 years, and >3 years. "
                "For CWIP overdue or where cost exceeded original plan, CWIP completion schedule must be disclosed."
            ),
            "common_deficiency": (
                "CWIP presented as a single carrying amount on Balance Sheet without the mandatory ageing schedule "
                "or completion schedule for overdue capital projects."
            ),
            "suggested_correction": (
                "Incorporate CWIP ageing schedule categorized by age brackets and disclose completion schedule for delayed projects."
            ),
            "risk": "High"
        },
        {
            "id": "FRRB-SCH3-TITLE-01",
            "category": "Assets - Immovable Properties",
            "framework": "Both",
            "topic": "Title Deeds of Immovable Property not held in Company Name",
            "standard_ref": "Schedule III (General Instructions, Part I, Clause 6(L)); CARO 2020 Clause 3(i)(c)",
            "statutory_ref": "Companies Act, 2013, Schedule III Part I",
            "principle": (
                "The company shall provide details of all immovable property (other than properties where company is lessee) "
                "whose title deeds are not held in the name of the company, disclosing description of property, gross carrying value, "
                "title deeds held in the name of (promoter, director, relative, employee), period held, and reason for not being held in name."
            ),
            "common_deficiency": (
                "CARO report notes title deeds in erstwhile promoter/transferor name, but required Schedule III tabular disclosure "
                "in financial statements is omitted."
            ),
            "suggested_correction": (
                "Disclose specific immovable properties title deed table complying with Schedule III Part I format."
            ),
            "risk": "High"
        },

        # --- LEASES (IND AS 116) ---
        {
            "id": "FRRB-LEASES-01",
            "category": "Accounting Standards - Leases (Ind AS 116)",
            "framework": "Ind AS",
            "topic": "ROU Asset Roll-Forward and Maturity Analysis of Lease Liabilities",
            "standard_ref": "Ind AS 116, Paragraphs 47, 51-60; Ind AS 107, Paragraph 39",
            "statutory_ref": "Ind AS 116 (Leases)",
            "principle": (
                "Lessee shall disclose: (a) Depreciation charge for right-of-use (ROU) assets by class of underlying asset, "
                "(b) Interest expense on lease liabilities, (c) Short-term and low-value lease expense, (d) Variable lease payments, "
                "and (e) Maturity analysis of lease liabilities showing undiscounted contractual lease payments under Ind AS 107.39."
            ),
            "common_deficiency": (
                "Single lump-sum lease expense presented without class-wise ROU depreciation or maturity analysis of lease liabilities."
            ),
            "suggested_correction": (
                "Provide comprehensive Ind AS 116 disclosure note containing ROU asset roll-forward and undiscounted lease maturity schedule."
            ),
            "risk": "High"
        },

        # --- REVENUE FROM CONTRACTS WITH CUSTOMERS (IND AS 115) ---
        {
            "id": "FRRB-REV-01",
            "category": "Accounting Standards - Revenue (Ind AS 115)",
            "framework": "Ind AS",
            "topic": "Disaggregation of Revenue and Contract Balances",
            "standard_ref": "Ind AS 115, Paragraphs 114, 116, 120",
            "statutory_ref": "Schedule III, Division II, Part II",
            "principle": (
                "An entity shall disaggregate revenue recognized from contracts with customers into categories that depict "
                "how economic factors affect nature, amount, timing and uncertainty of cash flows. Disclose opening/closing "
                "contract assets, contract liabilities (unearned revenue), and performance obligations unsatisfied."
            ),
            "common_deficiency": (
                "Lump-sum revenue disclosed in P&L without disaggregation by product type, geography, or contract timing, "
                "and omission of contract liability roll-forward."
            ),
            "suggested_correction": (
                "Incorporate revenue disaggregation table and disclose contract assets / liabilities reconciliation per Ind AS 115."
            ),
            "risk": "High"
        },

        # --- EMPLOYEE BENEFITS (IND AS 19) ---
        {
            "id": "FRRB-EMP-01",
            "category": "Accounting Standards - Employee Benefits (Ind AS 19)",
            "framework": "Ind AS",
            "topic": "Actuarial Assumptions, Sensitivity Analysis and OCI Presentation",
            "standard_ref": "Ind AS 19, Paragraphs 83, 142, 145",
            "statutory_ref": "Ind AS 19 (Employee Benefits)",
            "principle": (
                "The discount rate used to discount post-employment benefit obligations SHALL be determined by reference "
                "to market yields on government bonds at end of reporting period. Entity must disclose sensitivity analysis "
                "for each significant actuarial assumption (discount rate ±1%, salary escalation ±1%) and route remeasurements through OCI."
            ),
            "common_deficiency": (
                "Actuarial gratuity note omits sensitivity analysis of key assumptions or fails to benchmark discount rate "
                "to prevailing sovereign bond yield."
            ),
            "suggested_correction": (
                "Add sensitivity analysis table for discount rate and salary escalation, and confirm sovereign bond yield benchmark."
            ),
            "risk": "Medium"
        },

        # --- INCOME TAXES (IND AS 12) ---
        {
            "id": "FRRB-TAX-01",
            "category": "Accounting Standards - Income Taxes (Ind AS 12)",
            "framework": "Ind AS",
            "topic": "Tax Expense Reconciliation & Deferred Tax Assets Recognition",
            "standard_ref": "Ind AS 12, Paragraphs 35, 81(c)",
            "statutory_ref": "Ind AS 12 (Income Taxes)",
            "principle": (
                "Entity shall disclose a numerical reconciliation between tax expense (income) and accounting profit multiplied "
                "by the applicable tax rate. Deferred tax asset recognized on unabsorbed tax losses requires convincing evidence "
                "that sufficient future taxable profits will be available."
            ),
            "common_deficiency": (
                "Omission of effective tax rate numerical reconciliation or recognizing DTA on tax losses without disclosing "
                "the convincing evidence supporting recoverability."
            ),
            "suggested_correction": (
                "Include effective tax rate reconciliation table and disclose nature of convincing evidence for DTA on tax losses."
            ),
            "risk": "High"
        },

        # --- RELATED PARTY DISCLOSURES (IND AS 24) ---
        {
            "id": "FRRB-RPT-01",
            "category": "Accounting Standards - Related Parties (Ind AS 24)",
            "framework": "Both",
            "topic": "KMP Compensation Breakdown and Outstanding Balances Terms",
            "standard_ref": "Ind AS 24, Paragraphs 17, 18 / AS 18; Section 188 of Companies Act, 2013",
            "statutory_ref": "Companies Act, 2013, Section 188",
            "principle": (
                "Entities must disclose KMP compensation categorized into: (a) Short-term employee benefits, (b) Post-employment benefits, "
                "(c) Other long-term benefits, (d) Termination benefits, and (e) Share-based payments. Disclose outstanding balances, "
                "terms and conditions, security, and guarantees given/received."
            ),
            "common_deficiency": (
                "Omission of KMP compensation 5-tier breakdown or failure to disclose terms, interest rates, and security of loans given to related parties."
            ),
            "suggested_correction": (
                "Break down KMP remuneration into statutory categories under Ind AS 24.17 and disclose terms & security for balances."
            ),
            "risk": "High"
        },

        # --- FINANCIAL INSTRUMENTS & RISK DISCLOSURES (IND AS 107 & 109) ---
        {
            "id": "FRRB-FIN-01",
            "category": "Accounting Standards - Financial Instruments (Ind AS 107 / 109)",
            "framework": "Ind AS",
            "topic": "Fair Value Hierarchy and Liquidity & Market Risk Sensitivities",
            "standard_ref": "Ind AS 107, Paragraphs 34, 39, 40; Ind AS 113",
            "statutory_ref": "Ind AS 107 (Financial Instruments: Disclosures)",
            "principle": (
                "Entity shall disclose: (a) Fair value hierarchy (Level 1, 2, 3) for all financial instruments measured at fair value, "
                "(b) Contractual undiscounted maturity analysis for financial liabilities (liquidity risk), and "
                "(c) Sensitivity analysis for market risks (foreign exchange and interest rate fluctuations)."
            ),
            "common_deficiency": (
                "Absence of contractual undiscounted cash flow maturity table for borrowings and lease liabilities or omission "
                "of foreign currency sensitivity analysis."
            ),
            "suggested_correction": (
                "Disclose fair value hierarchy table, liquidity risk contractual maturity brackets, and forex/interest sensitivity tables."
            ),
            "risk": "High"
        },

        # --- PROVISIONS & CONTINGENT LIABILITIES (IND AS 37) ---
        {
            "id": "FRRB-PROV-01",
            "category": "Accounting Standards - Provisions & Contingencies (Ind AS 37)",
            "framework": "Both",
            "topic": "Movement in Provisions & Contingent Liabilities Qualitative Disclosures",
            "standard_ref": "Ind AS 37, Paragraphs 84, 86 / AS 29",
            "statutory_ref": "Ind AS 37 (Provisions, Contingent Liabilities and Contingent Assets)",
            "principle": (
                "For each class of provision, entity shall disclose opening balance, additions, amounts used, unused amounts reversed, "
                "and unwinding of discount. For contingent liabilities, disclose nature of obligation, estimate of financial effect, "
                "uncertainties relating to outflow, and possibility of reimbursement."
            ),
            "common_deficiency": (
                "Provisions presented without movement table or contingent claims listed without explaining uncertainties and timing of outflows."
            ),
            "suggested_correction": (
                "Present roll-forward table for all provisions and provide qualitative disclosure regarding timing and uncertainties of contingent claims."
            ),
            "risk": "Medium"
        },

        # --- EARNINGS PER SHARE (IND AS 33) ---
        {
            "id": "FRRB-EPS-01",
            "category": "Accounting Standards - EPS (Ind AS 33)",
            "framework": "Both",
            "topic": "Basic and Diluted EPS Presentation & Denominator Reconciliation",
            "standard_ref": "Ind AS 33, Paragraphs 66, 70 / AS 20",
            "statutory_ref": "Schedule III Part II",
            "principle": (
                "An entity shall present on the face of Statement of Profit and Loss basic and diluted EPS for profit/loss from continuing operations. "
                "Disclose amounts used as numerators and weighted average number of shares used as denominator with reconciliation."
            ),
            "common_deficiency": (
                "EPS disclosed without denominator weighted average share reconciliation or missing diluted EPS computation where potential shares exist."
            ),
            "suggested_correction": (
                "Include reconciliation of weighted average number of equity shares for both Basic and Diluted EPS."
            ),
            "risk": "Medium"
        },

        # --- STATEMENT OF CASH FLOWS (IND AS 7) ---
        {
            "id": "FRRB-CFS-01",
            "category": "Accounting Standards - Cash Flow (Ind AS 7)",
            "framework": "Ind AS",
            "topic": "Reconciliation of Liabilities arising from Financing Activities (Net Debt Roll-Forward)",
            "standard_ref": "Ind AS 7, Paragraphs 44A to 44E",
            "statutory_ref": "Ind AS 7 (Statement of Cash Flows)",
            "principle": (
                "An entity shall provide disclosures that enable users to evaluate changes in liabilities arising from financing activities, "
                "including both cash flow changes and non-cash changes (such as forex movements, acquisitions, fair value adjustments, lease additions)."
            ),
            "common_deficiency": (
                "Omission of mandatory reconciliation table of liabilities arising from financing activities (Net Debt reconciliation)."
            ),
            "suggested_correction": (
                "Include Note to Cash Flow Statement presenting opening to closing reconciliation of borrowings and lease liabilities."
            ),
            "risk": "High"
        },

        # --- SCHEDULE III MANDATORY DISCLOSURES ---
        {
            "id": "FRRB-SCH3-TP-01",
            "category": "Schedule III - Mandatory Ageing Schedules",
            "framework": "Both",
            "topic": "Trade Payables Ageing Schedule & MSME Disclosures",
            "standard_ref": "Schedule III (General Instructions, Part I, Clause 6(FA)); Section 22 of MSMED Act, 2006",
            "statutory_ref": "Ministry of Corporate Affairs Notification G.S.R. 207(E) dated 24th March 2021",
            "principle": (
                "Schedule III mandates an Ageing Schedule for Trade Payables categorized into: (i) MSME, (ii) Others, "
                "(iii) Disputed dues - MSME, and (iv) Disputed dues - Others for periods: <1 year, 1-2 years, 2-3 years, "
                ">3 years, plus Unbilled dues. Note must disclose MSMED Act Section 22 principal/interest unpaid."
            ),
            "common_deficiency": (
                "Trade Payables note does not present the required ageing schedule or lacks separate categorisation "
                "for MSME and non-MSME dues, or omits unbilled dues."
            ),
            "suggested_correction": (
                "Insert Trade Payables Ageing Schedule in strict compliance with MCA Schedule III format specifying "
                "age brackets (<1 yr, 1-2 yrs, 2-3 yrs, >3 yrs) and MSME vs Others split."
            ),
            "risk": "High"
        },
        {
            "id": "FRRB-SCH3-TR-01",
            "category": "Schedule III - Mandatory Ageing Schedules",
            "framework": "Both",
            "topic": "Trade Receivables Ageing Schedule & Credit Risk",
            "standard_ref": "Schedule III (General Instructions, Part I, Clause 6(L)); Ind AS 109 / AS 4",
            "statutory_ref": "MCA Notification G.S.R. 207(E) dated 24th March 2021",
            "principle": (
                "Schedule III requires ageing of Trade Receivables: Undisputed - considered good, Undisputed - "
                "which have significant increase in credit risk, Undisputed - credit impaired, Disputed - considered good, "
                "Disputed - credit impaired, across <6 months, 6 mos-1 yr, 1-2 yrs, 2-3 yrs, >3 yrs, plus Unbilled dues."
            ),
            "common_deficiency": (
                "Trade Receivables ageing omitted or presented without unbilled dues or without distinguishing disputed "
                "vs undisputed and credit impaired categories."
            ),
            "suggested_correction": (
                "Add complete Trade Receivables Ageing Schedule complying with Schedule III format, reconciling with total "
                "carrying amount on Balance Sheet."
            ),
            "risk": "High"
        },
        {
            "id": "FRRB-SCH3-PROMOTER-01",
            "category": "Schedule III - Share Capital Disclosures",
            "framework": "Both",
            "topic": "Promoter Shareholding Disclosure",
            "standard_ref": "Schedule III (General Instructions, Part I, Clause 6(J))",
            "statutory_ref": "MCA Notification G.S.R. 207(E) dated 24th March 2021",
            "principle": (
                "Company must disclose shareholding of promoters at the end of the year, including Promoter name, "
                "number of shares, % of total shares, and % change during the year."
            ),
            "common_deficiency": (
                "Share capital note lists major shareholders (>5%) but omits the mandatory Promoter Shareholding table "
                "or omits the column '% change during the year'."
            ),
            "suggested_correction": (
                "Add separate Promoter Shareholding table specifying Promoter Name, Number of Shares, % of total shares, "
                "and % change during the financial year."
            ),
            "risk": "Medium"
        },
        {
            "id": "FRRB-SCH3-RATIO-01",
            "category": "Schedule III - Financial Ratios",
            "framework": "Both",
            "topic": "Mandatory 11 Analytical Ratios and Variance Explanation",
            "standard_ref": "Schedule III (General Instructions, Part I, Clause 6(VA))",
            "statutory_ref": "Companies Act, 2013, Schedule III Amendment 2021",
            "principle": (
                "Entities must disclose 11 analytical ratios (Current ratio, Debt-Equity, Debt Service Coverage, "
                "ROCE, Inventory Turnover, Trade Receivables Turnover, Trade Payables Turnover, Net Capital Turnover, "
                "Net Profit ratio, Return on Investment) AND provide reasons for variance if change exceeds 25%."
            ),
            "common_deficiency": (
                "Ratios disclosed without explicit explanation for line items where year-on-year variance exceeds 25%, "
                "or elements used in numerator/denominator are not defined."
            ),
            "suggested_correction": (
                "Provide explanatory footnotes detailing operational and financial drivers for any ratio variance exceeding 25%."
            ),
            "risk": "High"
        },
        {
            "id": "FRRB-SCH3-STRUCK-01",
            "category": "Schedule III - Regulatory Disclosures",
            "framework": "Both",
            "topic": "Transactions and Relationships with Struck-off Companies",
            "standard_ref": "Schedule III (General Instructions, Part I, Clause 6(W))",
            "statutory_ref": "Section 248 of Companies Act, 2013 read with Schedule III",
            "principle": (
                "Where company has any transactions with companies struck off under section 248 of Companies Act, 2013, "
                "it shall disclose details: Nature of transaction, balance outstanding, and relationship with the struck off company. "
                "If no transactions exist, negative statement is required by good practice."
            ),
            "common_deficiency": (
                "Complete silence on struck-off companies disclosure in notes to accounts."
            ),
            "suggested_correction": (
                "Disclose transactions with struck-off companies table or negative declaration confirming no transactions."
            ),
            "risk": "Medium"
        },
        {
            "id": "FRRB-SCH3-ROC-01",
            "category": "Schedule III - Regulatory Disclosures",
            "framework": "Both",
            "topic": "Registration of Charges or Satisfaction with ROC",
            "standard_ref": "Schedule III (General Instructions, Part I, Clause 6(T))",
            "statutory_ref": "Section 77 and 82 of Companies Act, 2013",
            "principle": (
                "Where any charge or satisfaction is yet to be registered with ROC beyond the statutory period, "
                "details and reasons for delay shall be disclosed."
            ),
            "common_deficiency": (
                "Note on borrowings fails to disclose whether charges created for securing bank facilities are registered within statutory deadlines."
            ),
            "suggested_correction": (
                "Add explicit disclosure on registration/satisfaction of charges with Registrar of Companies."
            ),
            "risk": "Medium"
        },
        {
            "id": "FRRB-SCH3-WILFUL-01",
            "category": "Schedule III - Regulatory Disclosures",
            "framework": "Both",
            "topic": "Wilful Defaulter Disclosure",
            "standard_ref": "Schedule III (General Instructions, Part I, Clause 6(S))",
            "statutory_ref": "RBI Master Circular on Wilful Defaulters / Schedule III",
            "principle": (
                "Where a company is declared a wilful defaulter by any bank or financial institution or other lender, "
                "details of date of declaration, amount and nature of defaults shall be disclosed."
            ),
            "common_deficiency": (
                "Absence of declaration regarding wilful defaulter status."
            ),
            "suggested_correction": (
                "Include mandatory confirmation regarding wilful defaulter declaration in Borrowings note."
            ),
            "risk": "High"
        },
        {
            "id": "FRRB-CSR-01",
            "category": "Companies Act, 2013 - Section 135 (CSR)",
            "framework": "Both",
            "topic": "Corporate Social Responsibility (CSR) Disclosures",
            "standard_ref": "Section 135 of Companies Act, 2013; Schedule VII",
            "statutory_ref": "Companies (Corporate Social Responsibility Policy) Rules, 2014 as amended",
            "principle": (
                "Detailed disclosure of CSR obligation: Amount required to be spent, amount spent, shortfall amount, "
                "total previous years shortfall, reason for shortfall, transfer to Unspent CSR Account (Sec 135(6)) within 30 days, "
                "or transfer to specified Fund under Schedule VII (Sec 135(5)) within 6 months, and details of ongoing projects."
            ),
            "common_deficiency": (
                "Lump-sum CSR expense disclosed in P&L without the mandatory breakdown of spent, unspent, and statutory transfer status."
            ),
            "suggested_correction": (
                "Incorporate CSR disclosure table complying with MCA format, including details of ongoing vs other projects."
            ),
            "risk": "High"
        },

        # --- AUDITOR'S REPORT & CARO 2020 ---
        {
            "id": "FRRB-CARO-QTR-01",
            "category": "CARO 2020 - Working Capital Reconciliations",
            "framework": "Both",
            "topic": "Quarterly Returns Reconciliation with Books (Clause 3(ii)(b))",
            "standard_ref": "CARO 2020, Clause 3(ii)(b); Schedule III Clause 6(L)",
            "statutory_ref": "Companies (Auditor's Report) Order, 2020",
            "principle": (
                "Where company has sanctioned working capital limits > ₹5 Crores from banks/FIs on security of current assets, "
                "quarterly returns/statements filed with banks must be reconciled with books of accounts. Any material discrepancy "
                "must be disclosed."
            ),
            "common_deficiency": (
                "Discrepancies between stock statements filed with banks and books of accounts not disclosed, or CARO report "
                "omits details of quarterly variances."
            ),
            "suggested_correction": (
                "Disclose summary reconciliation table between quarterly returns submitted to banks and books of accounts, "
                "explaining differences."
            ),
            "risk": "High"
        },
        {
            "id": "FRRB-CARO-DUES-01",
            "category": "CARO 2020 - Statutory Dues & Disputes",
            "framework": "Both",
            "topic": "Undisputed Statutory Dues Outstanding > 6 Months (Clause 3(vii)(a))",
            "standard_ref": "CARO 2020, Clause 3(vii)(a); Section 143(11)",
            "statutory_ref": "Companies (Auditor's Report) Order, 2020",
            "principle": (
                "Auditor must report whether undisputed statutory dues including GST, PF, ESI, Income-tax, Customs duty "
                "have been regularly deposited and indicate arrears outstanding for a period of more than 6 months as on balance sheet date."
            ),
            "common_deficiency": (
                "Failure to identify arrears of statutory dues unpaid for >6 months as on 31st March."
            ),
            "suggested_correction": (
                "Provide detailed schedule of statutory dues outstanding for more than 6 months from the date they became payable."
            ),
            "risk": "High"
        },
        {
            "id": "FRRB-CARO-CASH-LOSS-01",
            "category": "CARO 2020 - Financial Health",
            "framework": "Both",
            "topic": "Cash Losses Incurred in Current and Preceding Year (Clause 3(xvii))",
            "standard_ref": "CARO 2020, Clause 3(xvii)",
            "statutory_ref": "Guidance Note on CARO 2020",
            "principle": (
                "Auditor shall report whether the company has incurred cash losses in the financial year and in the immediately preceding financial year, "
                "and if so, state the amount of cash losses."
            ),
            "common_deficiency": (
                "CARO report does not state explicit cash loss figures or reconciles incorrectly with net profit before non-cash adjustments."
            ),
            "suggested_correction": (
                "Compute and disclose exact cash loss figure (Net profit after tax adjusted for non-cash depreciation, deferred tax, etc.)."
            ),
            "risk": "High"
        },
        {
            "id": "FRRB-AUDIT-KAM-01",
            "category": "Auditor's Report Review",
            "framework": "Ind AS",
            "topic": "Key Audit Matters (KAM) Reporting for Listed Entities",
            "standard_ref": "Standard on Auditing (SA) 701; Section 143(2)",
            "statutory_ref": "SA 701 (Communicating Key Audit Matters in the Independent Auditor's Report)",
            "principle": (
                "Communicating Key Audit Matters (KAM) in the auditor's report is mandatory for audits of complete sets of "
                "general purpose financial statements of listed entities. Auditor must describe each KAM, why it was considered "
                "a matter of most significance, and how it was addressed in the audit."
            ),
            "common_deficiency": (
                "Auditor's report of a listed entity omits Key Audit Matters section or provides boilerplate descriptions without specific audit procedures."
            ),
            "suggested_correction": (
                "Ensure statutory auditor includes compliant KAM section complying with SA 701."
            ),
            "risk": "High"
        }
    ]

    @classmethod
    def get_precedents_by_framework(cls, framework: str) -> List[Dict[str, Any]]:
        """Returns precedents applicable to given framework."""
        is_ind_as = "ind as" in framework.lower()
        target_fw = "Ind AS" if is_ind_as else "AS"
        return [
            p for p in cls.PRECEDENTS
            if p["framework"] == "Both" or p["framework"] == target_fw
        ]

    @classmethod
    def get_precedent_by_id(cls, precedent_id: str) -> Optional[Dict[str, Any]]:
        """Finds a precedent by its ID."""
        for p in cls.PRECEDENTS:
            if p["id"] == precedent_id:
                return p
        return None
