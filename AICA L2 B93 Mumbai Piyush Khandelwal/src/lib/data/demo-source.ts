import type { Dataset, Field } from "../types";

/**
 * Deterministic demo dataset generator.
 * These rows stand in for normalised records produced by the integration
 * adapters (Invoice, InvoiceLine, Payment, Ledger, InventoryItem…).
 * Everything here is clearly labelled as demo data in the UI.
 */

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rand = mulberry32(20260917);
const pick = <T,>(arr: T[]) => arr[Math.floor(rand() * arr.length)];
const between = (min: number, max: number) => min + rand() * (max - min);

export const CUSTOMERS = [
  "Anandam Retail Pvt Ltd",
  "Bharat Steelworks",
  "Chandra Textiles",
  "Deccan Pharma",
  "Elevate Interiors",
  "Fortune Foods",
  "Gokul Agro Industries",
  "Hinduja Logistics",
  "Indus Packaging",
  "Jaipur Handicrafts",
  "Krishna Motors",
  "Lakshmi Traders",
  "Meridian Infotech",
  "Nirvana Hospitality",
  "Orbit Electricals",
];

export const VENDORS = [
  "Aditya Raw Materials",
  "Bombay Freight Co",
  "Coastal Chemicals",
  "Dhruv Power Solutions",
  "Everest Packaging",
  "Gurgaon Office Supplies",
];

export const PRODUCTS = [
  { name: "Industrial Valve 2in", hsn: "8481", category: "Components" },
  { name: "Copper Wire Spool", hsn: "8544", category: "Electricals" },
  { name: "Steel Fasteners Kit", hsn: "7318", category: "Hardware" },
  { name: "Control Panel Unit", hsn: "8537", category: "Electricals" },
  { name: "Polymer Sheet 4x8", hsn: "3920", category: "Polymers" },
  { name: "Hydraulic Pump", hsn: "8413", category: "Components" },
  { name: "Safety Gloves (Pack)", hsn: "6116", category: "Consumables" },
  { name: "Annual Service Plan", hsn: "9987", category: "Services" },
];

export const REGIONS = ["West", "North", "South", "East"];
export const BRANCHES = ["Mumbai", "Pune", "Delhi NCR", "Bengaluru", "Hyderabad"];
export const SALESPEOPLE = ["Rahul Menon", "Priya Nair", "Amit Sethi", "Farah Khan", "Vikram Rao"];
export const STATUSES = ["Paid", "Partially Paid", "Unpaid", "Overdue"];
export const EXPENSE_CATEGORIES = [
  "Salaries & Wages",
  "Rent",
  "Raw Materials",
  "Freight & Logistics",
  "Marketing",
  "Utilities",
  "Professional Fees",
  "Travel",
];

const MONTH_COUNT = 18;
const END = new Date(Date.UTC(2026, 8, 30)); // 30 Sep 2026

function monthStart(offsetFromEnd: number) {
  return new Date(Date.UTC(END.getUTCFullYear(), END.getUTCMonth() - offsetFromEnd, 1));
}

function randomDateInMonth(offsetFromEnd: number) {
  const start = monthStart(offsetFromEnd);
  const days = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 0)).getUTCDate();
  const day = 1 + Math.floor(rand() * days);
  return new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), day));
}

const iso = (d: Date) => d.toISOString().slice(0, 10);

export type Row = Record<string, string | number | null>;

function buildSalesInvoices(): Row[] {
  const rows: Row[] = [];
  let seq = 1000;
  for (let m = MONTH_COUNT - 1; m >= 0; m--) {
    // gentle growth + seasonality
    const growth = 1 + (MONTH_COUNT - m) * 0.022;
    const seasonal = 1 + Math.sin((m / 12) * Math.PI * 2) * 0.12;
    const count = Math.round(between(58, 76) * growth * seasonal);
    for (let i = 0; i < count; i++) {
      const product = pick(PRODUCTS);
      const qty = Math.round(between(2, 140));
      const rate = Math.round(between(450, 9800));
      const taxable = qty * rate;
      const gstRate = product.category === "Services" ? 18 : pick([5, 12, 18, 28]);
      const interState = rand() > 0.55;
      const tax = Math.round((taxable * gstRate) / 100);
      const status = pick(STATUSES);
      const date = randomDateInMonth(m);
      rows.push({
        invoice_no: `INV-${++seq}`,
        invoice_date: iso(date),
        customer: pick(CUSTOMERS),
        salesperson: pick(SALESPEOPLE),
        branch: pick(BRANCHES),
        region: pick(REGIONS),
        product: product.name,
        category: product.category,
        hsn: product.hsn,
        gstin: `27${String(Math.floor(between(10000, 99999)))}A1Z${Math.floor(between(1, 9))}`,
        quantity: qty,
        rate,
        taxable_value: taxable,
        gst_rate: gstRate,
        cgst: interState ? 0 : Math.round(tax / 2),
        sgst: interState ? 0 : Math.round(tax / 2),
        igst: interState ? tax : 0,
        tax_amount: tax,
        discount: Math.round(taxable * between(0, 0.05)),
        invoice_amount: taxable + tax,
        profit: Math.round(taxable * between(0.16, 0.34)),
        status,
        due_days: status === "Overdue" ? Math.round(between(31, 120)) : Math.round(between(0, 30)),
      });
    }
  }
  return rows;
}

function buildPurchaseInvoices(): Row[] {
  const rows: Row[] = [];
  let seq = 500;
  for (let m = MONTH_COUNT - 1; m >= 0; m--) {
    const count = Math.round(between(22, 34));
    for (let i = 0; i < count; i++) {
      const taxable = Math.round(between(28000, 640000));
      const gstRate = pick([5, 12, 18]);
      const tax = Math.round((taxable * gstRate) / 100);
      rows.push({
        bill_no: `PUR-${++seq}`,
        bill_date: iso(randomDateInMonth(m)),
        vendor: pick(VENDORS),
        branch: pick(BRANCHES),
        category: pick(EXPENSE_CATEGORIES),
        taxable_value: taxable,
        gst_rate: gstRate,
        tax_amount: tax,
        bill_amount: taxable + tax,
        status: pick(["Paid", "Unpaid", "Partially Paid"]),
      });
    }
  }
  return rows;
}

function buildExpenses(): Row[] {
  const rows: Row[] = [];
  for (let m = MONTH_COUNT - 1; m >= 0; m--) {
    for (const category of EXPENSE_CATEGORIES) {
      const base: Record<string, number> = {
        "Salaries & Wages": 1450000,
        Rent: 420000,
        "Raw Materials": 1850000,
        "Freight & Logistics": 320000,
        Marketing: 260000,
        Utilities: 140000,
        "Professional Fees": 180000,
        Travel: 120000,
      };
      rows.push({
        expense_date: iso(monthStart(m)),
        category,
        branch: pick(BRANCHES),
        amount: Math.round(base[category] * between(0.85, 1.2) * (1 + (MONTH_COUNT - m) * 0.008)),
      });
    }
  }
  return rows;
}

function buildPayments(): Row[] {
  const rows: Row[] = [];
  let seq = 9000;
  for (let m = MONTH_COUNT - 1; m >= 0; m--) {
    const count = Math.round(between(40, 60));
    for (let i = 0; i < count; i++) {
      rows.push({
        payment_ref: `PAY-${++seq}`,
        payment_date: iso(randomDateInMonth(m)),
        customer: pick(CUSTOMERS),
        mode: pick(["NEFT", "RTGS", "UPI", "Cheque", "Card"]),
        amount: Math.round(between(24000, 1250000)),
        status: pick(["Settled", "Settled", "Settled", "Pending"]),
      });
    }
  }
  return rows;
}

function buildCustomers(): Row[] {
  return CUSTOMERS.map((name, i) => ({
    customer: name,
    gstin: `27ABCDE${1000 + i}Z${i % 9}`,
    region: REGIONS[i % REGIONS.length],
    branch: BRANCHES[i % BRANCHES.length],
    credit_days: [15, 30, 45, 60][i % 4],
    outstanding: Math.round(between(120000, 3600000)),
    lifetime_value: Math.round(between(2400000, 42000000)),
  }));
}

function buildVendors(): Row[] {
  return VENDORS.map((name, i) => ({
    vendor: name,
    gstin: `27VEND${2000 + i}Z${i % 9}`,
    category: EXPENSE_CATEGORIES[i % EXPENSE_CATEGORIES.length],
    payable: Math.round(between(80000, 2400000)),
  }));
}

function buildInventory(): Row[] {
  return PRODUCTS.map((p) => {
    const qty = Math.round(between(20, 900));
    const rate = Math.round(between(400, 9000));
    return {
      product: p.name,
      category: p.category,
      hsn: p.hsn,
      quantity: qty,
      reorder_level: 120,
      rate,
      stock_value: qty * rate,
      turnover_days: Math.round(between(12, 140)),
    };
  });
}

function buildLedgers(): Row[] {
  const groups = [
    "Sales Accounts",
    "Purchase Accounts",
    "Direct Expenses",
    "Indirect Expenses",
    "Sundry Debtors",
    "Sundry Creditors",
    "Bank Accounts",
    "Duties & Taxes",
  ];
  return groups.map((g) => ({
    ledger: g,
    group: g.includes("Expenses") ? "Expenses" : g.includes("Accounts") ? "Trading" : "Balance Sheet",
    debit: Math.round(between(500000, 28000000)),
    credit: Math.round(between(500000, 28000000)),
  }));
}

const f = (name: string, label: string, type: Field["type"], role: Field["role"]): Field => ({
  name,
  label,
  type,
  role,
});

export const DATASETS: Dataset[] = [
  {
    id: "sales_invoices",
    name: "Sales Invoices",
    description: "Customer invoices with line values, GST breakup and payment status.",
    recordCount: 0,
    fields: [
      f("invoice_no", "Invoice No.", "string", "dimension"),
      f("invoice_date", "Invoice Date", "date", "dimension"),
      f("customer", "Customer", "string", "dimension"),
      f("salesperson", "Salesperson", "string", "dimension"),
      f("branch", "Branch", "string", "dimension"),
      f("region", "Region", "string", "dimension"),
      f("product", "Product", "string", "dimension"),
      f("category", "Category", "string", "dimension"),
      f("hsn", "HSN/SAC", "string", "dimension"),
      f("gstin", "GSTIN", "string", "dimension"),
      f("status", "Status", "string", "dimension"),
      f("quantity", "Quantity", "number", "measure"),
      f("taxable_value", "Taxable Value", "currency", "measure"),
      f("cgst", "CGST", "currency", "measure"),
      f("sgst", "SGST", "currency", "measure"),
      f("igst", "IGST", "currency", "measure"),
      f("tax_amount", "Tax", "currency", "measure"),
      f("discount", "Discount", "currency", "measure"),
      f("invoice_amount", "Invoice Amount", "currency", "measure"),
      f("profit", "Profit", "currency", "measure"),
      f("due_days", "Days Outstanding", "number", "measure"),
    ],
  },
  {
    id: "purchase_invoices",
    name: "Purchase Invoices",
    description: "Vendor bills with tax breakup and settlement status.",
    recordCount: 0,
    fields: [
      f("bill_no", "Bill No.", "string", "dimension"),
      f("bill_date", "Bill Date", "date", "dimension"),
      f("vendor", "Vendor", "string", "dimension"),
      f("branch", "Branch", "string", "dimension"),
      f("category", "Category", "string", "dimension"),
      f("status", "Status", "string", "dimension"),
      f("taxable_value", "Taxable Value", "currency", "measure"),
      f("tax_amount", "Tax", "currency", "measure"),
      f("bill_amount", "Bill Amount", "currency", "measure"),
    ],
  },
  {
    id: "expenses",
    name: "Expenses",
    description: "Monthly expense postings by category and branch.",
    recordCount: 0,
    fields: [
      f("expense_date", "Date", "date", "dimension"),
      f("category", "Category", "string", "dimension"),
      f("branch", "Branch", "string", "dimension"),
      f("amount", "Amount", "currency", "measure"),
    ],
  },
  {
    id: "payments",
    name: "Payments",
    description: "Customer receipts across NEFT, RTGS, UPI, cheque and card.",
    recordCount: 0,
    fields: [
      f("payment_ref", "Reference", "string", "dimension"),
      f("payment_date", "Date", "date", "dimension"),
      f("customer", "Customer", "string", "dimension"),
      f("mode", "Mode", "string", "dimension"),
      f("status", "Status", "string", "dimension"),
      f("amount", "Amount", "currency", "measure"),
    ],
  },
  {
    id: "customers",
    name: "Customers",
    description: "Customer master with GSTIN, credit terms and outstanding.",
    recordCount: 0,
    fields: [
      f("customer", "Customer", "string", "dimension"),
      f("gstin", "GSTIN", "string", "dimension"),
      f("region", "Region", "string", "dimension"),
      f("branch", "Branch", "string", "dimension"),
      f("credit_days", "Credit Days", "number", "measure"),
      f("outstanding", "Outstanding", "currency", "measure"),
      f("lifetime_value", "Lifetime Value", "currency", "measure"),
    ],
  },
  {
    id: "vendors",
    name: "Vendors",
    description: "Vendor master with payables.",
    recordCount: 0,
    fields: [
      f("vendor", "Vendor", "string", "dimension"),
      f("gstin", "GSTIN", "string", "dimension"),
      f("category", "Category", "string", "dimension"),
      f("payable", "Payable", "currency", "measure"),
    ],
  },
  {
    id: "inventory",
    name: "Inventory",
    description: "Stock on hand, valuation and turnover.",
    recordCount: 0,
    fields: [
      f("product", "Product", "string", "dimension"),
      f("category", "Category", "string", "dimension"),
      f("hsn", "HSN/SAC", "string", "dimension"),
      f("quantity", "Quantity", "number", "measure"),
      f("reorder_level", "Reorder Level", "number", "measure"),
      f("stock_value", "Stock Value", "currency", "measure"),
      f("turnover_days", "Turnover Days", "number", "measure"),
    ],
  },
  {
    id: "ledgers",
    name: "Ledgers",
    description: "Trial balance style ledger groups.",
    recordCount: 0,
    fields: [
      f("ledger", "Ledger", "string", "dimension"),
      f("group", "Group", "string", "dimension"),
      f("debit", "Debit", "currency", "measure"),
      f("credit", "Credit", "currency", "measure"),
    ],
  },
];

let cache: Record<string, Row[]> | null = null;

export function demoTables(): Record<string, Row[]> {
  if (cache) return cache;
  cache = {
    sales_invoices: buildSalesInvoices(),
    purchase_invoices: buildPurchaseInvoices(),
    expenses: buildExpenses(),
    payments: buildPayments(),
    customers: buildCustomers(),
    vendors: buildVendors(),
    inventory: buildInventory(),
    ledgers: buildLedgers(),
  };
  for (const ds of DATASETS) ds.recordCount = cache[ds.id]?.length ?? 0;
  return cache;
}

export function datasetById(id: string) {
  return DATASETS.find((d) => d.id === id);
}

export const DATE_FIELD_BY_DATASET: Record<string, string | undefined> = {
  sales_invoices: "invoice_date",
  purchase_invoices: "bill_date",
  expenses: "expense_date",
  payments: "payment_date",
};
