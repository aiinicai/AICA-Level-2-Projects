import { Account } from '../core/types';

export const DEPARTMENTS = [
  'Clinical',
  'Pharmacy',
  'Laboratory',
  'Radiology',
  'Administration',
  'Facilities',
  'IT',
  'Procurement',
];

export const CHART_OF_ACCOUNTS: Account[] = [
  // Cash & Bank
  { code: '1000', name: 'Main Cash on Hand', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Cash and cash equivalents', isActive: true },
  { code: '1010', name: 'Petty Cash', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Cash and cash equivalents', isActive: true },
  { code: '1020', name: 'Bank – Operating Account', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Cash and cash equivalents', isActive: true },
  { code: '1030', name: 'Bank – Collections Account', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Cash and cash equivalents', isActive: true },
  { code: '1040', name: 'Cash in Transit', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Cash and cash equivalents', isActive: true },

  // Receivables
  { code: '1100', name: 'Trade Receivables – Patients (AR control)', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Trade receivables', isControlAccount: true, isActive: true },
  { code: '1110', name: 'Trade Receivables – Insurance (AR control)', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Trade receivables', isControlAccount: true, isActive: true },
  { code: '1120', name: 'Trade Receivables – Corporate & Other (AR control)', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Trade receivables', isControlAccount: true, isActive: true },
  { code: '1190', name: 'Allowance for Expected Credit Losses (contra)', type: 'Contra', normalBalance: 'Credit', ifrsLine: 'Trade receivables', isActive: true },

  // Inventories
  { code: '1200', name: 'Inventory – Pharmaceuticals', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Inventories', isControlAccount: true, isActive: true },
  { code: '1210', name: 'Inventory – Medical Consumables', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Inventories', isControlAccount: true, isActive: true },
  { code: '1220', name: 'Inventory – Implants & Surgical', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Inventories', isControlAccount: true, isActive: true },
  { code: '1230', name: 'Inventory – General Stores', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Inventories', isControlAccount: true, isActive: true },

  // Other Current Assets
  { code: '1300', name: 'Prepayments', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Prepayments and other receivables', isActive: true },
  { code: '1310', name: 'Advances to Suppliers', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Prepayments and other receivables', isActive: true },
  { code: '1320', name: 'Deposits and Other Receivables', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Prepayments and other receivables', isActive: true },
  { code: '1400', name: 'VAT Input Recoverable', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Prepayments and other receivables', isActive: true },
  { code: '1500', name: 'Intercompany Receivable (Due from units)', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Due from related units (eliminated on consolidation)', isControlAccount: true, isActive: true },

  // Non-Current Assets / PPE
  { code: '1600', name: 'Capital Work in Progress', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment (CWIP)', isNonCurrent: true, isActive: true },
  { code: '1610', name: 'Asset Clearing – Pending Capitalisation', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment (CWIP)', isNonCurrent: true, isControlAccount: true, isActive: true },
  { code: '1700', name: 'PPE – Land', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isActive: true },
  { code: '1710', name: 'PPE – Buildings', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isActive: true },
  { code: '1720', name: 'PPE – Leasehold Improvements', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isActive: true },
  { code: '1730', name: 'PPE – Medical Equipment', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isActive: true },
  { code: '1740', name: 'PPE – Furniture and Fixtures', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isActive: true },
  { code: '1750', name: 'PPE – IT Equipment', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isActive: true },
  { code: '1760', name: 'PPE – Vehicles', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isActive: true },
  { code: '1770', name: 'PPE – Plant, HVAC and Electrical', type: 'Asset', normalBalance: 'Debit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isActive: true },

  // Accumulated Depreciation (Contra Assets)
  { code: '1810', name: 'Accumulated Depreciation – Buildings', type: 'Contra', normalBalance: 'Credit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isControlAccount: true, isActive: true },
  { code: '1820', name: 'Accumulated Depreciation – Leasehold Improvements', type: 'Contra', normalBalance: 'Credit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isControlAccount: true, isActive: true },
  { code: '1830', name: 'Accumulated Depreciation – Medical Equipment', type: 'Contra', normalBalance: 'Credit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isControlAccount: true, isActive: true },
  { code: '1840', name: 'Accumulated Depreciation – Furniture and Fixtures', type: 'Contra', normalBalance: 'Credit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isControlAccount: true, isActive: true },
  { code: '1850', name: 'Accumulated Depreciation – IT Equipment', type: 'Contra', normalBalance: 'Credit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isControlAccount: true, isActive: true },
  { code: '1860', name: 'Accumulated Depreciation – Vehicles', type: 'Contra', normalBalance: 'Credit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isControlAccount: true, isActive: true },
  { code: '1870', name: 'Accumulated Depreciation – Plant, HVAC & Electrical', type: 'Contra', normalBalance: 'Credit', ifrsLine: 'Property, plant and equipment', isNonCurrent: true, isControlAccount: true, isActive: true },

  // Liabilities
  { code: '2000', name: 'Trade Payables (AP control)', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Trade and other payables', isControlAccount: true, isActive: true },
  { code: '2010', name: 'Goods Received Not Invoiced (GRNI)', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Trade and other payables', isControlAccount: true, isActive: true },
  { code: '2020', name: 'Accrued Expenses', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Trade and other payables', isActive: true },
  { code: '2100', name: 'VAT Output Payable', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Trade and other payables', isActive: true },
  { code: '2200', name: 'Accrued Salaries and Staff Payables', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Trade and other payables', isActive: true },
  { code: '2210', name: 'End of Service Benefits Provision', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Employee benefits provision', isNonCurrent: true, isActive: true },
  { code: '2300', name: 'Patient Deposits and Deferred Revenue', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Contract liabilities', isActive: true },
  { code: '2400', name: 'Corporate Tax Payable', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Current tax liability', isActive: true },
  { code: '2500', name: 'Intercompany Payable (Due to units)', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Due to related units (eliminated on consolidation)', isControlAccount: true, isActive: true },
  { code: '2600', name: 'Lease Liabilities', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Lease liabilities', isNonCurrent: true, isActive: true },
  { code: '2700', name: 'Bank Loan – Current Portion', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Borrowings (current)', isActive: true },
  { code: '2710', name: 'Bank Loan – Non-current', type: 'Liability', normalBalance: 'Credit', ifrsLine: 'Borrowings (non-current)', isNonCurrent: true, isActive: true },

  // Equity
  { code: '3000', name: 'Share Capital', type: 'Equity', normalBalance: 'Credit', ifrsLine: 'Share capital', isActive: true },
  { code: '3100', name: 'Retained Earnings', type: 'Equity', normalBalance: 'Credit', ifrsLine: 'Retained earnings', isActive: true },
  { code: '3200', name: 'Statutory Reserve', type: 'Equity', normalBalance: 'Credit', ifrsLine: 'Reserves', isActive: true },

  // Revenue
  { code: '4000', name: 'Inpatient Revenue', type: 'Revenue', normalBalance: 'Credit', ifrsLine: 'Revenue from contracts with customers', isActive: true },
  { code: '4010', name: 'Outpatient Revenue', type: 'Revenue', normalBalance: 'Credit', ifrsLine: 'Revenue from contracts with customers', isActive: true },
  { code: '4020', name: 'Surgery and Procedures Revenue', type: 'Revenue', normalBalance: 'Credit', ifrsLine: 'Revenue from contracts with customers', isActive: true },
  { code: '4030', name: 'Laboratory and Radiology Revenue', type: 'Revenue', normalBalance: 'Credit', ifrsLine: 'Revenue from contracts with customers', isActive: true },
  { code: '4040', name: 'Pharmacy Sales – Retail', type: 'Revenue', normalBalance: 'Credit', ifrsLine: 'Revenue from contracts with customers', isActive: true },
  { code: '4050', name: 'Pharmacy Sales – Insurance', type: 'Revenue', normalBalance: 'Credit', ifrsLine: 'Revenue from contracts with customers', isActive: true },
  { code: '4060', name: 'Clinic Consultation Revenue', type: 'Revenue', normalBalance: 'Credit', ifrsLine: 'Revenue from contracts with customers', isActive: true },
  { code: '4090', name: 'Discounts and Contractual Adjustments (contra)', type: 'Revenue', normalBalance: 'Debit', ifrsLine: 'Revenue from contracts with customers', isActive: true },
  { code: '4900', name: 'Intercompany Service Revenue', type: 'Revenue', normalBalance: 'Credit', ifrsLine: 'Eliminated on consolidation', isActive: true },
  { code: '4950', name: 'Other Income', type: 'Revenue', normalBalance: 'Credit', ifrsLine: 'Other income', isActive: true },

  // Cost of Sales
  { code: '5000', name: 'Cost of Medicines Sold', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Cost of sales', isActive: true },
  { code: '5010', name: 'Medical Consumables Consumed', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Cost of sales', isActive: true },
  { code: '5020', name: 'Implants and Surgical Items Consumed', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Cost of sales', isActive: true },
  { code: '5030', name: 'Inventory Adjustments, Expiry and Shrinkage', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Cost of sales', isActive: true },
  { code: '5040', name: 'Purchase Price Variance', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Cost of sales', isActive: true },
  { code: '5100', name: 'Clinical Staff Costs', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Cost of sales', isActive: true },
  { code: '5110', name: 'Doctors’ Professional Fees', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Cost of sales', isActive: true },

  // Administrative & Operating Expenses
  { code: '6000', name: 'Administrative Salaries', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6100', name: 'Rent Expense', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6110', name: 'Utilities', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6120', name: 'Repairs and Maintenance', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6130', name: 'Cleaning and Housekeeping', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6140', name: 'Security Services', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6150', name: 'Insurance Expense (Malpractice and Property)', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6200', name: 'Office Supplies and Stationery', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6220', name: 'Communication and Internet', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6230', name: 'Travel and Transport', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6240', name: 'Hospitality and Staff Welfare', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6250', name: 'Professional and Consulting Fees', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6260', name: 'Marketing and Advertising', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Selling and distribution expenses', isActive: true },
  { code: '6270', name: 'Bank Charges', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6280', name: 'Licences and Regulatory Fees', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6290', name: 'Miscellaneous Expenses', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6300', name: 'Depreciation Expense', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6310', name: 'Expected Credit Loss Expense', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Impairment losses on financial assets', isActive: true },
  { code: '6320', name: 'Medical Waste Disposal', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Administrative expenses', isActive: true },
  { code: '6400', name: 'Intercompany Service Charge Expense', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Eliminated on consolidation', isActive: true },

  // Financing & Tax
  { code: '7000', name: 'Finance Costs', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Finance costs', isActive: true },
  { code: '7100', name: 'Gain/Loss on Disposal of Assets', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Other income / other expenses', isActive: true },
  { code: '7200', name: 'Foreign Exchange Gain/Loss', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Other income / other expenses', isActive: true },
  { code: '7300', name: 'Corporate Tax Expense', type: 'Expense', normalBalance: 'Debit', ifrsLine: 'Income tax expense', isActive: true },
];

export function enrichAccount(a: Account): Account {
  let subledgerSource: Account['subledgerSource'] = 'None';
  const c = parseInt(a.code, 10);
  if (c >= 1000 && c <= 1040) subledgerSource = 'Cash';
  else if (c >= 1100 && c <= 1190) subledgerSource = 'Receivables';
  else if (c >= 1200 && c <= 1299) subledgerSource = 'Inventory';
  else if (c === 1500 || c === 2500 || c === 4900 || c === 6400) subledgerSource = 'Intercompany';
  else if ((c >= 1600 && c <= 1899) || c === 6300) subledgerSource = 'Fixed Assets';
  else if (c >= 2000 && c <= 2020) subledgerSource = 'Payables';

  return {
    ...a,
    manualJournalAllowed: a.manualJournalAllowed ?? !a.isControlAccount,
    subledgerSource: a.subledgerSource ?? subledgerSource,
  };
}

export const ENRICHED_CHART_OF_ACCOUNTS: Account[] = CHART_OF_ACCOUNTS.map(enrichAccount);

export function getAllAccounts(): Account[] {
  try {
    // Dynamic import avoidance; access global or localStorage if available
    const raw = typeof window !== 'undefined' ? localStorage.getItem('medicore_accounts_override') : null;
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch {}
  return ENRICHED_CHART_OF_ACCOUNTS;
}

export function getAccountByCode(code: string): Account | undefined {
  return getAllAccounts().find((a) => a.code === code);
}

export function isControlAccount(code: string): boolean {
  const acct = getAccountByCode(code);
  return Boolean(acct?.isControlAccount);
}

