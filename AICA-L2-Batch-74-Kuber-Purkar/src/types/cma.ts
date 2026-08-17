// ─── CMA Pro Builder — Core Type Definitions ───────────────────────────────

export type LoanType = 'cc' | 'tl' | 'both';
export type UnitMode = 'rs' | 'thousands' | 'lakhs';

/** User-registered custom ledger head (appears in P&L or Balance Sheet) */
export interface CustomHead {
  id: string;
  name: string;
  kind: 'expense' | 'asset' | 'liability';
  /** for asset/liability: whether it counts as current (feeds Current Ratio) */
  current: boolean;
}

/** Standard P&L / BS heads captured for every actual (audited) year */
export interface YearActual {
  label: string;              // e.g. "2023-24"
  months: number;             // months in the period (normally 12)

  // P&L — Income
  salesDomestic: number;
  salesExport: number;
  otherIncome: number;

  // P&L — Cost of sales
  rmOpening: number;
  rmPurchases: number;
  rmClosing: number;          // doubles as closing stock (RM + FG + WIP combined)
  powerFuel: number;
  directLabour: number;

  // P&L — Expenses
  salary: number;
  freight: number;
  salesPromo: number;
  travelAdmin: number;
  repairs: number;
  professionalFees: number;
  operatingExp: number;
  otherExp: number;
  customExp1: number;
  customExp2: number;
  customExp1Name: string;
  customExp2Name: string;

  // P&L — Financials
  depreciation: number;       // 0 → pick from depreciation schedule
  interestCC: number;
  interestTL: number;
  bankCharges: number;
  tax: number;
  dividend: number;

  // BS — Assets
  fixedAssets: number;        // net block
  deposits: number;
  investments: number;
  debtors: number;
  cash: number;
  otherCurrentAssets: number;

  // BS — Liabilities
  shareCapital: number;
  reserves: number;
  termLoan: number;           // closing TL outstanding (incl. CPLTD)
  cc: number;                 // CC / working-capital bank borrowing
  unsecured: number;
  creditors: number;
  otherCurrentLiab: number;

  /** values for user-registered custom heads, keyed by CustomHead.id */
  customValues: Record<string, number>;
}

export interface AssetBlockInput {
  id: string;
  name: string;
  rate: number;               // WDV %
  opening: number;            // opening WDV at first CMA year
}

export interface LoanConfig {
  loanType: LoanType;
  ccLimit: number;
  ccRate: number;
  ccStockMarginPct: number;   // margin on stock for DP (e.g. 25)
  ccDebtorMarginPct: number;  // margin on debtors for DP (e.g. 40)
  ccDebtorCoverDays: number;  // debtors up to N days counted for DP

  tlAmount: number;
  tlRate: number;
  tlTenureMonths: number;     // total repayment period incl. moratorium
  tlMoratoriumMonths: number; // interest-only period
  grantMonthIndex: number;    // 0 = April … 11 = March, within first estimated FY
  emiDay: number;             // day of month EMI falls due
  grantDay: number;           // day of month loan disbursed
}

export interface ProjectConfig {
  clientName: string;
  startYear: number;          // FY start year of first actual (e.g. 2023 → FY 2023-24)
  actualYears: number;
  estimatedYears: number;     // normally 1
  projectedYears: number;     // e.g. 5
  unit: UnitMode;
  assetBlocks: AssetBlockInput[];
  customHeads: CustomHead[];
  loan: LoanConfig;
  actuals: YearActual[];      // length = actualYears (oldest first)
}

export interface SimParams {
  salesGrowth: number;        // % p.a. applied to estimated + projected
  marginAdj: number;          // % efficiency boost on cost ratios (+ve = cheaper)
  inventoryDays: number;
  debtorDays: number;
  creditorDays: number;
  taxRate: number;            // %
  dividendPct: number;        // % of PAT paid out
  minCashBalance: number;
  tlAssetBlockId: string;     // block that receives the TL addition
  manualAssetAdditions: Record<string, Record<number, number>>; // blockId → yearIndex → amount
}

// ─── Outputs ────────────────────────────────────────────────────────────────

export interface EmiRow {
  month: number;              // 1..n
  date: string;               // ISO date of EMI
  fyIndex: number;            // CMA year index this EMI falls in
  opening: number;
  emi: number;
  interest: number;
  principal: number;
  closing: number;
  moratorium: boolean;
}

export interface DepBlockYear {
  id: string;
  name: string;
  rate: number;
  opening: number;
  addition: number;
  depreciation: number;
  closing: number;
}

export interface DepYear {
  yearIndex: number;
  blocks: DepBlockYear[];
  totalDep: number;
  totalNetBlock: number;
}

export interface RatioWorkLine { label: string; value: number; }
export interface RatioWorking {
  formula: string;
  numerator: RatioWorkLine[];
  denominator: RatioWorkLine[];
  numeratorTotal: number;
  denominatorTotal: number;
  result: number;
}

export interface YearReport {
  yearIndex: number;
  year: string;               // "2024-25"
  type: 'Actual' | 'Estimated' | 'Projected';
  months: number;

  // Operating statement
  salesDomestic: number;
  salesExport: number;
  sales: number;
  salesGrowthPct: number | null;
  otherIncome: number;
  rmOpening: number;
  rmPurchases: number;
  rmClosing: number;
  rmConsumed: number;
  powerFuel: number;
  directLabour: number;
  salary: number;
  freight: number;
  salesPromo: number;
  travelAdmin: number;
  repairs: number;
  professionalFees: number;
  operatingExp: number;
  otherExp: number;
  customExp1: number;
  customExp2: number;
  totalExpenses: number;      // all expense heads excl. dep & interest
  ebitda: number;             // PBDIT
  depreciation: number;
  interestCC: number;
  interestTL: number;
  bankCharges: number;
  interest: number;           // total
  pbt: number;
  tax: number;
  pat: number;
  dividend: number;
  retained: number;
  netCashAccrual: number;     // PAT + Dep

  // Balance sheet — liabilities
  shareCapital: number;
  reserves: number;
  termLoan: number;           // total outstanding at year end
  cpltd: number;              // principal due next 12 months
  cc: number;
  unsecured: number;
  creditors: number;
  otherCurrentLiab: number;
  totalLiabilities: number;

  // Balance sheet — assets
  fixedAssets: number;
  deposits: number;
  investments: number;
  stock: number;
  debtors: number;
  cash: number;
  otherCurrentAssets: number;
  totalAssets: number;
  bsDifference: number;       // should be 0 for non-actual years

  // Derived
  netWorth: number;
  totalOutsideLiab: number;
  currentAssets: number;
  currentLiabilities: number; // incl. CPLTD
  workingCapitalGap: number;
  netWorkingCapital: number;

  // Ratios
  currentRatio: number;
  dscr: number;
  debtEquity: number;
  tolTnw: number;
  interestCoverage: number;
  netProfitRatio: number;     // PAT / sales %
  returnOnInvestment: number; // PAT / capital employed %
  debtorDaysActual: number;
  inventoryDaysActual: number;
  creditorDaysActual: number;
  breakEvenPct: number;       // fixed cost / contribution × 100

  // MPBF (Tandon Method II)
  mpbfGap: number;            // CA - other CL
  mpbfMinNwc: number;         // 25% of CA
  mpbf: number;
  // MPBF (Turnover method)
  mpbfTurnover: number;

  // Drawing power (year-end)
  dpStock: number;
  dpDebtors: number;
  dpTotal: number;
  dpShortfall: number;        // cc - dpTotal (>0 → overdrawn)

  // Ratio workings (for drill-downs)
  workings: Record<string, RatioWorking>;

  /** resolved values of custom ledger heads for this year */
  customHeadValues: Record<string, number>;
}

export interface FeasibilityCheck {
  key: string;
  name: string;
  value: number;
  target: number;
  direction: 'min' | 'max';
  pass: boolean;
}

export interface Feasibility {
  feasible: boolean;
  checks: FeasibilityCheck[];
  maxCcSupportable: number;   // via DP + MPBF
  maxTlSupportable: number;   // via DSCR back-solving
  minGrowthNeeded: number | null; // % sales growth at which all checks pass
}

export interface CmaResult {
  config: ProjectConfig;
  sim: SimParams;
  totalYears: number;
  emiSchedule: EmiRow[];
  depSchedule: DepYear[];
  years: YearReport[];
  feasibility: Feasibility;
}
