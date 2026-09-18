import { SourceItem } from '../types';

export const INITIAL_SAMPLE_SOURCES: SourceItem[] = [
  {
    id: 'src-01-26as',
    name: '26AS_Rajinder_Kumar_FY2023-24_AY2024-25.pdf',
    fileType: 'PDF',
    sizeBytes: 428000,
    charCount: 3850,
    preview: 'Annual Tax Statement under Section 203AA of Income Tax Act 1961 for Assessee Sh. Rajinder Kumar PAN: BULPK6349C...',
    text: `--- Page 1 ---
FORM NO. 26AS
Annual Tax Statement under Section 203AA of the Income-tax Act, 1961
Assessment Year: 2024-25 | Financial Year: 2023-24

Taxpayer Profile & Details:
- Assessee Name: Sh. Rajinder Kumar
- PAN: BULPK6349C (Active and Operative)
- Status: Individual / Resident
- Address: 60 Phase 2, Bapu Dham Colony, Sector 26, Chandigarh - 160019
- Current Status of PAN: Operative (Aadhaar linked)

--- Page 2 ---
PART I - Details of Tax Deducted at Source (TDS):
Sr. No. | Name of Deductor | TAN | Section | Total Amount Paid/Credited (Rs.) | Total Tax Deducted (Rs.) | Total TDS Deposited (Rs.)
1 | CSC E-GOVERNANCE SERVICES INDIA LIMITED | DELC11375A | 194C | 3876.88 | 196.00 | 196.00
2 | POINT INDIA NETWORK PRIVATE LIMITED | DELP09821B | 194H | 4210.00 | 210.50 | 210.50
3 | FINO PAYMENTS BANK LIMITED | MUMF04918A | 194H | 6120.16 | 306.00 | 306.00
4 | SPICE MONEY DIGITAL SERVICES | NOIS02319C | 194C | 2145.00 | 107.25 | 107.25
5 | PAYTM PAYMENTS BANK LTD | DELP14902E | 194C | 1230.00 | 26.58 | 26.58

Summary of Total TDS:
- Total Amount Paid / Credited across all 5 Deductors: Rs. 17,582.04
- Total TDS Deducted and Deposited: Rs. 846.33
- Other Sections (Sale of property 194-IA, Virtual digital assets 194S, TCS 206C): Nil / No transactions reported.`,
    createdAt: new Date(Date.now() - 3600000 * 5).toISOString(),
  },
  {
    id: 'src-02-ledger',
    name: 'CSC_and_Banking_Correspondent_Ledger.xlsx',
    fileType: 'XLSX',
    sizeBytes: 198000,
    charCount: 2940,
    preview: 'Daily customer AEPS cash withdrawal and public deposit ledger for Digital Seva Kendra kiosk operations...',
    text: `### Sheet: CSP Customer Footfall & Cash Rotation Summary
Date | Total Public Footfall | AEPS Gross Cash Dispensed (Rs.) | Margin Commission (Rs.) | Net Retention (%)
April 2023 | 840 Citizens | 28,45,000.00 | 4,260.00 | 0.15%
May 2023 | 910 Citizens | 31,10,000.00 | 4,665.00 | 0.15%
June 2023 | 790 Citizens | 26,80,000.00 | 4,020.00 | 0.15%
July 2023 | 825 Citizens | 27,95,000.00 | 4,192.50 | 0.15%

Key Takeaway & Operational Verification:
1. Gross bank account credits represent daily revolving public funds where citizens withdraw cash via Aadhaar biometric terminal and the bank replenishes the merchant account.
2. The taxpayer retains merely 0.15% to 0.20% as digital kiosk commission.
3. Total business turnover is strictly confined to commission income documented in Form 26AS.`,
    createdAt: new Date(Date.now() - 3600000 * 3).toISOString(),
  },
  {
    id: 'src-03-briefing',
    name: 'Written_Submissions_and_Case_Laws.docx',
    fileType: 'DOCX',
    sizeBytes: 152000,
    charCount: 2150,
    preview: 'Legal grounds of appeal before Commissioner of Income Tax (Appeals) on presumptive taxation under Section 44AD and fiduciary capacity...',
    text: `--- Page 1 ---
CIT(A) APPEAL SUBMISSION GROUNDS & PRECEDENTS

Ground 1: Fiduciary Capacity of Customer Service Point (CSP) / Kiosk Operator
- The appellant operates as a Business Correspondent / Kiosk operator providing essential digital banking to rural/urban citizens.
- Cash deposited in bank accounts is sourced from daily customer ATM withdrawals and utility collections, not unexplained income under Section 69A.

--- Page 2 ---
Ground 2: Judicial Precedents on Peak Credit and Gross vs Net Business Turnover
- ITAT Delhi Bench in ITO vs. Kiosk Operators: Cash turnover of banking correspondents cannot be treated as undisclosed turnover.
- Presumptive taxation under Section 44AD or 44ADA applies solely on the net commission earned (Rs. 17,582.04).`,
    createdAt: new Date(Date.now() - 3600000 * 1).toISOString(),
  },
];

