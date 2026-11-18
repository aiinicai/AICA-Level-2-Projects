/** API contracts shared by server and web. Amounts crossing the API are rupees (number, 2dp) unless named *_paise. */

export type Role = 'admin' | 'analyst' | 'viewer';

/** Where a figure comes from. Always shown to the user next to important numbers. */
export type DataStatus =
  | 'actual' //      taken directly from source records (sums of posted vouchers / balances)
  | 'calculated' //  derived by a documented formula from actual figures
  | 'estimated' //   derived using an assumption (e.g. weighted-average cost); explained in `notes`
  | 'unavailable'; // cannot be computed defensibly; `notes` explains what is missing

export type Unit = 'currency' | 'percent' | 'ratio' | 'days' | 'count' | 'qty' | 'months';

export interface MetricValue {
  value: number | null;
  status: DataStatus;
  unit: Unit;
  notes?: string[];
}

export interface Comparison {
  previous: number | null;
  absChange: number | null;
  /** null when the base is zero, negative or unavailable — never a misleading percentage */
  pctChange: number | null;
  pctNote?: string;
}

export interface KpiResult {
  code: string;
  name: string;
  category: string;
  description: string;
  unit: Unit;
  better: 'higher' | 'lower' | 'neutral';
  measureType: 'official' | 'management' | 'estimate';
  expression: string;
  current: MetricValue;
  comparison: Comparison | null;
  trend: { period: string; value: number | null }[];
  thresholdState?: 'ok' | 'warn' | 'bad';
  drivers?: { label: string; change: number }[];
  drill?: { kind: 'class' | 'ledger' | 'page'; target: string };
}

export interface FilterState {
  companyId: number;
  from: string;
  to: string;
  compare: 'previous_period' | 'previous_year' | 'none';
  costCentre?: string;
}

export interface Insight {
  id: string;
  headline: string;
  severity: 'high' | 'medium' | 'low' | 'info';
  confidence: 'high' | 'medium' | 'low';
  metric: string;
  current: string;
  baseline: string;
  rule: string;
  explanation: string;
  possibleCauses?: string[];
  action: string;
  drill?: { path: string; label: string };
  category: 'profitability' | 'liquidity' | 'working_capital' | 'concentration' | 'inventory' | 'data_quality' | 'anomaly';
}

export interface DqIssue {
  code: string;
  title: string;
  severity: 'high' | 'medium' | 'low' | 'info';
  count: number;
  amount: number | null;
  detail: string;
  remediation: string;
  samples?: { label: string; value?: string; link?: string }[];
}
