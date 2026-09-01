export type SourceKey =
  | "tally_sales"
  | "tally_purchase"
  | "tally_gst_ledger"
  | "gstr1"
  | "gstr3b"
  | "gstr2b"
  | "gstr9"
  | "prev_year_adj";

export const SOURCES: { key: SourceKey; label: string; group: "books" | "returns"; note: string }[] = [
  { key: "tally_sales", label: "Tally Sales Register", group: "books", note: "Outward supplies as per books" },
  { key: "tally_purchase", label: "Tally Purchase Register", group: "books", note: "Inward supplies as per books" },
  { key: "tally_gst_ledger", label: "Tally GST Ledger Summary", group: "books", note: "Tax ledger balances as per books" },
  { key: "gstr1", label: "GSTR-1 Data", group: "returns", note: "Outward supplies filed" },
  { key: "gstr3b", label: "GSTR-3B Data", group: "returns", note: "Summary liability and ITC" },
  { key: "gstr2b", label: "GSTR-2B Data", group: "returns", note: "Auto-drafted ITC statement" },
  { key: "gstr9", label: "GSTR-9 Draft / Annual Summary", group: "returns", note: "Annual return figures" },
  { key: "prev_year_adj", label: "Previous Year Reconciliation Adjustments", group: "returns", note: "Carry-forward adjustments" },
];

export type FieldKey =
  | "invoice_no"
  | "invoice_date"
  | "party_name"
  | "party_gstin"
  | "taxable_value"
  | "gst_rate"
  | "cgst"
  | "sgst"
  | "igst"
  | "cess"
  | "place_of_supply"
  | "voucher_type"
  | "reverse_charge"
  | "doc_type"
  | "original_invoice_no"
  | "supply_type"
  | "hsn";

export const FIELDS: {
  key: FieldKey;
  label: string;
  type: "text" | "number" | "date" | "bool";
  required?: boolean;
  hint?: string;
}[] = [
  { key: "invoice_no", label: "Invoice / Document Number", type: "text", required: true },
  { key: "invoice_date", label: "Invoice / Document Date", type: "date", required: true },
  { key: "party_name", label: "Party Name", type: "text" },
  { key: "party_gstin", label: "Party GSTIN", type: "text" },
  { key: "taxable_value", label: "Taxable Value", type: "number", required: true },
  { key: "gst_rate", label: "GST Rate (%)", type: "number" },
  { key: "cgst", label: "CGST Amount", type: "number" },
  { key: "sgst", label: "SGST Amount", type: "number" },
  { key: "igst", label: "IGST Amount", type: "number" },
  { key: "cess", label: "Cess Amount", type: "number" },
  { key: "place_of_supply", label: "Place of Supply", type: "text" },
  { key: "voucher_type", label: "Voucher Type", type: "text" },
  { key: "reverse_charge", label: "Reverse Charge (Y/N)", type: "bool" },
  { key: "doc_type", label: "Document Type (Invoice / Credit Note / Debit Note / Amendment)", type: "text" },
  { key: "original_invoice_no", label: "Original Invoice No. (for CN / DN / Amendment)", type: "text" },
  { key: "supply_type", label: "Supply Type (B2B / B2C / Export / SEZ / Exempt / Nil / Non-GST)", type: "text" },
  { key: "hsn", label: "HSN / SAC Code", type: "text" },
];

export type MismatchStatus =
  | "matched"
  | "missing_in_tally"
  | "missing_in_return"
  | "value_mismatch"
  | "tax_mismatch"
  | "gstin_mismatch"
  | "invoice_no_mismatch"
  | "timing_difference"
  | "manual_review";

export const STATUS_LABEL: Record<MismatchStatus, string> = {
  matched: "Matched",
  missing_in_tally: "Missing in Tally",
  missing_in_return: "Missing in GST Return",
  value_mismatch: "Value Mismatch",
  tax_mismatch: "Tax Mismatch",
  gstin_mismatch: "GSTIN Mismatch",
  invoice_no_mismatch: "Invoice Number Mismatch",
  timing_difference: "Timing Difference",
  manual_review: "Requires Manual Review",
};

export interface Client {
  id: string;
  name: string;
  gstin: string;
  fy: string;
  state: string;
  reg_type: string;
  created_at: string;
}

export interface Txn {
  id: string;
  client_id: string;
  source: SourceKey;
  invoice_no: string;
  invoice_date: string;
  party_name: string;
  party_gstin: string;
  taxable_value: number;
  gst_rate: number;
  cgst: number;
  sgst: number;
  igst: number;
  cess: number;
  place_of_supply: string;
  voucher_type: string;
  reverse_charge: number;
  doc_type: string;
  original_invoice_no: string;
  supply_type: string;
  hsn: string;
  import_id: string;
}

export interface ReconItem {
  id: string;
  client_id: string;
  section: string;
  key_label: string;
  party: string;
  status: MismatchStatus;
  books_taxable: number;
  books_tax: number;
  gst_taxable: number;
  gst_tax: number;
  remarks: string;
  adjustment: number;
  proposed_treatment: string;
  resolved: number;
}

export const REG_TYPES = ["Regular", "Composition", "SEZ Unit", "SEZ Developer", "Input Service Distributor", "Casual Taxable Person"];

export const STATES = [
  "Andhra Pradesh","Assam","Bihar","Chhattisgarh","Delhi","Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Odisha","Punjab","Rajasthan","Tamil Nadu","Telangana","Uttar Pradesh","Uttarakhand","West Bengal","Other",
];
