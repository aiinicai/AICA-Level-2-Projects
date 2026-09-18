import { TrialBalanceItem, TrialBalanceSummary, TrialBalanceData } from '../types';

export function computeTBSummary(items: TrialBalanceItem[]): TrialBalanceSummary {
  let totalDebit = 0;
  let totalCredit = 0;
  let totalRevenue = 0;
  let totalExpenses = 0;
  let totalAssets = 0;
  let totalLiabilities = 0;
  let totalEquity = 0;
  let totalBorrowings = 0;

  for (const item of items) {
    totalDebit += item.currentYearDebit || 0;
    totalCredit += item.currentYearCredit || 0;

    const net = item.currentYearNet || 0;
    const cat = item.category;
    const group = item.scheduleIIIGroup;

    if (cat === 'Revenue') {
      // In trial balance, revenue has credit balance
      totalRevenue += (item.currentYearCredit - item.currentYearDebit);
    } else if (cat === 'Expenses') {
      // Expenses have debit balance (changes in inventory may be credit)
      totalExpenses += (item.currentYearDebit - item.currentYearCredit);
    } else if (cat === 'Assets') {
      totalAssets += Math.max(0, net);
    } else if (cat === 'Equity') {
      totalEquity += Math.abs(net);
    } else if (cat === 'Liabilities') {
      totalLiabilities += Math.abs(net);
      if (group.toLowerCase().includes('borrowing') || item.accountName.toLowerCase().includes('loan') || item.accountName.toLowerCase().includes('credit')) {
        totalBorrowings += Math.abs(net);
      }
    }
  }

  const diff = Math.abs(totalDebit - totalCredit);
  const isBalanced = diff < 1.0; // within 1 rupee rounding
  const profitBeforeTax = totalRevenue - totalExpenses;

  return {
    totalDebit,
    totalCredit,
    isBalanced,
    difference: diff,
    totalRevenue,
    totalExpenses,
    profitBeforeTax,
    totalAssets,
    totalLiabilities,
    totalEquity,
    totalBorrowings,
    itemCount: items.length,
  };
}

export const ZENITH_TRIAL_BALANCE_ITEMS: TrialBalanceItem[] = [
  // 1. REVENUE (Credits)
  {
    id: 'tb-101',
    accountCode: '3010',
    accountName: 'Domestic Sales - Greige Fabric',
    scheduleIIIGroup: 'Revenue from Operations',
    category: 'Revenue',
    currentYearDebit: 0,
    currentYearCredit: 1185000000, // ₹ 118.50 Cr
    currentYearNet: -1185000000,
    priorYearBalance: -1050000000,
    varianceAmount: 135000000,
    variancePercent: 12.86,
    materialityFlag: 'Material (>OM)',
    notes: 'Major domestic fabric dispatch from Surat mill.',
  },
  {
    id: 'tb-102',
    accountCode: '3020',
    accountName: 'Export Sales - Finished Cotton Fabric (FOB/CIF)',
    scheduleIIIGroup: 'Revenue from Operations',
    category: 'Revenue',
    currentYearDebit: 0,
    currentYearCredit: 665000000, // ₹ 66.50 Cr
    currentYearNet: -665000000,
    priorYearBalance: -580000000,
    varianceAmount: 85000000,
    variancePercent: 14.66,
    materialityFlag: 'Material (>OM)',
    notes: 'Export shipments to UAE, Bangladesh, and Sri Lanka.',
  },
  {
    id: 'tb-103',
    accountCode: '3030',
    accountName: 'Other Operating Income - Export Incentives (RoDTEP)',
    scheduleIIIGroup: 'Revenue from Operations',
    category: 'Revenue',
    currentYearDebit: 0,
    currentYearCredit: 15000000, // ₹ 1.50 Cr
    currentYearNet: -15000000,
    priorYearBalance: -12000000,
    varianceAmount: 3000000,
    variancePercent: 25.0,
    materialityFlag: 'Significant (>PM)',
    notes: 'Duty remission export script credits.',
  },
  {
    id: 'tb-104',
    accountCode: '3040',
    accountName: 'Other Income - Fixed Deposit Interest & Scrap Sales',
    scheduleIIIGroup: 'Other Income',
    category: 'Revenue',
    currentYearDebit: 0,
    currentYearCredit: 9000000, // ₹ 0.90 Cr
    currentYearNet: -9000000,
    priorYearBalance: -8000000,
    varianceAmount: 1000000,
    variancePercent: 12.5,
    materialityFlag: 'Significant (>PM)',
    notes: 'Bank FD interest and cotton ginning scrap disposal.',
  },

  // 2. COST OF MATERIALS & DIRECT COSTS (Debits)
  {
    id: 'tb-201',
    accountCode: '4010',
    accountName: 'Raw Cotton Shankar-6 Purchases',
    scheduleIIIGroup: 'Cost of Materials Consumed',
    category: 'Expenses',
    currentYearDebit: 885000000, // ₹ 88.50 Cr
    currentYearCredit: 0,
    currentYearNet: 885000000,
    priorYearBalance: 790000000,
    varianceAmount: 95000000,
    variancePercent: 12.03,
    materialityFlag: 'Material (>OM)',
    notes: 'Primary procurement from APMC mandis.',
  },
  {
    id: 'tb-202',
    accountCode: '4020',
    accountName: 'Spun Yarn & Synthetic Filament Yarn Purchases',
    scheduleIIIGroup: 'Cost of Materials Consumed',
    category: 'Expenses',
    currentYearDebit: 165000000, // ₹ 16.50 Cr
    currentYearCredit: 0,
    currentYearNet: 165000000,
    priorYearBalance: 150000000,
    varianceAmount: 15000000,
    variancePercent: 10.0,
    materialityFlag: 'Material (>OM)',
    notes: 'Specialty yarn for blended shirting weaves.',
  },
  {
    id: 'tb-203',
    accountCode: '4030',
    accountName: 'Textile Dyes, Sizing & Processing Chemicals',
    scheduleIIIGroup: 'Cost of Materials Consumed',
    category: 'Expenses',
    currentYearDebit: 75000000, // ₹ 7.50 Cr
    currentYearCredit: 0,
    currentYearNet: 75000000,
    priorYearBalance: 68000000,
    varianceAmount: 7000000,
    variancePercent: 10.29,
    materialityFlag: 'Material (>OM)',
    notes: 'Includes packaging materials from related party Zenith Packaging.',
  },
  {
    id: 'tb-204',
    accountCode: '4040',
    accountName: 'Changes in Inventory of Finished Goods & WIP',
    scheduleIIIGroup: 'Changes in Inventories',
    category: 'Expenses',
    currentYearDebit: 0,
    currentYearCredit: 42000000, // (₹ 4.20 Cr) Increase in stock
    currentYearNet: -42000000,
    priorYearBalance: -25000000,
    varianceAmount: -17000000,
    variancePercent: 68.0,
    materialityFlag: 'Significant (>PM)',
    notes: 'Accretion to closing inventory of finished fabric and WIP.',
  },

  // 3. OPERATING & ADMINISTRATIVE EXPENSES
  {
    id: 'tb-301',
    accountCode: '5010',
    accountName: 'Salaries, Wages & Factory Worker Allowances',
    scheduleIIIGroup: 'Employee Benefit Expenses',
    category: 'Expenses',
    currentYearDebit: 124000000, // ₹ 12.40 Cr
    currentYearCredit: 0,
    currentYearNet: 124000000,
    priorYearBalance: 110000000,
    varianceAmount: 14000000,
    variancePercent: 12.73,
    materialityFlag: 'Material (>OM)',
    notes: 'Direct wages for 650 factory workers in Surat plant.',
  },
  {
    id: 'tb-302',
    accountCode: '5020',
    accountName: 'PF, ESI & Employee Welfare Contributions',
    scheduleIIIGroup: 'Employee Benefit Expenses',
    category: 'Expenses',
    currentYearDebit: 18000000, // ₹ 1.80 Cr
    currentYearCredit: 0,
    currentYearNet: 18000000,
    priorYearBalance: 16000000,
    varianceAmount: 2000000,
    variancePercent: 12.5,
    materialityFlag: 'Significant (>PM)',
    notes: 'Statutory compliance timely paid before due dates.',
  },
  {
    id: 'tb-303',
    accountCode: '5030',
    accountName: 'Bank Interest & LC Discounting Charges',
    scheduleIIIGroup: 'Finance Costs',
    category: 'Expenses',
    currentYearDebit: 56000000, // ₹ 5.60 Cr
    currentYearCredit: 0,
    currentYearNet: 56000000,
    priorYearBalance: 52000000,
    varianceAmount: 4000000,
    variancePercent: 7.69,
    materialityFlag: 'Material (>OM)',
    notes: 'SBI and consortium bank debt interest.',
  },
  {
    id: 'tb-304',
    accountCode: '5040',
    accountName: 'Depreciation on Plant, Machinery & Buildings',
    scheduleIIIGroup: 'Depreciation & Amortisation',
    category: 'Expenses',
    currentYearDebit: 64000000, // ₹ 6.40 Cr
    currentYearCredit: 0,
    currentYearNet: 64000000,
    priorYearBalance: 58000000,
    varianceAmount: 6000000,
    variancePercent: 10.34,
    materialityFlag: 'Material (>OM)',
    notes: 'Calculated per Schedule II of Companies Act 2013.',
  },
  {
    id: 'tb-305',
    accountCode: '5050',
    accountName: 'Electric Power, Fuel & Gas (DGVCL Grid)',
    scheduleIIIGroup: 'Other Expenses',
    category: 'Expenses',
    currentYearDebit: 215000000, // ₹ 21.50 Cr
    currentYearCredit: 0,
    currentYearNet: 215000000,
    priorYearBalance: 190000000,
    varianceAmount: 25000000,
    variancePercent: 13.16,
    materialityFlag: 'Material (>OM)',
    notes: 'Energy charges for spinning and weaving operations.',
  },
  {
    id: 'tb-306',
    accountCode: '5060',
    accountName: 'Outsourced Job-Work & Processing Charges',
    scheduleIIIGroup: 'Other Expenses',
    category: 'Expenses',
    currentYearDebit: 98000000, // ₹ 9.80 Cr
    currentYearCredit: 0,
    currentYearNet: 98000000,
    priorYearBalance: 85000000,
    varianceAmount: 13000000,
    variancePercent: 15.29,
    materialityFlag: 'Material (>OM)',
    notes: 'External dyeing, printing and sanforizing processors.',
  },
  {
    id: 'tb-307',
    accountCode: '5070',
    accountName: 'Export Ocean Freight, Insurance & Clearing',
    scheduleIIIGroup: 'Other Expenses',
    category: 'Expenses',
    currentYearDebit: 65000000, // ₹ 6.50 Cr
    currentYearCredit: 0,
    currentYearNet: 65000000,
    priorYearBalance: 52000000,
    varianceAmount: 13000000,
    variancePercent: 25.0,
    materialityFlag: 'Material (>OM)',
    notes: 'Freight to Dubai and Colombo ports.',
  },
  {
    id: 'tb-308',
    accountCode: '5080',
    accountName: 'Repairs & Maintenance - Machinery & Loom Spares',
    scheduleIIIGroup: 'Other Expenses',
    category: 'Expenses',
    currentYearDebit: 38000000, // ₹ 3.80 Cr
    currentYearCredit: 0,
    currentYearNet: 38000000,
    priorYearBalance: 32000000,
    varianceAmount: 6000000,
    variancePercent: 18.75,
    materialityFlag: 'Significant (>PM)',
    notes: 'Overhauls of Tsudakoma air-jet looms.',
  },
  {
    id: 'tb-309',
    accountCode: '5090',
    accountName: 'Legal, Professional & Audit Fees',
    scheduleIIIGroup: 'Other Expenses',
    category: 'Expenses',
    currentYearDebit: 16000000, // ₹ 1.60 Cr
    currentYearCredit: 0,
    currentYearNet: 16000000,
    priorYearBalance: 14000000,
    varianceAmount: 2000000,
    variancePercent: 14.29,
    materialityFlag: 'Significant (>PM)',
    notes: 'Includes statutory audit fee and transfer pricing consultant.',
  },
  {
    id: 'tb-310',
    accountCode: '5100',
    accountName: 'Rates, Taxes & Administrative Expenses',
    scheduleIIIGroup: 'Other Expenses',
    category: 'Expenses',
    currentYearDebit: 12000000, // ₹ 1.20 Cr
    currentYearCredit: 0,
    currentYearNet: 12000000,
    priorYearBalance: 10000000,
    varianceAmount: 2000000,
    variancePercent: 20.0,
    materialityFlag: 'Clearly Trivial',
    notes: 'GIDC water cess, property tax, and office stationery.',
  },

  // 4. NON-CURRENT ASSETS (Debits)
  {
    id: 'tb-401',
    accountCode: '1010',
    accountName: 'Freehold Land - GIDC Industrial Estate, Sachin',
    scheduleIIIGroup: 'Property, Plant & Equipment (PPE)',
    category: 'Assets',
    currentYearDebit: 180000000, // ₹ 18.00 Cr
    currentYearCredit: 0,
    currentYearNet: 180000000,
    priorYearBalance: 180000000,
    varianceAmount: 0,
    variancePercent: 0,
    materialityFlag: 'Material (>OM)',
    notes: 'Title deeds verified; zero encumbrance except bank mortgage.',
  },
  {
    id: 'tb-402',
    accountCode: '1020',
    accountName: 'Factory Buildings & Sheds (Net Block)',
    scheduleIIIGroup: 'Property, Plant & Equipment (PPE)',
    category: 'Assets',
    currentYearDebit: 215000000, // ₹ 21.50 Cr
    currentYearCredit: 0,
    currentYearNet: 215000000,
    priorYearBalance: 228000000,
    varianceAmount: -13000000,
    variancePercent: -5.7,
    materialityFlag: 'Material (>OM)',
    notes: 'Surat plant main spinning shed and warehouse.',
  },
  {
    id: 'tb-403',
    accountCode: '1030',
    accountName: 'Plant & Machinery - Air-jet Looms & Blow Room (Net Block)',
    scheduleIIIGroup: 'Property, Plant & Equipment (PPE)',
    category: 'Assets',
    currentYearDebit: 289000000, // ₹ 28.90 Cr
    currentYearCredit: 0,
    currentYearNet: 289000000,
    priorYearBalance: 295000000,
    varianceAmount: -6000000,
    variancePercent: -2.03,
    materialityFlag: 'Material (>OM)',
    notes: '120 Tsudakoma looms and Reiter spinning spindles.',
  },
  {
    id: 'tb-404',
    accountCode: '1040',
    accountName: 'Capital Work-in-Progress - 1.2 MW Rooftop Solar Project',
    scheduleIIIGroup: 'Capital Work-in-Progress (CWIP)',
    category: 'Assets',
    currentYearDebit: 32000000, // ₹ 3.20 Cr
    currentYearCredit: 0,
    currentYearNet: 32000000,
    priorYearBalance: 8000000,
    varianceAmount: 24000000,
    variancePercent: 300.0,
    materialityFlag: 'Significant (>PM)',
    notes: 'Under installation by Tata Power Solar; completion Q1 next FY.',
  },
  {
    id: 'tb-405',
    accountCode: '1050',
    accountName: 'Security Deposits & Long-term Advances with DGVCL/GIDC',
    scheduleIIIGroup: 'Other Non-Current Assets',
    category: 'Assets',
    currentYearDebit: 40000000, // ₹ 4.00 Cr
    currentYearCredit: 0,
    currentYearNet: 40000000,
    priorYearBalance: 38000000,
    varianceAmount: 2000000,
    variancePercent: 5.26,
    materialityFlag: 'Significant (>PM)',
    notes: 'High-tension electricity deposit with DGVCL.',
  },

  // 5. CURRENT ASSETS (Debits)
  {
    id: 'tb-501',
    accountCode: '1210',
    accountName: 'Raw Cotton Bales Inventory at Godown & Ginners',
    scheduleIIIGroup: 'Inventories',
    category: 'Assets',
    currentYearDebit: 145000000, // ₹ 14.50 Cr
    currentYearCredit: 0,
    currentYearNet: 145000000,
    priorYearBalance: 125000000,
    varianceAmount: 20000000,
    variancePercent: 16.0,
    materialityFlag: 'Material (>OM)',
    notes: 'Surat godown stock and ginning lot advances.',
  },
  {
    id: 'tb-502',
    accountCode: '1220',
    accountName: 'Work-in-Process (Yarn in Spinning & Looms Beam Stock)',
    scheduleIIIGroup: 'Inventories',
    category: 'Assets',
    currentYearDebit: 62000000, // ₹ 6.20 Cr
    currentYearCredit: 0,
    currentYearNet: 62000000,
    priorYearBalance: 55000000,
    varianceAmount: 7000000,
    variancePercent: 12.73,
    materialityFlag: 'Material (>OM)',
    notes: 'Valued at raw material plus absorption of conversion costs.',
  },
  {
    id: 'tb-503',
    accountCode: '1230',
    accountName: 'Finished Greige & Processed Fabric Inventory',
    scheduleIIIGroup: 'Inventories',
    category: 'Assets',
    currentYearDebit: 78000000, // ₹ 7.80 Cr
    currentYearCredit: 0,
    currentYearNet: 78000000,
    priorYearBalance: 63000000,
    varianceAmount: 15000000,
    variancePercent: 23.81,
    materialityFlag: 'Material (>OM)',
    notes: 'Lower of cost and net realizable value.',
  },
  {
    id: 'tb-504',
    accountCode: '1310',
    accountName: 'Trade Receivables - Domestic Garment Manufacturers',
    scheduleIIIGroup: 'Trade Receivables',
    category: 'Assets',
    currentYearDebit: 156000000, // ₹ 15.60 Cr
    currentYearCredit: 0,
    currentYearNet: 156000000,
    priorYearBalance: 135000000,
    varianceAmount: 21000000,
    variancePercent: 15.56,
    materialityFlag: 'Material (>OM)',
    notes: 'Subject to external circularization under SA 505.',
  },
  {
    id: 'tb-505',
    accountCode: '1320',
    accountName: 'Trade Receivables - Export Buyers (Dubai / Colombo)',
    scheduleIIIGroup: 'Trade Receivables',
    category: 'Assets',
    currentYearDebit: 72000000, // ₹ 7.20 Cr
    currentYearCredit: 0,
    currentYearNet: 72000000,
    priorYearBalance: 60000000,
    varianceAmount: 12000000,
    variancePercent: 20.0,
    materialityFlag: 'Material (>OM)',
    notes: 'Backed by Irrevocable Letters of Credit (LCs).',
  },
  {
    id: 'tb-506',
    accountCode: '1410',
    accountName: 'State Bank of India - Current Account & EPC Disbursal',
    scheduleIIIGroup: 'Cash & Cash Equivalents',
    category: 'Assets',
    currentYearDebit: 28000000, // ₹ 2.80 Cr
    currentYearCredit: 0,
    currentYearNet: 28000000,
    priorYearBalance: 18000000,
    varianceAmount: 10000000,
    variancePercent: 55.56,
    materialityFlag: 'Significant (>PM)',
    notes: 'Main operational bank account, reconciled with statement.',
  },
  {
    id: 'tb-507',
    accountCode: '1420',
    accountName: 'HDFC Bank - Margin Money Fixed Deposits for LC/BG',
    scheduleIIIGroup: 'Cash & Cash Equivalents',
    category: 'Assets',
    currentYearDebit: 26000000, // ₹ 2.60 Cr
    currentYearCredit: 0,
    currentYearNet: 26000000,
    priorYearBalance: 24000000,
    varianceAmount: 2000000,
    variancePercent: 8.33,
    materialityFlag: 'Significant (>PM)',
    notes: 'Lien marked by bank for issuing vendor bank guarantees.',
  },
  {
    id: 'tb-508',
    accountCode: '1510',
    accountName: 'Supplier Advances for Cotton & Yarn Procurement',
    scheduleIIIGroup: 'Short-Term Loans & Advances',
    category: 'Assets',
    currentYearDebit: 41000000, // ₹ 4.10 Cr
    currentYearCredit: 0,
    currentYearNet: 41000000,
    priorYearBalance: 32000000,
    varianceAmount: 9000000,
    variancePercent: 28.13,
    materialityFlag: 'Significant (>PM)',
    notes: 'Seasonality advances given to ginning mills.',
  },
  {
    id: 'tb-509',
    accountCode: '1610',
    accountName: 'GST Input Tax Credit & Inverted Duty Refund Claims',
    scheduleIIIGroup: 'Other Current Assets',
    category: 'Assets',
    currentYearDebit: 62000000, // ₹ 6.20 Cr
    currentYearCredit: 0,
    currentYearNet: 62000000,
    priorYearBalance: 48000000,
    varianceAmount: 14000000,
    variancePercent: 29.17,
    materialityFlag: 'Material (>OM)',
    notes: 'Inverted duty structure refund applications with GST department.',
  },

  // 6. EQUITY & RESERVES (Credits)
  {
    id: 'tb-601',
    accountCode: '2010',
    accountName: 'Equity Share Capital (1,50,00,000 Equity Shares of ₹ 10 each)',
    scheduleIIIGroup: 'Equity Share Capital & Other Equity',
    category: 'Equity',
    currentYearDebit: 0,
    currentYearCredit: 150000000, // ₹ 15.00 Cr
    currentYearNet: -150000000,
    priorYearBalance: -150000000,
    varianceAmount: 0,
    variancePercent: 0,
    materialityFlag: 'Material (>OM)',
    notes: 'Held by promoter family and associate holding entities.',
  },
  {
    id: 'tb-602',
    accountCode: '2020',
    accountName: 'Retained Earnings & General Reserves (Opening Balance)',
    scheduleIIIGroup: 'Equity Share Capital & Other Equity',
    category: 'Equity',
    currentYearDebit: 0,
    currentYearCredit: 235000000, // ₹ 23.50 Cr
    currentYearNet: -235000000,
    priorYearBalance: -195000000,
    varianceAmount: 40000000,
    variancePercent: 20.51,
    materialityFlag: 'Material (>OM)',
    notes: 'Accumulated statutory reserves after dividend allocations.',
  },

  // 7. BORROWINGS & LIABILITIES (Credits)
  {
    id: 'tb-701',
    accountCode: '2110',
    accountName: 'SBI Consortium Term Loan - TUFS Textile Modernization',
    scheduleIIIGroup: 'Borrowings (Term Loans & Working Capital)',
    category: 'Liabilities',
    currentYearDebit: 0,
    currentYearCredit: 180000000, // ₹ 18.00 Cr
    currentYearNet: -180000000,
    priorYearBalance: -220000000,
    varianceAmount: -40000000,
    variancePercent: -18.18,
    materialityFlag: 'Material (>OM)',
    notes: 'Repayable in quarterly installments; TUFS interest subsidy verified.',
  },
  {
    id: 'tb-702',
    accountCode: '2120',
    accountName: 'SBI Cash Credit & Export Packing Credit (EPC) Facility',
    scheduleIIIGroup: 'Borrowings (Term Loans & Working Capital)',
    category: 'Liabilities',
    currentYearDebit: 0,
    currentYearCredit: 240000000, // ₹ 24.00 Cr
    currentYearNet: -240000000,
    priorYearBalance: -210000000,
    varianceAmount: 30000000,
    variancePercent: 14.29,
    materialityFlag: 'Material (>OM)',
    notes: 'Secured against hypothecation of stock and trade receivables.',
  },
  {
    id: 'tb-703',
    accountCode: '2210',
    accountName: 'Trade Payables - Raw Cotton Ginners & Chemical Suppliers',
    scheduleIIIGroup: 'Trade Payables (MSME & Others)',
    category: 'Liabilities',
    currentYearDebit: 0,
    currentYearCredit: 124000000, // ₹ 12.40 Cr
    currentYearNet: -124000000,
    priorYearBalance: -108000000,
    varianceAmount: 16000000,
    variancePercent: 14.81,
    materialityFlag: 'Material (>OM)',
    notes: 'Non-MSME vendors, subject to confirmation circularization.',
  },
  {
    id: 'tb-704',
    accountCode: '2220',
    accountName: 'Trade Payables - MSME Micro & Small Enterprises',
    scheduleIIIGroup: 'Trade Payables (MSME & Others)',
    category: 'Liabilities',
    currentYearDebit: 0,
    currentYearCredit: 32000000, // ₹ 3.20 Cr
    currentYearNet: -32000000,
    priorYearBalance: -28000000,
    varianceAmount: 4000000,
    variancePercent: 14.29,
    materialityFlag: 'Significant (>PM)',
    notes: 'Monitored under Section 43B(h) and MSMED Act 45-day rule.',
  },
  {
    id: 'tb-705',
    accountCode: '2310',
    accountName: 'Provisions for Employee Gratuity & Leave Encashment',
    scheduleIIIGroup: 'Provisions & Other Financial Liabilities',
    category: 'Liabilities',
    currentYearDebit: 0,
    currentYearCredit: 19000000, // ₹ 1.90 Cr
    currentYearNet: -19000000,
    priorYearBalance: -16000000,
    varianceAmount: 3000000,
    variancePercent: 18.75,
    materialityFlag: 'Significant (>PM)',
    notes: 'Based on independent actuary report under Ind AS 19.',
  },
  {
    id: 'tb-706',
    accountCode: '2320',
    accountName: 'Statutory Dues Payable (TDS, GST RCM, PF & ESI Payable)',
    scheduleIIIGroup: 'Provisions & Other Financial Liabilities',
    category: 'Liabilities',
    currentYearDebit: 0,
    currentYearCredit: 20000000, // ₹ 2.00 Cr
    currentYearNet: -20000000,
    priorYearBalance: -17000000,
    varianceAmount: 3000000,
    variancePercent: 17.65,
    materialityFlag: 'Significant (>PM)',
    notes: 'Cleared subsequent to March 31 in April.',
  },
];

export const ZENITH_SAMPLE_TRIAL_BALANCE: TrialBalanceData = {
  importedAt: '2026-03-31T18:00:00.000Z',
  fileName: 'Zenith_Fabrics_Final_TB_FY2526_Audited.xlsx',
  items: ZENITH_TRIAL_BALANCE_ITEMS,
  summary: computeTBSummary(ZENITH_TRIAL_BALANCE_ITEMS),
};
