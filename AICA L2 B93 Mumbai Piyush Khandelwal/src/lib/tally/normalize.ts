/**
 * Normalises a raw Tally payload (pushed in by the on-premise bridge) into the
 * same dataset shapes the dashboards already speak. Widgets never see raw
 * Tally structures.
 */

export interface TallyVoucher {
  date: string;
  type: string;
  number?: string;
  party?: string;
  amount: number;
  taxable?: number;
  cgst?: number;
  sgst?: number;
  igst?: number;
  narration?: string;
}

export interface TallyLedger {
  name: string;
  group?: string;
  closing?: number;
}

export interface TallyStockItem {
  name: string;
  quantity?: number;
  value?: number;
  category?: string;
}

export interface TallyPayload {
  company?: string;
  vouchers?: TallyVoucher[];
  ledgers?: TallyLedger[];
  stock?: TallyStockItem[];
}

export type NormalRow = Record<string, string | number | null>;
export interface NormalRecord {
  dataset: string;
  record_date: string | null;
  data: NormalRow;
}

const num = (v: unknown) => {
  const n = Number(v);
  return Number.isFinite(n) ? Math.abs(Math.round(n)) : 0;
};

const isoDate = (v: unknown): string | null => {
  const s = String(v ?? "").trim();
  // Tally exports YYYYMMDD as well as ISO dates.
  if (/^\d{8}$/.test(s)) return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d.toISOString().slice(0, 10);
};

const kind = (type: string) => {
  const t = type.toLowerCase();
  if (t.includes("sales") || t.includes("credit note")) return "sales";
  if (t.includes("purchase") || t.includes("debit note")) return "purchase";
  if (t.includes("receipt")) return "receipt";
  if (t.includes("payment")) return "payment";
  return "other";
};

export function normaliseTally(payload: TallyPayload): NormalRecord[] {
  const out: NormalRecord[] = [];
  const company = payload.company ?? "—";

  for (const v of payload.vouchers ?? []) {
    const date = isoDate(v.date);
    if (!date) continue;
    const taxable = v.taxable != null ? num(v.taxable) : num(v.amount) - num(v.cgst) - num(v.sgst) - num(v.igst);
    const tax = num(v.cgst) + num(v.sgst) + num(v.igst);
    switch (kind(v.type)) {
      case "sales":
        out.push({
          dataset: "sales_invoices",
          record_date: date,
          data: {
            invoice_no: v.number ?? "—",
            invoice_date: date,
            customer: v.party ?? "—",
            salesperson: "—",
            branch: company,
            region: "—",
            product: "—",
            category: v.type,
            hsn: "—",
            gstin: "—",
            status: "Posted",
            quantity: 0,
            taxable_value: taxable,
            cgst: num(v.cgst),
            sgst: num(v.sgst),
            igst: num(v.igst),
            tax_amount: tax,
            discount: 0,
            invoice_amount: num(v.amount),
            profit: 0,
            due_days: 0,
          },
        });
        break;
      case "purchase":
        out.push({
          dataset: "purchase_invoices",
          record_date: date,
          data: {
            bill_no: v.number ?? "—",
            bill_date: date,
            vendor: v.party ?? "—",
            branch: company,
            category: v.type,
            status: "Posted",
            taxable_value: taxable,
            tax_amount: tax,
            bill_amount: num(v.amount),
          },
        });
        break;
      case "receipt":
        out.push({
          dataset: "payments",
          record_date: date,
          data: {
            payment_ref: v.number ?? "—",
            payment_date: date,
            customer: v.party ?? "—",
            mode: v.narration ?? "—",
            status: "Received",
            amount: num(v.amount),
          },
        });
        break;
      case "payment":
        out.push({
          dataset: "expenses",
          record_date: date,
          data: {
            expense_date: date,
            category: v.party ?? "Other",
            branch: company,
            amount: num(v.amount),
          },
        });
        break;
      default:
        break;
    }
  }

  for (const l of payload.ledgers ?? []) {
    const group = l.group ?? "—";
    const closing = Number(l.closing ?? 0);
    out.push({
      dataset: "ledgers",
      record_date: null,
      data: {
        ledger: l.name,
        group,
        debit: closing > 0 ? Math.round(closing) : 0,
        credit: closing < 0 ? Math.round(-closing) : 0,
      },
    });
    if (group.toLowerCase().includes("debtor")) {
      out.push({
        dataset: "customers",
        record_date: null,
        data: {
          customer: l.name,
          gstin: "—",
          region: "—",
          branch: company,
          credit_days: 0,
          outstanding: num(closing),
          lifetime_value: 0,
        },
      });
    }
    if (group.toLowerCase().includes("creditor")) {
      out.push({
        dataset: "vendors",
        record_date: null,
        data: { vendor: l.name, gstin: "—", category: group, payable: num(closing) },
      });
    }
  }

  for (const s of payload.stock ?? []) {
    out.push({
      dataset: "inventory",
      record_date: null,
      data: {
        product: s.name,
        category: s.category ?? "—",
        hsn: "—",
        quantity: num(s.quantity),
        reorder_level: 0,
        stock_value: num(s.value),
        turnover_days: 0,
      },
    });
  }

  return out;
}
