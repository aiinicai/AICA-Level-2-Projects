export type NumberUnitMode = 'standard' | 'lakhs' | 'crores';

export function formatINR(
  value: number | string | null | undefined,
  mode: NumberUnitMode = 'standard',
  includeSymbol: boolean = true
): string {
  if (value === null || value === undefined || value === '') {
    return '₹ 0.00';
  }
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '₹ 0.00';

  const prefix = includeSymbol ? '₹ ' : '';

  if (mode === 'crores') {
    const inCrores = num / 10000000;
    return `${prefix}${inCrores.toFixed(2)} Cr`;
  }

  if (mode === 'lakhs') {
    const inLakhs = num / 100000;
    return `${prefix}${inLakhs.toFixed(2)} L`;
  }

  // Standard Indian formatting (e.g. 12,34,567.89)
  const isNegative = num < 0;
  const absNum = Math.abs(num);
  const parts = absNum.toFixed(2).split('.');
  let integerPart = parts[0];
  const decimalPart = parts[1];

  let lastThree = integerPart.substring(integerPart.length - 3);
  const otherNumbers = integerPart.substring(0, integerPart.length - 3);
  if (otherNumbers !== '') {
    lastThree = ',' + lastThree;
  }
  const formattedInteger = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + lastThree;
  const result = `${formattedInteger}.${decimalPart}`;

  return `${isNegative ? '-' : ''}${prefix}${result}`;
}

export function formatProductType(type: string): string {
  const map: Record<string, string> = {
    home_loan: 'Home Loan',
    lap: 'Loan Against Property (LAP)',
    business_loan_secured: 'Secured Business Loan',
    business_loan_unsecured: 'Unsecured Business Loan',
    cash_credit_od: 'Cash Credit / Overdraft (CC/OD)',
    working_capital: 'Working Capital Facility',
    project_finance_term_loan: 'Project Finance & Term Loan',
    balance_transfer_topup: 'Balance Transfer & Top-up',
  };
  return map[type] || type.replace(/_/g, ' ').toUpperCase();
}

export function formatProposalStatus(status: string): { label: string; color: string } {
  const map: Record<string, { label: string; color: string }> = {
    lead: { label: 'Lead Sourced', color: 'bg-slate-100 text-slate-700 border-slate-300' },
    onboarding: { label: 'Client Onboarding', color: 'bg-sky-100 text-sky-800 border-sky-300' },
    proposal_draft: { label: 'Proposal Drafting', color: 'bg-indigo-100 text-indigo-800 border-indigo-300' },
    document_collection: { label: 'Document Collection', color: 'bg-amber-100 text-amber-800 border-amber-300' },
    extraction_verification: { label: 'Extraction & Verification', color: 'bg-purple-100 text-purple-800 border-purple-300' },
    financial_analysis: { label: 'Financial Underwriting', color: 'bg-blue-100 text-blue-800 border-blue-300' },
    lender_comparison: { label: 'Lender Policy Matching', color: 'bg-teal-100 text-teal-800 border-teal-300' },
    reviewer_approval: { label: 'Reviewer Approval Queue', color: 'bg-orange-100 text-orange-800 border-orange-300' },
    report_generation: { label: 'Report Pack Generation', color: 'bg-cyan-100 text-cyan-800 border-cyan-300' },
    submission_tracking: { label: 'Bank Submission Tracking', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
    sanctioned: { label: 'Sanctioned', color: 'bg-green-100 text-green-800 border-green-300' },
    rejected: { label: 'Rejected / Declined', color: 'bg-rose-100 text-rose-800 border-rose-300' },
    closed_won: { label: 'Closed - Won', color: 'bg-emerald-100 text-emerald-800 border-emerald-400 font-semibold' },
    closed_lost: { label: 'Closed - Not Won', color: 'bg-rose-100 text-rose-800 border-rose-300 font-medium' },
  };
  return map[status] || { label: status, color: 'bg-slate-100 text-slate-700 border-slate-300' };
}
