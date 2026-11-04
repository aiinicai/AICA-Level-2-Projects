import * as XLSX from "xlsx";
import { formatMoney, fromMinorUnits } from "./currencies";

/**
 * Prevents formula injection (CSV/Excel injection) by prefixing dangerous characters with an apostrophe.
 * Attacks often start with '=', '+', '-', '@', '\t', '\r'.
 */
export function sanitizeCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const str = String(value).trim();
  if (/^[=+\-@\t\r]/.test(str)) {
    return `'${str}`;
  }
  return str;
}

export interface ExportTransaction {
  date: string;
  type: "Expense" | "Settlement";
  description: string;
  category?: string;
  currency: string;
  amount_units: number;
  payer: string;
  recipient_or_participants: string;
  my_share_or_impact: string;
  note?: string;
}

export function exportTransactionsToXlsx(
  title: string,
  transactions: ExportTransaction[],
  dateRange?: { from?: string; to?: string },
) {
  let filtered = transactions;
  if (dateRange?.from) {
    filtered = filtered.filter((t) => t.date >= dateRange.from!);
  }
  if (dateRange?.to) {
    filtered = filtered.filter((t) => t.date <= dateRange.to!);
  }

  // Build rows with sanitized string cells
  const rows = [
    [`Fair Share Export: ${sanitizeCell(title)}`],
    [
      `Generated: ${new Date().toISOString()}`,
      dateRange?.from || dateRange?.to
        ? `Filter: ${dateRange.from || "Start"} to ${dateRange.to || "End"}`
        : "Filter: All time",
    ],
    [], // empty line
    [
      "Date",
      "Type",
      "Description",
      "Category",
      "Currency",
      "Total Amount",
      "Payer / From",
      "Participants / To",
      "Your Share / Impact",
      "Note",
    ],
    ...filtered.map((t) => [
      sanitizeCell(t.date),
      sanitizeCell(t.type),
      sanitizeCell(t.description),
      sanitizeCell(t.category ?? "—"),
      sanitizeCell(t.currency),
      fromMinorUnits(t.amount_units, t.currency),
      sanitizeCell(t.payer),
      sanitizeCell(t.recipient_or_participants),
      sanitizeCell(t.my_share_or_impact),
      sanitizeCell(t.note ?? ""),
    ]),
  ];

  const worksheet = XLSX.utils.aoa_to_sheet(rows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Transactions");

  const safeFilename = `${title.toLowerCase().replace(/[^a-z0-9]/g, "-")}-fairlyshare.xlsx`;
  XLSX.writeFile(workbook, safeFilename);
}
