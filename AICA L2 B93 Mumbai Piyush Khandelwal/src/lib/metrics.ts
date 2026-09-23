import { runQuery } from "./query/engine";
import type { Aggregation } from "./types";

export interface Metric {
  id: string;
  label: string;
  value: number;
  change: number | null;
  series: { i: number; v: number }[];
  format: "currency" | "compact";
}

function monthly(dataset: string, field: string, agg: Aggregation = "sum") {
  const res = runQuery({
    sourceId: "tally",
    dataset,
    grain: "month",
    measures: [{ field, aggregation: agg }],
    limit: 24,
  });
  return res.rows.map((r) => Number(r[field]) || 0);
}

function metric(id: string, label: string, values: number[], format: Metric["format"] = "currency"): Metric {
  const value = values.reduce((a, b) => a + b, 0);
  const last = values[values.length - 1] ?? 0;
  const prev = values[values.length - 2] ?? 0;
  return {
    id,
    label,
    value,
    change: prev ? ((last - prev) / Math.abs(prev)) * 100 : null,
    series: values.map((v, i) => ({ i, v })),
    format,
  };
}

function scalar(dataset: string, field: string) {
  const res = runQuery({
    sourceId: "tally",
    dataset,
    groupBy: ["__all"],
    measures: [{ field, aggregation: "sum" }],
  });
  return Number(res.rows[0]?.[field]) || 0;
}

/** Headline workspace metrics, derived through the same query engine as widgets. */
export function headlineMetrics(): Metric[] {
  const revenue = monthly("sales_invoices", "invoice_amount");
  const profit = monthly("sales_invoices", "profit");
  const expenses = monthly("expenses", "amount");
  const receipts = monthly("payments", "amount");
  const orders = monthly("sales_invoices", "quantity");
  const purchases = monthly("purchase_invoices", "bill_amount");

  const receivables = scalar("customers", "outstanding");
  const payables = scalar("vendors", "payable");
  const cash = receipts.reduce((a, b) => a + b, 0) - purchases.reduce((a, b) => a + b, 0);

  return [
    metric("revenue", "Revenue", revenue),
    metric("expenses", "Expenses", expenses),
    metric("profit", "Net Profit", profit),
    {
      id: "receivables",
      label: "Receivables",
      value: receivables,
      change: null,
      series: [],
      format: "currency",
    },
    { id: "payables", label: "Payables", value: payables, change: null, series: [], format: "currency" },
    {
      id: "cash",
      label: "Cash Balance",
      value: cash,
      change: null,
      series: receipts.map((v, i) => ({ i, v })),
      format: "currency",
    },
    metric("receipts", "Collections", receipts),
    metric("orders", "Units Sold", orders, "compact"),
  ];
}
