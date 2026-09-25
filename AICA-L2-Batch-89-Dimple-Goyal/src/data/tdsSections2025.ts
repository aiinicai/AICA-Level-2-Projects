/**
 * Income Tax Act - Comprehensive TDS & TCS Sections Directory for FY 2026-27 & AY 2027-28
 * Incorporates all amendments under Finance Acts and statutory provisions effective for FY 2026-27.
 */

export interface TDSSection2025 {
  section: string;
  name: string;
  natureOfPayment: string;
  rateIndHuf: number; // percentage
  rateOthers: number; // percentage
  thresholdLimit: number; // in INR
  thresholdType: 'Single' | 'Annual' | 'Monthly' | 'Excess Over Threshold' | 'Per Transaction';
  effectiveDate: string;
  category: 
    | 'Contractor & Transport'
    | 'Professional & Technical'
    | 'Rent'
    | 'Commission & Brokerage'
    | 'Interest'
    | 'Purchase & Sale of Goods'
    | 'Partners & Firms'
    | 'Assets & Immovable Property'
    | 'E-Commerce & Digital'
    | 'Salary & Benefits'
    | 'Other Special Rates';
  keyNotes: string;
  statutoryReference: string;
}

export const TDS_SECTIONS_2025: TDSSection2025[] = [
  // 1. Contractor & Sub-contractor
  {
    section: '194C',
    name: 'Payments to Contractors & Sub-contractors',
    natureOfPayment: 'Carrying out any work (including supply of labour) pursuant to a contract',
    rateIndHuf: 1.0,
    rateOthers: 2.0,
    thresholdLimit: 30000,
    thresholdType: 'Single',
    effectiveDate: 'Standard (FY 2026-27 / AY 2027-28)',
    category: 'Contractor & Transport',
    keyNotes: 'Threshold: ₹30,000 for single contract or ₹1,00,000 aggregate in FY. 0% for goods carriage transporter owning up to 10 goods carriages upon PAN declaration.',
    statutoryReference: 'Section 194C, Income-tax Act, 1961'
  },

  // 2. Professional & Technical Services
  {
    section: '194J(a)',
    name: 'Fees for Professional Services & Royalty',
    natureOfPayment: 'Legal, medical, engineering, architectural, accountancy, or other notified professions and general royalty',
    rateIndHuf: 10.0,
    rateOthers: 10.0,
    thresholdLimit: 30000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Professional & Technical',
    keyNotes: 'Threshold: ₹30,000 per financial year for each category. Includes non-compete fees.',
    statutoryReference: 'Section 194J(1), Income-tax Act, 1961'
  },
  {
    section: '194J(b)',
    name: 'Fees for Technical Services (FTS) & Call Centers',
    natureOfPayment: 'Fees for Technical Services (FTS), royalty for sale/distribution of cinematographic films, or call center operation',
    rateIndHuf: 2.0,
    rateOthers: 2.0,
    thresholdLimit: 30000,
    thresholdType: 'Annual',
    effectiveDate: 'Rationalized Rate (2%)',
    category: 'Professional & Technical',
    keyNotes: 'Rationalized rate of 2% for FTS and call centers to eliminate litigation between 194C and 194J.',
    statutoryReference: 'Section 194J Proviso, Income-tax Act, 1961'
  },
  {
    section: '194J(c)',
    name: 'Director Remuneration / Sitting Fees',
    natureOfPayment: 'Remuneration, fees or commission paid to a director (other than employee salary u/s 192)',
    rateIndHuf: 10.0,
    rateOthers: 10.0,
    thresholdLimit: 0,
    thresholdType: 'Single',
    effectiveDate: 'Standard',
    category: 'Professional & Technical',
    keyNotes: 'No minimum threshold — TDS applies on all non-salary director fees and sitting fees at 10%.',
    statutoryReference: 'Section 194J(1)(ba), Income-tax Act, 1961'
  },

  // 3. Purchase of Goods
  {
    section: '194Q',
    name: 'TDS on Purchase of Goods',
    natureOfPayment: 'Payment for purchase of goods from resident seller by buyer whose turnover > ₹10 Crore in preceding FY',
    rateIndHuf: 0.1,
    rateOthers: 0.1,
    thresholdLimit: 5000000,
    thresholdType: 'Excess Over Threshold',
    effectiveDate: 'Standard',
    category: 'Purchase & Sale of Goods',
    keyNotes: '0.1% on value exceeding ₹50 Lakhs in a financial year. Higher rate of 5% if seller PAN is not furnished (Sec 206AA). Takes precedence over TCS u/s 206C(1H).',
    statutoryReference: 'Section 194Q, Income-tax Act, 1961'
  },
  {
    section: '206C(1H)',
    name: 'TCS on Sale of Goods',
    natureOfPayment: 'Receipt of consideration by seller (turnover > ₹10 Cr) on sale of goods',
    rateIndHuf: 0.1,
    rateOthers: 0.1,
    thresholdLimit: 5000000,
    thresholdType: 'Excess Over Threshold',
    effectiveDate: 'Standard',
    category: 'Purchase & Sale of Goods',
    keyNotes: 'Collected by seller on receipt basis on amount exceeding ₹50 Lakhs. Not applicable if buyer is liable to deduct TDS u/s 194Q.',
    statutoryReference: 'Section 206C(1H), Income-tax Act, 1961'
  },

  // 4. Rent
  {
    section: '194I(a)',
    name: 'Rent for Plant, Machinery or Equipment',
    natureOfPayment: 'Lease or hire charges for plant, machinery or industrial equipment',
    rateIndHuf: 2.0,
    rateOthers: 2.0,
    thresholdLimit: 240000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Rent',
    keyNotes: '2% rate where annual rent exceeds ₹2,40,000. Separate limit from land & building rent.',
    statutoryReference: 'Section 194I(a), Income-tax Act, 1961'
  },
  {
    section: '194I(b)',
    name: 'Rent for Land, Building or Furniture',
    natureOfPayment: 'Rent paid for use of land, commercial/residential building, or furniture and fittings',
    rateIndHuf: 10.0,
    rateOthers: 10.0,
    thresholdLimit: 240000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Rent',
    keyNotes: '10% rate where annual rent exceeds ₹2,40,000 for the financial year.',
    statutoryReference: 'Section 194I(b), Income-tax Act, 1961'
  },
  {
    section: '194IB',
    name: 'Rent Paid by Individuals & HUF (Not liable to Tax Audit)',
    natureOfPayment: 'Rent of residential or commercial property paid by non-audit individuals/HUF',
    rateIndHuf: 2.0,
    rateOthers: 2.0,
    thresholdLimit: 50000,
    thresholdType: 'Monthly',
    effectiveDate: 'Reduced from 5% to 2% w.e.f. October 1, 2024 (Finance Act 2024)',
    category: 'Rent',
    keyNotes: 'Applicable where rent exceeds ₹50,000/month. Deducted once per year in last month. Rate rationalized to 2% by Finance (No. 2) Act, 2024.',
    statutoryReference: 'Section 194IB, Income-tax Act, 1961'
  },

  // 5. Commission & Brokerage
  {
    section: '194H',
    name: 'Commission or Brokerage',
    natureOfPayment: 'Commission (other than insurance commission) or brokerage for services rendered',
    rateIndHuf: 2.0,
    rateOthers: 2.0,
    thresholdLimit: 15000,
    thresholdType: 'Annual',
    effectiveDate: 'Reduced from 5% to 2% w.e.f. October 1, 2024 (Finance Act 2024)',
    category: 'Commission & Brokerage',
    keyNotes: 'Rate slashed from 5% down to 2% w.e.f. Oct 1, 2024 to ease liquidity for SMEs. Annual threshold: ₹15,000.',
    statutoryReference: 'Section 194H, Income-tax Act, 1961'
  },
  {
    section: '194G',
    name: 'Commission on Sale of Lottery Tickets',
    natureOfPayment: 'Commission, remuneration or prize on stocking, distributing, or purchasing lottery tickets',
    rateIndHuf: 2.0,
    rateOthers: 2.0,
    thresholdLimit: 15000,
    thresholdType: 'Annual',
    effectiveDate: 'Reduced from 5% to 2% w.e.f. October 1, 2024',
    category: 'Commission & Brokerage',
    keyNotes: 'Rate rationalized to 2% under Budget 2024. Threshold: ₹15,000.',
    statutoryReference: 'Section 194G, Income-tax Act, 1961'
  },
  {
    section: '194D',
    name: 'Insurance Commission',
    natureOfPayment: 'Remuneration or reward for soliciting or procuring insurance business',
    rateIndHuf: 5.0,
    rateOthers: 10.0,
    thresholdLimit: 15000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Commission & Brokerage',
    keyNotes: '5% for resident individuals, 10% for corporate entities. Annual threshold: ₹15,000.',
    statutoryReference: 'Section 194D, Income-tax Act, 1961'
  },

  // 6. Partners & Firms (New Budget 2024 Provision)
  {
    section: '194T',
    name: 'Payments to Partners by Partnership Firm / LLP',
    natureOfPayment: 'Salary, remuneration, commission, bonus or interest paid or credited to partners',
    rateIndHuf: 10.0,
    rateOthers: 10.0,
    thresholdLimit: 20000,
    thresholdType: 'Annual',
    effectiveDate: 'Enacted under Finance Act (Applicable for FY 2026-27 / AY 2027-28)',
    category: 'Partners & Firms',
    keyNotes: 'Newly enacted in Budget 2024 w.e.f. April 1, 2025! Firm/LLP must deduct 10% TDS on any salary, interest or bonus to partners where aggregate exceeds ₹20,000 in FY.',
    statutoryReference: 'Section 194T, Income-tax Act, 1961 (Inserted by Finance Act 2024)'
  },

  // 7. Immovable Property & Assets
  {
    section: '194IA',
    name: 'TDS on Transfer of Immovable Property',
    natureOfPayment: 'Consideration for transfer of any immovable property (other than agricultural land)',
    rateIndHuf: 1.0,
    rateOthers: 1.0,
    thresholdLimit: 5000000,
    thresholdType: 'Single',
    effectiveDate: 'Clarified in Finance Act 2024',
    category: 'Assets & Immovable Property',
    keyNotes: '1% on consideration or stamp duty value (higher). Finance Act 2024 clarified threshold applies to aggregate property consideration even across multiple buyers/sellers.',
    statutoryReference: 'Section 194IA, Income-tax Act, 1961'
  },
  {
    section: '194LA',
    name: 'Compensation on Acquisition of Immovable Property',
    natureOfPayment: 'Compensation on compulsory acquisition of certain immovable property',
    rateIndHuf: 10.0,
    rateOthers: 10.0,
    thresholdLimit: 250000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Assets & Immovable Property',
    keyNotes: '10% on compensation exceeding ₹2,50,000.',
    statutoryReference: 'Section 194LA, Income-tax Act, 1961'
  },

  // 8. Individual / HUF Special Contract Payments
  {
    section: '194M',
    name: 'Payments to Contractors & Professionals by Individuals/HUF',
    natureOfPayment: 'Sums paid by individuals/HUF (not liable to audit) for contractual work or professional fees',
    rateIndHuf: 2.0,
    rateOthers: 2.0,
    thresholdLimit: 5000000,
    thresholdType: 'Annual',
    effectiveDate: 'Reduced from 5% to 2% w.e.f. October 1, 2024 (Finance Act 2024)',
    category: 'Contractor & Transport',
    keyNotes: 'Applies to high-value payments exceeding ₹50 Lakhs in FY. Rate reduced from 5% to 2% to ease compliance burden.',
    statutoryReference: 'Section 194M, Income-tax Act, 1961'
  },

  // 9. E-Commerce & Virtual Digital Assets
  {
    section: '194O',
    name: 'TDS by E-Commerce Operator on Participant Sales',
    natureOfPayment: 'Gross amount of sales of goods or provision of services facilitated via e-commerce platform',
    rateIndHuf: 0.1,
    rateOthers: 0.1,
    thresholdLimit: 500000,
    thresholdType: 'Annual',
    effectiveDate: 'Reduced from 1% to 0.1% w.e.f. October 1, 2024 (Finance Act 2024)',
    category: 'E-Commerce & Digital',
    keyNotes: 'Massive tax relief: Rate slashed from 1% to 0.1% effective Oct 1, 2024. Exemption threshold of ₹5 Lakhs for resident Individual/HUF furnishing PAN.',
    statutoryReference: 'Section 194O, Income-tax Act, 1961'
  },
  {
    section: '194S',
    name: 'TDS on Transfer of Virtual Digital Asset (Crypto/NFT)',
    natureOfPayment: 'Payment for transfer of Virtual Digital Assets (cryptocurrency, tokens, NFTs)',
    rateIndHuf: 1.0,
    rateOthers: 1.0,
    thresholdLimit: 50000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'E-Commerce & Digital',
    keyNotes: '1% on consideration. Threshold is ₹50,000 for specified persons or ₹10,000 for others.',
    statutoryReference: 'Section 194S, Income-tax Act, 1961'
  },

  // 10. Interest
  {
    section: '194A',
    name: 'Interest other than Interest on Securities',
    natureOfPayment: 'Interest on bank deposits, loans, corporate deposits, advances, NBFC interest',
    rateIndHuf: 10.0,
    rateOthers: 10.0,
    thresholdLimit: 40000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Interest',
    keyNotes: 'Threshold: ₹40,000 for banks/co-op societies (₹50,000 for senior citizens); ₹5,000 for other loans/corporate deposits.',
    statutoryReference: 'Section 194A, Income-tax Act, 1961'
  },

  // 11. Perks & Business Benefits
  {
    section: '194R',
    name: 'TDS on Benefit or Perquisite in Business / Profession',
    natureOfPayment: 'Any benefit or perquisite arising from business or exercise of a profession (cash or kind)',
    rateIndHuf: 10.0,
    rateOthers: 10.0,
    thresholdLimit: 20000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Salary & Benefits',
    keyNotes: '10% TDS on business incentives, dealer gifts, conferences, or promotional perks exceeding ₹20,000 in FY. Payer must ensure tax is deducted even if benefit is in kind.',
    statutoryReference: 'Section 194R, Income-tax Act, 1961'
  },

  // 12. Cash Withdrawal
  {
    section: '194N',
    name: 'TDS on Cash Withdrawals from Banks',
    natureOfPayment: 'Cash withdrawal exceeding ₹1 Crore in aggregate during the financial year from bank/post office',
    rateIndHuf: 2.0,
    rateOthers: 2.0,
    thresholdLimit: 10000000,
    thresholdType: 'Excess Over Threshold',
    effectiveDate: 'Standard',
    category: 'Other Special Rates',
    keyNotes: '2% on cash withdrawal above ₹1 Crore. For non-filers of ITR (3 preceding years), threshold is ₹20 Lakhs (2% up to 1 Cr, 5% above 1 Cr).',
    statutoryReference: 'Section 194N, Income-tax Act, 1961'
  },

  // 13. Life Insurance & NSS
  {
    section: '194DA',
    name: 'Maturity / Payment of Life Insurance Policy',
    natureOfPayment: 'Payment under life insurance policy including bonus which is not exempt u/s 10(10D)',
    rateIndHuf: 5.0,
    rateOthers: 5.0,
    thresholdLimit: 100000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Other Special Rates',
    keyNotes: '5% on the net taxable income component (gross payout less aggregate premiums paid) if exceeding ₹1,00,000.',
    statutoryReference: 'Section 194DA, Income-tax Act, 1961'
  },
  {
    section: '194EE',
    name: 'Payment in respect of Deposit under NSS',
    natureOfPayment: 'Payment out of National Savings Scheme account with interest',
    rateIndHuf: 10.0,
    rateOthers: 10.0,
    thresholdLimit: 2500,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Other Special Rates',
    keyNotes: '10% on payments exceeding ₹2,500.',
    statutoryReference: 'Section 194EE, Income-tax Act, 1961'
  },

  // 14. Salary
  {
    section: '192',
    name: 'TDS on Salary',
    natureOfPayment: 'Estimated annual income of employee chargeable under the head "Salaries"',
    rateIndHuf: 0, // Slab rates
    rateOthers: 0,
    thresholdLimit: 300000,
    thresholdType: 'Annual',
    effectiveDate: 'New Tax Regime Default (FY 2026-27 / AY 2027-28)',
    category: 'Salary & Benefits',
    keyNotes: 'Deducted as per average rate of income tax computed on employee estimated total income under chosen regime (Standard deduction ₹75,000 in new regime).',
    statutoryReference: 'Section 192, Income-tax Act, 1961'
  },

  // 15. Gaming & Lotteries
  {
    section: '194B & 194BA',
    name: 'Winnings from Lotteries, Crosswords & Online Gaming',
    natureOfPayment: 'Winnings from lottery/card game or net winnings in user online gaming account',
    rateIndHuf: 30.0,
    rateOthers: 30.0,
    thresholdLimit: 10000,
    thresholdType: 'Per Transaction',
    effectiveDate: 'Standard',
    category: 'Other Special Rates',
    keyNotes: 'Flat 30% without basic exemption. Sec 194BA applies to net winnings in online gaming at time of withdrawal or financial year end with zero threshold.',
    statutoryReference: 'Section 194B / 194BA, Income-tax Act, 1961'
  },

  // 16. Higher Deduction for Non-filers
  {
    section: '206AB / 206CCA',
    name: 'Special Higher Rate for Non-Filers of Return',
    natureOfPayment: 'Applicable to specified persons who have not filed ITR for the assessment year relevant to preceding previous year with aggregate TDS/TCS >= ₹50,000',
    rateIndHuf: 0, // dynamic
    rateOthers: 0,
    thresholdLimit: 50000,
    thresholdType: 'Annual',
    effectiveDate: 'Standard',
    category: 'Other Special Rates',
    keyNotes: 'Mandatory deduction at higher of: (i) Twice the rate specified in relevant provision, or (ii) Twice the rate in force, or (iii) 5%. (Not applicable to 192, 192A, 194B, 194BA, 194IA, 194IB, 194M, 194S).',
    statutoryReference: 'Sections 206AB & 206CCA, Income-tax Act, 1961'
  }
];

/**
 * Returns details for a specified TDS section code or synonym
 */
export function getTDSSectionDetails(sectionCode: string): TDSSection2025 | undefined {
  const clean = sectionCode.trim().toUpperCase().replace(/SECTION|\s+/g, '');
  return TDS_SECTIONS_2025.find(s => {
    const sCode = s.section.toUpperCase().replace(/\s+/g, '');
    return sCode === clean || clean.startsWith(sCode) || sCode.startsWith(clean);
  });
}

/**
 * Calculate expected TDS deduction amount based on 2025 rules
 */
export function calculateExpectedTDS(
  taxableAmount: number,
  sectionCode: string,
  entityType: 'Company' | 'LLP' | 'Individual' | 'HUF' = 'Company'
): { rate: number; tdsAmount: number; section: string; notes: string } {
  const section = getTDSSectionDetails(sectionCode) || TDS_SECTIONS_2025[0];
  const isIndHuf = entityType === 'Individual' || entityType === 'HUF';
  const rate = isIndHuf ? section.rateIndHuf : section.rateOthers;
  const tdsAmount = Math.round(taxableAmount * (rate / 100));

  return {
    rate,
    tdsAmount,
    section: section.section,
    notes: `${section.name} (${rate}%)`
  };
}
