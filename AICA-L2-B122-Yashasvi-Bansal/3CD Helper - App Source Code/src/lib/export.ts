// Excel / CSV / JSON exports and downloadable templates (SheetJS).
import * as XLSX from "xlsx";

export function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function safeFileName(s: string) {
  return s.replace(/[^\w\- ]+/g, "").replace(/\s+/g, "_").slice(0, 60);
}

type Aoa = (string | number | null)[][];

export function sheetFromAoa(aoa: Aoa, widths?: number[], merges?: XLSX.Range[]) {
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  if (widths) ws["!cols"] = widths.map((w) => ({ wch: w }));
  if (merges) ws["!merges"] = merges;
  return ws;
}

export type WorkbookSheets = { name: string; ws: XLSX.WorkSheet }[];

function bookOf(sheets: WorkbookSheets) {
  const wb = XLSX.utils.book_new();
  sheets.forEach((s) => XLSX.utils.book_append_sheet(wb, s.ws, s.name.slice(0, 31)));
  return wb;
}

export function writeWorkbook(sheets: WorkbookSheets, fileName: string) {
  XLSX.writeFile(bookOf(sheets), fileName);
}

/** The same workbook as a file in memory (for sharing a link instead of downloading). */
export function workbookBlob(sheets: WorkbookSheets): Blob {
  const data = XLSX.write(bookOf(sheets), { bookType: "xlsx", type: "array" }) as ArrayBuffer;
  return new Blob([data], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

export function downloadCsv(aoa: Aoa, fileName: string) {
  const csv = aoa.map((r) => r.map((c) => {
    const s = c === null || c === undefined ? "" : String(c);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }).join(",")).join("\r\n");
  downloadBlob(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }), fileName);
}

export function downloadJson(obj: unknown, fileName: string) {
  downloadBlob(new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" }), fileName);
}

export function downloadExpenseTemplate() {
  const aoa: Aoa = [
    ["Date", "Party Name", "GSTIN", "Expense Head", "Amount", "Goods/Services"],
    ["01-04-2024", "ABC Traders", "27AAPFU0939F1ZV", "Purchases", 118000, "Goods"],
    ["05-04-2024", "Sharma Transport", "", "Freight", 12500, "Services"],
    ["10-04-2024", "City Electricals", "29AAGCB7383J1Z4", "Repairs & Maintenance", 8450, "Services"],
  ];
  const notes: Aoa = [
    ["How to fill"],
    ["• One row per expense entry (or per party per head). Amount is the expenditure amount."],
    ["• GSTIN blank = unregistered. Invalid GSTINs are flagged for review."],
    ["• Column names can differ – 3CD Helper lets you map columns while uploading."],
    ["• You can also upload Tally / Busy / Marg / Zoho exports directly (Excel, CSV, XML) and GSTR-2B JSON."],
  ];
  writeWorkbook([
    { name: "Expenses", ws: sheetFromAoa(aoa, [12, 30, 18, 26, 14, 16]) },
    { name: "Instructions", ws: sheetFromAoa(notes, [100]) },
  ], "3CD_Helper_Clause44_Template.xlsx");
}

export function downloadClientTemplate() {
  const aoa: Aoa = [
    ["Client Name", "PAN", "GSTIN", "Status", "Contact Person", "Email", "Mobile", "Address"],
    ["Sharma Textiles Pvt Ltd", "AAPFU0939F", "27AAPFU0939F1ZV", "Company", "Rajesh Sharma", "accounts@example.com", "9876543210", "Mumbai"],
  ];
  writeWorkbook([{ name: "Clients", ws: sheetFromAoa(aoa, [30, 14, 18, 12, 20, 26, 14, 30]) }], "3CD_Helper_Clients_Template.xlsx");
}
