"use client";

import React, { useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

type Screen =
  | "new-valuation"
  | "financial-analysis"
  | "valuation";

type FinancialMetrics = {
  revenue?: number | null;
  total_income?: number | null;

  ebitda?: number | null;
  ebit?: number | null;
  pbt?: number | null;
  pat?: number | null;

  depreciation?: number | null;
  finance_cost?: number | null;

  ebitda_margin?: number | null;
  ebit_margin?: number | null;
  pbt_margin?: number | null;
  pat_margin?: number | null;

  current_assets?: number | null;
  current_liabilities?: number | null;

  inventory?: number | null;
  trade_receivables?: number | null;
  trade_payables?: number | null;

  cash?: number | null;
  net_worth?: number | null;
  total_assets?: number | null;
  total_debt?: number | null;
  capital_employed?: number | null;

  current_ratio?: number | null;
  quick_ratio?: number | null;
  debt_equity?: number | null;

  interest_coverage?: number | null;
  interest_coverage_ebit?: number | null;
  interest_coverage_ebitda?: number | null;

  cash_flow_from_operations?: number | null;
  cash_flow_from_investing?: number | null;
  cash_flow_from_financing?: number | null;
  closing_cash?: number | null;

  roe?: number | null;
  roce?: number | null;

  receivable_days?: number | null;
  inventory_days?: number | null;
  payable_days?: number | null;

  revenue_growth?: number | null;
  ebitda_growth?: number | null;
  pat_growth?: number | null;

  capex?: number | null;
  change_working_capital?: number | null;

  capex_source?: string | null;
  capex_basis?: string | null;

  working_capital_source?: string | null;
  working_capital_basis?: string | null;
};

type FinancialPeriod = {
  period: string;
  display: string;
  sort_key: string;
  bucket: string;
  metrics: FinancialMetrics;
};

type Observation = {
  type: string;
  category: string;
  message: string;
};

type CrossCheck = {
  bucket: string;
  period: string;
  check: string;
  difference: number;
  status: string;
};

type CapitalStructureCheck = {
  check: string;
  difference?: number | null;
  status: string;
};

type CapitalStructureInstrument = {
  instrument: string;
  outstanding?: number | null;
  conversion_ratio?: number | null;
  equity_equivalent?: number | null;
  exercise_or_conversion_price?: number | null;
  terms?: string | null;
};

type CapitalStructureHolder = {
  holder: string;
  basic_equity_shares?: number | null;
  basic_percentage?: number | null;
  equity_from_ccps?: number | null;
  equity_from_warrants?: number | null;
  equity_from_esops?: number | null;
  fully_diluted_shares?: number | null;
  fully_diluted_percentage?: number | null;
};

type CapitalStructureData = {
  available?: boolean;
  status?: string;
  source_file?: string | null;
  basic_equity_shares?: number | null;
  ccps_outstanding?: number | null;
  ccps_conversion_ratio?: number | null;
  equity_from_ccps?: number | null;
  warrants_outstanding?: number | null;
  equity_from_warrants?: number | null;
  esop_vested?: number | null;
  esop_unvested?: number | null;
  equity_from_esops?: number | null;
  computed_fully_diluted_shares?: number | null;
  fully_diluted_shares?: number | null;
  future_cash_receivable_on_exercise?: number | null;
  future_cash_receivable_warrants?: number | null;
  future_cash_receivable_esops?: number | null;
  instruments?: CapitalStructureInstrument[];
  holders?: CapitalStructureHolder[];
  checks?: CapitalStructureCheck[];
  valuation_note?: string | null;
};

type ReviewItem = {
  review_id: string;
  file_name?: string;
  sheet?: string;
  sheet_type?: string;
  document_category?: string;
  row?: number;
  source_label?: string;
  canonical_field?: string;
  statement?: string;
  confidence?: number;
  match_type?: string;
  matched_alias?: string;
  reason?: string;
  review_status?: string;
  review_note?: string;
  reviewed_at?: string | null;
  material?: boolean;
};

type ReviewSummary = {
  total?: number;
  unresolved?: number;
  resolved?: number;
  unresolved_material?: number;
  failed_cross_checks?: number;
  failed_capital_checks?: number;
  data_ready_for_valuation?: boolean;
  draft_work_allowed?: boolean;
  final_report_ready?: boolean;
};

type FinancialAnalysisResponse = {
  success: boolean;
  assignment_id: string;
  message: string;

  analysis_engine_version?: string;

  historical?: FinancialPeriod[];
  provisional?: FinancialPeriod[];
  projected?: FinancialPeriod[];

  projection_schedule_metrics?: Record<string, any>;
  capital_structure?: CapitalStructureData;

  historical_cagr?: {
    revenue_cagr?: number | null;
    ebitda_cagr?: number | null;
    pat_cagr?: number | null;
  };

  projected_cagr?: {
    revenue_cagr?: number | null;
    ebitda_cagr?: number | null;
    pat_cagr?: number | null;
  };

  projection_comparison?: Record<
    string,
    any
  >;

  observations?: Observation[];

  cross_checks?: CrossCheck[];

  review_items?: number;
  review_required?: ReviewItem[];
  review_summary?: ReviewSummary;
};

type WaccSensitivityCell = {
  pre_tax_cost_of_debt_percent: number;
  wacc_percent: number;
};

type WaccSensitivityRow = {
  beta: number;
  values: WaccSensitivityCell[];
};

type WaccAnalysis = {
  risk_free_rate_percent: number;
  equity_risk_premium_percent: number;
  beta: number;
  company_specific_risk_premium_percent: number;
  cost_of_equity_percent: number;
  pre_tax_cost_of_debt_percent: number;
  tax_rate_percent: number;
  after_tax_cost_of_debt_percent: number;
  equity_weight_percent: number;
  debt_weight_percent: number;
  wacc_percent: number;
  market_data_date?: string;
  sources?: {
    risk_free_rate?: string;
    equity_risk_premium?: string;
    beta?: string;
    cost_of_debt?: string;
  };
  notes?: string;
  formula?: string;
  sensitivity?: {
    beta_offsets?: number[];
    debt_cost_offsets_percent?: number[];
    rows?: WaccSensitivityRow[];
  };
};

type MarketDataSuggestion = {
  success?: boolean;
  assignment_id?: string;
  valuation_date?: string;
  company_name?: string;
  risk_free_rate_percent?: number | null;
  equity_risk_premium_percent?: number | null;
  beta?: number | null;
  company_specific_risk_premium_percent?: number | null;
  pre_tax_cost_of_debt_percent?: number | null;
  equity_weight_percent?: number | null;
  debt_weight_percent?: number | null;
  market_data_date?: string | null;
  industry?: string | null;
  status?: string;
  approval_required?: boolean;
  sources?: {
    risk_free_rate?: string;
    risk_free_url?: string;
    equity_risk_premium?: string;
    erp_url?: string;
    beta?: string;
    beta_url?: string;
    cost_of_debt?: string;
    capital_weights?: string;
  };
  basis?: {
    risk_free_rate?: string;
    equity_risk_premium?: string;
    beta?: string;
    cost_of_debt?: string;
    capital_weights?: string;
  };
  warnings?: string[];
};


type ProjectionRow = {
  year: string;

  ebit: string;

  depreciation: string;

  capex: string;

  change_working_capital: string;

  ebit_source?: string;

  depreciation_source?: string;

  capex_source?: string;

  working_capital_source?: string;
};


/* =========================================================
   DISPLAY HELPERS
========================================================= */

function money(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "en-IN",
    {
      maximumFractionDigits: 2,
    }
  ).format(value);
}


function percent(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return `${value.toFixed(2)}%`;
}


function ratio(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return `${value.toFixed(2)}x`;
}


function days(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return `${value.toFixed(1)} days`;
}


function numberToInput(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  return String(value);
}


function numericValue(
  value: string
) {
  const number = Number(value);

  if (
    value.trim() === "" ||
    Number.isNaN(number)
  ) {
    return null;
  }

  return number;
}


/* =========================================================
   UI COMPONENTS
========================================================= */

function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}


function SectionTitle({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-4">
      <h2 className="text-xl font-semibold text-slate-900">
        {title}
      </h2>

      {subtitle && (
        <p className="mt-1 text-sm text-slate-500">
          {subtitle}
        </p>
      )}
    </div>
  );
}


function Input({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  placeholder = "",
}: {
  label: string;
  value: string;
  onChange: (
    value: string
  ) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-700">
        {label}

        {required && (
          <span className="ml-1 text-red-500">
            *
          </span>
        )}
      </label>

      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) =>
          onChange(
            event.target.value
          )
        }
        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-100"
      />
    </div>
  );
}


function Select({
  label,
  value,
  onChange,
  options,
  required = false,
}: {
  label: string;
  value: string;
  onChange: (
    value: string
  ) => void;
  options: string[];
  required?: boolean;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-700">
        {label}

        {required && (
          <span className="ml-1 text-red-500">
            *
          </span>
        )}
      </label>

      <select
        value={value}
        onChange={(event) =>
          onChange(
            event.target.value
          )
        }
        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none"
      >
        <option value="">
          Select
        </option>

        {options.map(
          (option) => (
            <option
              key={option}
              value={option}
            >
              {option}
            </option>
          )
        )}
      </select>
    </div>
  );
}


function UploadField({
  label,
  files,
  onChange,
}: {
  label: string;
  files: File[];
  onChange: (
    files: File[]
  ) => void;
}) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
      <p className="text-sm font-medium text-slate-800">
        {label}
      </p>

      <input
        className="mt-3 block w-full text-sm text-slate-600"
        type="file"
        multiple
        accept=".xlsx,.xls,.xlsm,.pdf,.doc,.docx,.csv"
        onChange={(event) =>
          onChange(
            Array.from(
              event.target.files ||
                []
            )
          )
        }
      />

      {files.length > 0 && (
        <p className="mt-2 text-xs text-slate-500">
          {files.length} file(s)
          selected
        </p>
      )}
    </div>
  );
}


function KpiCard({
  label,
  value,
  caption,
}: {
  label: string;
  value: string;
  caption?: string;
}) {
  return (
    <Card className="p-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>

      <p className="mt-2 text-2xl font-semibold text-slate-900">
        {value}
      </p>

      {caption && (
        <p className="mt-1 text-xs text-slate-500">
          {caption}
        </p>
      )}
    </Card>
  );
}


function StatusBadge({
  good,
  goodText = "Ready",
  badText = "Required",
}: {
  good: boolean;
  goodText?: string;
  badText?: string;
}) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
        good
          ? "bg-emerald-50 text-emerald-700"
          : "bg-amber-50 text-amber-700"
      }`}
    >
      {good
        ? goodText
        : badText}
    </span>
  );
}


/* =========================================================
   FINANCIAL ANALYSIS TABLE
========================================================= */

function MetricTable({
  rows,
  title,
}: {
  rows: FinancialPeriod[];
  title: string;
}) {
  if (!rows.length) {
    return null;
  }

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-200 px-5 py-4">
        <h3 className="font-semibold text-slate-900">
          {title}
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1150px] w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3 text-left">
                Period
              </th>

              <th className="px-4 py-3 text-right">
                Revenue
              </th>

              <th className="px-4 py-3 text-right">
                EBITDA
              </th>

              <th className="px-4 py-3 text-right">
                EBITDA %
              </th>

              <th className="px-4 py-3 text-right">
                PAT
              </th>

              <th className="px-4 py-3 text-right">
                PAT %
              </th>

              <th className="px-4 py-3 text-right">
                Debt
              </th>

              <th className="px-4 py-3 text-right">
                D/E
              </th>

              <th className="px-4 py-3 text-right">
                Current
              </th>

              <th className="px-4 py-3 text-right">
                Interest Cover
              </th>

              <th className="px-4 py-3 text-right">
                ROE
              </th>

              <th className="px-4 py-3 text-right">
                ROCE
              </th>
            </tr>
          </thead>

          <tbody>
            {rows.map(
              (row) => (
                <tr
                  key={row.period}
                  className="border-t border-slate-100"
                >
                  <td className="px-4 py-3 font-medium text-slate-800">
                    {row.display}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {money(
                      row.metrics
                        .revenue
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {money(
                      row.metrics
                        .ebitda
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {percent(
                      row.metrics
                        .ebitda_margin
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {money(
                      row.metrics.pat
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {percent(
                      row.metrics
                        .pat_margin
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {money(
                      row.metrics
                        .total_debt
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {ratio(
                      row.metrics
                        .debt_equity
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {ratio(
                      row.metrics
                        .current_ratio
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {ratio(
                      row.metrics
                        .interest_coverage
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {percent(
                      row.metrics.roe
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {percent(
                      row.metrics.roce
                    )}
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}


/* =========================================================
   WORKING CAPITAL TABLE
========================================================= */

function WorkingCapitalTable({
  rows,
}: {
  rows: FinancialPeriod[];
}) {
  if (!rows.length) {
    return null;
  }

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-200 px-5 py-4">
        <h3 className="font-semibold text-slate-900">
          Working Capital Trends
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[750px] text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left">
                Period
              </th>

              <th className="px-4 py-3 text-right">
                Receivable Days
              </th>

              <th className="px-4 py-3 text-right">
                Inventory Days
              </th>

              <th className="px-4 py-3 text-right">
                Payable Days
              </th>

              <th className="px-4 py-3 text-right">
                CFO
              </th>
            </tr>
          </thead>

          <tbody>
            {rows.map(
              (row) => (
                <tr
                  key={row.period}
                  className="border-t border-slate-100"
                >
                  <td className="px-4 py-3 font-medium">
                    {row.display}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {days(
                      row.metrics
                        .receivable_days
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {days(
                      row.metrics
                        .inventory_days
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {days(
                      row.metrics
                        .payable_days
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {money(
                      row.metrics
                        .cash_flow_from_operations
                    )}
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}


function CapitalStructurePanel({
  data,
}: {
  data?: CapitalStructureData;
}) {
  if (!data?.available) {
    return (
      <Card className="p-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold text-slate-900">
              Capital Structure & Dilution
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              No validated capital structure was available for this assignment.
            </p>
          </div>
          <StatusBadge good={false} goodText="Validated" badText="Review" />
        </div>
      </Card>
    );
  }

  const checks = data.checks || [];
  const holders = data.holders || [];
  const allChecksOk =
    checks.length > 0 &&
    checks.every((item) => item.status === "OK");

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-200 px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold text-slate-900">
              Capital Structure & Fully Diluted Shares
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              {data.source_file
                ? `Source: ${data.source_file}`
                : "Extracted from uploaded capital structure"}
            </p>
          </div>

          <StatusBadge
            good={data.status === "VALIDATED" || allChecksOk}
            goodText="Validated"
            badText={data.status || "Review"}
          />
        </div>
      </div>

      <div className="p-5">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <KpiCard
            label="Basic Equity Shares"
            value={money(data.basic_equity_shares)}
            caption="Existing equity shares"
          />
          <KpiCard
            label="CCPS Dilution"
            value={money(data.equity_from_ccps)}
            caption={
              data.ccps_conversion_ratio != null
                ? `${money(data.ccps_outstanding)} CCPS × ${data.ccps_conversion_ratio}x`
                : "Equity equivalent on conversion"
            }
          />
          <KpiCard
            label="Warrant Dilution"
            value={money(data.equity_from_warrants)}
            caption="Equity equivalent"
          />
          <KpiCard
            label="ESOP Dilution"
            value={money(data.equity_from_esops)}
            caption="Vested + unvested options"
          />
          <KpiCard
            label="Fully Diluted Shares"
            value={money(data.fully_diluted_shares)}
            caption="Used as valuation denominator"
          />
        </div>

        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Reconciliation & Checks
            </p>
            <div className="mt-3 space-y-2">
              {checks.length === 0 ? (
                <p className="text-sm text-slate-500">No validation checks returned.</p>
              ) : (
                checks.map((check, index) => (
                  <div
                    key={index}
                    className="flex items-start justify-between gap-4 rounded-lg bg-slate-50 px-3 py-2.5"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-800">{check.check}</p>
                      {check.difference != null && (
                        <p className="mt-0.5 text-xs text-slate-500">
                          Difference: {money(check.difference)}
                        </p>
                      )}
                    </div>
                    <StatusBadge
                      good={check.status === "OK"}
                      goodText="OK"
                      badText="Review"
                    />
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Future Exercise Proceeds
            </p>
            <div className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <span className="text-slate-600">Warrants</span>
                <strong>{money(data.future_cash_receivable_warrants)}</strong>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-600">ESOPs</span>
                <strong>{money(data.future_cash_receivable_esops)}</strong>
              </div>
              <div className="flex justify-between gap-4 border-t border-slate-200 pt-2">
                <span className="font-medium text-slate-800">Total future proceeds</span>
                <strong>{money(data.future_cash_receivable_on_exercise)}</strong>
              </div>
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-500">
              These are disclosed separately and are not automatically added to valuation-date cash.
            </p>
          </div>
        </div>

        {holders.length > 0 && (
          <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full min-w-[850px] text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-4 py-3 text-left">Holder</th>
                  <th className="px-4 py-3 text-right">Basic Shares</th>
                  <th className="px-4 py-3 text-right">CCPS</th>
                  <th className="px-4 py-3 text-right">Warrants</th>
                  <th className="px-4 py-3 text-right">ESOPs</th>
                  <th className="px-4 py-3 text-right">Fully Diluted</th>
                  <th className="px-4 py-3 text-right">FD %</th>
                </tr>
              </thead>
              <tbody>
                {holders.map((holder, index) => (
                  <tr key={`${holder.holder}-${index}`} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium text-slate-800">{holder.holder}</td>
                    <td className="px-4 py-3 text-right">{money(holder.basic_equity_shares)}</td>
                    <td className="px-4 py-3 text-right">{money(holder.equity_from_ccps)}</td>
                    <td className="px-4 py-3 text-right">{money(holder.equity_from_warrants)}</td>
                    <td className="px-4 py-3 text-right">{money(holder.equity_from_esops)}</td>
                    <td className="px-4 py-3 text-right font-medium">{money(holder.fully_diluted_shares)}</td>
                    <td className="px-4 py-3 text-right">{percent(holder.fully_diluted_percentage)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data.valuation_note && (
          <p className="mt-4 text-xs leading-5 text-slate-500">{data.valuation_note}</p>
        )}
      </div>
    </Card>
  );
}


/* =========================================================
   SIMPLE TREND
========================================================= */

function TrendBars({
  rows,
}: {
  rows: FinancialPeriod[];
}) {
  const maximum = Math.max(
    ...rows.map(
      (row) =>
        row.metrics.revenue ||
        0
    ),
    1
  );

  return (
    <Card className="p-5">
      <h3 className="font-semibold text-slate-900">
        Revenue Trend
      </h3>

      <p className="mt-1 text-xs text-slate-500">
        Historical and projected
        revenue
      </p>

      <div className="mt-6 space-y-4">
        {rows.map(
          (row) => {
            const width =
              ((row.metrics
                .revenue || 0) /
                maximum) *
              100;

            return (
              <div
                key={row.period}
              >
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-700">
                    {row.display}
                  </span>

                  <span className="text-slate-500">
                    {money(
                      row.metrics
                        .revenue
                    )}
                  </span>
                </div>

                <div className="h-2.5 rounded-full bg-slate-100">
                  <div
                    className="h-2.5 rounded-full bg-slate-700"
                    style={{
                      width:
                        `${Math.max(
                          width,
                          2
                        )}%`,
                    }}
                  />
                </div>
              </div>
            );
          }
        )}
      </div>
    </Card>
  );
}


function ReviewPanel({
  items,
  summary,
  busy,
  onUpdate,
}: {
  items: ReviewItem[];
  summary?: ReviewSummary;
  busy: boolean;
  onUpdate: (
    reviewId: string,
    status: string
  ) => void;
}) {
  const [filter, setFilter] =
    useState("open");

  const resolved = new Set([
    "reviewed",
    "accepted",
    "ignored",
  ]);

  const visibleItems = items.filter(
    (item) => {
      const status =
        item.review_status ||
        "pending";

      if (filter === "all") {
        return true;
      }

      if (filter === "resolved") {
        return resolved.has(status);
      }

      if (filter === "material") {
        return (
          item.material === true &&
          !resolved.has(status)
        );
      }

      return !resolved.has(status);
    }
  );

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-200 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="font-semibold text-slate-900">
              Valuer Review & Data Validation
            </h3>

            <p className="mt-1 text-sm text-slate-500">
              Review uncertain mappings before relying on the extracted data for a final valuation report.
            </p>
          </div>

          <StatusBadge
            good={
              summary?.data_ready_for_valuation ===
              true
            }
            goodText="Data Ready for Valuation"
            badText="Review Pending"
          />
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Total</p>
            <p className="mt-1 text-xl font-semibold">{summary?.total ?? items.length}</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Open</p>
            <p className="mt-1 text-xl font-semibold">{summary?.unresolved ?? 0}</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Material Open</p>
            <p className="mt-1 text-xl font-semibold">{summary?.unresolved_material ?? 0}</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Resolved</p>
            <p className="mt-1 text-xl font-semibold">{summary?.resolved ?? 0}</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Failed Checks</p>
            <p className="mt-1 text-xl font-semibold">
              {(summary?.failed_cross_checks ?? 0) +
                (summary?.failed_capital_checks ?? 0)}
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {[
            ["open", "Open"],
            ["material", "Material Open"],
            ["resolved", "Resolved"],
            ["all", "All"],
          ].map(([value, label]) => (
            <button
              key={value}
              onClick={() =>
                setFilter(value)
              }
              className={`rounded-lg px-3 py-2 text-xs font-medium ${
                filter === value
                  ? "bg-slate-950 text-white"
                  : "border border-slate-200 bg-white text-slate-600"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="divide-y divide-slate-100">
        {visibleItems.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">
            No review items in this view.
          </div>
        ) : (
          visibleItems.map((item) => {
            const status =
              item.review_status ||
              "pending";

            return (
              <div
                key={item.review_id}
                className="p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-slate-900">
                        {item.source_label ||
                          "Unmapped item"}
                      </p>

                      {item.material && (
                        <span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-semibold uppercase text-amber-700">
                          Material
                        </span>
                      )}

                      <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold uppercase text-slate-600">
                        {status}
                      </span>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span>File: {item.file_name || "—"}</span>
                      <span>Sheet: {item.sheet || "—"}</span>
                      <span>Row: {item.row ?? "—"}</span>
                      {item.canonical_field && (
                        <span>
                          Suggested: {item.canonical_field}
                        </span>
                      )}
                      {item.confidence !== undefined && (
                        <span>
                          Confidence: {item.confidence}%
                        </span>
                      )}
                    </div>

                    <p className="mt-2 text-sm text-slate-600">
                      {item.reason ||
                        "Valuer review required."}
                    </p>

                    {item.review_note && (
                      <p className="mt-2 text-xs text-slate-500">
                        Review note: {item.review_note}
                      </p>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      disabled={busy}
                      onClick={() =>
                        onUpdate(
                          item.review_id,
                          "reviewed"
                        )
                      }
                      className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 disabled:opacity-50"
                    >
                      Reviewed
                    </button>

                    <button
                      disabled={busy}
                      onClick={() =>
                        onUpdate(
                          item.review_id,
                          "accepted"
                        )
                      }
                      className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
                    >
                      Accept
                    </button>

                    <button
                      disabled={busy}
                      onClick={() =>
                        onUpdate(
                          item.review_id,
                          "ignored"
                        )
                      }
                      className="rounded-lg bg-slate-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
                    >
                      Ignore
                    </button>

                    {status !== "pending" && (
                      <button
                        disabled={busy}
                        onClick={() =>
                          onUpdate(
                            item.review_id,
                            "pending"
                          )
                        }
                        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-500 disabled:opacity-50"
                      >
                        Reset
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="border-t border-slate-200 bg-slate-50 px-5 py-4 text-xs text-slate-600">
        Draft valuation work remains available while review items are open. Final-report readiness is achieved only when material review items and failed validation checks are cleared.
      </div>
    </Card>
  );
}


/* =========================================================
   MAIN
========================================================= */

export default function Home() {
  const [
    screen,
    setScreen,
  ] =
    useState<Screen>(
      "new-valuation"
    );

  const [
    assignmentId,
    setAssignmentId,
  ] = useState("");

  const [
    notice,
    setNotice,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    busy,
    setBusy,
  ] = useState(false);


  /* =======================================================
     NEW VALUATION
  ======================================================= */

  const [
    companyName,
    setCompanyName,
  ] = useState("");

  const [
    cin,
    setCin,
  ] = useState("");

  const [
    pan,
    setPan,
  ] = useState("");

  const [
    valuationDate,
    setValuationDate,
  ] = useState("");

  const [
    engagementDate,
    setEngagementDate,
  ] = useState("");

  const [
    reportDate,
    setReportDate,
  ] = useState("");

  const [
    purpose,
    setPurpose,
  ] = useState("");

  const [
    securityType,
    setSecurityType,
  ] = useState("");

  const [
    applicableProvision,
    setApplicableProvision,
  ] = useState("");

  const [
    transactionDetails,
    setTransactionDetails,
  ] = useState("");

  const [
    contactName,
    setContactName,
  ] = useState("");

  const [
    designation,
    setDesignation,
  ] = useState("");

  const [
    mobile,
    setMobile,
  ] = useState("");

  const [
    email,
    setEmail,
  ] = useState("");

  const [
    provisionalFiles,
    setProvisionalFiles,
  ] = useState<File[]>([]);

  const [
    historicalFiles,
    setHistoricalFiles,
  ] = useState<File[]>([]);

  const [
    projectionFiles,
    setProjectionFiles,
  ] = useState<File[]>([]);

  const [
    capitalStructureFiles,
    setCapitalStructureFiles,
  ] = useState<File[]>([]);

  const [
    debtScheduleFiles,
    setDebtScheduleFiles,
  ] = useState<File[]>([]);

  const [
    companyProfileFiles,
    setCompanyProfileFiles,
  ] = useState<File[]>([]);

  const [
    otherFiles,
    setOtherFiles,
  ] = useState<File[]>([]);


  /* =======================================================
     FINANCIAL ANALYSIS
  ======================================================= */

  const [
    financialData,
    setFinancialData,
  ] =
    useState<FinancialAnalysisResponse | null>(
      null
    );


  /* =======================================================
     VALUATION
  ======================================================= */

  const [
    dilutedShares,
    setDilutedShares,
  ] = useState("");

  const [
    taxRate,
    setTaxRate,
  ] = useState("25");

  const [
    wacc,
    setWacc,
  ] = useState("15");

  const [
    terminalGrowth,
    setTerminalGrowth,
  ] = useState("5");

  const [
    cash,
    setCash,
  ] = useState("");

  const [
    debt,
    setDebt,
  ] = useState("");

  const [
    nonOperatingAssets,
    setNonOperatingAssets,
  ] = useState("0");

  const [
    adjustedAssets,
    setAdjustedAssets,
  ] = useState("");

  const [
    adjustedLiabilities,
    setAdjustedLiabilities,
  ] = useState("");


  const [
    navAutoPopulated,
    setNavAutoPopulated,
  ] = useState(false);

  const [
    dcfWeight,
    setDcfWeight,
  ] = useState("50");

  const [
    navWeight,
    setNavWeight,
  ] = useState("50");

  const [
    dcfResult,
    setDcfResult,
  ] = useState<any>(null);

  const [
    navResult,
    setNavResult,
  ] = useState<any>(null);

  const [
    weightedResult,
    setWeightedResult,
  ] = useState<any>(null);


  /* =======================================================
     WACC & MARKET DATA
  ======================================================= */

  const [
    riskFreeRate,
    setRiskFreeRate,
  ] = useState("");

  const [
    equityRiskPremium,
    setEquityRiskPremium,
  ] = useState("");

  const [
    beta,
    setBeta,
  ] = useState("");

  const [
    companySpecificRiskPremium,
    setCompanySpecificRiskPremium,
  ] = useState("0");

  const [
    preTaxCostOfDebt,
    setPreTaxCostOfDebt,
  ] = useState("");

  const [
    equityWeight,
    setEquityWeight,
  ] = useState("70");

  const [
    debtWeight,
    setDebtWeight,
  ] = useState("30");

  const [
    marketDataDate,
    setMarketDataDate,
  ] = useState("");

  const [
    riskFreeSource,
    setRiskFreeSource,
  ] = useState("");

  const [
    erpSource,
    setErpSource,
  ] = useState("");

  const [
    betaSource,
    setBetaSource,
  ] = useState("");

  const [
    debtSource,
    setDebtSource,
  ] = useState("");

  const [
    waccNotes,
    setWaccNotes,
  ] = useState("");

  const [
    waccAnalysis,
    setWaccAnalysis,
  ] = useState<WaccAnalysis | null>(null);

  const [
    waccApproved,
    setWaccApproved,
  ] = useState(false);


  const [
    marketSuggestion,
    setMarketSuggestion,
  ] = useState<MarketDataSuggestion | null>(null);

  const [
    marketDataBusy,
    setMarketDataBusy,
  ] = useState(false);


  const [
    projections,
    setProjections,
  ] =
    useState<
      ProjectionRow[]
    >([
      {
        year: "FY2027",
        ebit: "",
        depreciation: "",
        capex: "",
        change_working_capital:
          "",
      },

      {
        year: "FY2028",
        ebit: "",
        depreciation: "",
        capex: "",
        change_working_capital:
          "",
      },

      {
        year: "FY2029",
        ebit: "",
        depreciation: "",
        capex: "",
        change_working_capital:
          "",
      },

      {
        year: "FY2030",
        ebit: "",
        depreciation: "",
        capex: "",
        change_working_capital:
          "",
      },

      {
        year: "FY2031",
        ebit: "",
        depreciation: "",
        capex: "",
        change_working_capital:
          "",
      },
    ]);


  /* =======================================================
     DERIVED
  ======================================================= */

  const combinedTrend =
    useMemo(
      () => [
        ...(
          financialData
            ?.historical ||
          []
        ),

        ...(
          financialData
            ?.projected ||
          []
        ),
      ],
      [financialData]
    );


  const latestHistorical =
    financialData
      ?.historical?.[
        (
          financialData
            .historical
            ?.length || 1
        ) - 1
      ];


  const dcfPreview =
    useMemo(() => {

      const tax =
        Number(taxRate) /
        100;

      return projections.map(
        (row) => {

          const ebit =
            numericValue(
              row.ebit
            );

          const depreciation =
            numericValue(
              row.depreciation
            );

          const capex =
            numericValue(
              row.capex
            );

          const changeWC =
            numericValue(
              row.change_working_capital
            );

          const ready =
            ebit !== null &&
            depreciation !==
              null &&
            capex !== null &&
            changeWC !== null;

          const nopat =
            ebit !== null
              ? ebit *
                (1 - tax)
              : null;

          const fcff =
            ready &&
            nopat !== null &&
            depreciation !==
              null &&
            capex !== null &&
            changeWC !== null
              ? nopat +
                depreciation -
                capex -
                changeWC
              : null;

          return {
            year:
              row.year,

            ready,

            nopat,

            fcff,
          };
        }
      );

    }, [
      projections,
      taxRate,
    ]);


  const dcfRowsReady =
    dcfPreview.every(
      (row) => row.ready
    );


  const dcfGeneralInputsReady =
    dilutedShares.trim() !==
      "" &&
    cash.trim() !== "" &&
    debt.trim() !== "" &&
    taxRate.trim() !== "" &&
    wacc.trim() !== "" &&
    terminalGrowth.trim() !==
      "";


  const dcfReady =
    dcfRowsReady &&
    dcfGeneralInputsReady;


  /* =======================================================
     ASSIGNMENT
  ======================================================= */

  async function submitAssignment() {
    setBusy(true);
    setError("");
    setNotice("");

    try {

      if (
        !companyName.trim()
      ) {
        throw new Error(
          "Company Name is required."
        );
      }

      if (
        !valuationDate ||
        !engagementDate ||
        !reportDate
      ) {
        throw new Error(
          "Please enter all three dates."
        );
      }

      const formData =
        new FormData();

      formData.append(
        "company_name",
        companyName
      );

      formData.append(
        "cin",
        cin
      );

      formData.append(
        "pan",
        pan
      );

      formData.append(
        "valuation_date",
        valuationDate
      );

      formData.append(
        "engagement_date",
        engagementDate
      );

      formData.append(
        "report_date",
        reportDate
      );

      formData.append(
        "purpose",
        purpose
      );

      formData.append(
        "security_type",
        securityType
      );

      formData.append(
        "applicable_provision",
        applicableProvision
      );

      formData.append(
        "transaction_details",
        transactionDetails
      );

      formData.append(
        "contact_name",
        contactName
      );

      formData.append(
        "designation",
        designation
      );

      formData.append(
        "mobile",
        mobile
      );

      formData.append(
        "email",
        email
      );

      provisionalFiles.forEach(
        (file) =>
          formData.append(
            "provisional_files",
            file
          )
      );

      historicalFiles.forEach(
        (file) =>
          formData.append(
            "historical_files",
            file
          )
      );

      projectionFiles.forEach(
        (file) =>
          formData.append(
            "projection_files",
            file
          )
      );

      capitalStructureFiles.forEach(
        (file) =>
          formData.append(
            "capital_structure_files",
            file
          )
      );

      debtScheduleFiles.forEach(
        (file) =>
          formData.append(
            "debt_schedule_files",
            file
          )
      );

      companyProfileFiles.forEach(
        (file) =>
          formData.append(
            "company_profile_files",
            file
          )
      );

      otherFiles.forEach(
        (file) =>
          formData.append(
            "other_files",
            file
          )
      );

      const response =
        await fetch(
          `${API_BASE}/assignments`,
          {
            method:
              "POST",
            body:
              formData,
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Unable to create assignment."
        );
      }

      setAssignmentId(
        data.assignment_id
      );

      setNotice(
        `Assignment ${data.assignment_id} created successfully.`
      );

    } catch (
      err: any
    ) {

      setError(
        err.message ||
          "Something went wrong."
      );

    } finally {

      setBusy(false);
    }
  }


  /* =======================================================
     FINANCIAL ANALYSIS
  ======================================================= */

  async function runFinancialAnalysis() {
    setBusy(true);
    setError("");
    setNotice("");

    try {

      if (
        !assignmentId.trim()
      ) {
        throw new Error(
          "Enter an Assignment ID first."
        );
      }

      const response =
        await fetch(
          `${API_BASE}/financials/analysis/${assignmentId.trim()}`,
          {
            method:
              "POST",
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Financial analysis failed."
        );
      }

      setFinancialData(
        data
      );

      setNotice(
        `Financial analysis completed successfully. Engine version: ${data.analysis_engine_version || "N/A"}.`
      );

    } catch (
      err: any
    ) {

      setError(
        err.message ||
          "Financial analysis failed."
      );

    } finally {

      setBusy(false);
    }
  }


  async function updateReviewItem(
    reviewId: string,
    status: string
  ) {
    setBusy(true);
    setError("");
    setNotice("");

    try {
      if (!assignmentId.trim()) {
        throw new Error(
          "Enter an Assignment ID first."
        );
      }

      const response = await fetch(
        `${API_BASE}/reviews/${assignmentId.trim()}`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            review_id: reviewId,
            status,
            note: "",
          }),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Unable to update review item."
        );
      }

      setFinancialData(
        (current) =>
          current
            ? {
                ...current,
                review_required:
                  data.review_required ||
                  [],
                review_summary:
                  data.review_summary ||
                  {},
                review_items:
                  data.review_summary
                    ?.unresolved ?? 0,
              }
            : current
      );

      setNotice(
        status === "pending"
          ? "Review item reset to pending."
          : `Review item marked as ${status}.`
      );
    } catch (err: any) {
      setError(
        err.message ||
          "Unable to update review item."
      );
    } finally {
      setBusy(false);
    }
  }


  /* =======================================================
     USE ANALYSIS IN DCF
  ======================================================= */

  function useAnalysisInValuation() {

    if (!financialData) {

      setError(
        "Please run Financial Analysis first."
      );

      return;
    }


    const projected =
      financialData.projected ||
      [];


    if (!projected.length) {

      setError(
        "No projected financial periods are available."
      );

      return;
    }


    const newRows:
      ProjectionRow[] =
      projected.map(
        (row) => ({

          year:
            row.period,

          ebit:
            numberToInput(
              row.metrics.ebit
            ),

          depreciation:
            numberToInput(
              row.metrics
                .depreciation
            ),

          capex:
            numberToInput(
              row.metrics.capex
            ),

          change_working_capital:
            numberToInput(
              row.metrics
                .change_working_capital
            ),

          ebit_source:
            "Projected Profit & Loss",

          depreciation_source:
            "Projected Profit & Loss",

          capex_source:
            row.metrics
              .capex_source ||
            undefined,

          working_capital_source:
            row.metrics
              .working_capital_source ||
            undefined,
        })
      );


    setProjections(
      newRows
    );


    /* -----------------------------------------------
       FULLY DILUTED SHARES
    ----------------------------------------------- */

    const capitalStructure =
      financialData.capital_structure;

    if (
      capitalStructure?.available &&
      capitalStructure.fully_diluted_shares !== null &&
      capitalStructure.fully_diluted_shares !== undefined
    ) {
      setDilutedShares(
        String(
          capitalStructure.fully_diluted_shares
        )
      );
    }


    /* -----------------------------------------------
       VALUATION DATE CASH + DEBT
    ----------------------------------------------- */

    const provisional =
      financialData
        .provisional ||
      [];


    const valuationDateBS =
      provisional.find(
        (row) =>
          !row.period.startsWith(
            "FY"
          ) &&
          !row.period.startsWith(
            "STUB_"
          ) &&
          (
            row.metrics.cash !==
              null ||
            row.metrics.total_debt !==
              null
          )
      );


    const balanceSheetSource =
      valuationDateBS ||
      latestHistorical;


    if (
      balanceSheetSource
        ?.metrics.cash !==
        null &&
      balanceSheetSource
        ?.metrics.cash !==
        undefined
    ) {

      setCash(
        String(
          balanceSheetSource
            .metrics.cash
        )
      );
    }


    if (
      balanceSheetSource
        ?.metrics
        .total_debt !==
        null &&
      balanceSheetSource
        ?.metrics
        .total_debt !==
        undefined
    ) {

      setDebt(
        String(
          balanceSheetSource
            .metrics
            .total_debt
        )
      );
    }


    /* -----------------------------------------------
       NAV STARTING POINT FROM VALUATION-DATE BS
       Assets = Total Assets
       Liabilities = Total Assets - Net Worth
       Valuer may edit both for fair-value adjustments.
    ----------------------------------------------- */

    if (
      balanceSheetSource
        ?.metrics
        .total_assets !==
        null &&
      balanceSheetSource
        ?.metrics
        .total_assets !==
        undefined &&
      balanceSheetSource
        ?.metrics
        .net_worth !==
        null &&
      balanceSheetSource
        ?.metrics
        .net_worth !==
        undefined
    ) {
      const totalAssets =
        Number(
          balanceSheetSource
            .metrics
            .total_assets
        );

      const netWorth =
        Number(
          balanceSheetSource
            .metrics
            .net_worth
        );

      setAdjustedAssets(
        String(totalAssets)
      );

      setAdjustedLiabilities(
        String(
          Number(
            (
              totalAssets -
              netWorth
            ).toFixed(2)
          )
        )
      );

      setNavAutoPopulated(true);
      setNavResult(null);
    }


    setDcfResult(null);

    setWeightedResult(
      null
    );


    const missingRows =
      newRows.filter(
        (row) =>
          row.ebit === "" ||
          row.depreciation ===
            "" ||
          row.capex === "" ||
          row.change_working_capital ===
            ""
      );


    if (
      missingRows.length ===
      0
    ) {

      setNotice(
        "Valuation inputs transferred successfully: fully diluted shares, EBIT, depreciation, Capex, Change in Working Capital, cash and debt. Please review the inputs before calculating the valuation."
      );

    } else {

      setNotice(
        `Financial data transferred. ${missingRows.length} projected year(s) still contain incomplete DCF inputs and require valuer review.`
      );
    }


    setError("");

    setScreen(
      "valuation"
    );
  }


  /* =======================================================
     PROJECTION EDIT
  ======================================================= */

  function updateProjection(
    index: number,
    field:
      keyof ProjectionRow,
    value: string
  ) {

    setProjections(
      (current) =>
        current.map(
          (
            row,
            rowIndex
          ) =>
            rowIndex ===
            index
              ? {
                  ...row,
                  [field]:
                    value,
                }
              : row
        )
    );


    setDcfResult(
      null
    );

    setWeightedResult(
      null
    );
  }


  /* =======================================================
     WACC & MARKET DATA
  ======================================================= */

  async function fetchMarketDataSuggestions() {
    setMarketDataBusy(true);
    setError("");
    setNotice("");

    try {
      if (!assignmentId.trim()) {
        throw new Error(
          "Enter / load an Assignment ID before fetching market-data suggestions."
        );
      }

      const response = await fetch(
        `${API_BASE}/valuation/market-data/suggest/${assignmentId.trim()}`
      );

      const data: MarketDataSuggestion =
        await response.json();

      if (!response.ok) {
        throw new Error(
          (data as any).detail ||
            "Unable to fetch market-data suggestions."
        );
      }

      setMarketSuggestion(data);

      if (
        data.risk_free_rate_percent !== null &&
        data.risk_free_rate_percent !== undefined
      ) {
        setRiskFreeRate(
          String(data.risk_free_rate_percent)
        );
      }

      if (
        data.equity_risk_premium_percent !== null &&
        data.equity_risk_premium_percent !== undefined
      ) {
        setEquityRiskPremium(
          String(data.equity_risk_premium_percent)
        );
      }

      if (
        data.beta !== null &&
        data.beta !== undefined
      ) {
        setBeta(
          String(data.beta)
        );
      }

      if (
        data.company_specific_risk_premium_percent !== null &&
        data.company_specific_risk_premium_percent !== undefined
      ) {
        setCompanySpecificRiskPremium(
          String(
            data.company_specific_risk_premium_percent
          )
        );
      }

      if (
        data.pre_tax_cost_of_debt_percent !== null &&
        data.pre_tax_cost_of_debt_percent !== undefined
      ) {
        setPreTaxCostOfDebt(
          String(data.pre_tax_cost_of_debt_percent)
        );
      }

      if (
        data.equity_weight_percent !== null &&
        data.equity_weight_percent !== undefined
      ) {
        setEquityWeight(
          String(data.equity_weight_percent)
        );
      }

      if (
        data.debt_weight_percent !== null &&
        data.debt_weight_percent !== undefined
      ) {
        setDebtWeight(
          String(data.debt_weight_percent)
        );
      }

      if (data.market_data_date) {
        setMarketDataDate(
          data.market_data_date
        );
      }

      setRiskFreeSource(
        data.sources?.risk_free_rate || ""
      );

      setErpSource(
        data.sources?.equity_risk_premium || ""
      );

      setBetaSource(
        data.sources?.beta || ""
      );

      setDebtSource(
        data.sources?.cost_of_debt || ""
      );

      setWaccApproved(false);
      setWaccAnalysis(null);

      const warnings =
        data.warnings || [];

      setNotice(
        data.status === "SUGGESTIONS_READY"
          ? "Market-data suggestions loaded. Review the values and sources, then click Calculate WACC."
          : `Market-data suggestions loaded partially. ${warnings.join(" ")}`
      );
    } catch (err: any) {
      setError(
        err.message ||
          "Unable to fetch market-data suggestions."
      );
    } finally {
      setMarketDataBusy(false);
    }
  }


  async function calculateWacc() {
    setBusy(true);
    setError("");
    setNotice("");

    try {
      const required = [
        riskFreeRate,
        equityRiskPremium,
        beta,
        preTaxCostOfDebt,
        equityWeight,
        debtWeight,
      ];

      if (
        required.some(
          (value) => value.trim() === ""
        )
      ) {
        throw new Error(
          "Please complete all required WACC inputs."
        );
      }

      if (
        Math.abs(
          Number(equityWeight) +
            Number(debtWeight) -
            100
        ) > 0.01
      ) {
        throw new Error(
          "Equity Weight and Debt Weight must total 100%."
        );
      }

      const response = await fetch(
        `${API_BASE}/valuation/wacc`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            risk_free_rate_percent: Number(riskFreeRate),
            equity_risk_premium_percent: Number(equityRiskPremium),
            beta: Number(beta),
            company_specific_risk_premium_percent:
              Number(companySpecificRiskPremium) || 0,
            pre_tax_cost_of_debt_percent:
              Number(preTaxCostOfDebt),
            tax_rate_percent: Number(taxRate),
            equity_weight_percent: Number(equityWeight),
            debt_weight_percent: Number(debtWeight),
            market_data_date: marketDataDate,
            risk_free_source: riskFreeSource,
            erp_source: erpSource,
            beta_source: betaSource,
            debt_source: debtSource,
            notes: waccNotes,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "WACC calculation failed."
        );
      }

      setWaccAnalysis(data);
      setWaccApproved(false);
      setNotice(
        `WACC calculated at ${Number(
          data.wacc_percent
        ).toFixed(2)}%. Review the assumptions and click Approve & Use in DCF.`
      );
    } catch (err: any) {
      setError(
        err.message ||
          "WACC calculation failed."
      );
    } finally {
      setBusy(false);
    }
  }


  function approveWaccForDcf() {
    if (!waccAnalysis) {
      setError(
        "Calculate WACC before approving it for DCF."
      );
      return;
    }

    setWacc(
      String(waccAnalysis.wacc_percent)
    );
    setWaccApproved(true);
    setDcfResult(null);
    setWeightedResult(null);
    setError("");
    setNotice(
      `WACC ${Number(
        waccAnalysis.wacc_percent
      ).toFixed(2)}% approved and transferred to DCF.`
    );
  }


  /* =======================================================
     DCF
  ======================================================= */

  async function calculateDCF() {
    setBusy(true);
    setError("");
    setNotice("");

    try {

      if (
        !dcfRowsReady
      ) {
        throw new Error(
          "DCF cannot be calculated because one or more projected years are missing EBIT, depreciation, Capex or Change in Working Capital."
        );
      }


      if (
        dilutedShares.trim() ===
        ""
      ) {
        throw new Error(
          "Please enter Fully Diluted Shares before calculating DCF."
        );
      }


      if (
        cash.trim() === ""
      ) {
        throw new Error(
          "Please enter Cash before calculating DCF."
        );
      }


      if (
        debt.trim() === ""
      ) {
        throw new Error(
          "Please enter Debt before calculating DCF."
        );
      }


      const numericWacc =
        Number(wacc) /
        100;


      const numericGrowth =
        Number(
          terminalGrowth
        ) / 100;


      if (
        numericWacc <=
        numericGrowth
      ) {
        throw new Error(
          "WACC must be higher than Terminal Growth Rate."
        );
      }


      const response =
        await fetch(
          `${API_BASE}/valuation/dcf`,
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                projections:
                  projections.map(
                    (row) => ({
                      year:
                        row.year,

                      ebit:
                        Number(
                          row.ebit
                        ),

                      depreciation:
                        Number(
                          row.depreciation
                        ),

                      capex:
                        Number(
                          row.capex
                        ),

                      change_working_capital:
                        Number(
                          row.change_working_capital
                        ),
                    })
                  ),

                tax_rate:
                  Number(
                    taxRate
                  ) / 100,

                wacc:
                  numericWacc,

                terminal_growth:
                  numericGrowth,

                cash:
                  Number(cash),

                debt:
                  Number(debt),

                non_operating_assets:
                  Number(
                    nonOperatingAssets
                  ) || 0,

                diluted_shares:
                  Number(
                    dilutedShares
                  ),
              }),
          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(
          data.detail ||
            "DCF calculation failed."
        );
      }


      setDcfResult(
        data
      );


      setNotice(
        "DCF calculation completed successfully."
      );

    } catch (
      err: any
    ) {

      setError(
        err.message ||
          "DCF calculation failed."
      );

    } finally {

      setBusy(false);
    }
  }


  /* =======================================================
     NAV
  ======================================================= */

  async function calculateNAV() {
    setBusy(true);
    setError("");
    setNotice("");

    try {

      if (
        dilutedShares.trim() ===
        ""
      ) {

        throw new Error(
          "Please enter Fully Diluted Shares."
        );
      }


      const response =
        await fetch(
          `${API_BASE}/valuation/nav`,
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                adjusted_assets:
                  Number(
                    adjustedAssets
                  ) || 0,

                adjusted_liabilities:
                  Number(
                    adjustedLiabilities
                  ) || 0,

                diluted_shares:
                  Number(
                    dilutedShares
                  ),
              }),
          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(
          data.detail ||
            "NAV calculation failed."
        );
      }


      setNavResult(
        data
      );


      setNotice(
        "NAV calculation completed successfully."
      );

    } catch (
      err: any
    ) {

      setError(
        err.message ||
          "NAV calculation failed."
      );

    } finally {

      setBusy(false);
    }
  }


  /* =======================================================
     WEIGHTAGE
  ======================================================= */

  async function calculateWeightage() {
    setBusy(true);
    setError("");
    setNotice("");

    try {

      if (
        !dcfResult ||
        !navResult
      ) {

        throw new Error(
          "Calculate DCF and NAV first."
        );
      }


      if (
        Number(
          dcfWeight
        ) +
          Number(
            navWeight
          ) !==
        100
      ) {

        throw new Error(
          "DCF Weight and NAV Weight must total 100%."
        );
      }


      const response =
        await fetch(
          `${API_BASE}/valuation/weightage`,
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                methods: [
                  {
                    method:
                      "DCF",

                    value:
                      dcfResult
                        .equity_value,

                    weight:
                      Number(
                        dcfWeight
                      ),
                  },

                  {
                    method:
                      "NAV",

                    value:
                      navResult
                        .equity_value,

                    weight:
                      Number(
                        navWeight
                      ),
                  },
                ],

                diluted_shares:
                  Number(
                    dilutedShares
                  ),
              }),
          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(
          data.detail ||
            "Weightage calculation failed."
        );
      }


      setWeightedResult(
        data
      );


      setNotice(
        "Concluded valuation calculated successfully."
      );

    } catch (
      err: any
    ) {

      setError(
        err.message ||
          "Weightage calculation failed."
      );

    } finally {

      setBusy(false);
    }
  }


  /* =======================================================
     OUTPUT
  ======================================================= */

  async function generateOutputs() {
    setBusy(true);
    setError("");
    setNotice("");

    try {

      if (
        !assignmentId.trim()
      ) {

        throw new Error(
          "Enter Assignment ID."
        );
      }


      const response =
        await fetch(
          `${API_BASE}/outputs/generate`,
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                assignment_id:
                  assignmentId.trim(),

                projections:
                  projections.map(
                    (row) => ({
                      year:
                        row.year,

                      ebit:
                        Number(
                          row.ebit
                        ) || 0,

                      depreciation:
                        Number(
                          row.depreciation
                        ) || 0,

                      capex:
                        Number(
                          row.capex
                        ) || 0,

                      change_working_capital:
                        Number(
                          row.change_working_capital
                        ) || 0,
                    })
                  ),

                tax_rate_percent:
                  Number(
                    taxRate
                  ),

                wacc_percent:
                  Number(
                    wacc
                  ),

                terminal_growth_percent:
                  Number(
                    terminalGrowth
                  ),

                cash:
                  Number(cash) ||
                  0,

                debt:
                  Number(debt) ||
                  0,

                non_operating_assets:
                  Number(
                    nonOperatingAssets
                  ) || 0,

                diluted_shares:
                  Number(
                    dilutedShares
                  ) || 0,

                adjusted_assets:
                  Number(
                    adjustedAssets
                  ) || 0,

                adjusted_liabilities:
                  Number(
                    adjustedLiabilities
                  ) || 0,

                dcf_weight:
                  Number(
                    dcfWeight
                  ),

                nav_weight:
                  Number(
                    navWeight
                  ),

                wacc_analysis:
                  waccAnalysis
                    ? {
                        ...waccAnalysis,
                        approved_for_dcf: waccApproved,
                        approved_wacc_percent: waccApproved
                          ? Number(wacc)
                          : null,
                      }
                    : null,
              }),
          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(
          data.detail ||
            "Output generation failed."
        );
      }


      setNotice(
        data.report_status ===
          "READY_FOR_FINAL_REVIEW"
          ? "Excel working and draft valuation report generated successfully. Data validation is complete and the assignment is ready for final valuer review."
          : "Excel working and draft valuation report generated successfully as DRAFT ONLY because data-review items remain open."
      );

    } catch (
      err: any
    ) {

      setError(
        err.message ||
          "Output generation failed."
      );

    } finally {

      setBusy(false);
    }
  }


  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="min-h-screen bg-slate-50">

      <div className="flex min-h-screen">

        {/* =================================================
            SIDEBAR
        ================================================= */}

        <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-slate-950 text-white lg:block">

          <div className="border-b border-white/10 px-6 py-6">

            <p className="text-lg font-semibold">
              myvaluation
            </p>

            <p className="mt-1 text-xs text-slate-400">
              Valuation workflow
              platform
            </p>

          </div>


          <nav className="space-y-1 p-4">

            <button
              disabled
              className="w-full rounded-xl px-4 py-3 text-left text-sm text-slate-500"
            >
              Dashboard
            </button>


            <button
              onClick={() =>
                setScreen(
                  "new-valuation"
                )
              }
              className={`w-full rounded-xl px-4 py-3 text-left text-sm transition ${
                screen ===
                "new-valuation"
                  ? "bg-white text-slate-950"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              New Valuation
            </button>


            <button
              disabled
              className="w-full rounded-xl px-4 py-3 text-left text-sm text-slate-500"
            >
              Assignments
            </button>


            <button
              disabled
              className="w-full rounded-xl px-4 py-3 text-left text-sm text-slate-500"
            >
              Documents
            </button>


            <button
              onClick={() =>
                setScreen(
                  "financial-analysis"
                )
              }
              className={`w-full rounded-xl px-4 py-3 text-left text-sm transition ${
                screen ===
                "financial-analysis"
                  ? "bg-white text-slate-950"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              Financial Analysis
            </button>


            <button
              onClick={() =>
                setScreen(
                  "valuation"
                )
              }
              className={`w-full rounded-xl px-4 py-3 text-left text-sm transition ${
                screen ===
                "valuation"
                  ? "bg-white text-slate-950"
                  : "text-slate-300 hover:bg-white/10"
              }`}
            >
              Valuation
            </button>


            <button
              disabled
              className="w-full rounded-xl px-4 py-3 text-left text-sm text-slate-500"
            >
              Reports
            </button>


            <button
              disabled
              className="w-full rounded-xl px-4 py-3 text-left text-sm text-slate-500"
            >
              Settings
            </button>

          </nav>

        </aside>


        {/* =================================================
            MAIN
        ================================================= */}

        <main className="min-w-0 flex-1">

          <div className="border-b border-slate-200 bg-white px-6 py-4 lg:px-10">

            <div className="flex flex-wrap items-center justify-between gap-4">

              <div>

                <h1 className="text-xl font-semibold text-slate-950">
                  Application for
                  Valuation
                </h1>

                <p className="mt-1 text-xs text-slate-500">
                  Registered Valuer
                  workflow
                </p>

              </div>


              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2">

                <p className="text-[11px] uppercase tracking-wide text-slate-500">
                  Current Assignment
                </p>

                <p className="mt-0.5 text-sm font-semibold text-slate-800">
                  {assignmentId ||
                    "Not selected"}
                </p>

              </div>

            </div>

          </div>


          <div className="p-6 lg:p-10">

            {notice && (
              <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                {notice}
              </div>
            )}


            {error && (
              <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}


            {/* =============================================
                NEW VALUATION
            ============================================= */}

            {screen ===
              "new-valuation" && (

              <div className="space-y-8">

                <SectionTitle
                  title="New Valuation Assignment"
                  subtitle="Create the engagement and upload the documents required for the valuation."
                />


                <Card className="p-6">

                  <h3 className="font-semibold text-slate-900">
                    Assignment Details
                  </h3>


                  <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-3">

                    <Input
                      label="Company Name"
                      value={
                        companyName
                      }
                      onChange={
                        setCompanyName
                      }
                      required
                    />

                    <Input
                      label="CIN"
                      value={cin}
                      onChange={setCin}
                    />

                    <Input
                      label="PAN"
                      value={pan}
                      onChange={setPan}
                    />

                    <Input
                      label="Valuation Date"
                      type="date"
                      value={
                        valuationDate
                      }
                      onChange={
                        setValuationDate
                      }
                      required
                    />

                    <Input
                      label="Engagement Date"
                      type="date"
                      value={
                        engagementDate
                      }
                      onChange={
                        setEngagementDate
                      }
                      required
                    />

                    <Input
                      label="Report Date"
                      type="date"
                      value={
                        reportDate
                      }
                      onChange={
                        setReportDate
                      }
                      required
                    />

                    <Select
                      label="Purpose"
                      value={
                        purpose
                      }
                      onChange={
                        setPurpose
                      }
                      required
                      options={[
                        "Issue of Shares / Securities",
                        "Transfer of Shares / Securities",
                        "Merger / Share Swap",
                        "Sweat Equity",
                        "ESOP",
                        "FEMA / ODI / FDI",
                        "Income-tax",
                        "Ind AS / Financial Reporting",
                        "Internal / Management",
                        "Other",
                      ]}
                    />

                    <Select
                      label="Security Type"
                      value={
                        securityType
                      }
                      onChange={
                        setSecurityType
                      }
                      required
                      options={[
                        "Equity Shares",
                        "CCPS",
                        "OCRPS",
                        "NCRPS",
                        "CCD",
                        "OCD",
                        "NCD",
                        "Share Warrants",
                        "ESOP",
                        "Sweat Equity",
                        "Business / Enterprise",
                        "Brand / Intangible Asset",
                        "Other",
                      ]}
                    />

                    <Select
                      label="Applicable Provision"
                      value={
                        applicableProvision
                      }
                      onChange={
                        setApplicableProvision
                      }
                      required
                      options={[
                        "Companies Act, 2013",
                        "FEMA",
                        "Income-tax Act",
                        "Ind AS",
                        "Multiple Regulations",
                        "Internal / Management – No Statutory Requirement",
                      ]}
                    />

                  </div>


                  <div className="mt-5">

                    <label className="mb-1.5 block text-sm font-medium text-slate-700">
                      Proposed Transaction
                    </label>

                    <textarea
                      value={
                        transactionDetails
                      }
                      onChange={(
                        event
                      ) =>
                        setTransactionDetails(
                          event.target
                            .value
                        )
                      }
                      rows={4}
                      className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none"
                      placeholder="Briefly describe the proposed transaction..."
                    />

                  </div>

                </Card>


                <Card className="p-6">

                  <h3 className="font-semibold text-slate-900">
                    Documents
                  </h3>

                  <p className="mt-1 text-sm text-slate-500">
                    Multiple files can be
                    uploaded under each
                    category.
                  </p>


                  <div className="mt-5 grid gap-4 lg:grid-cols-2">

                    <UploadField
                      label="1. Provisional Financial Statements as at Valuation Date"
                      files={
                        provisionalFiles
                      }
                      onChange={
                        setProvisionalFiles
                      }
                    />

                    <UploadField
                      label="2. Historical Audited Financial Statements"
                      files={
                        historicalFiles
                      }
                      onChange={
                        setHistoricalFiles
                      }
                    />

                    <UploadField
                      label="3. Projected Financial Statements"
                      files={
                        projectionFiles
                      }
                      onChange={
                        setProjectionFiles
                      }
                    />

                    <UploadField
                      label="4. Fully Diluted Shareholding / Capital Structure"
                      files={
                        capitalStructureFiles
                      }
                      onChange={
                        setCapitalStructureFiles
                      }
                    />

                    <UploadField
                      label="5. Debt Schedule"
                      files={
                        debtScheduleFiles
                      }
                      onChange={
                        setDebtScheduleFiles
                      }
                    />

                    <UploadField
                      label="6. Company / Business Profile"
                      files={
                        companyProfileFiles
                      }
                      onChange={
                        setCompanyProfileFiles
                      }
                    />

                    <UploadField
                      label="7. Other Relevant Documents"
                      files={
                        otherFiles
                      }
                      onChange={
                        setOtherFiles
                      }
                    />

                  </div>

                </Card>


                <Card className="p-6">

                  <h3 className="font-semibold text-slate-900">
                    Contact Person
                  </h3>


                  <div className="mt-5 grid gap-5 md:grid-cols-2">

                    <Input
                      label="Name"
                      value={
                        contactName
                      }
                      onChange={
                        setContactName
                      }
                      required
                    />

                    <Input
                      label="Designation"
                      value={
                        designation
                      }
                      onChange={
                        setDesignation
                      }
                    />

                    <Input
                      label="Mobile"
                      value={
                        mobile
                      }
                      onChange={
                        setMobile
                      }
                      required
                    />

                    <Input
                      label="Email"
                      value={
                        email
                      }
                      onChange={
                        setEmail
                      }
                      type="email"
                      required
                    />

                  </div>

                </Card>


                <div className="flex justify-end">

                  <button
                    disabled={busy}
                    onClick={
                      submitAssignment
                    }
                    className="rounded-xl bg-slate-950 px-6 py-3 text-sm font-medium text-white disabled:opacity-50"
                  >
                    {busy
                      ? "Submitting..."
                      : "Create Valuation Assignment"}
                  </button>

                </div>

              </div>
            )}


            {/* =============================================
                FINANCIAL ANALYSIS
            ============================================= */}

            {screen ===
              "financial-analysis" && (

              <div className="space-y-8">

                <div className="flex flex-wrap items-end justify-between gap-4">

                  <SectionTitle
                    title="Financial Analysis"
                    subtitle="Normalized historical, provisional and projected financial analysis."
                  />


                  <div className="flex flex-wrap items-end gap-3">

                    <div className="w-56">

                      <Input
                        label="Assignment ID"
                        value={
                          assignmentId
                        }
                        onChange={
                          setAssignmentId
                        }
                        placeholder="VAL-2026-003"
                      />

                    </div>


                    <button
                      disabled={busy}
                      onClick={
                        runFinancialAnalysis
                      }
                      className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
                    >
                      {busy
                        ? "Analyzing..."
                        : "Run Analysis"}
                    </button>

                  </div>

                </div>


                {!financialData && (

                  <Card className="p-10 text-center">

                    <p className="text-lg font-semibold text-slate-900">
                      No analysis loaded
                    </p>

                    <p className="mt-2 text-sm text-slate-500">
                      Enter an Assignment
                      ID and run Financial
                      Analysis.
                    </p>

                  </Card>
                )}


                {financialData && (
                  <>

                    <Card className="border-slate-300 p-5">

                      <div className="flex flex-wrap items-center justify-between gap-5">

                        <div>

                          <div className="flex flex-wrap items-center gap-3">

                            <h3 className="font-semibold text-slate-900">
                              Ready for
                              Valuation
                            </h3>

                            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                              Engine{" "}
                              {
                                financialData.analysis_engine_version
                              }
                            </span>

                            <StatusBadge
                              good={
                                financialData.review_summary?.data_ready_for_valuation ===
                                true
                              }
                              goodText="Data Validated"
                              badText="Review Pending"
                            />

                          </div>

                          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                            Transfer projected
                            EBIT, depreciation,
                            Capex and Change in
                            Working Capital to
                            DCF together with
                            valuation-date cash
                            and debt. All fields
                            remain editable by
                            the Registered
                            Valuer.
                          </p>

                        </div>


                        <button
                          onClick={
                            useAnalysisInValuation
                          }
                          className="rounded-xl bg-slate-950 px-5 py-3 text-sm font-medium text-white"
                        >
                          Use in Valuation →
                        </button>

                      </div>

                    </Card>


                    <CapitalStructurePanel
                      data={
                        financialData.capital_structure
                      }
                    />


                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">

                      <KpiCard
                        label="Latest Revenue"
                        value={money(
                          latestHistorical
                            ?.metrics
                            .revenue
                        )}
                        caption={
                          latestHistorical
                            ?.display
                        }
                      />

                      <KpiCard
                        label="EBITDA Margin"
                        value={percent(
                          latestHistorical
                            ?.metrics
                            .ebitda_margin
                        )}
                        caption={
                          latestHistorical
                            ?.display
                        }
                      />

                      <KpiCard
                        label="Debt / Equity"
                        value={ratio(
                          latestHistorical
                            ?.metrics
                            .debt_equity
                        )}
                        caption="Total debt / net worth"
                      />

                      <KpiCard
                        label="Interest Cover"
                        value={ratio(
                          latestHistorical
                            ?.metrics
                            .interest_coverage
                        )}
                        caption="EBITDA / Finance Cost"
                      />

                      <KpiCard
                        label="Open Review Items"
                        value={String(
                          financialData
                            .review_items ??
                            0
                        )}
                        caption="Unresolved extraction items"
                      />

                    </div>


                    <div className="grid gap-6 xl:grid-cols-2">

                      <TrendBars
                        rows={
                          combinedTrend
                        }
                      />


                      <Card className="p-5">

                        <h3 className="font-semibold text-slate-900">
                          CAGR Summary
                        </h3>


                        <div className="mt-5 grid grid-cols-2 gap-4">

                          <div className="rounded-xl bg-slate-50 p-4">

                            <p className="text-xs font-semibold uppercase text-slate-500">
                              Historical
                            </p>

                            <div className="mt-3 space-y-2 text-sm">

                              <div className="flex justify-between">
                                <span>
                                  Revenue
                                </span>
                                <strong>
                                  {percent(
                                    financialData
                                      .historical_cagr
                                      ?.revenue_cagr
                                  )}
                                </strong>
                              </div>

                              <div className="flex justify-between">
                                <span>
                                  EBITDA
                                </span>
                                <strong>
                                  {percent(
                                    financialData
                                      .historical_cagr
                                      ?.ebitda_cagr
                                  )}
                                </strong>
                              </div>

                              <div className="flex justify-between">
                                <span>
                                  PAT
                                </span>
                                <strong>
                                  {percent(
                                    financialData
                                      .historical_cagr
                                      ?.pat_cagr
                                  )}
                                </strong>
                              </div>

                            </div>

                          </div>


                          <div className="rounded-xl bg-slate-50 p-4">

                            <p className="text-xs font-semibold uppercase text-slate-500">
                              Projected
                            </p>

                            <div className="mt-3 space-y-2 text-sm">

                              <div className="flex justify-between">
                                <span>
                                  Revenue
                                </span>
                                <strong>
                                  {percent(
                                    financialData
                                      .projected_cagr
                                      ?.revenue_cagr
                                  )}
                                </strong>
                              </div>

                              <div className="flex justify-between">
                                <span>
                                  EBITDA
                                </span>
                                <strong>
                                  {percent(
                                    financialData
                                      .projected_cagr
                                      ?.ebitda_cagr
                                  )}
                                </strong>
                              </div>

                              <div className="flex justify-between">
                                <span>
                                  PAT
                                </span>
                                <strong>
                                  {percent(
                                    financialData
                                      .projected_cagr
                                      ?.pat_cagr
                                  )}
                                </strong>
                              </div>

                            </div>

                          </div>

                        </div>

                      </Card>

                    </div>


                    <MetricTable
                      title="Historical Financial Analysis"
                      rows={
                        financialData
                          .historical ||
                        []
                      }
                    />


                    <MetricTable
                      title="Provisional / Valuation Date Financials"
                      rows={
                        financialData
                          .provisional ||
                        []
                      }
                    />


                    <MetricTable
                      title="Projected Financial Analysis"
                      rows={
                        financialData
                          .projected ||
                        []
                      }
                    />


                    <WorkingCapitalTable
                      rows={[
                        ...(
                          financialData
                            .historical ||
                          []
                        ),

                        ...(
                          financialData
                            .projected ||
                          []
                        ),
                      ]}
                    />


                    <ReviewPanel
                      items={
                        financialData.review_required ||
                        []
                      }
                      summary={
                        financialData.review_summary
                      }
                      busy={busy}
                      onUpdate={
                        updateReviewItem
                      }
                    />


                    <div className="grid gap-6 lg:grid-cols-2">

                      <Card className="p-5">

                        <h3 className="font-semibold text-slate-900">
                          Automated
                          Observations
                        </h3>


                        <div className="mt-4 space-y-3">

                          {(
                            financialData
                              .observations ||
                            []
                          ).length ===
                          0 ? (

                            <p className="text-sm text-slate-500">
                              No observations
                              generated.
                            </p>

                          ) : (

                            financialData
                              .observations
                              ?.map(
                                (
                                  observation,
                                  index
                                ) => (

                                  <div
                                    key={
                                      index
                                    }
                                    className="rounded-xl border border-slate-200 p-4"
                                  >

                                    <p className="text-sm font-semibold text-slate-900">
                                      {
                                        observation.category
                                      }
                                    </p>

                                    <p className="mt-2 text-sm text-slate-600">
                                      {
                                        observation.message
                                      }
                                    </p>

                                  </div>
                                )
                              )
                          )}

                        </div>

                      </Card>


                      <Card className="p-5">

                        <h3 className="font-semibold text-slate-900">
                          Data Quality &
                          Cross-checks
                        </h3>


                        <div className="mt-4 space-y-2">

                          {financialData
                            .cross_checks
                            ?.map(
                              (
                                check,
                                index
                              ) => (

                                <div
                                  key={
                                    index
                                  }
                                  className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3 text-sm"
                                >

                                  <div>

                                    <p className="font-medium text-slate-800">
                                      {
                                        check.check
                                      }
                                    </p>

                                    <p className="text-xs text-slate-500">
                                      {
                                        check.bucket
                                      }{" "}
                                      ·{" "}
                                      {
                                        check.period
                                      }
                                    </p>

                                  </div>


                                  <StatusBadge
                                    good={
                                      check.status ===
                                      "OK"
                                    }
                                    goodText="OK"
                                    badText="Review"
                                  />

                                </div>
                              )
                            )}

                        </div>

                      </Card>

                    </div>

                  </>
                )}

              </div>
            )}


            {/* =============================================
                VALUATION
            ============================================= */}

            {screen ===
              "valuation" && (

              <div className="space-y-8">

                <SectionTitle
                  title="Valuation"
                  subtitle="Deterministic valuation calculations with valuer-controlled assumptions."
                />


                {financialData && (

                  <Card className="border-emerald-200 bg-emerald-50/30 p-5">

                    <div className="flex flex-wrap items-center justify-between gap-4">

                      <div>

                        <p className="font-semibold text-slate-900">
                          Financial Analysis
                          Linked
                        </p>

                        <p className="mt-1 text-sm text-slate-600">
                          DCF inputs and fully diluted shares can be
                          refreshed from the extracted financial and
                          capital-structure schedules.
                        </p>

                        {financialData.capital_structure?.available && (
                          <p className="mt-2 text-xs text-slate-500">
                            Fully diluted shares from analysis: {money(
                              financialData.capital_structure.fully_diluted_shares
                            )} · Status: {financialData.capital_structure.status || "Available"}
                          </p>
                        )}

                      </div>


                      <button
                        onClick={
                          useAnalysisInValuation
                        }
                        className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium"
                      >
                        Refresh from
                        Analysis
                      </button>

                    </div>

                  </Card>
                )}


                {/* WACC & MARKET DATA */}

                <Card className="p-6">

                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <h3 className="font-semibold text-slate-900">
                        WACC & Market Data
                      </h3>
                      <p className="mt-1 text-sm text-slate-500">
                        Record valuation-date market assumptions, source references and the valuer-approved discount rate. The calculation is deterministic and performed by the Python backend.
                      </p>
                    </div>

                    <StatusBadge
                      good={waccApproved}
                      goodText="Valuer Approved"
                      badText="Approval Required"
                    />
                  </div>

                  <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
                    <Input
                      label="Risk-free Rate (%)"
                      value={riskFreeRate}
                      onChange={(value) => {
                        setRiskFreeRate(value);
                        setWaccApproved(false);
                      }}
                      type="number"
                      required
                    />

                    <Input
                      label="Equity Risk Premium (%)"
                      value={equityRiskPremium}
                      onChange={(value) => {
                        setEquityRiskPremium(value);
                        setWaccApproved(false);
                      }}
                      type="number"
                      required
                    />

                    <Input
                      label="Beta"
                      value={beta}
                      onChange={(value) => {
                        setBeta(value);
                        setWaccApproved(false);
                      }}
                      type="number"
                      required
                    />

                    <Input
                      label="Company-specific Risk Premium (%)"
                      value={companySpecificRiskPremium}
                      onChange={(value) => {
                        setCompanySpecificRiskPremium(value);
                        setWaccApproved(false);
                      }}
                      type="number"
                    />

                    <Input
                      label="Pre-tax Cost of Debt (%)"
                      value={preTaxCostOfDebt}
                      onChange={(value) => {
                        setPreTaxCostOfDebt(value);
                        setWaccApproved(false);
                      }}
                      type="number"
                      required
                    />

                    <Input
                      label="Equity Weight (%)"
                      value={equityWeight}
                      onChange={(value) => {
                        setEquityWeight(value);
                        setWaccApproved(false);
                      }}
                      type="number"
                      required
                    />

                    <Input
                      label="Debt Weight (%)"
                      value={debtWeight}
                      onChange={(value) => {
                        setDebtWeight(value);
                        setWaccApproved(false);
                      }}
                      type="number"
                      required
                    />

                    <Input
                      label="Market Data Date"
                      value={marketDataDate}
                      onChange={setMarketDataDate}
                      type="date"
                    />
                  </div>

                  <div className="mt-5 grid gap-5 md:grid-cols-2">
                    <Input
                      label="Risk-free Rate Source"
                      value={riskFreeSource}
                      onChange={setRiskFreeSource}
                      placeholder="e.g. 10-year Government Security yield"
                    />

                    <Input
                      label="ERP Source"
                      value={erpSource}
                      onChange={setErpSource}
                      placeholder="e.g. published country equity risk premium source"
                    />

                    <Input
                      label="Beta Source"
                      value={betaSource}
                      onChange={setBetaSource}
                      placeholder="e.g. comparable companies / industry beta source"
                    />

                    <Input
                      label="Cost of Debt Source"
                      value={debtSource}
                      onChange={setDebtSource}
                      placeholder="e.g. borrowing rate / sanction letter / debt schedule"
                    />
                  </div>

                  <div className="mt-5">
                    <label className="mb-1.5 block text-sm font-medium text-slate-700">
                      WACC Notes / Valuer Rationale
                    </label>
                    <textarea
                      value={waccNotes}
                      onChange={(event) =>
                        setWaccNotes(event.target.value)
                      }
                      rows={3}
                      className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none"
                      placeholder="Document any normalization, peer selection, override or professional judgement."
                    />
                  </div>

                  <div className="mt-5 flex flex-wrap gap-3">
                    <button
                      onClick={fetchMarketDataSuggestions}
                      disabled={marketDataBusy || busy}
                      className="rounded-xl border border-slate-950 bg-white px-5 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-50"
                    >
                      {marketDataBusy
                        ? "Fetching..."
                        : "Fetch / Suggest Market Data"}
                    </button>

                    <button
                      onClick={calculateWacc}
                      disabled={busy || marketDataBusy}
                      className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
                    >
                      {busy ? "Calculating..." : "Calculate WACC"}
                    </button>

                    <button
                      onClick={approveWaccForDcf}
                      disabled={!waccAnalysis}
                      className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-800 disabled:opacity-40"
                    >
                      Approve & Use in DCF
                    </button>
                  </div>

                  {marketSuggestion && (
                    <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">
                            System Suggestions Loaded
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            Valuation date: {marketSuggestion.valuation_date || "—"}
                            {marketSuggestion.industry
                              ? ` · Industry: ${marketSuggestion.industry}`
                              : ""}
                          </p>
                        </div>

                        <StatusBadge
                          good={marketSuggestion.status === "SUGGESTIONS_READY"}
                          goodText="Suggestions Ready"
                          badText="Partial Suggestions"
                        />
                      </div>

                      <div className="mt-4 grid gap-3 lg:grid-cols-2">
                        <div className="rounded-lg bg-white p-3 text-xs leading-5 text-slate-600">
                          <strong>Risk-free basis:</strong>{" "}
                          {marketSuggestion.basis?.risk_free_rate || "—"}
                        </div>

                        <div className="rounded-lg bg-white p-3 text-xs leading-5 text-slate-600">
                          <strong>ERP basis:</strong>{" "}
                          {marketSuggestion.basis?.equity_risk_premium || "—"}
                        </div>

                        <div className="rounded-lg bg-white p-3 text-xs leading-5 text-slate-600">
                          <strong>Beta basis:</strong>{" "}
                          {marketSuggestion.basis?.beta || "—"}
                        </div>

                        <div className="rounded-lg bg-white p-3 text-xs leading-5 text-slate-600">
                          <strong>Cost of debt basis:</strong>{" "}
                          {marketSuggestion.basis?.cost_of_debt || "—"}
                        </div>
                      </div>

                      {(marketSuggestion.warnings || []).length > 0 && (
                        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
                          <p className="text-xs font-semibold text-amber-800">
                            Valuer review points
                          </p>
                          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-amber-800">
                            {(marketSuggestion.warnings || []).map(
                              (warning, index) => (
                                <li key={index}>{warning}</li>
                              )
                            )}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {waccAnalysis && (
                    <>
                      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                        <KpiCard
                          label="Cost of Equity"
                          value={percent(waccAnalysis.cost_of_equity_percent)}
                          caption="Rf + Beta × ERP + CSRP"
                        />

                        <KpiCard
                          label="After-tax Cost of Debt"
                          value={percent(waccAnalysis.after_tax_cost_of_debt_percent)}
                          caption="Pre-tax Kd × (1 − Tax)"
                        />

                        <KpiCard
                          label="Calculated WACC"
                          value={percent(waccAnalysis.wacc_percent)}
                          caption="Python deterministic calculation"
                        />

                        <KpiCard
                          label="Capital Weights"
                          value={`${money(waccAnalysis.equity_weight_percent)} / ${money(waccAnalysis.debt_weight_percent)}`}
                          caption="Equity % / Debt %"
                        />
                      </div>

                      <div className="mt-6 overflow-x-auto rounded-xl border border-slate-200">
                        <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                          <p className="text-sm font-semibold text-slate-900">
                            WACC Sensitivity
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            Beta varies by ±0.20 and pre-tax cost of debt by ±1.00%.
                          </p>
                        </div>

                        <table className="w-full min-w-[620px] text-sm">
                          <thead className="bg-white text-slate-600">
                            <tr>
                              <th className="px-4 py-3 text-left">Beta</th>
                              {(waccAnalysis.sensitivity?.rows?.[0]?.values || []).map(
                                (cell, index) => (
                                  <th
                                    key={index}
                                    className="px-4 py-3 text-right"
                                  >
                                    Kd {cell.pre_tax_cost_of_debt_percent.toFixed(2)}%
                                  </th>
                                )
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {(waccAnalysis.sensitivity?.rows || []).map(
                              (row, rowIndex) => (
                                <tr
                                  key={rowIndex}
                                  className="border-t border-slate-100"
                                >
                                  <td className="px-4 py-3 font-medium">
                                    {row.beta.toFixed(2)}
                                  </td>
                                  {row.values.map((cell, cellIndex) => (
                                    <td
                                      key={cellIndex}
                                      className="px-4 py-3 text-right"
                                    >
                                      {cell.wacc_percent.toFixed(2)}%
                                    </td>
                                  ))}
                                </tr>
                              )
                            )}
                          </tbody>
                        </table>
                      </div>

                      <div className="mt-4 rounded-xl bg-slate-50 p-4 text-xs leading-5 text-slate-600">
                        <strong>Source date:</strong>{" "}
                        {waccAnalysis.market_data_date || "Not recorded"}.
                        The calculated rate is not used in DCF until the valuer clicks
                        <strong> Approve & Use in DCF</strong>.
                      </div>
                    </>
                  )}

                </Card>


                {/* GENERAL DCF INPUTS */}

                <Card className="p-6">

                  <div className="flex flex-wrap items-center justify-between gap-4">

                    <h3 className="font-semibold text-slate-900">
                      DCF Assumptions
                    </h3>


                    <StatusBadge
                      good={
                        dcfGeneralInputsReady
                      }
                      goodText="General Inputs Ready"
                      badText="Inputs Required"
                    />

                  </div>


                  <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-4">

                    <Input
                      label="Assignment ID"
                      value={
                        assignmentId
                      }
                      onChange={
                        setAssignmentId
                      }
                    />


                    <Input
                      label="Fully Diluted Shares"
                      value={
                        dilutedShares
                      }
                      onChange={
                        setDilutedShares
                      }
                      type="number"
                    />


                    <Input
                      label="Tax Rate (%)"
                      value={
                        taxRate
                      }
                      onChange={
                        setTaxRate
                      }
                      type="number"
                    />


                    <div>
                      <Input
                        label="WACC (%)"
                        value={wacc}
                        onChange={(value) => {
                          setWacc(value);
                          setWaccApproved(false);
                          setDcfResult(null);
                          setWeightedResult(null);
                        }}
                        type="number"
                      />
                      <p className="mt-1 text-[11px] text-slate-500">
                        {waccApproved
                          ? "Valuer-approved WACC from WACC working"
                          : "Manual / not yet approved from WACC working"}
                      </p>
                    </div>


                    <Input
                      label="Terminal Growth (%)"
                      value={
                        terminalGrowth
                      }
                      onChange={
                        setTerminalGrowth
                      }
                      type="number"
                    />


                    <Input
                      label="Cash"
                      value={
                        cash
                      }
                      onChange={
                        setCash
                      }
                      type="number"
                    />


                    <Input
                      label="Debt"
                      value={
                        debt
                      }
                      onChange={
                        setDebt
                      }
                      type="number"
                    />


                    <Input
                      label="Non-operating Assets"
                      value={
                        nonOperatingAssets
                      }
                      onChange={
                        setNonOperatingAssets
                      }
                      type="number"
                    />

                  </div>

                </Card>


                {/* DCF INPUT TABLE */}

                <Card className="overflow-hidden">

                  <div className="border-b border-slate-200 px-5 py-4">

                    <div className="flex flex-wrap items-center justify-between gap-3">

                      <div>

                        <h3 className="font-semibold text-slate-900">
                          DCF Projection
                          Inputs
                        </h3>

                        <p className="mt-1 text-xs text-slate-500">
                          FCFF = EBIT ×
                          (1 − Tax Rate) +
                          Depreciation −
                          Capex − Change in
                          Working Capital
                        </p>

                      </div>


                      <StatusBadge
                        good={
                          dcfRowsReady
                        }
                        goodText="Projection Inputs Ready"
                        badText="Projection Inputs Incomplete"
                      />

                    </div>

                  </div>


                  <div className="overflow-x-auto">

                    <table className="w-full min-w-[1250px] text-sm">

                      <thead className="bg-slate-50 text-slate-600">

                        <tr>

                          <th className="px-4 py-3 text-left">
                            Year
                          </th>

                          <th className="px-4 py-3 text-right">
                            EBIT
                          </th>

                          <th className="px-4 py-3 text-right">
                            Depreciation
                          </th>

                          <th className="px-4 py-3 text-right">
                            Capex
                          </th>

                          <th className="px-4 py-3 text-right">
                            Change WC
                          </th>

                          <th className="px-4 py-3 text-right">
                            NOPAT
                          </th>

                          <th className="px-4 py-3 text-right">
                            FCFF
                          </th>

                          <th className="px-4 py-3 text-center">
                            Status
                          </th>

                        </tr>

                      </thead>


                      <tbody>

                        {projections.map(
                          (
                            row,
                            index
                          ) => {

                            const preview =
                              dcfPreview[
                                index
                              ];

                            return (

                              <tr
                                key={
                                  index
                                }
                                className="border-t border-slate-100"
                              >

                                <td className="px-4 py-3">

                                  <input
                                    value={
                                      row.year
                                    }
                                    onChange={(
                                      event
                                    ) =>
                                      updateProjection(
                                        index,
                                        "year",
                                        event
                                          .target
                                          .value
                                      )
                                    }
                                    className="w-28 rounded-lg border border-slate-300 px-3 py-2"
                                  />

                                </td>


                                <td className="px-4 py-3">

                                  <input
                                    type="number"
                                    value={
                                      row.ebit
                                    }
                                    onChange={(
                                      event
                                    ) =>
                                      updateProjection(
                                        index,
                                        "ebit",
                                        event
                                          .target
                                          .value
                                      )
                                    }
                                    className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-right"
                                  />

                                  {row.ebit_source && (
                                    <p className="mt-1 text-[10px] text-slate-400">
                                      {
                                        row.ebit_source
                                      }
                                    </p>
                                  )}

                                </td>


                                <td className="px-4 py-3">

                                  <input
                                    type="number"
                                    value={
                                      row.depreciation
                                    }
                                    onChange={(
                                      event
                                    ) =>
                                      updateProjection(
                                        index,
                                        "depreciation",
                                        event
                                          .target
                                          .value
                                      )
                                    }
                                    className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-right"
                                  />

                                  {row.depreciation_source && (
                                    <p className="mt-1 text-[10px] text-slate-400">
                                      {
                                        row.depreciation_source
                                      }
                                    </p>
                                  )}

                                </td>


                                <td className="px-4 py-3">

                                  <input
                                    type="number"
                                    value={
                                      row.capex
                                    }
                                    onChange={(
                                      event
                                    ) =>
                                      updateProjection(
                                        index,
                                        "capex",
                                        event
                                          .target
                                          .value
                                      )
                                    }
                                    className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-right"
                                  />

                                  {row.capex_source && (
                                    <p className="mt-1 text-[10px] text-slate-400">
                                      Source:{" "}
                                      {
                                        row.capex_source
                                      }
                                    </p>
                                  )}

                                </td>


                                <td className="px-4 py-3">

                                  <input
                                    type="number"
                                    value={
                                      row.change_working_capital
                                    }
                                    onChange={(
                                      event
                                    ) =>
                                      updateProjection(
                                        index,
                                        "change_working_capital",
                                        event
                                          .target
                                          .value
                                      )
                                    }
                                    className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-right"
                                  />

                                  {row.working_capital_source && (
                                    <p className="mt-1 text-[10px] text-slate-400">
                                      Source:{" "}
                                      {
                                        row.working_capital_source
                                      }
                                    </p>
                                  )}

                                </td>


                                <td className="px-4 py-3 text-right font-medium text-slate-700">
                                  {money(
                                    preview
                                      ?.nopat
                                  )}
                                </td>


                                <td className="px-4 py-3 text-right font-semibold text-slate-900">
                                  {money(
                                    preview
                                      ?.fcff
                                  )}
                                </td>


                                <td className="px-4 py-3 text-center">

                                  <StatusBadge
                                    good={
                                      preview
                                        ?.ready ||
                                      false
                                    }
                                    goodText="Ready"
                                    badText="Missing"
                                  />

                                </td>

                              </tr>
                            );
                          }
                        )}

                      </tbody>

                    </table>

                  </div>

                </Card>


                {/* READINESS */}

                <Card className="p-6">

                  <div className="flex flex-wrap items-center justify-between gap-4">

                    <div>

                      <h3 className="font-semibold text-slate-900">
                        DCF Readiness
                      </h3>

                      <p className="mt-1 text-sm text-slate-500">
                        The valuation will
                        only run when all
                        required deterministic
                        inputs are available.
                      </p>

                    </div>


                    <StatusBadge
                      good={
                        dcfReady
                      }
                      goodText="Ready to Calculate"
                      badText="Not Ready"
                    />

                  </div>


                  <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">

                    <div className="rounded-xl border border-slate-200 p-4">

                      <p className="text-sm font-medium">
                        Projected EBIT
                      </p>

                      <div className="mt-2">
                        <StatusBadge
                          good={
                            projections.every(
                              (
                                row
                              ) =>
                                row.ebit !==
                                ""
                            )
                          }
                        />
                      </div>

                    </div>


                    <div className="rounded-xl border border-slate-200 p-4">

                      <p className="text-sm font-medium">
                        Depreciation
                      </p>

                      <div className="mt-2">
                        <StatusBadge
                          good={
                            projections.every(
                              (
                                row
                              ) =>
                                row.depreciation !==
                                ""
                            )
                          }
                        />
                      </div>

                    </div>


                    <div className="rounded-xl border border-slate-200 p-4">

                      <p className="text-sm font-medium">
                        Capex
                      </p>

                      <div className="mt-2">
                        <StatusBadge
                          good={
                            projections.every(
                              (
                                row
                              ) =>
                                row.capex !==
                                ""
                            )
                          }
                        />
                      </div>

                    </div>


                    <div className="rounded-xl border border-slate-200 p-4">

                      <p className="text-sm font-medium">
                        Change in Working
                        Capital
                      </p>

                      <div className="mt-2">
                        <StatusBadge
                          good={
                            projections.every(
                              (
                                row
                              ) =>
                                row.change_working_capital !==
                                ""
                            )
                          }
                        />
                      </div>

                    </div>

                  </div>


                  <button
                    onClick={
                      calculateDCF
                    }
                    disabled={
                      busy ||
                      !dcfReady
                    }
                    className="mt-6 rounded-xl bg-slate-950 px-6 py-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {busy
                      ? "Calculating..."
                      : "Calculate DCF"}
                  </button>

                </Card>


                {/* DCF RESULT */}

                {dcfResult && (

                  <div className="grid gap-4 sm:grid-cols-2">

                    <KpiCard
                      label="DCF Equity Value"
                      value={money(
                        dcfResult
                          .equity_value
                      )}
                    />

                    <KpiCard
                      label="DCF Value / Share"
                      value={money(
                        dcfResult
                          .value_per_share
                      )}
                    />

                  </div>
                )}


                {dcfResult?.sensitivity?.rows?.length > 0 && (

                  <Card className="overflow-hidden">

                    <div className="border-b border-slate-200 px-5 py-4">

                      <h3 className="font-semibold text-slate-900">
                        DCF Sensitivity — Value Per Share
                      </h3>

                      <p className="mt-1 text-xs text-slate-500">
                        Sensitivity across WACC and terminal-growth assumptions. The central case corresponds to the currently selected DCF assumptions.
                      </p>

                    </div>


                    <div className="overflow-x-auto">

                      <table className="w-full min-w-[760px] text-sm">

                        <thead className="bg-slate-50 text-slate-600">

                          <tr>

                            <th className="px-4 py-3 text-left">
                              Terminal Growth / WACC
                            </th>

                            {(dcfResult.sensitivity.wacc_values_percent || []).map(
                              (value: number, index: number) => (
                                <th
                                  key={index}
                                  className="px-4 py-3 text-right"
                                >
                                  {Number(value).toFixed(2)}%
                                </th>
                              )
                            )}

                          </tr>

                        </thead>


                        <tbody>

                          {(dcfResult.sensitivity.rows || []).map(
                            (row: any, rowIndex: number) => (

                              <tr
                                key={rowIndex}
                                className="border-t border-slate-100"
                              >

                                <td className="px-4 py-3 font-medium">
                                  {Number(row.terminal_growth).toFixed(2)}%
                                </td>

                                {(row.values || []).map(
                                  (cell: any, cellIndex: number) => {

                                    const isBase =
                                      Math.abs(
                                        Number(cell.wacc) -
                                        Number(dcfResult.sensitivity.base_wacc_percent)
                                      ) < 0.001 &&
                                      Math.abs(
                                        Number(row.terminal_growth) -
                                        Number(dcfResult.sensitivity.base_terminal_growth_percent)
                                      ) < 0.001;

                                    return (
                                      <td
                                        key={cellIndex}
                                        className={`px-4 py-3 text-right ${
                                          isBase
                                            ? "bg-emerald-50 font-semibold text-emerald-800"
                                            : ""
                                        }`}
                                      >
                                        {cell.status === "OK"
                                          ? money(cell.value_per_share)
                                          : "N/A"}
                                      </td>
                                    );
                                  }
                                )}

                              </tr>
                            )
                          )}

                        </tbody>

                      </table>

                    </div>

                  </Card>
                )}


                {/* NAV */}

                <Card className="p-6">

                  <div className="flex flex-wrap items-start justify-between gap-4">

                    <div>

                      <h3 className="font-semibold text-slate-900">
                        Net Asset Value
                      </h3>

                      <p className="mt-1 text-sm text-slate-500">
                        The system uses the valuation-date balance sheet as the starting point. Review and edit the values for fair-value adjustments, contingent items and other NAV adjustments.
                      </p>

                    </div>

                    <StatusBadge
                      good={navAutoPopulated}
                      goodText="Starting Point Auto-populated"
                      badText="Manual Input"
                    />

                  </div>


                  <div className="mt-5 grid gap-5 md:grid-cols-2">

                    <Input
                      label="Adjusted / Considered Assets"
                      value={
                        adjustedAssets
                      }
                      onChange={(value) => {
                        setAdjustedAssets(value);
                        setNavAutoPopulated(false);
                        setNavResult(null);
                        setWeightedResult(null);
                      }}
                      type="number"
                    />

                    <Input
                      label="Adjusted / Considered Liabilities"
                      value={
                        adjustedLiabilities
                      }
                      onChange={(value) => {
                        setAdjustedLiabilities(value);
                        setNavAutoPopulated(false);
                        setNavResult(null);
                        setWeightedResult(null);
                      }}
                      type="number"
                    />

                  </div>

                  {navAutoPopulated && (
                    <p className="mt-3 text-xs leading-5 text-slate-500">
                      Auto-populated basis: Total Assets from the valuation-date balance sheet; total liabilities derived as Total Assets less Net Worth. These are only starting values and remain fully editable by the Registered Valuer.
                    </p>
                  )}


                  <button
                    onClick={
                      calculateNAV
                    }
                    disabled={busy}
                    className="mt-5 rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-medium text-white"
                  >
                    Calculate NAV
                  </button>


                  {navResult && (

                    <div className="mt-5 grid gap-4 sm:grid-cols-2">

                      <KpiCard
                        label="NAV Equity Value"
                        value={money(
                          navResult
                            .equity_value
                        )}
                      />

                      <KpiCard
                        label="NAV Value / Share"
                        value={money(
                          navResult
                            .value_per_share
                        )}
                      />

                    </div>
                  )}

                </Card>


                {/* WEIGHTAGE */}

                <Card className="p-6">

                  <h3 className="font-semibold text-slate-900">
                    Method Weightage
                  </h3>


                  <div className="mt-5 grid gap-5 md:grid-cols-2">

                    <Input
                      label="DCF Weight (%)"
                      value={
                        dcfWeight
                      }
                      onChange={
                        setDcfWeight
                      }
                      type="number"
                    />

                    <Input
                      label="NAV Weight (%)"
                      value={
                        navWeight
                      }
                      onChange={
                        setNavWeight
                      }
                      type="number"
                    />

                  </div>


                  <p className="mt-3 text-xs text-slate-500">
                    Total Weight:{" "}
                    <strong>
                      {Number(
                        dcfWeight
                      ) +
                        Number(
                          navWeight
                        )}
                      %
                    </strong>
                  </p>


                  <button
                    onClick={
                      calculateWeightage
                    }
                    disabled={busy}
                    className="mt-5 rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-medium text-white"
                  >
                    Calculate Concluded
                    Value
                  </button>


                  {weightedResult && (

                    <div className="mt-5 grid gap-4 sm:grid-cols-2">

                      <KpiCard
                        label="Concluded Equity Value"
                        value={money(
                          weightedResult
                            .concluded_value
                        )}
                      />

                      <KpiCard
                        label="Concluded Value / Share"
                        value={money(
                          weightedResult
                            .value_per_share
                        )}
                      />

                    </div>
                  )}


                  {weightedResult && (

                    <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-5">

                      <div className="flex flex-wrap items-start justify-between gap-4">

                        <div>

                          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                            Valuation Conclusion
                          </p>

                          <p className="mt-2 text-2xl font-semibold text-slate-950">
                            Rs. {money(weightedResult.value_per_share)} per share
                          </p>

                          <p className="mt-1 text-sm text-slate-600">
                            Concluded Equity Value: {money(weightedResult.concluded_value)}
                          </p>

                        </div>

                        <StatusBadge
                          good={
                            financialData?.review_summary?.final_report_ready === true
                          }
                          goodText="Ready for Final Valuer Review"
                          badText="Draft Only — Review Pending"
                        />

                      </div>

                      <p className="mt-4 text-xs leading-5 text-slate-600">
                        This conclusion is generated from the selected method weights and remains subject to Registered Valuer review, including methodology, assumptions, market data, NAV adjustments and outstanding data-review items.
                      </p>

                    </div>
                  )}

                </Card>


                {/* OUTPUTS */}

                <Card className="p-6">

                  <h3 className="font-semibold text-slate-900">
                    Outputs
                  </h3>

                  <p className="mt-1 text-sm text-slate-500">
                    Generate the consolidated Excel working and draft valuation report containing DCF, NAV, WACC, sensitivity, capital structure and review-readiness information.
                  </p>

                  <div className="mt-4 rounded-xl bg-slate-50 p-4">

                    <div className="flex flex-wrap items-center justify-between gap-3">

                      <div>

                        <p className="text-sm font-medium text-slate-900">
                          Output Readiness
                        </p>

                        <p className="mt-1 text-xs text-slate-500">
                          Draft outputs can be generated at any stage. Final issuance remains subject to valuer approval.
                        </p>

                      </div>

                      <StatusBadge
                        good={
                          financialData?.review_summary?.final_report_ready === true
                        }
                        goodText="Ready for Final Review"
                        badText="Draft Only"
                      />

                    </div>

                  </div>


                  <div className="mt-5 flex flex-wrap gap-3">

                    <button
                      disabled={busy}
                      onClick={
                        generateOutputs
                      }
                      className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-medium text-white"
                    >
                      Generate Excel &
                      Draft Report
                    </button>


                    {assignmentId && (
                      <>

                        <a
                          href={`${API_BASE}/outputs/${assignmentId}/excel`}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700"
                        >
                          Download Excel
                          Working
                        </a>


                        <a
                          href={`${API_BASE}/outputs/${assignmentId}/word`}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700"
                        >
                          Download Draft
                          Valuation Report
                        </a>

                      </>
                    )}

                  </div>

                </Card>

              </div>
            )}

          </div>

        </main>

      </div>

    </div>
  );
}