import * as XLSX from "xlsx";
import {
  SAMPLE_COMPANY,
  SAMPLE_TX_HEADERS,
  SAMPLE_TX_COMPACT,
  SAMPLE_PARTIES,
  SAMPLE_ITEMS,
  SAMPLE_RP_HEADERS,
  SAMPLE_RP,
  SAMPLE_AP_HEADERS,
  SAMPLE_AP,
} from "../data/sampleData";
import { NATURES } from "./rules";
export type Mode = "Unlisted" | "Listed";
export interface Company {
  name: string;
  fy: string;
  start: string;
  end: string;
  turnover: number;
  netWorth: number;
  consolidated: number;
}
export interface Transaction {
  date: string;
  party: string;
  vchType: string;
  vchNo: string;
  item: string;
  quantity: number;
  unit: string;
  rate: number;
  amount: number;
  direction: "Dr" | "Cr";
  nature: string;
}
export interface Party {
  party: string;
  relationship: string;
  recognised: string;
  category: string;
  interested: string;
  balance: number;
  balanceNature: string;
}
export interface Approval {
  id: string;
  party: string;
  nature: string;
  body: string;
  type: string;
  date: string;
  from: string;
  to: string;
  limit: number;
  interested: string;
  stayedOut: string;
  reference: string;
}
export interface Dataset {
  company: Company;
  transactions: Transaction[];
  parties: Party[];
  approvals: Approval[];
}
export const key = (v: unknown) =>
  String(v ?? "")
    .trim()
    .toLowerCase();
const text = (v: unknown) => String(v ?? "").trim();
const present = (v: unknown) => v !== undefined && v !== null && v !== "";
function numeric(v: unknown, label: string, blank = false): number {
  if (!present(v) && blank) return 0;
  if (!present(v)) throw new Error(`${label}: a number is required.`);
  const n = Number(typeof v === "string" ? v.replace(/,/g, "").trim() : v);
  if (!Number.isFinite(n)) throw new Error(`${label}: invalid number.`);
  return n;
}
export function isoDate(v: unknown, label: string): string {
  let iso: string;
  if (v instanceof Date && !Number.isNaN(v.getTime())) {
    // Excel stores calendar dates, not UTC instants. Use local calendar fields,
    // rounding sub-second floating-point noise introduced by serial conversion.
    const local = new Date(Math.round(v.getTime() / 1000) * 1000);
    iso = `${local.getFullYear()}-${String(local.getMonth() + 1).padStart(2, "0")}-${String(local.getDate()).padStart(2, "0")}`;
  } else if (typeof v === "number") {
    const d = XLSX.SSF.parse_date_code(v);
    if (!d) throw new Error(`${label}: invalid Excel date.`);
    iso = `${d.y}-${String(d.m).padStart(2, "0")}-${String(d.d).padStart(2, "0")}`;
  } else iso = text(v);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso) || new Date(iso).toISOString().slice(0, 10) !== iso)
    throw new Error(`${label}: use a valid Excel date or YYYY-MM-DD.`);
  return iso;
}
function rows(wb: XLSX.WorkBook, name: string, headers: string[], prefix?: string) {
  const sheet = wb.Sheets[name];
  if (!sheet) throw new Error(`Missing sheet: ${name}.`);
  const all = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: "", raw: true });
  const actual = (all[0] ?? []).map(key);
  const indices = headers.map((h) => {
    const i = actual.findIndex((a) =>
      prefix && key(h).startsWith(key(prefix)) ? a.startsWith(key(prefix)) : a === key(h),
    );
    if (i < 0) throw new Error(`Missing column "${h}" in sheet "${name}".`);
    return i;
  });
  return all
    .slice(1)
    .filter((r) => r.some(present))
    .map((r) => indices.map((i) => r[i]));
}
export function parseWorkbook(wb: XLSX.WorkBook): Dataset {
  const c = rows(wb, "Company", ["Field", "Value"]);
  const field = (prefix: string) => {
    const row = c.find((r) => key(r[0]).startsWith(key(prefix)));
    if (!row) throw new Error(`Missing field "${prefix}" in sheet "Company".`);
    return row[1];
  };
  const company: Company = {
    name: text(field("Company name")),
    fy: text(field("Financial year under review")),
    start: isoDate(field("FY start"), "Company FY start"),
    end: isoDate(field("FY end"), "Company FY end"),
    turnover: numeric(field("Standalone turnover"), "Standalone turnover"),
    netWorth: numeric(field("Net worth"), "Net worth"),
    consolidated: numeric(field("Consolidated turnover"), "Consolidated turnover"),
  };
  if (company.start > company.end) throw new Error("Company: FY start must precede FY end.");
  const transactions = rows(wb, "Transactions", SAMPLE_TX_HEADERS).map((r, i): Transaction => {
    const label = `Transactions row ${i + 2}`;
    const nature = NATURES.find((n) => key(n) === key(r[10]));
    if (!nature) throw new Error(`${label}: unknown Nature "${text(r[10])}".`);
    if (!present(r[8]) && !present(r[9]))
      throw new Error(`${label}: Debit Amount or Credit Amount is required.`);
    if (!text(r[1])) throw new Error(`${label}: Particulars is required.`);
    return {
      date: isoDate(r[0], label + " Date"),
      party: text(r[1]),
      vchType: text(r[2]),
      vchNo: text(r[3]),
      item: text(r[4]),
      quantity: numeric(r[5], label + " Quantity", true),
      unit: text(r[6]),
      rate: numeric(r[7], label + " Rate", true),
      amount: numeric(present(r[8]) ? r[8] : r[9], label + " Amount"),
      direction: present(r[8]) ? "Dr" : "Cr",
      nature,
    };
  });
  const parties = rows(wb, "Related_Parties", SAMPLE_RP_HEADERS, "Closing balance").map(
    (r): Party => ({
      party: text(r[0]),
      relationship: text(r[1]),
      recognised: text(r[2]),
      category: text(r[3]),
      interested: text(r[4]),
      balance: numeric(r[5], "Related_Parties Closing balance", true),
      balanceNature: text(r[6]),
    }),
  );
  const approvals = rows(wb, "Approvals", SAMPLE_AP_HEADERS).map((r, i): Approval => {
    const body = ["Audit Committee", "Board", "Shareholders"].find((b) => key(b) === key(r[3]));
    const nature = NATURES.find((n) => key(n) === key(r[2]));
    if (!body || !nature)
      throw new Error(`Approvals row ${i + 2}: invalid Approving body or Nature.`);
    const a = {
      id: text(r[0]),
      party: text(r[1]),
      nature,
      body,
      type: text(r[4]),
      date: isoDate(r[5], "Approval date"),
      from: isoDate(r[6], "Valid from"),
      to: isoDate(r[7], "Valid to"),
      limit: numeric(r[8], "Approval Limit"),
      interested: text(r[9]),
      stayedOut: text(r[10]),
      reference: text(r[11]),
    };
    if (a.from > a.to) throw new Error(`Approvals row ${i + 2}: Valid from must precede Valid to.`);
    return a;
  });
  return { company, transactions, parties, approvals };
}
export function readWorkbook(bytes: ArrayBuffer) {
  const workbook = XLSX.read(bytes, { type: "array", cellDates: true });
  // SheetJS 0.18 can shift date cells backwards across midnight in zones with
  // historical sub-minute offsets (including Kolkata). Preserve the workbook's
  // timezone-free calendar serial rather than that lossy Date conversion.
  const serialWorkbook = XLSX.read(bytes, { type: "array", cellDates: false });
  for (const name of workbook.SheetNames) {
    const sheet = workbook.Sheets[name];
    const serialSheet = serialWorkbook.Sheets[name];
    if (!sheet || !serialSheet) continue;
    for (const address of Object.keys(sheet)) {
      if (address.startsWith("!")) continue;
      const cell = sheet[address];
      const serial = serialSheet[address];
      if (cell?.t === "d" && serial?.t === "n") {
        const calendar = XLSX.SSF.parse_date_code(serial.v, {
          date1904: workbook.Workbook?.WBProps?.date1904 ?? false,
        });
        if (!calendar) throw new Error(`${name} ${address}: invalid Excel date.`);
        cell.t = "s";
        cell.v = `${calendar.y}-${String(calendar.m).padStart(2, "0")}-${String(calendar.d).padStart(2, "0")}`;
      }
    }
  }
  return parseWorkbook(workbook);
}
export function sampleWorkbook(): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();
  const tx = SAMPLE_TX_COMPACT.map(([d, p, type, no, i, q, r, side, amount]) => {
    const item = SAMPLE_ITEMS[i];
    return [
      d,
      SAMPLE_PARTIES[p],
      type,
      no,
      item?.[0],
      q,
      item?.[1],
      r,
      side === "D" ? amount : "",
      side === "C" ? amount : "",
      item?.[2],
    ];
  });
  for (const [name, data] of [
    ["Company", [["Field", "Value"], ...SAMPLE_COMPANY]],
    ["Transactions", [SAMPLE_TX_HEADERS, ...tx]],
    ["Related_Parties", [SAMPLE_RP_HEADERS, ...SAMPLE_RP]],
    ["Approvals", [SAMPLE_AP_HEADERS, ...SAMPLE_AP]],
  ] as [string, unknown[][]][]) {
    const sheet = XLSX.utils.aoa_to_sheet(data);
    sheet["!cols"] = (data[0] ?? []).map(() => ({ wch: 25 }));
    XLSX.utils.book_append_sheet(wb, sheet, name);
  }
  return wb;
}
export function loadSample() {
  return readWorkbook(XLSX.write(sampleWorkbook(), { type: "array", bookType: "xlsx" }));
}
export function downloadSample() {
  XLSX.writeFile(sampleWorkbook(), "RPT_sample_Sahyadri.xlsx");
}
