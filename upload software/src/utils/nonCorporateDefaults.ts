import { DepreciationAssetItem, NoteToAccountItem } from '../types/accounting';

/**
 * Standard default depreciation schedule items for Non-Corporate entities.
 * Columns: Gross Block, Rate of Depreciation, Accumulated Depreciation,
 * Depreciation of the Year, Closing Value, and Closing of Previous Year.
 */
export const DEFAULT_DEPRECIATION_ASSETS: DepreciationAssetItem[] = [
  {
    id: 'depr-1',
    assetName: 'Commercial Shop Premises & Showroom',
    category: 'Building / Premises',
    grossBlock: 2400000,
    depreciationRate: 10,
    accumulatedDepreciation: 240000,
    depreciationForTheYear: 216000,
    closingValue: 1944000,
    previousYearClosing: 2160000,
    notes: 'Immovable commercial showroom property; WDV basis @ 10%',
  },
  {
    id: 'depr-2',
    assetName: 'Plant & Packaging Machinery',
    category: 'Plant & Machinery',
    grossBlock: 1200000,
    depreciationRate: 15,
    accumulatedDepreciation: 250000,
    depreciationForTheYear: 142500,
    closingValue: 807500,
    previousYearClosing: 950000,
    notes: 'Textile processing and packaging machinery; WDV basis @ 15%',
  },
  {
    id: 'depr-3',
    assetName: 'Delivery Commercial Van (Tata Ace)',
    category: 'Vehicles',
    grossBlock: 700000,
    depreciationRate: 15,
    accumulatedDepreciation: 150000,
    depreciationForTheYear: 82500,
    closingValue: 467500,
    previousYearClosing: 550000,
    notes: 'Commercial delivery vehicle; WDV basis @ 15%',
  },
  {
    id: 'depr-4',
    assetName: 'Computer Systems, Servers & Printers',
    category: 'Computers & IT Equipment',
    grossBlock: 250000,
    depreciationRate: 40,
    accumulatedDepreciation: 105000,
    depreciationForTheYear: 58000,
    closingValue: 87000,
    previousYearClosing: 145000,
    notes: 'Office computing hardware; WDV basis @ 40%',
  },
  {
    id: 'depr-5',
    assetName: 'Furniture, Fittings & Office Fixtures',
    category: 'Furniture & Fixtures',
    grossBlock: 180000,
    depreciationRate: 10,
    accumulatedDepreciation: 30000,
    depreciationForTheYear: 15000,
    closingValue: 135000,
    previousYearClosing: 150000,
    notes: 'Showroom interior racks, counters and air conditioning; WDV @ 10%',
  },
];

/**
 * Standard Notes to Accounts applicable to Non-Corporate entities
 * (Sole Proprietorships, Partnership Firms, LLPs, AOPs/BOIs)
 * under ICAI Technical Guides & Accounting Standards (AS).
 */
export const DEFAULT_STANDARD_NOTES: NoteToAccountItem[] = [
  {
    id: 'note-1',
    noteNumber: 1,
    title: 'Entity Information & Basis of Preparation',
    category: 'POLICIES',
    isActive: true,
    isStandard: true,
    content: `1.1 Entity Information:
The entity is a non-corporate enterprise carrying on business activities primarily in trading, manufacturing, and related commercial operations. The principal place of business and administrative office is situated as stated in the general particulars of the financial statements.

1.2 Basis of Preparation of Financial Statements:
The financial statements have been prepared under the historical cost convention on an accrual basis of accounting (unless stated otherwise) in accordance with Generally Accepted Accounting Principles (GAAP) in India and the mandatory Accounting Standards (AS) issued by the Institute of Chartered Accountants of India (ICAI) as applicable to Non-Corporate Entities (Level II / Level III / Level IV enterprises).

1.3 Going Concern:
The accounting policies have been consistently applied by the entity and are consistent with those used in the previous year. The management is of the considered opinion that the entity has adequate resources to continue its operations for the foreseeable future and accordingly financial statements are drawn on a going concern basis.`,
  },
  {
    id: 'note-2',
    noteNumber: 2,
    title: 'Significant Accounting Policies (AS 1 to AS 29)',
    category: 'POLICIES',
    isActive: true,
    isStandard: true,
    content: `(a) Property, Plant & Equipment (Fixed Assets) (AS 10 Revised):
Property, Plant & Equipment are stated at cost of acquisition less accumulated depreciation and accumulated impairment losses, if any. Cost includes purchase price, non-refundable taxes, duties, freight, insurance, and all directly attributable expenses incurred to bring the assets to their working condition and location for their intended commercial use.

(b) Depreciation (AS 10):
Depreciation on Property, Plant & Equipment is provided on Written Down Value (WDV) method at the rates and in the manner specified under the Income Tax Act, 1961 / based on the estimated economic useful lives evaluated by the Management. Depreciation on additions/deletions during the year is calculated on a pro-rata basis from/up to the date of acquisition/disposal.

(c) Inventories Valuation (AS 2):
Inventories comprising Raw Materials, Work-in-Progress, Stock-in-Trade (Finished Goods), and Consumable Stores are valued at the lower of Cost or Net Realizable Value (NRV). Cost is determined on First-In-First-Out (FIFO) / Weighted Average basis. Stock quantities and valuation are physically verified and certified by the Management at the close of the financial year.

(d) Revenue Recognition (AS 9):
Revenue from the sale of goods is recognized when significant risks and rewards of ownership have been transferred to the buyer, usually coinciding with delivery/dispatch of goods, and is recorded net of Goods and Services Tax (GST), trade discounts, and sales returns. Revenue from services is recognized as and when services are rendered. Interest income is recognized on a time-proportion basis.

(e) Employee Benefits (AS 15):
Short-term employee benefits including salaries, wages, bonus, and staff welfare are charged to the Profit & Loss Statement on an undiscounted basis during the period in which the employees render related service.

(f) Borrowing Costs (AS 16):
Borrowing costs directly attributable to the acquisition or construction of qualifying assets are capitalized as part of the cost of such assets. All other borrowing costs and finance charges are expensed in the period in which they are incurred.

(g) Taxes on Income (AS 22):
Provision for Current Tax is made in accordance with the provisions of the Income Tax Act, 1961. Non-corporate entities eligible for standard exemptions as Level II/III/IV entities have accounted for taxes on income on actual liability basis.

(h) Provisions, Contingent Liabilities & Contingent Assets (AS 29):
Provisions are recognized when there is a present obligation as a result of past events for which it is probable that an outflow of economic benefits will be required. Contingent liabilities are not recognized in the books of account but are disclosed by way of notes.`,
  },
  {
    id: 'note-3',
    noteNumber: 3,
    title: 'Capital Account & Terms of Constitution',
    category: 'CAPITAL',
    isActive: true,
    isStandard: true,
    content: `3.1 In case of Partnership Firm / LLP:
(a) Profit & Loss Sharing: The net profit or loss for the financial year after providing for partner remuneration and interest on capital has been credited/debited to the respective partners' capital accounts in the profit sharing ratio specified in the Partnership Deed / LLP Agreement.
(b) Interest on Capital: Interest on partner capital balances has been credited at 12% per annum (or the rate mutually agreed in terms of the Partnership Deed) in strict compliance with Section 40(b) of the Income Tax Act, 1961.
(c) Partner Remuneration: Remuneration to working partners has been authorized by the Partnership Deed and computed in accordance with the statutory limits prescribed under Section 40(b)(v) of the Income Tax Act, 1961.
(d) Drawings: Personal withdrawals and drawings made by partners during the year are debited directly to their respective capital/current accounts.

3.2 In case of Sole Proprietorship:
The entire net profit/loss for the financial year has been transferred to the Proprietor's Capital Account. Personal drawings, life insurance premiums, and personal income tax payments have been debited directly to the Capital Account.`,
  },
  {
    id: 'note-4',
    noteNumber: 4,
    title: 'Borrowings & Security Particulars',
    category: 'LOANS',
    isActive: true,
    isStandard: true,
    content: `4.1 Secured Borrowings:
(a) Working Capital / Cash Credit facilities availed from scheduled banks are secured by way of hypothecation of current assets comprising inventories and trade receivables.
(b) The credit facilities are further secured by collateral mortgage of commercial/immovable property and personal guarantees of the Proprietor / Partners.
(c) Term Loans and vehicle loans are secured by exclusive hypothecation charge over the respective vehicles / equipment financed.

4.2 Unsecured Loans:
Unsecured loans received from friends, relatives of partners, and associated parties are interest-bearing or interest-free as agreed upon mutually, and are repayable on demand. Confirmations of balances have been obtained.`,
  },
  {
    id: 'note-5',
    noteNumber: 5,
    title: 'Disclosures under the MSMED Act, 2006',
    category: 'MSME',
    isActive: true,
    isStandard: true,
    content: `Disclosures required under Section 22 of the Micro, Small and Medium Enterprises Development (MSMED) Act, 2006:

(a) Principal amount remaining unpaid to suppliers registered under the MSMED Act as at 31st March: ₹ Nil (Previous Year: ₹ Nil).
(b) Interest due thereon remaining unpaid as at 31st March: ₹ Nil (Previous Year: ₹ Nil).
(c) The amount of interest paid by the buyer in terms of Section 16 along with the payments made beyond the appointed day: ₹ Nil.
(d) The amount of interest due and payable for the period of delay in making payment: ₹ Nil.
(e) The amount of further interest remaining due and payable even in succeeding years: ₹ Nil.

Note: The identification of micro, small, and medium enterprises is based on information received and compiled by the management from vendors on a best-effort basis.`,
  },
  {
    id: 'note-6',
    noteNumber: 6,
    title: 'Trade Receivables, Payables & Balances Confirmation',
    category: 'RECEIVABLES_PAYABLES',
    isActive: true,
    isStandard: true,
    content: `6.1 Balances Subject to Confirmation:
Balances appearing under Trade Receivables (Sundry Debtors), Trade Payables (Sundry Creditors), Loans, Advances, and Security Deposits are subject to formal confirmation, reconciliation, and consequential adjustments, if any. However, in the opinion of the management, all balances are stated at their realizable value in the ordinary course of business.

6.2 Trade Receivables Recovery:
All trade receivables are considered good and recoverable by the management. No debts are classified as doubtful, and therefore no specific provision for bad and doubtful debts has been deemed necessary for the current financial year.`,
  },
  {
    id: 'note-7',
    noteNumber: 7,
    title: 'Contingent Liabilities & Commitments (AS 29)',
    category: 'CONTINGENT',
    isActive: true,
    isStandard: true,
    content: `Contingent liabilities and commitments not provided for in the books of account:

(a) Claims against the entity not acknowledged as debts: ₹ Nil (Previous Year: ₹ Nil).
(b) Disputed statutory demands (GST / Income Tax / VAT / Customs) under appeal: ₹ Nil (Previous Year: ₹ Nil).
(c) Guarantees given by bankers on behalf of the entity: ₹ Nil (Previous Year: ₹ Nil).
(d) Estimated amount of contracts remaining to be executed on capital account and not provided for (net of advances): ₹ Nil (Previous Year: ₹ Nil).`,
  },
  {
    id: 'note-8',
    noteNumber: 8,
    title: 'Related Party Disclosures (AS 18)',
    category: 'RELATED_PARTY',
    isActive: true,
    isStandard: true,
    content: `In accordance with Accounting Standard 18 (AS 18) "Related Party Disclosures":

(a) Key Management Personnel & Owners:
Proprietor / Partners having substantial control and management authority.

(b) Relatives of Key Management Personnel:
Spouses and immediate relatives of Proprietor / Partners.

(c) Enterprises under Common Influence:
Allied proprietary concerns, partnership firms, and private companies wherein partners/proprietor have significant influence.

(d) Summary of Transactions:
Transactions entered with related parties during the year comprise partner remuneration, interest on capital, and commercial rent paid at prevailing fair market values in the ordinary course of business.`,
  },
  {
    id: 'note-9',
    noteNumber: 9,
    title: 'Cash in Hand & Bank Balances Verification',
    category: 'STATUTORY',
    isActive: true,
    isStandard: true,
    content: `9.1 Cash in Hand:
Cash in hand as at 31st March of the financial year has been physically verified and certified by the Management / Proprietor and is supported by daily cash book entries.

9.2 Bank Balances:
Balances held with Scheduled Commercial Banks in Current Accounts, Cash Credit Accounts, and Term Deposit Accounts are reconciled with respective bank statements and certificates of balance obtained as at the year end.`,
  },
  {
    id: 'note-10',
    noteNumber: 10,
    title: 'Previous Year Figures & Rounding Off',
    category: 'STATUTORY',
    isActive: true,
    isStandard: true,
    content: `10.1 Regrouping of Previous Year Figures:
Figures of the previous financial year have been regrouped, rearranged, reclassified, and recasted wherever considered necessary to make them strictly comparable with the current year's presentation and ICAI Non-Corporate reporting formats.

10.2 Rounding Off:
All financial figures presented in the Balance Sheet, Profit & Loss Statement, Schedules, and Notes to Accounts have been rounded off to the nearest Indian Rupee (₹).`,
  },
];
