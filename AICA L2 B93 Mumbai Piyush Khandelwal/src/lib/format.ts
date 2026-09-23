import type { WorkspaceSettings } from "./types";

const SYMBOLS: Record<WorkspaceSettings["currency"], string> = {
  INR: "₹",
  USD: "$",
  EUR: "€",
  GBP: "£",
  AED: "AED ",
};

export function currencySymbol(currency: WorkspaceSettings["currency"] = "INR") {
  return SYMBOLS[currency] ?? "₹";
}

/** 1250000 -> "12,50,000" (Indian) or "1,250,000" (international) */
export function groupDigits(value: number, system: "indian" | "international" = "indian") {
  const locale = system === "indian" ? "en-IN" : "en-US";
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value);
}

export interface FormatOpts {
  currency?: WorkspaceSettings["currency"];
  numberSystem?: "indian" | "international";
  compact?: boolean;
  decimals?: number;
}

/** Compact Indian: 24,80,000 -> ₹24.8L ; 125000000 -> ₹12.5Cr */
export function formatCurrency(value: number, opts: FormatOpts = {}) {
  const {
    currency = "INR",
    numberSystem = "indian",
    compact = true,
    decimals = 1,
  } = opts;
  const sym = currencySymbol(currency);
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);

  if (!compact) return `${sign}${sym}${groupDigits(abs, numberSystem)}`;

  if (numberSystem === "indian") {
    if (abs >= 1_00_00_000) return `${sign}${sym}${trim(abs / 1_00_00_000, decimals)}Cr`;
    if (abs >= 1_00_000) return `${sign}${sym}${trim(abs / 1_00_000, decimals)}L`;
    if (abs >= 1_000) return `${sign}${sym}${trim(abs / 1_000, decimals)}K`;
  } else {
    if (abs >= 1_000_000_000) return `${sign}${sym}${trim(abs / 1_000_000_000, decimals)}B`;
    if (abs >= 1_000_000) return `${sign}${sym}${trim(abs / 1_000_000, decimals)}M`;
    if (abs >= 1_000) return `${sign}${sym}${trim(abs / 1_000, decimals)}K`;
  }
  return `${sign}${sym}${trim(abs, 0)}`;
}

export function formatNumber(value: number, opts: FormatOpts = {}) {
  const { numberSystem = "indian", compact = false, decimals = 1 } = opts;
  if (!compact) return groupDigits(value, numberSystem);
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (numberSystem === "indian") {
    if (abs >= 1_00_00_000) return `${sign}${trim(abs / 1_00_00_000, decimals)}Cr`;
    if (abs >= 1_00_000) return `${sign}${trim(abs / 1_00_000, decimals)}L`;
  } else if (abs >= 1_000_000) {
    return `${sign}${trim(abs / 1_000_000, decimals)}M`;
  }
  if (abs >= 1_000) return `${sign}${trim(abs / 1_000, decimals)}K`;
  return `${sign}${trim(abs, 0)}`;
}

export function formatPercent(value: number, decimals = 1) {
  return `${value > 0 ? "+" : ""}${value.toFixed(decimals)}%`;
}

function trim(value: number, decimals: number) {
  const fixed = value.toFixed(decimals);
  return fixed.replace(/\.0+$/, "");
}

export function formatDate(value: string | Date, format: WorkspaceSettings["dateFormat"] = "DD/MM/YYYY") {
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return String(value);
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const yyyy = d.getUTCFullYear();
  if (format === "MM/DD/YYYY") return `${mm}/${dd}/${yyyy}`;
  if (format === "YYYY-MM-DD") return `${yyyy}-${mm}-${dd}`;
  return `${dd}/${mm}/${yyyy}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function prettyDate(value: string | Date) {
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return String(value);
  return `${String(d.getUTCDate()).padStart(2, "0")} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export function relativeTime(value: string | Date) {
  const d = typeof value === "string" ? new Date(value) : value;
  const diff = Date.now() - d.getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return prettyDate(d);
}

export function formatValue(
  value: number | string | null,
  type: "currency" | "number" | "percent" | "compact" | "string" | "date",
  opts: FormatOpts = {},
) {
  if (value === null || value === undefined) return "—";
  if (type === "string") return String(value);
  if (type === "date") return prettyDate(String(value));
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(n)) return String(value);
  if (type === "currency") return formatCurrency(n, opts);
  if (type === "percent") return `${trim(n, opts.decimals ?? 1)}%`;
  if (type === "compact") return formatNumber(n, { ...opts, compact: true });
  return formatNumber(n, { ...opts, compact: false });
}
