/**
 * Fictitious demo dataset. Loaded into the same local SQLite database as any
 * other client — nothing is uploaded anywhere.
 */
import { logAudit, run, uid } from "./db";
import type { SourceKey } from "./types";

export const DEMO_CLIENT_NAME = "Harmony Demo Solutions Pvt Ltd";
export const DEMO_LABEL = "DEMO DATA – NOT REAL CLIENT INFORMATION";
export const isDemoClient = (name?: string) => name === DEMO_CLIENT_NAME;

interface Row {
  invoice_no: string;
  invoice_date: string;
  party_name: string;
  party_gstin: string;
  taxable_value: number;
  gst_rate?: number;
  cgst?: number;
  sgst?: number;
  igst?: number;
  cess?: number;
  place_of_supply?: string;
  voucher_type?: string;
  reverse_charge?: number;
  doc_type?: string;
  original_invoice_no?: string;
  supply_type?: string;
  hsn?: string;
}

/** Intra-state row helper (CGST + SGST). */
const intra = (
  invoice_no: string,
  invoice_date: string,
  party_name: string,
  party_gstin: string,
  taxable_value: number,
  rate: number,
  extra: Partial<Row> = {},
): Row => ({
  invoice_no,
  invoice_date,
  party_name,
  party_gstin,
  taxable_value,
  gst_rate: rate,
  cgst: +((taxable_value * rate) / 200).toFixed(2),
  sgst: +((taxable_value * rate) / 200).toFixed(2),
  igst: 0,
  cess: 0,
  place_of_supply: "Maharashtra",
  voucher_type: "Sales",
  doc_type: "Invoice",
  supply_type: "B2B",
  hsn: "998313",
  ...extra,
});

/** Inter-state row helper (IGST). */
const inter = (
  invoice_no: string,
  invoice_date: string,
  party_name: string,
  party_gstin: string,
  taxable_value: number,
  rate: number,
  extra: Partial<Row> = {},
): Row => ({
  invoice_no,
  invoice_date,
  party_name,
  party_gstin,
  taxable_value,
  gst_rate: rate,
  cgst: 0,
  sgst: 0,
  igst: +((taxable_value * rate) / 100).toFixed(2),
  cess: 0,
  place_of_supply: "Karnataka",
  voucher_type: "Sales",
  doc_type: "Invoice",
  supply_type: "B2B",
  hsn: "998313",
  ...extra,
});

/* ---------------- Books: Tally Sales Register ---------------- */
const TALLY_SALES: Row[] = [
  intra("INV-2501", "2025-04-08", "Blue Orchid Traders", "27AABCB1234C1Z5", 450000, 18),
  inter("INV-2502", "2025-04-19", "Sunrise Infotech LLP", "29AACFS5678D1ZK", 320000, 18),
  intra("INV-2503", "2025-05-06", "Meridian Textiles", "27AAECM4321F1Z2", 275000, 12),
  inter("INV-2504", "2025-05-27", "Vertex Logistics Pvt Ltd", "06AAGCV8765H1Z8", 610000, 18),
  intra("INV-2505", "2025-06-14", "Kalpataru Foods", "27AAJCK2468K1Z1", 185000, 5, { hsn: "210690" }),
  // Present in books but never reported in GSTR-1 -> Missing in GST Return
  intra("INV-2506", "2025-06-29", "Nirvana Interiors", "27AAKCN1357L1Z9", 240000, 18),
  // Value mismatch against GSTR-1 (books 500000 vs return 485000)
  inter("INV-2507", "2025-07-11", "Zenith Pharma Ltd", "24AAMCZ9753M1Z4", 500000, 18),
  // Invoice number mismatch (books INV-2508 vs return INV-2508A)
  intra("INV-2508", "2025-08-05", "Everest Packaging", "27AANCE1122N1Z3", 365000, 18),
  intra("INV-2509", "2025-09-16", "Sahyadri Retail", "27AAPCS3344P1Z7", 128000, 12),
  intra("CN-2501", "2025-10-03", "Blue Orchid Traders", "27AABCB1234C1Z5", 40000, 18, {
    voucher_type: "Credit Note",
    doc_type: "Credit Note",
    original_invoice_no: "INV-2501",
  }),
  inter("INV-2510", "2025-11-21", "Global Exim Co", "27AAQCG5566Q1Z6", 720000, 0, {
    supply_type: "Export",
    place_of_supply: "Other",
  }),
  intra("INV-2511", "2025-12-09", "Sparsh Charitable Trust", "27AARCS7788R1Z2", 96000, 0, {
    supply_type: "Exempt",
  }),
  intra("INV-2512", "2026-01-19", "Retail Walk-in Customers", "", 154000, 18, { supply_type: "B2C" }),
  intra("INV-2513", "2026-02-24", "Aarohi Engineering", "27AASCA9900S1Z8", 288000, 18),
  intra("INV-2514", "2026-03-12", "Meridian Textiles", "27AAECM4321F1Z2", 198000, 12),
];

/* ---------------- Returns: GSTR-1 ---------------- */
const GSTR1: Row[] = [
  intra("INV-2501", "2025-04-08", "Blue Orchid Traders", "27AABCB1234C1Z5", 450000, 18),
  inter("INV-2502", "2025-04-19", "Sunrise Infotech LLP", "29AACFS5678D1ZK", 320000, 18),
  intra("INV-2503", "2025-05-06", "Meridian Textiles", "27AAECM4321F1Z2", 275000, 12),
  inter("INV-2504", "2025-05-27", "Vertex Logistics Pvt Ltd", "06AAGCV8765H1Z8", 610000, 18),
  intra("INV-2505", "2025-06-14", "Kalpataru Foods", "27AAJCK2468K1Z1", 185000, 5, { hsn: "210690" }),
  // Value mismatch
  inter("INV-2507", "2025-07-11", "Zenith Pharma Ltd", "24AAMCZ9753M1Z4", 485000, 18),
  // Invoice number mismatch (same party & value, different number)
  intra("INV-2508A", "2025-08-05", "Everest Packaging", "27AANCE1122N1Z3", 365000, 18),
  intra("INV-2509", "2025-09-16", "Sahyadri Retail", "27AAPCS3344P1Z7", 128000, 12),
  intra("CN-2501", "2025-10-03", "Blue Orchid Traders", "27AABCB1234C1Z5", 40000, 18, {
    voucher_type: "Credit Note",
    doc_type: "Credit Note",
    original_invoice_no: "INV-2501",
  }),
  inter("INV-2510", "2025-11-21", "Global Exim Co", "27AAQCG5566Q1Z6", 720000, 0, {
    supply_type: "Export",
    place_of_supply: "Other",
  }),
  intra("INV-2511", "2025-12-09", "Sparsh Charitable Trust", "27AARCS7788R1Z2", 96000, 0, {
    supply_type: "Exempt",
  }),
  intra("INV-2512", "2026-01-19", "Retail Walk-in Customers", "", 154000, 18, { supply_type: "B2C" }),
  intra("INV-2513", "2026-02-24", "Aarohi Engineering", "27AASCA9900S1Z8", 288000, 18),
  intra("INV-2514", "2026-03-12", "Meridian Textiles", "27AAECM4321F1Z2", 198000, 12),
  // Reported in GSTR-1 but absent from books -> Missing in Tally
  intra("INV-2515", "2026-03-28", "Prism Constructions", "27AATCP2233T1Z5", 175000, 18),
];

/* ---------------- Books: Tally Purchase Register ---------------- */
const TALLY_PURCHASE: Row[] = [
  intra("PUR-901", "2025-04-12", "Aditya Steel Supply", "27AAUCA3344U1Z1", 260000, 18, {
    voucher_type: "Purchase",
    supply_type: "B2B",
  }),
  inter("PUR-902", "2025-05-15", "Coastal Chemicals Ltd", "33AAVCC4455V1Z9", 190000, 18, {
    voucher_type: "Purchase",
  }),
  intra("PUR-903", "2025-06-20", "Deepak Office Systems", "27AAWCD5566W1Z6", 88000, 18, {
    voucher_type: "Purchase",
  }),
  // In books, not in GSTR-2B -> ITC at risk
  intra("PUR-904", "2025-07-25", "Falcon Advertising", "27AAXCF6677X1Z3", 120000, 18, {
    voucher_type: "Purchase",
  }),
  // Value mismatch against GSTR-2B
  inter("PUR-905", "2025-09-02", "Nova Components Pvt Ltd", "29AAYCN7788Y1Z0", 340000, 18, {
    voucher_type: "Purchase",
  }),
  intra("PUR-906", "2025-11-14", "Sahaj Transport", "27AAZCS8899Z1Z7", 65000, 5, {
    voucher_type: "Purchase",
    reverse_charge: 1,
    hsn: "996511",
  }),
  intra("PUR-907", "2026-01-08", "Prime Legal Advisors", "27ABACP9911A1Z4", 90000, 18, {
    voucher_type: "Purchase",
    reverse_charge: 1,
    hsn: "998213",
  }),
  intra("PUR-908", "2026-02-18", "Deepak Office Systems", "27AAWCD5566W1Z6", 74000, 18, {
    voucher_type: "Purchase",
  }),
];

/* ---------------- Returns: GSTR-2B ---------------- */
const GSTR2B: Row[] = [
  intra("PUR-901", "2025-04-12", "Aditya Steel Supply", "27AAUCA3344U1Z1", 260000, 18, { voucher_type: "Purchase" }),
  inter("PUR-902", "2025-05-15", "Coastal Chemicals Ltd", "33AAVCC4455V1Z9", 190000, 18, { voucher_type: "Purchase" }),
  intra("PUR-903", "2025-06-20", "Deepak Office Systems", "27AAWCD5566W1Z6", 88000, 18, { voucher_type: "Purchase" }),
  // Value mismatch (books 340000)
  inter("PUR-905", "2025-09-02", "Nova Components Pvt Ltd", "29AAYCN7788Y1Z0", 325000, 18, { voucher_type: "Purchase" }),
  intra("PUR-908", "2026-02-18", "Deepak Office Systems", "27AAWCD5566W1Z6", 74000, 18, { voucher_type: "Purchase" }),
  // In 2B but not in books -> Missing in Tally
  intra("PUR-909", "2026-03-05", "Crystal Utilities Ltd", "27ABBCC1212B1Z9", 52000, 18, { voucher_type: "Purchase" }),
];

/* ---------------- Returns: GSTR-3B (outward + ITC lines) ---------------- */
const GSTR3B: Row[] = [
  {
    invoice_no: "3B-OUT-FY2526",
    invoice_date: "2026-03-31",
    party_name: "Annual outward summary",
    party_gstin: "",
    taxable_value: 4104000,
    gst_rate: 0,
    cgst: 244530,
    sgst: 244530,
    igst: 219600,
    cess: 0,
    place_of_supply: "Maharashtra",
    voucher_type: "3.1(a) Outward taxable supplies",
    doc_type: "Summary",
    supply_type: "Outward taxable",
    hsn: "",
  },
  {
    invoice_no: "3B-RCM-FY2526",
    invoice_date: "2026-03-31",
    party_name: "Inward supplies liable to reverse charge",
    party_gstin: "",
    taxable_value: 155000,
    gst_rate: 0,
    cgst: 9725,
    sgst: 9725,
    igst: 0,
    cess: 0,
    place_of_supply: "Maharashtra",
    voucher_type: "3.1(d) Reverse charge",
    doc_type: "Summary",
    reverse_charge: 1,
    supply_type: "Outward taxable RCM",
    hsn: "",
  },
  {
    invoice_no: "3B-ITC-FY2526",
    invoice_date: "2026-03-31",
    party_name: "ITC availed during the year",
    party_gstin: "",
    taxable_value: 0,
    gst_rate: 0,
    cgst: 43110,
    sgst: 43110,
    igst: 95400,
    cess: 0,
    place_of_supply: "Maharashtra",
    voucher_type: "4(A)(5) All other ITC",
    doc_type: "Summary",
    supply_type: "ITC availed",
    hsn: "",
  },
];

/* ---------------- Books: Tally GST Ledger Summary ---------------- */
const TALLY_LEDGER: Row[] = [
  {
    invoice_no: "LEDGER-CGST",
    invoice_date: "2026-03-31",
    party_name: "Output CGST Ledger",
    party_gstin: "",
    taxable_value: 244530,
    gst_rate: 0,
    cgst: 0, sgst: 0, igst: 0, cess: 0,
    place_of_supply: "Maharashtra",
    voucher_type: "Output CGST",
    doc_type: "Ledger",
    supply_type: "Ledger balance",
    hsn: "",
  },
  {
    invoice_no: "LEDGER-SGST",
    invoice_date: "2026-03-31",
    party_name: "Output SGST Ledger",
    party_gstin: "",
    taxable_value: 244530,
    gst_rate: 0,
    cgst: 0, sgst: 0, igst: 0, cess: 0,
    place_of_supply: "Maharashtra",
    voucher_type: "Output SGST",
    doc_type: "Ledger",
    supply_type: "Ledger balance",
    hsn: "",
  },
  {
    invoice_no: "LEDGER-IGST",
    invoice_date: "2026-03-31",
    party_name: "Output IGST Ledger",
    party_gstin: "",
    taxable_value: 219600,
    gst_rate: 0,
    cgst: 0, sgst: 0, igst: 0, cess: 0,
    place_of_supply: "Maharashtra",
    voucher_type: "Output IGST",
    doc_type: "Ledger",
    supply_type: "Ledger balance",
    hsn: "",
  },
  {
    invoice_no: "LEDGER-ITC",
    invoice_date: "2026-03-31",
    party_name: "Input Tax Credit Ledger",
    party_gstin: "",
    taxable_value: 190270,
    gst_rate: 0,
    cgst: 0, sgst: 0, igst: 0, cess: 0,
    place_of_supply: "Maharashtra",
    voucher_type: "Input Tax Credit",
    doc_type: "Ledger",
    supply_type: "Ledger balance",
    hsn: "",
  },
];

/* ---------------- Returns: GSTR-9 annual summary ---------------- */
const mkG9 = (
  table: string,
  desc: string,
  supply_type: string,
  taxable_value: number,
  cgst = 0,
  sgst = 0,
  igst = 0,
): Row => ({
  invoice_no: table,
  invoice_date: "2026-03-31",
  party_name: desc,
  party_gstin: "",
  taxable_value,
  gst_rate: 0,
  cgst,
  sgst,
  igst,
  cess: 0,
  place_of_supply: "Maharashtra",
  voucher_type: `Table ${table}`,
  doc_type: "Annual Summary",
  supply_type,
  hsn: "",
});

const GSTR9: Row[] = [
  mkG9("4A", "Supplies to unregistered persons", "B2C", 154000, 13860, 13860, 0),
  mkG9("4B", "Supplies to registered persons", "B2B", 3214000, 230670, 230670, 219600),
  mkG9("4C", "Zero rated supply (Export)", "Export", 720000),
  mkG9("4I", "Credit notes issued", "Credit Note", 40000, 3600, 3600, 0),
  mkG9("5D", "Exempted supplies", "Exempt", 96000),
  mkG9("6A", "Total ITC availed in GSTR-3B", "ITC availed", 0, 43110, 43110, 95400),
  mkG9("8A", "ITC as per GSTR-2B", "ITC 2B", 0, 39240, 39240, 92700),
];

/* ---------------- Previous year adjustments ---------------- */
const PREV_ADJ: Row[] = [
  {
    invoice_no: "PY-ADJ-01",
    invoice_date: "2025-04-30",
    party_name: "FY 2024-25 invoice reported in FY 2025-26 GSTR-1",
    party_gstin: "27AABCB1234C1Z5",
    taxable_value: 85000,
    gst_rate: 18,
    cgst: 7650, sgst: 7650, igst: 0, cess: 0,
    place_of_supply: "Maharashtra",
    voucher_type: "Prior period",
    doc_type: "Amendment",
    original_invoice_no: "INV-2412",
    supply_type: "B2B",
    hsn: "998313",
  },
  {
    invoice_no: "PY-ADJ-02",
    invoice_date: "2025-05-31",
    party_name: "FY 2024-25 ITC availed in FY 2025-26",
    party_gstin: "27AAUCA3344U1Z1",
    taxable_value: 42000,
    gst_rate: 18,
    cgst: 3780, sgst: 3780, igst: 0, cess: 0,
    place_of_supply: "Maharashtra",
    voucher_type: "Prior period ITC",
    doc_type: "Adjustment",
    supply_type: "ITC availed",
    hsn: "",
  },
];

const DATASET: { source: SourceKey; filename: string; rows: Row[] }[] = [
  { source: "tally_sales", filename: "demo-tally-sales-register.xlsx", rows: TALLY_SALES },
  { source: "tally_purchase", filename: "demo-tally-purchase-register.xlsx", rows: TALLY_PURCHASE },
  { source: "tally_gst_ledger", filename: "demo-tally-gst-ledger.xlsx", rows: TALLY_LEDGER },
  { source: "gstr1", filename: "demo-gstr1.xlsx", rows: GSTR1 },
  { source: "gstr3b", filename: "demo-gstr3b.xlsx", rows: GSTR3B },
  { source: "gstr2b", filename: "demo-gstr2b.xlsx", rows: GSTR2B },
  { source: "gstr9", filename: "demo-gstr9.xlsx", rows: GSTR9 },
  { source: "prev_year_adj", filename: "demo-previous-year-adjustments.xlsx", rows: PREV_ADJ },
];

/** Creates the demo client and loads every demo source. Returns the client id. */
export async function loadDemoData(): Promise<string> {
  const clientId = uid();
  await run("INSERT INTO clients (id, name, gstin, fy, state, reg_type, created_at) VALUES (?,?,?,?,?,?,?)", [
    clientId,
    DEMO_CLIENT_NAME,
    "27AAHCH1234K1Z6",
    "2025-26",
    "Maharashtra",
    "Regular",
    new Date().toISOString(),
  ]);
  await logAudit(clientId, "Demo data loaded", DEMO_LABEL);

  for (const { source, filename, rows } of DATASET) {
    const importId = uid();
    await run("INSERT INTO imports (id, client_id, source, filename, row_count, created_at) VALUES (?,?,?,?,?,?)", [
      importId,
      clientId,
      source,
      filename,
      rows.length,
      new Date().toISOString(),
    ]);
    for (const r of rows) {
      await run(
        `INSERT INTO txns (id, client_id, source, import_id, invoice_no, invoice_date, party_name, party_gstin,
          taxable_value, gst_rate, cgst, sgst, igst, cess, place_of_supply, voucher_type, reverse_charge,
          doc_type, original_invoice_no, supply_type, hsn)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
        [
          uid(), clientId, source, importId,
          r.invoice_no, r.invoice_date, r.party_name, r.party_gstin,
          r.taxable_value, r.gst_rate ?? 0, r.cgst ?? 0, r.sgst ?? 0, r.igst ?? 0, r.cess ?? 0,
          r.place_of_supply ?? "", r.voucher_type ?? "", r.reverse_charge ?? 0,
          r.doc_type ?? "Invoice", r.original_invoice_no ?? "", r.supply_type ?? "", r.hsn ?? "",
        ],
      );
    }
    await logAudit(clientId, "Demo import", `${filename} (${rows.length} rows)`);
  }
  return clientId;
}
