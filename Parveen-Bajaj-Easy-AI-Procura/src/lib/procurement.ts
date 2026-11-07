import type { Database } from "@/integrations/supabase/types";

export type DocStatus = Database["public"]["Enums"]["doc_status"];
export type SupplierStatus = Database["public"]["Enums"]["supplier_status"];
export type ReceiptStatus = Database["public"]["Enums"]["grn_receipt_status"];
export type ItemCondition = Database["public"]["Enums"]["item_condition"];

export const money = (value: number | string | null | undefined) =>
  new Intl.NumberFormat("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    Number(value ?? 0),
  );

export const qty = (value: number | string | null | undefined) =>
  new Intl.NumberFormat("en-KE", { maximumFractionDigits: 3 }).format(Number(value ?? 0));

export const shortDate = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—";

export const stamp = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "—";

export function receiptStatusFor(lines: { qty_ordered: number; qty_received: number }[]): ReceiptStatus {
  const received = lines.reduce((sum, l) => sum + Number(l.qty_received || 0), 0);
  if (received === 0) return "REJECTED";
  const complete = lines.every((l) => Number(l.qty_received) >= Number(l.qty_ordered));
  return complete ? "ACCEPTED" : "PARTIAL";
}

export function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "";
  const first = rows[0];
  if (!first) return "";
  const headers = Object.keys(first);
  const escape = (v: unknown) => {
    const raw = v === null || v === undefined ? "" : String(v);
    const s = typeof v === "string" && /^\s*[=+@-]/.test(raw) ? `'${raw}` : raw;
    return /[",\n\r]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
  };
  return [headers.join(","), ...rows.map((r) => headers.map((h) => escape(r[h])).join(","))].join("\n");
}

export function downloadCsv(filename: string, rows: Record<string, unknown>[]) {
  const blob = new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
