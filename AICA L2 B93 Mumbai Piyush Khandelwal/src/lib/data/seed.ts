import type {
  AlertRule,
  AppNotification,
  Connection,
  Dashboard,
  Member,
  Report,
  ScheduledReport,
  Widget,
  WorkspaceSettings,
} from "../types";

export const uid = () => Math.random().toString(36).slice(2, 10);

let n = 0;
const wid = (prefix: string) => `${prefix}-${++n}`;

const kpi = (
  title: string,
  dataset: string,
  field: string,
  opts: Partial<Widget["options"]> = {},
  w = 3,
): Widget => ({
  id: wid("kpi"),
  type: "kpi",
  title,
  options: { format: "currency", sparkline: true, drilldown: true, ...opts },
  layout: { w, h: 2 },
  query: {
    sourceId: "tally",
    dataset,
    measures: [{ field, aggregation: "sum" }],
  },
});

export const DEFAULT_SETTINGS: WorkspaceSettings = {
  workspaceName: "Acme Industries",
  currency: "INR",
  numberSystem: "indian",
  dateFormat: "DD/MM/YYYY",
  timezone: "Asia/Kolkata",
  compactNumbers: true,
  theme: "system",
};

function executiveOverview(): Dashboard {
  return {
    id: "executive-overview",
    name: "Executive Overview",
    description: "Company-wide performance at a glance.",
    tabs: ["Overview", "Detail"],
    visibility: "workspace",
    favourite: true,
    updatedAt: new Date().toISOString(),
    filters: [
      { id: "date", label: "Date range", field: "invoice_date", type: "date-range", value: "last_12m" },
      { id: "branch", label: "Branch", field: "branch", type: "select", value: "All" },
      { id: "region", label: "Region", field: "region", type: "select", value: "All" },
    ],
    widgets: [
      kpi("Revenue", "sales_invoices", "invoice_amount"),
      kpi("Gross Profit", "sales_invoices", "profit"),
      kpi("Expenses", "expenses", "amount"),
      kpi("Receivables", "customers", "outstanding", { sparkline: false }),
      {
        id: wid("chart"),
        type: "area",
        title: "Revenue trend",
        subtitle: "Monthly invoiced value",
        options: { format: "currency", showGrid: true, showLegend: false, colorIndex: 0 },
        layout: { w: 8, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "sales_invoices",
          dateField: "invoice_date",
          grain: "month",
          measures: [{ field: "invoice_amount", aggregation: "sum" }],
        },
      },
      {
        id: wid("chart"),
        type: "pie",
        title: "Revenue by region",
        options: { donut: true, format: "currency", showLegend: true },
        layout: { w: 4, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "sales_invoices",
          groupBy: ["region"],
          measures: [{ field: "invoice_amount", aggregation: "sum" }],
        },
      },
      {
        id: wid("chart"),
        type: "bar",
        title: "Top customers",
        subtitle: "By invoiced value",
        options: { horizontal: true, format: "currency", colorIndex: 1 },
        layout: { w: 6, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "sales_invoices",
          groupBy: ["customer"],
          measures: [{ field: "invoice_amount", aggregation: "sum" }],
          limit: 7,
        },
      },
      {
        id: wid("chart"),
        type: "bar",
        title: "Expenses by category",
        options: { format: "currency", colorIndex: 4 },
        layout: { w: 6, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "expenses",
          groupBy: ["category"],
          measures: [{ field: "amount", aggregation: "sum" }],
          limit: 8,
        },
      },
      {
        id: wid("table"),
        type: "table",
        title: "Recent invoices",
        options: { format: "currency" },
        layout: { w: 12, h: 5 },
        query: {
          sourceId: "tally",
          dataset: "sales_invoices",
          dimensions: ["invoice_no", "invoice_date", "customer", "branch", "invoice_amount", "tax_amount", "status"],
          sort: [{ field: "invoice_date", dir: "desc" }],
          limit: 60,
        },
      },
    ],
  };
}

function financeDashboard(): Dashboard {
  return {
    id: "finance",
    name: "Finance Dashboard",
    description: "P&L, working capital and GST position.",
    tabs: ["Overview"],
    visibility: "workspace",
    updatedAt: new Date().toISOString(),
    filters: [{ id: "date", label: "Date range", field: "invoice_date", type: "date-range", value: "last_12m" }],
    widgets: [
      kpi("Revenue", "sales_invoices", "invoice_amount"),
      kpi("Purchases", "purchase_invoices", "bill_amount"),
      kpi("Payables", "vendors", "payable", { sparkline: false }),
      kpi("Receipts", "payments", "amount"),
      {
        id: wid("chart"),
        type: "line",
        title: "Receipts vs purchases",
        options: { format: "currency", showGrid: true, showLegend: true },
        layout: { w: 8, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "payments",
          dateField: "payment_date",
          grain: "month",
          measures: [{ field: "amount", aggregation: "sum" }],
        },
      },
      {
        id: wid("gauge"),
        type: "gauge",
        title: "Collection target",
        subtitle: "Against ₹5Cr quarterly target",
        options: { format: "currency", target: 50000000 },
        layout: { w: 4, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "payments",
          measures: [{ field: "amount", aggregation: "sum" }],
        },
      },
      {
        id: wid("table"),
        type: "table",
        title: "GST summary",
        subtitle: "CGST / SGST / IGST by rate",
        options: { format: "currency" },
        layout: { w: 7, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "sales_invoices",
          groupBy: ["gst_rate"],
          measures: [
            { field: "taxable_value", aggregation: "sum" },
            { field: "cgst", aggregation: "sum" },
            { field: "sgst", aggregation: "sum" },
            { field: "igst", aggregation: "sum" },
          ],
        },
      },
      {
        id: wid("chart"),
        type: "bar",
        title: "Receivables ageing",
        subtitle: "Days outstanding buckets",
        options: { format: "currency", colorIndex: 3 },
        layout: { w: 5, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "sales_invoices",
          groupBy: ["status"],
          measures: [{ field: "invoice_amount", aggregation: "sum" }],
        },
      },
    ],
  };
}

function salesDashboard(): Dashboard {
  return {
    id: "sales",
    name: "Sales Dashboard",
    description: "Pipeline, people and product performance.",
    tabs: ["Overview"],
    visibility: "workspace",
    updatedAt: new Date().toISOString(),
    filters: [
      { id: "date", label: "Date range", field: "invoice_date", type: "date-range", value: "last_6m" },
      { id: "salesperson", label: "Salesperson", field: "salesperson", type: "select", value: "All" },
    ],
    widgets: [
      kpi("Revenue", "sales_invoices", "invoice_amount", {}, 4),
      kpi("Orders", "sales_invoices", "quantity", { format: "compact" }, 4),
      kpi("Avg. invoice value", "sales_invoices", "invoice_amount", { sparkline: false }, 4),
      {
        id: wid("chart"),
        type: "bar",
        title: "Salesperson performance",
        options: { format: "currency", colorIndex: 0 },
        layout: { w: 6, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "sales_invoices",
          groupBy: ["salesperson"],
          measures: [{ field: "invoice_amount", aggregation: "sum" }],
        },
      },
      {
        id: wid("chart"),
        type: "bar",
        title: "Product performance",
        options: { format: "currency", horizontal: true, colorIndex: 5 },
        layout: { w: 6, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "sales_invoices",
          groupBy: ["product"],
          measures: [{ field: "invoice_amount", aggregation: "sum" }],
        },
      },
      {
        id: wid("chart"),
        type: "line",
        title: "Monthly orders",
        options: { format: "compact", showGrid: true, colorIndex: 2 },
        layout: { w: 12, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "sales_invoices",
          dateField: "invoice_date",
          grain: "month",
          measures: [{ field: "quantity", aggregation: "sum" }],
        },
      },
    ],
  };
}

function inventoryDashboard(): Dashboard {
  return {
    id: "inventory",
    name: "Inventory Dashboard",
    description: "Stock value, movement and reorder risk.",
    tabs: ["Overview"],
    visibility: "private",
    updatedAt: new Date().toISOString(),
    filters: [],
    widgets: [
      kpi("Stock value", "inventory", "stock_value", { sparkline: false }, 4),
      kpi("Units on hand", "inventory", "quantity", { format: "compact", sparkline: false }, 4),
      kpi("Avg. turnover days", "inventory", "turnover_days", { format: "number", sparkline: false }, 4),
      {
        id: wid("chart"),
        type: "bar",
        title: "Stock value by product",
        options: { format: "currency", horizontal: true, colorIndex: 1 },
        layout: { w: 7, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "inventory",
          groupBy: ["product"],
          measures: [{ field: "stock_value", aggregation: "sum" }],
        },
      },
      {
        id: wid("chart"),
        type: "pie",
        title: "Stock by category",
        options: { donut: true, format: "currency", showLegend: true },
        layout: { w: 5, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "inventory",
          groupBy: ["category"],
          measures: [{ field: "stock_value", aggregation: "sum" }],
        },
      },
      {
        id: wid("table"),
        type: "table",
        title: "Reorder watchlist",
        options: { format: "currency" },
        layout: { w: 12, h: 4 },
        query: {
          sourceId: "tally",
          dataset: "inventory",
          dimensions: ["product", "category", "quantity", "reorder_level", "stock_value", "turnover_days"],
          sort: [{ field: "quantity", dir: "asc" }],
          limit: 8,
        },
      },
    ],
  };
}

export const SEED_DASHBOARDS: Dashboard[] = [
  executiveOverview(),
  financeDashboard(),
  salesDashboard(),
  inventoryDashboard(),
];

export const SEED_CONNECTIONS: Connection[] = [
  {
    id: "conn-tally",
    providerId: "tally",
    name: "TallyPrime — Acme Industries",
    status: "connected",
    datasets: ["sales_invoices", "purchase_invoices", "customers", "vendors", "payments", "expenses"],
    frequency: "6h",
    lastSync: new Date(Date.now() - 1000 * 60 * 42).toISOString(),
    nextSync: new Date(Date.now() + 1000 * 60 * 60 * 5).toISOString(),
    records: 124829,
  },
  {
    id: "conn-razorpay",
    providerId: "razorpay",
    name: "Razorpay — Live",
    status: "connected",
    datasets: ["payments"],
    frequency: "hourly",
    lastSync: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    nextSync: new Date(Date.now() + 1000 * 60 * 48).toISOString(),
    records: 18422,
  },
  {
    id: "conn-zoho",
    providerId: "zoho_books",
    name: "Zoho Books — Acme Exports",
    status: "error",
    datasets: ["sales_invoices", "customers"],
    frequency: "daily",
    lastSync: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
    records: 9310,
    error: "Authentication token expired. Reconnect to resume syncing.",
  },
];

export const SEED_NOTIFICATIONS: AppNotification[] = [
  {
    id: uid(),
    title: "Tally sync completed",
    body: "124,829 records refreshed across 6 datasets.",
    category: "sync",
    level: "success",
    at: new Date(Date.now() - 1000 * 60 * 42).toISOString(),
    read: false,
  },
  {
    id: uid(),
    title: "Zoho Books sync failed",
    body: "Authentication token expired. Reconnect to resume syncing.",
    category: "sync",
    level: "error",
    at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    read: false,
  },
  {
    id: uid(),
    title: "Receivables crossed threshold",
    body: "Outstanding receivables are above ₹50L for the first time this quarter.",
    category: "alert",
    level: "warning",
    at: new Date(Date.now() - 1000 * 60 * 60 * 9).toISOString(),
    read: false,
  },
  {
    id: uid(),
    title: "Monthly Financial Review generated",
    body: "The August report was generated and shared with the finance team.",
    category: "report",
    level: "info",
    at: new Date(Date.now() - 1000 * 60 * 60 * 30).toISOString(),
    read: true,
  },
];

export const SEED_ALERTS: AlertRule[] = [
  {
    id: uid(),
    name: "Revenue drop",
    metric: "Revenue",
    condition: "decreases_by",
    value: 20,
    unit: "percent",
    comparison: "previous_month",
    channels: ["Email", "In-app"],
    enabled: true,
  },
  {
    id: uid(),
    name: "Receivables ceiling",
    metric: "Receivables",
    condition: "rises_above",
    value: 5000000,
    unit: "amount",
    comparison: "absolute",
    channels: ["In-app"],
    enabled: true,
  },
  {
    id: uid(),
    name: "Low cash balance",
    metric: "Cash Balance",
    condition: "drops_below",
    value: 2500000,
    unit: "amount",
    comparison: "absolute",
    channels: ["Email"],
    enabled: false,
  },
];

export const SEED_SCHEDULES: ScheduledReport[] = [
  {
    id: uid(),
    reportName: "Monthly Financial Review",
    cadence: "monthly",
    time: "09:00",
    recipients: ["finance@acme.in", "rahul@acme.in"],
    format: "pdf",
    enabled: true,
    nextRun: "01 Oct 2026, 09:00",
  },
  {
    id: uid(),
    reportName: "Weekly Sales Snapshot",
    cadence: "weekly",
    time: "08:30",
    recipients: ["sales@acme.in"],
    format: "pdf",
    enabled: true,
    nextRun: "21 Sep 2026, 08:30",
  },
];

export const SEED_REPORTS: Report[] = [
  {
    id: "monthly-financial-review",
    name: "Monthly Financial Review",
    period: "August 2026",
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 30).toISOString(),
    sections: [
      {
        id: uid(),
        kind: "summary",
        title: "Executive summary",
        body:
          "Revenue grew 14.2% month on month, driven by the West region and the Components category. Collections improved but receivables remain concentrated in five accounts.",
      },
      { id: uid(), kind: "kpis", title: "Headline metrics" },
      { id: uid(), kind: "chart", title: "Revenue trend" },
      { id: uid(), kind: "table", title: "Top customers" },
      {
        id: uid(),
        kind: "commentary",
        title: "CFO commentary",
        body: "Working capital cycle shortened by 4 days. Watch freight costs, up 18% against budget.",
      },
    ],
  },
  {
    id: "quarterly-board-pack",
    name: "Quarterly Board Pack",
    period: "Q1 FY27",
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 6).toISOString(),
    sections: [
      { id: uid(), kind: "summary", title: "Quarter in review", body: "Consolidated view across all branches." },
      { id: uid(), kind: "kpis", title: "Headline metrics" },
      { id: uid(), kind: "chart", title: "Revenue trend" },
    ],
  },
];

export const SEED_MEMBERS: Member[] = [
  { id: uid(), name: "Rahul Menon", email: "rahul@acme.in", role: "owner", status: "active", lastActive: "Today" },
  { id: uid(), name: "Priya Nair", email: "priya@acme.in", role: "admin", status: "active", lastActive: "Today" },
  { id: uid(), name: "Amit Sethi", email: "amit@acme.in", role: "editor", status: "active", lastActive: "Yesterday" },
  { id: uid(), name: "Farah Khan", email: "farah@acme.in", role: "viewer", status: "active", lastActive: "3 days ago" },
  { id: uid(), name: "Vikram Rao", email: "vikram@acme.in", role: "viewer", status: "invited" },
];
