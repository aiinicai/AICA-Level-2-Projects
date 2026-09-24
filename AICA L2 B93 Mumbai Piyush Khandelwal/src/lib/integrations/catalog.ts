export type IntegrationCategory =
  | "Accounting"
  | "Finance"
  | "Payments"
  | "CRM"
  | "E-commerce"
  | "HR"
  | "Productivity"
  | "Custom API";

export type AuthType = "api_key" | "bearer" | "oauth2" | "basic" | "local_bridge";

export interface CredentialField {
  key: string;
  label: string;
  placeholder?: string;
  secret?: boolean;
  optional?: boolean;
  help?: string;
}

export interface IntegrationDefinition {
  id: string;
  name: string;
  category: IntegrationCategory;
  tagline: string;
  description: string;
  auth: AuthType;
  /** Datasets this provider can expose, mapped to normalised dataset ids. */
  datasets: { id: string; label: string; default?: boolean }[];
  credentials: CredentialField[];
  /** Demo adapters answer locally; production adapters call a server function. */
  mode: "demo" | "production";
  accent: string;
  initials: string;
  popular?: boolean;
}

const ACCOUNTING_DATASETS = [
  { id: "sales_invoices", label: "Sales invoices", default: true },
  { id: "purchase_invoices", label: "Purchase invoices", default: true },
  { id: "customers", label: "Customers", default: true },
  { id: "vendors", label: "Vendors", default: true },
  { id: "payments", label: "Payments", default: true },
  { id: "ledgers", label: "Ledgers" },
  { id: "inventory", label: "Inventory" },
  { id: "expenses", label: "Expenses", default: true },
];

export const INTEGRATIONS: IntegrationDefinition[] = [
  {
    id: "tally",
    name: "Tally / TallyPrime",
    category: "Accounting",
    tagline: "Accounting & ERP",
    description: "Pull vouchers, ledgers and GST data from TallyPrime to power automated financial dashboards.",
    auth: "local_bridge",
    datasets: ACCOUNTING_DATASETS,
    credentials: [
      { key: "host", label: "Tally gateway host", placeholder: "http://localhost:9000", help: "Enable ODBC/HTTP gateway in Tally: F1 → Settings → Connectivity." },
      { key: "company", label: "Company name", placeholder: "Acme Industries Pvt Ltd" },
      { key: "bridge_token", label: "Bridge token", secret: true, help: "Issued by the on-premise sync bridge. Stored server-side, never in the browser." },
    ],
    mode: "demo",
    accent: "var(--color-chart-3)",
    initials: "TP",
    popular: true,
  },
  {
    id: "zoho_books",
    name: "Zoho Books",
    category: "Accounting",
    tagline: "Accounting",
    description: "Sync invoices, bills, contacts and GST returns from your Zoho Books organisation.",
    auth: "oauth2",
    datasets: ACCOUNTING_DATASETS,
    credentials: [
      { key: "org_id", label: "Organisation ID", placeholder: "60012345678" },
      { key: "region", label: "Data centre", placeholder: "zoho.in" },
    ],
    mode: "demo",
    accent: "var(--color-chart-5)",
    initials: "ZB",
    popular: true,
  },
  {
    id: "zoho_inventory",
    name: "Zoho Inventory",
    category: "Accounting",
    tagline: "Inventory",
    description: "Stock levels, valuation and item movement across warehouses.",
    auth: "oauth2",
    datasets: [{ id: "inventory", label: "Inventory items", default: true }],
    credentials: [{ key: "org_id", label: "Organisation ID", placeholder: "60012345678" }],
    mode: "demo",
    accent: "var(--color-chart-4)",
    initials: "ZI",
  },
  {
    id: "busy",
    name: "Busy Accounting",
    category: "Accounting",
    tagline: "Accounting & ERP",
    description: "Import masters and vouchers from Busy via the on-premise connector.",
    auth: "local_bridge",
    datasets: ACCOUNTING_DATASETS,
    credentials: [
      { key: "host", label: "Connector host", placeholder: "http://192.168.1.14:8080" },
      { key: "bridge_token", label: "Bridge token", secret: true },
    ],
    mode: "demo",
    accent: "var(--color-chart-6)",
    initials: "BY",
  },
  {
    id: "marg",
    name: "Marg ERP",
    category: "Accounting",
    tagline: "Accounting & ERP",
    description: "Distribution-focused ERP data: sales, purchases, stock and GST.",
    auth: "api_key",
    datasets: ACCOUNTING_DATASETS,
    credentials: [
      { key: "base_url", label: "Base URL", placeholder: "https://api.margerp.com" },
      { key: "api_key", label: "API key", secret: true },
    ],
    mode: "demo",
    accent: "var(--color-chart-2)",
    initials: "MG",
  },
  {
    id: "quickbooks",
    name: "QuickBooks",
    category: "Accounting",
    tagline: "Accounting",
    description: "Invoices, bills, expenses and chart of accounts from QuickBooks Online.",
    auth: "oauth2",
    datasets: ACCOUNTING_DATASETS,
    credentials: [{ key: "realm_id", label: "Realm ID", placeholder: "4620816365..." }],
    mode: "demo",
    accent: "var(--color-chart-3)",
    initials: "QB",
  },
  {
    id: "xero",
    name: "Xero",
    category: "Accounting",
    tagline: "Accounting",
    description: "Connect a Xero tenant for P&L, balance sheet and receivables data.",
    auth: "oauth2",
    datasets: ACCOUNTING_DATASETS,
    credentials: [{ key: "tenant_id", label: "Tenant ID", placeholder: "xxxxxxxx-xxxx" }],
    mode: "demo",
    accent: "var(--color-chart-2)",
    initials: "XR",
  },
  {
    id: "razorpay",
    name: "Razorpay",
    category: "Payments",
    tagline: "Payments",
    description: "Settlements, payouts, refunds and payment-level fee analysis.",
    auth: "api_key",
    datasets: [{ id: "payments", label: "Payments", default: true }],
    credentials: [
      { key: "key_id", label: "Key ID", placeholder: "rzp_live_..." },
      { key: "key_secret", label: "Key secret", secret: true },
    ],
    mode: "demo",
    accent: "var(--color-chart-1)",
    initials: "RZ",
    popular: true,
  },
  {
    id: "stripe",
    name: "Stripe",
    category: "Payments",
    tagline: "Payments",
    description: "Charges, subscriptions and payout reconciliation.",
    auth: "api_key",
    datasets: [{ id: "payments", label: "Payments", default: true }],
    credentials: [{ key: "secret_key", label: "Secret key", secret: true, placeholder: "sk_live_..." }],
    mode: "demo",
    accent: "var(--color-chart-6)",
    initials: "ST",
  },
  {
    id: "payu",
    name: "PayU",
    category: "Payments",
    tagline: "Payments",
    description: "Transaction and settlement data for Indian payment flows.",
    auth: "api_key",
    datasets: [{ id: "payments", label: "Payments", default: true }],
    credentials: [
      { key: "merchant_key", label: "Merchant key" },
      { key: "salt", label: "Salt", secret: true },
    ],
    mode: "demo",
    accent: "var(--color-chart-4)",
    initials: "PU",
  },
  {
    id: "salesforce",
    name: "Salesforce",
    category: "CRM",
    tagline: "CRM",
    description: "Opportunities, accounts and pipeline stages for revenue forecasting.",
    auth: "oauth2",
    datasets: [{ id: "customers", label: "Accounts", default: true }],
    credentials: [{ key: "instance_url", label: "Instance URL", placeholder: "https://acme.my.salesforce.com" }],
    mode: "demo",
    accent: "var(--color-chart-2)",
    initials: "SF",
  },
  {
    id: "hubspot",
    name: "HubSpot",
    category: "CRM",
    tagline: "CRM",
    description: "Deals, contacts and lifecycle stages.",
    auth: "oauth2",
    datasets: [{ id: "customers", label: "Contacts", default: true }],
    credentials: [{ key: "portal_id", label: "Portal ID" }],
    mode: "demo",
    accent: "var(--color-chart-4)",
    initials: "HS",
  },
  {
    id: "zoho_crm",
    name: "Zoho CRM",
    category: "CRM",
    tagline: "CRM",
    description: "Leads, deals and salesperson performance.",
    auth: "oauth2",
    datasets: [{ id: "customers", label: "Accounts", default: true }],
    credentials: [{ key: "org_id", label: "Organisation ID" }],
    mode: "demo",
    accent: "var(--color-chart-5)",
    initials: "ZC",
  },
  {
    id: "shopify",
    name: "Shopify",
    category: "E-commerce",
    tagline: "E-commerce",
    description: "Orders, products and customers from your Shopify storefront.",
    auth: "api_key",
    datasets: [
      { id: "sales_invoices", label: "Orders", default: true },
      { id: "inventory", label: "Products" },
    ],
    credentials: [
      { key: "shop", label: "Shop domain", placeholder: "acme.myshopify.com" },
      { key: "access_token", label: "Admin API token", secret: true },
    ],
    mode: "demo",
    accent: "var(--color-chart-3)",
    initials: "SH",
    popular: true,
  },
  {
    id: "woocommerce",
    name: "WooCommerce",
    category: "E-commerce",
    tagline: "E-commerce",
    description: "WordPress store orders and product performance.",
    auth: "basic",
    datasets: [{ id: "sales_invoices", label: "Orders", default: true }],
    credentials: [
      { key: "store_url", label: "Store URL", placeholder: "https://shop.acme.in" },
      { key: "consumer_key", label: "Consumer key" },
      { key: "consumer_secret", label: "Consumer secret", secret: true },
    ],
    mode: "demo",
    accent: "var(--color-chart-6)",
    initials: "WC",
  },
  {
    id: "amazon",
    name: "Amazon Seller",
    category: "E-commerce",
    tagline: "Marketplace",
    description: "Marketplace orders, settlements and fee breakdowns.",
    auth: "oauth2",
    datasets: [{ id: "sales_invoices", label: "Orders", default: true }],
    credentials: [{ key: "seller_id", label: "Seller ID" }],
    mode: "demo",
    accent: "var(--color-chart-4)",
    initials: "AZ",
  },
  {
    id: "flipkart",
    name: "Flipkart Seller",
    category: "E-commerce",
    tagline: "Marketplace",
    description: "Flipkart order and settlement data.",
    auth: "api_key",
    datasets: [{ id: "sales_invoices", label: "Orders", default: true }],
    credentials: [
      { key: "client_id", label: "Client ID" },
      { key: "client_secret", label: "Client secret", secret: true },
    ],
    mode: "demo",
    accent: "var(--color-chart-1)",
    initials: "FK",
  },
  {
    id: "google_sheets",
    name: "Google Sheets",
    category: "Productivity",
    tagline: "Spreadsheets",
    description: "Treat any sheet as a dataset — budgets, targets, manual adjustments.",
    auth: "oauth2",
    datasets: [{ id: "expenses", label: "Sheet range", default: true }],
    credentials: [{ key: "sheet_url", label: "Sheet URL", placeholder: "https://docs.google.com/spreadsheets/..." }],
    mode: "demo",
    accent: "var(--color-chart-3)",
    initials: "GS",
  },
  {
    id: "csv_upload",
    name: "CSV / Excel upload",
    category: "Productivity",
    tagline: "File import",
    description: "Upload a file once or on a schedule and map columns to the business model.",
    auth: "api_key",
    datasets: [{ id: "expenses", label: "Uploaded file", default: true }],
    credentials: [],
    mode: "demo",
    accent: "var(--color-chart-2)",
    initials: "CSV",
  },
  {
    id: "greythr",
    name: "greytHR",
    category: "HR",
    tagline: "HR & Payroll",
    description: "Headcount, payroll cost and attrition metrics.",
    auth: "api_key",
    datasets: [{ id: "expenses", label: "Payroll cost", default: true }],
    credentials: [{ key: "api_key", label: "API key", secret: true }],
    mode: "demo",
    accent: "var(--color-chart-5)",
    initials: "GH",
  },
  {
    id: "custom_rest",
    name: "Custom REST API",
    category: "Custom API",
    tagline: "Any HTTP API",
    description: "Connect any REST endpoint, map its response to the business data model and schedule syncs.",
    auth: "bearer",
    datasets: [{ id: "sales_invoices", label: "Mapped endpoint", default: true }],
    credentials: [
      { key: "name", label: "API name", placeholder: "Internal orders API" },
      { key: "base_url", label: "Base URL", placeholder: "https://api.example.com/v1" },
      { key: "token", label: "Bearer token", secret: true },
      { key: "headers", label: "Extra headers (JSON)", placeholder: '{"X-Org":"acme"}', optional: true },
    ],
    mode: "demo",
    accent: "var(--color-chart-1)",
    initials: "API",
  },
];

export const CATEGORIES: IntegrationCategory[] = [
  "Accounting",
  "Finance",
  "Payments",
  "CRM",
  "E-commerce",
  "HR",
  "Productivity",
  "Custom API",
];

export function integrationById(id: string) {
  return INTEGRATIONS.find((i) => i.id === id);
}
