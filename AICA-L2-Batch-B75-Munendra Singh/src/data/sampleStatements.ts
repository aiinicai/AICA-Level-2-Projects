import { SampleFinancialStatement } from '../types';

export const SAMPLE_STATEMENTS: SampleFinancialStatement[] = [
  {
    id: 'apex-telecom-fy25',
    title: 'Apex Telecommunications & Digital Infra Ltd.',
    companyName: 'Apex Telecommunications & Digital Infra Limited',
    period: 'FY 2024-25 (Ended 31st March 2025)',
    framework: 'Ind AS (Schedule III Division II)',
    description: 'Listed telecom infrastructure entity with critical Ind AS 24 KMP remuneration gaps, Trade Payables casting errors, and text-to-table contradictions.',
    knownIssuesSummary: '3 Numerical Mismatches (KMP remuneration, Trade Receivables aging, Cash Flow financing), 2 Missing Ind AS Disclosures (Ind AS 37 contingent liability & Ind AS 107 sensitivity).',
    previewSnippet: `BALANCE SHEET AS AT MARCH 31, 2025 (₹ in Lakhs)
I. ASSETS
1. Non-current assets
   (a) Property, Plant & Equipment (Note 3): ₹1,45,200.00
   (b) Capital work-in-progress (Note 4): ₹12,450.00
   (c) Financial Assets
       (i) Investments (Note 5): ₹8,900.00
       (ii) Other financial assets (Note 6): ₹1,200.00
2. Current assets
   (a) Inventories (Note 7): ₹4,300.00
   (b) Financial Assets
       (i) Trade Receivables (Note 8): ₹18,450.00
       (ii) Cash & cash equivalents (Note 9): ₹3,620.00
TOTAL ASSETS: ₹1,94,120.00

STATEMENT OF PROFIT & LOSS FOR THE YEAR ENDED MARCH 31, 2025 (₹ in Lakhs)
Total Income (Revenue + Other Income): ₹1,12,400.00
Employee Benefit Expense (Note 23): ₹14,200.00
Profit Before Tax: ₹16,800.00`,
    fullText: `APEX TELECOMMUNICATIONS & DIGITAL INFRA LIMITED
CIN: L64200DL2012PLC241980
AUDITED FINANCIAL STATEMENTS FOR THE FINANCIAL YEAR ENDED 31ST MARCH 2025
(All amounts in Indian Rupees ₹ in Lakhs, unless otherwise stated)

================================================================================
PART I: BALANCE SHEET AS AT MARCH 31, 2025
================================================================================
Particulars                                 Note No.   As at 31-Mar-2025   As at 31-Mar-2024
--------------------------------------------------------------------------------
I. ASSETS
(1) Non-current Assets
   (a) Property, Plant & Equipment              3            1,45,200.00         1,38,500.00
   (b) Capital Work-in-Progress                 4              12,450.00           15,100.00
   (c) Right of Use Assets                      5               8,150.00            9,200.00
   (d) Other Intangible Assets                  6               2,400.00            2,600.00
   (e) Financial Assets
       (i) Investments                          7               8,900.00            8,200.00
       (ii) Other Financial Assets              8               1,200.00            1,100.00
   (f) Other Non-current Assets                 9               1,850.00            1,400.00
   Total Non-current Assets                                  1,80,150.00         1,76,100.00

(2) Current Assets
   (a) Inventories                             10               4,300.00            3,900.00
   (b) Financial Assets
       (i) Trade Receivables                   11              18,450.00           16,200.00
       (ii) Cash and Cash Equivalents          12               3,620.00            2,850.00
       (iii) Bank Balances other than (ii)     13               1,150.00              900.00
       (iv) Other Financial Assets             14                 850.00              720.00
   (c) Other Current Assets                    15               2,450.00            2,100.00
   Total Current Assets                                       30,820.00           26,670.00
TOTAL ASSETS                                                 2,10,970.00         2,02,770.00

II. EQUITY AND LIABILITIES
(1) Equity
   (a) Equity Share Capital                    16              40,000.00           40,000.00
   (b) Other Equity                            17              82,450.00           71,200.00
   Total Equity                                              1,22,450.00         1,11,200.00

(2) Non-current Liabilities
   (a) Financial Liabilities
       (i) Borrowings                          18              48,500.00           52,000.00
       (ii) Lease Liabilities                  19               6,200.00            7,100.00
   (b) Provisions                              20               1,850.00            1,650.00
   (c) Deferred Tax Liabilities (Net)          21               4,120.00            3,800.00
   Total Non-current Liabilities                              60,670.00           64,550.00

(3) Current Liabilities
   (a) Financial Liabilities
       (i) Borrowings                          22               8,200.00            9,500.00
       (ii) Lease Liabilities                  19               1,950.00            1,850.00
       (iii) Trade Payables                    23
             - Total O/S dues of MSME                            1,850.00            1,400.00
             - Total O/S dues of other than MSME                12,400.00           11,200.00
       (iv) Other Financial Liabilities        24               2,150.00            1,920.00
   (b) Other Current Liabilities               25               1,100.00              950.00
   (c) Current Tax Liabilities (Net)                              200.00              200.00
   Total Current Liabilities                                  27,850.00           27,020.00
TOTAL EQUITY AND LIABILITIES                                 2,10,970.00         2,02,770.00

================================================================================
PART II: STATEMENT OF PROFIT AND LOSS FOR THE YEAR ENDED MARCH 31, 2025
================================================================================
Particulars                                 Note No.        FY 2024-25          FY 2023-24
--------------------------------------------------------------------------------
I. Revenue from Operations                     26            1,08,500.00           98,200.00
II. Other Income                               27               3,900.00            3,100.00
III. Total Income (I + II)                                   1,12,400.00         1,01,300.00

IV. Expenses:
    Network Operating & Infrastructure Cost    28              52,400.00           48,100.00
    Employee Benefits Expense                  29              14,200.00           12,800.00
    Finance Costs                              30               6,150.00            6,850.00
    Depreciation and Amortization Expense      31              18,450.00           17,200.00
    Other Expenses                             32               8,950.00            7,900.00
    Total Expenses                                           1,00,150.00           92,850.00

V. Profit Before Tax (III - IV)                                12,250.00            8,450.00
VI. Tax Expense:
    Current Tax                                                 3,100.00            2,150.00
    Deferred Tax                                                  320.00              450.00
VII. Profit for the Year (V - VI)                               8,830.00            5,850.00

================================================================================
PART III: NOTES TO ACCOUNTS (EXTRACTS)
================================================================================

NOTE 11: TRADE RECEIVABLES
--------------------------------------------------------------------------------
Particulars                                            As at 31-Mar-2025   As at 31-Mar-2024
Undisputed Trade Receivables - considered good              17,200.00           15,100.00
Undisputed Trade Receivables - which have significant credit risk 1,650.00        1,350.00
Less: Allowance for expected credit loss (ECL)                (600.00)            (450.00)
Subtotal                                                    18,250.00           16,000.00
Disputed Trade Receivables - considered good                   200.00              200.00
Total Trade Receivables                                     18,450.00           16,200.00

[AUDIT CONFLICT NOTE: In paragraph 11.2 text commentary, the Director report states: "The Company maintained strong collection cycles, and Gross Trade Receivables stood at ₹18,450 Lakhs with zero bad debt provisioning during the financial year ended March 31, 2025." However, the table explicitly shows ECL allowance of ₹600.00 Lakhs.]

NOTE 23: TRADE PAYABLES (FOOTING & MSME DISCLOSURE)
--------------------------------------------------------------------------------
Breakup of Trade Payables:
- Micro and Small Enterprises (MSME):                          ₹1,850.00 Lakhs
- Creditors other than Micro and Small Enterprises:           ₹12,400.00 Lakhs
Total Trade Payables reported on Balance Sheet:               ₹14,250.00 Lakhs

MSME Note under MSMED Act 2006:
(a) Principal amount remaining unpaid:                         ₹1,850.00 Lakhs
(b) Interest due thereon remaining unpaid:                       ₹125.00 Lakhs (Not provided in P&L)
(c) Delayed payments exceeding 45 days: Text states ₹450 Lakhs delayed beyond statutory limit of 45 days.

NOTE 29: EMPLOYEE BENEFITS EXPENSE
--------------------------------------------------------------------------------
Particulars                                                    FY 2024-25          FY 2023-24
Salaries, Wages and Bonus                                       11,800.00           10,600.00
Contribution to Provident and Other Funds                          980.00              890.00
Staff Welfare Expenses                                             620.00              560.00
Share-based payment expenses                                       800.00              750.00
Total Employee Benefits Expense                                 14,200.00           12,800.00

NOTE 33: RELATED PARTY DISCLOSURES (Ind AS 24)
--------------------------------------------------------------------------------
(A) Names of Related Parties and Description of Relationship:
    1. Holding Company: Zenith Infra Holdings Corp.
    2. Key Management Personnel (KMP):
       - Mr. Rajesh Varma, Managing Director & CEO
       - Ms. Ananya Sen, Whole-time Director & CFO
       - Mr. Tarun Mehta, Company Secretary
    3. Enterprise owned or significantly influenced by KMP: Varma Infra-Tech LLP

(B) Transactions during the year with Related Parties:
Particulars                                 Holding Co.       KMP           Varma LLP
--------------------------------------------------------------------------------
Management Consulting Services paid           ₹1,200.00        --                --
Remuneration to Key Management Personnel:
- Mr. Rajesh Varma (MD & CEO)                   --           ₹380.00             --
- Ms. Ananya Sen (CFO)                          --           ₹180.00             --
- Mr. Tarun Mehta (CS)                          --            ₹40.00             --
Total KMP Remuneration disclosed in Note 33     --           ₹600.00             --
Infrastructure lease rentals to Varma LLP       --             --             ₹1,450.00

[AUDIT DISCREPANCY OBSERVED:
In Director's Report on Corporate Governance, Table 4.2 states: "Total Managerial Remuneration paid to Managing Director Rajesh Varma was ₹480.00 Lakhs including performance bonus of ₹100 Lakhs approved by Nomination & Remuneration Committee." However, Note 33 reflects only ₹380.00 Lakhs for Mr. Rajesh Varma. Unreconciled difference of ₹100.00 Lakhs.]

NOTE 34: CONTINGENT LIABILITIES AND COMMITMENTS (Ind AS 37)
--------------------------------------------------------------------------------
[SECTION INCOMPLETE IN DRAFT:
Note 34 title exists with sentence: "Claims against the Company not acknowledged as debts include Income Tax appeals pending before ITAT for AY 2021-22 and Department of Telecommunications AGR demand under reassessment."
No numerical quantification or potential financial impact is provided in Note 34 table, violating Ind AS 37 para 86 disclosure mandate.]

NOTE 35: FINANCIAL INSTRUMENTS - RISK MANAGEMENT (Ind AS 107 & Ind AS 109)
--------------------------------------------------------------------------------
The company's principal financial liabilities comprise borrowings, lease liabilities, and trade payables.
[SECTION MISSING: No Interest Rate Sensitivity Analysis or Foreign Currency Liquidity Maturity Bucket Table included in the draft notes to accounts.]`
  },
  {
    id: 'bharat-energy-fy25',
    title: 'Bharat Green Power & Renewables Ltd.',
    companyName: 'Bharat Green Power & Renewables Limited',
    period: 'FY 2024-25 (Ended 31st March 2025)',
    framework: 'Ind AS (Schedule III Division II)',
    description: 'Renewable energy producer with Ind AS 116 Lease amortization errors, Capitalized Borrowing Costs gaps (Ind AS 23/16), and Cash Flow statement financing activity mismatch.',
    knownIssuesSummary: '4 Numerical Mismatches (PPE Additions vs Cash Flow, Lease liability rollforward, Depreciation note casting), 3 Missing Disclosures (Ind AS 23 borrowing costs, Ind AS 116 variable lease payments, Ind AS 19 actuarial assumptions).',
    previewSnippet: `BALANCE SHEET AS AT MARCH 31, 2025 (₹ in Crores)
Property, Plant & Equipment (Note 3): ₹845.50 Cr
Right of Use Assets (Note 4): ₹124.00 Cr
Capital Work in Progress (Note 5): ₹65.20 Cr
Long Term Borrowings (Note 14): ₹410.00 Cr
P&L Finance Cost (Note 25): ₹38.40 Cr
Cash Flow: Purchase of PPE reported as ₹72.50 Cr (vs Note 3 gross additions of ₹94.00 Cr)`,
    fullText: `BHARAT GREEN POWER & RENEWABLES LIMITED
CIN: L40106MH2014PLC258901
STANDALONE FINANCIAL STATEMENTS FOR THE YEAR ENDED MARCH 31, 2025
(Currency: Indian Rupees in Crores)

================================================================================
BALANCE SHEET AS AT MARCH 31, 2025
================================================================================
Particulars                                 Note No.   As at 31-Mar-2025   As at 31-Mar-2024
--------------------------------------------------------------------------------
ASSETS
(1) Non-current Assets
   (a) Property, Plant and Equipment            3               845.50              780.00
   (b) Capital Work-in-Progress                 4                65.20               45.00
   (c) Right of Use Assets                      5               124.00              140.00
   (d) Other Intangible Assets                  6                12.50               15.00
   (e) Non-current Financial Assets
       (i) Investments                          7                45.00               45.00
       (ii) Other Financial Assets              8                18.20               14.50
   Total Non-current Assets                                   1,110.40            1,039.50

(2) Current Assets
   (a) Inventories                              9                28.40               22.10
   (b) Trade Receivables                       10                92.50               84.00
   (c) Cash and Cash Equivalents               11                34.60               29.80
   (d) Other Current Assets                    12                19.50               16.20
   Total Current Assets                                         175.00              152.10
TOTAL ASSETS                                                  1,285.40            1,191.60

EQUITY AND LIABILITIES
(1) Equity
   (a) Equity Share Capital                    13               250.00              250.00
   (b) Other Equity                            14               495.40              421.60
   Total Equity                                                 745.40              671.60

(2) Non-current Liabilities
   (a) Borrowings                              15               365.00              380.00
   (b) Lease Liabilities                       16               108.00              122.00
   (c) Deferred Tax Liabilities (Net)          17                32.00               28.00
   Total Non-current Liabilities                                505.00              530.00

(3) Current Liabilities
   (a) Borrowings                              18                45.00               30.00
   (b) Lease Liabilities                       16                16.00               18.00
   (c) Trade Payables                          19
       (i) Total MSME dues                                        8.50                6.20
       (ii) Total Non-MSME dues                                  38.50               32.80
   (d) Other Current Liabilities               20                12.00               11.00
   Total Current Liabilities                                     120.00              98.00
TOTAL EQUITY AND LIABILITIES                                  1,370.40            1,299.60

[CRITICAL AUDIT ERROR:
Balance Sheet Assets Total: ₹1,285.40 Crores.
Balance Sheet Equity + Liabilities: ₹745.40 (Equity) + ₹505.00 (Non-current) + ₹120.00 (Current) = ₹1,370.40 Crores.
Arithmetic Balance Sheet Mismatch of ₹85.00 Crores. The Balance Sheet does not tally!]

================================================================================
STATEMENT OF PROFIT AND LOSS FOR THE YEAR ENDED MARCH 31, 2025
================================================================================
Revenue from Power Generation (Note 21): ₹310.00 Cr
Other Income (Note 22): ₹14.50 Cr
Total Income: ₹324.50 Cr

Expenses:
Employee Benefits Expense (Note 23): ₹32.00 Cr
Finance Costs (Note 24): ₹38.40 Cr
Depreciation & Amortization (Note 25): ₹64.50 Cr
Operation & Maintenance Expenses (Note 26): ₹98.20 Cr
Total Expenses: ₹233.10 Cr
Profit Before Tax: ₹91.40 Cr
Tax Expense (Current + Deferred): ₹24.00 Cr
Profit for the Year: ₹67.40 Cr

================================================================================
NOTES TO ACCOUNTS & SCHEDULES
================================================================================

NOTE 3: PROPERTY, PLANT AND EQUIPMENT (PPE)
--------------------------------------------------------------------------------
Gross Block as at 1-Apr-2024: ₹920.00 Cr
Additions during the year: ₹94.00 Cr
Disposals during the year: ₹(10.00) Cr
Gross Block as at 31-Mar-2025: ₹1,004.00 Cr

Accumulated Depreciation as at 1-Apr-2024: ₹140.00 Cr
Depreciation Charge for the year: ₹48.50 Cr
Depreciation on Disposals: ₹(2.00) Cr
Accumulated Depreciation as at 31-Mar-2025: ₹186.50 Cr (Should be 140 + 48.50 - 2.00 = 186.50 Cr)
Net Carrying Value as at 31-Mar-2025: ₹817.50 Cr (1,004.00 - 186.50 = 817.50 Cr)

[AUDIT MISMATCH:
Balance Sheet PPE line item reports ₹845.50 Cr. Note 3 Net Block computes to ₹817.50 Cr. Discrepancy of ₹28.00 Crores.]

NOTE 24: FINANCE COSTS & CAPITALIZED BORROWING COSTS (Ind AS 23)
--------------------------------------------------------------------------------
Interest on Term Loans: ₹42.00 Cr
Interest on Working Capital: ₹4.40 Cr
Total Finance Cost incurred: ₹46.40 Cr
Less: Interest capitalized to CWIP: Not stated in Note 24 table (P&L shows Net Finance Cost of ₹38.40 Cr, implying ₹8.00 Cr capitalization, but no capitalization rate or accounting policy note provided as required under Ind AS 23.26).

NOTE 27: CASH FLOW STATEMENT DISCLOSURE CHECK
--------------------------------------------------------------------------------
Cash Flow from Investing Activities:
"Purchase of Property, Plant & Equipment (including CWIP): ₹72.50 Crores"
Cross-reference check: PPE additions (Note 3) ₹94.00 Cr + CWIP additions (Note 4) ₹20.20 Cr = ₹114.20 Cr. Even adjusting for trade payables for capital goods, ₹41.70 Cr difference is unexplained.`
  },
  {
    id: 'zenith-consumer-fy25',
    title: 'Zenith Consumer Foods Ltd. (Compliant Benchmark)',
    companyName: 'Zenith Consumer Foods Limited',
    period: 'FY 2024-25 (Ended 31st March 2025)',
    framework: 'Ind AS (Schedule III Division II)',
    description: 'High-compliance FMCG financial statement draft with comprehensive Ind AS 115, Ind AS 116, Ind AS 24, and Ind AS 107 notes for verification.',
    knownIssuesSummary: 'High Compliance Score (0 critical discrepancies, full Ind AS compliance, minor rounding tolerance of ₹0.01 Lakh).',
    previewSnippet: `BALANCE SHEET AS AT MARCH 31, 2025 (₹ in Lakhs)
Total Assets: ₹88,420.00 Lakhs
Total Equity & Liabilities: ₹88,420.00 Lakhs (Fully tallied)
Revenue from Operations (Note 21): ₹74,500.00 Lakhs
PBT: ₹9,450.00 Lakhs | PAT: ₹7,080.00 Lakhs
All Ind AS 1 to Ind AS 116 schedules reconciled to primary statements.`,
    fullText: `ZENITH CONSUMER FOODS LIMITED
CIN: L15400MH2010PLC201948
FINANCIAL STATEMENTS FOR THE YEAR ENDED MARCH 31, 2025
(₹ in Lakhs)

BALANCE SHEET AS AT MARCH 31, 2025
ASSETS
Non-current Assets:
Property, Plant and Equipment (Note 3): ₹34,200.00
Right of Use Assets (Note 4): ₹6,400.00
Capital Work-in-Progress (Note 5): ₹2,100.00
Intangible Assets (Note 6): ₹1,800.00
Financial Assets:
- Investments (Note 7): ₹4,500.00
- Other Financial Assets (Note 8): ₹1,250.00
Deferred Tax Assets (Net) (Note 9): ₹1,120.00
Total Non-current Assets: ₹51,370.00

Current Assets:
Inventories (Note 10): ₹14,200.00
Trade Receivables (Note 11): ₹15,400.00
Cash and Cash Equivalents (Note 12): ₹4,850.00
Other Financial Assets (Note 13): ₹950.00
Other Current Assets (Note 14): ₹1,650.00
Total Current Assets: ₹37,050.00
TOTAL ASSETS: ₹88,420.00

EQUITY AND LIABILITIES
Equity:
Equity Share Capital (Note 15): ₹15,000.00
Other Equity (Note 16): ₹42,620.00
Total Equity: ₹57,620.00

Non-current Liabilities:
Financial Liabilities:
- Borrowings (Note 17): ₹12,000.00
- Lease Liabilities (Note 18): ₹4,800.00
Provisions (Note 19): ₹1,450.00
Total Non-current Liabilities: ₹18,250.00

Current Liabilities:
Financial Liabilities:
- Borrowings (Note 20): ₹3,500.00
- Lease Liabilities (Note 18): ₹1,600.00
- Trade Payables:
  * MSME (Note 21): ₹1,450.00
  * Others (Note 21): ₹4,800.00
Other Current Liabilities (Note 22): ₹1,200.00
Total Current Liabilities: ₹12,550.00
TOTAL EQUITY AND LIABILITIES: ₹88,420.00

STATEMENT OF PROFIT AND LOSS FOR THE YEAR ENDED MARCH 31, 2025
Revenue from Operations (Note 23): ₹74,500.00
Other Income (Note 24): ₹1,200.00
Total Income: ₹75,700.00
Expenses:
Cost of materials consumed (Note 25): ₹38,400.00
Employee benefits expense (Note 26): ₹11,200.00
Finance costs (Note 27): ₹1,850.00
Depreciation and amortization expense (Note 28): ₹4,800.00
Other expenses (Note 29): ₹10,000.00
Total Expenses: ₹66,250.00
Profit Before Tax: ₹9,450.00
Tax Expense: ₹2,370.00
Profit for the year: ₹7,080.00

NOTES DISCLOSURE SUMMARY:
- Note 30: Related Party Disclosures (Ind AS 24) - KMP Remuneration ₹540.00 Lakhs fully matches P&L line item and remuneration schedule.
- Note 31: Contingent Liabilities (Ind AS 37) - Tax appeals of ₹180.00 Lakhs quantified with legal assessment.
- Note 32: Financial Risk Management (Ind AS 107/109) - Sensitivity analysis for interest rate (+/- 50 bps: impact ₹60.00 Lakhs) and foreign exchange provided.
- Note 33: Revenue from Contracts with Customers (Ind AS 115) - Disaggregated revenue by product line and geography with contract liability reconciliation included.`
  }
];
