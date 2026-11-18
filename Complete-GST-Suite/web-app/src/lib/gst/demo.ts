import { MONTHS, isoDay } from "./format";
import { makeGstin } from "./gstin";
import { dataVersion, uploadsFor, type UploadedData } from "./uploads";

export type SaleType = "B2B" | "B2CS" | "CDNR";
export type ItcType = "Inputs" | "Capital goods" | "Input services";

export interface Invoice {
  id: string;
  no: string;
  date: string;
  /** Books / GSTR-1: invoice month. GSTR-2B: the 2B return period. */
  month: string;
  party: string;
  gstin: string;
  taxable: number;
  igst: number;
  cgst: number;
  sgst: number;
  cess: number;
  type?: SaleType | undefined;
  itcType?: ItcType | undefined;
  itcAvailable?: boolean | undefined;
}

export type DataSource = "Auto" | "GSP API" | "Downloaded files";
export const DATA_SOURCES: DataSource[] = ["Auto", "GSP API", "Downloaded files"];

/** Client master record. There is deliberately no password field anywhere. */
export interface Client {
  id: string;
  name: string;
  tradeName: string;
  gstin: string;
  portalUsername: string;
  mobile4: string;
  email: string;
  frequency: "Monthly" | "QRMP";
  fy: string;
  tallyCompany: string;
  apiEnabled: boolean;
  apiValidTill: string;
  staff: string;
  fetchReturns: boolean;
  fetchNotices: boolean;
  active: boolean;
  dataSource: DataSource;
  remarks: string;
  /* descriptive extras */
  state: string;
  city: string;
  business: string;
  contact: string;
  filing: string;
  note: string;
  /** true for the seeded demo clients (their invoices are generated from a seed) */
  demo?: boolean | undefined;
}

export interface TaxHeads {
  taxable: number;
  igst: number;
  cgst: number;
  sgst: number;
  cess: number;
}

export interface Return3B {
  month: string;
  /** Table 3.1(a) outward taxable supplies */
  out: TaxHeads;
  /** Table 4(C) net ITC available (tax heads only, taxable = 0) */
  itc: TaxHeads;
}

export type ReturnKind = "gstr1" | "gstr2b" | "gstr3b";

export interface ClientData {
  sales: Invoice[];
  purchases: Invoice[];
  gstr1: Invoice[];
  gstr2b: Invoice[];
  gstr3b: Return3B[];
  /** months for which a return is not available */
  missing: Record<ReturnKind, string[]>;
}

export type NoticeStatusInternal = "Open" | "In progress" | "Replied" | "Closed";
export const NOTICE_STATUSES: NoticeStatusInternal[] = ["Open", "In progress", "Replied", "Closed"];

export interface Notice {
  id: string;
  clientId: string;
  gstin: string;
  form: string;
  /** nature of the notice (from the form library, editable) */
  subject: string;
  ref: string;
  taxPeriod: string;
  issued: string;
  due: string;
  amount: number;
  priority: "Critical" | "High" | "Medium" | "Low";
  action: string;
  portalStatus: string;
  source: "Manual" | "GSP notices API" | "Template upload";
  assignedTo: string;
  status: NoticeStatusInternal;
  notes: string;
  attachment?: { name: string; dataUrl: string } | undefined;
  reply?: { name: string; dataUrl: string } | undefined;
  repliedOn?: string | undefined;
  /** kept in sync with status for older screens: Replied/Closed = true */
  replied: boolean;
}

const seedClient = (c: Partial<Client> & Pick<Client, "id" | "name" | "gstin">): Client => ({
  tradeName: c.name,
  portalUsername: "",
  mobile4: "",
  email: "",
  frequency: "Monthly",
  fy: "2025-26",
  tallyCompany: c.name,
  apiEnabled: false,
  apiValidTill: "",
  staff: "",
  fetchReturns: true,
  fetchNotices: true,
  active: true,
  dataSource: "Auto",
  remarks: "",
  state: "",
  city: "",
  business: "",
  contact: "",
  filing: "Monthly",
  note: "",
  demo: true,
  ...c,
});

export const CLIENTS: Client[] = [
  seedClient({
    id: "shree-ganesh",
    name: "Shree Ganesh Traders",
    gstin: "24ABCDE1234F1Z6",
    portalUsername: "shreeganesh_gst",
    mobile4: "4421",
    state: "Gujarat",
    city: "Rajkot",
    business: "Wholesale trading",
    contact: "Ganesh Patel",
    email: "accounts@shreeganesh.in",
    apiEnabled: true,
    apiValidTill: "2026-12-31",
    note: "Planted differences: missing sales in GSTR-1, 3B short payment, ITC excess and under-claim, supplier gaps.",
    remarks: "Demo client with planted differences",
    dataSource: "Auto",
    staff: "Riya Shah",
  }),
  seedClient({
    id: "patel-polymers",
    name: "Patel Polymers Pvt Ltd",
    tradeName: "Patel Polymers",
    gstin: "24AACCP4521K1ZK",
    portalUsername: "patelpoly",
    mobile4: "7788",
    state: "Gujarat",
    city: "Ahmedabad",
    business: "Plastic granules manufacturing",
    contact: "Nidhi Patel",
    email: "finance@patelpolymers.in",
    apiEnabled: true,
    apiValidTill: "2026-12-31",
    note: "Books and all returns fully agree.",
    remarks: "Clean reconciliation",
    dataSource: "GSP API",
    staff: "Amit Desai",
  }),
  seedClient({
    id: "mehta-textiles",
    name: "Mehta Textiles",
    gstin: "24AAHFM7788Q1Z9",
    portalUsername: "mehtatex",
    mobile4: "1290",
    state: "Gujarat",
    city: "Surat",
    business: "Textile trading",
    contact: "Kunal Mehta",
    email: "kunal@mehtatextiles.in",
    apiEnabled: false,
    fetchNotices: false,
    note: "API access not enabled — uses downloaded files. GSTR-1 for Mar-26 has not been downloaded yet.",
    remarks: "API not enabled — uses downloaded files",
    dataSource: "Downloaded files",
    staff: "Riya Shah",
  }),
  seedClient({
    id: "sunrise-hospitality",
    name: "Sunrise Hospitality LLP",
    tradeName: "Sunrise Residency",
    gstin: "27ABDFS1122M1Z7",
    portalUsername: "sunrise_llp",
    mobile4: "5512",
    frequency: "QRMP",
    filing: "QRMP",
    state: "Maharashtra",
    city: "Pune",
    business: "Hotels and restaurants",
    contact: "Sunil Rao",
    email: "accounts@sunrisehospitality.in",
    apiEnabled: false,
    note: "Inactive — waiting for the client to enable API access.",
    remarks: "Waiting for API access",
    dataSource: "Auto",
    active: false,
    staff: "Amit Desai",
  }),
];
export const DEMO_IDS = new Set(CLIENTS.map((c) => c.id));

/* ---------- planted values (Shree Ganesh Traders) ---------- */
export const PLANT = {
  S1: { month: "2025-08", taxable: 155900, igst: 28062 },
  S2: { month: "2026-01", taxable: 80000, cgst: 7200, sgst: 7200 },
  S3: { month: "2025-10", taxable: 50000, cgst: 4500, sgst: 4500 },
  S4: { month: "2026-03", taxable: 125000, typo: 152000 },
  S5: { month: "2025-12" },
  P1: ["2025-04", "2025-06", "2025-07", "2025-09", "2025-11", "2026-01"],
  P2: ["2025-05", "2025-08", "2025-10", "2026-02"],
  P3: ["2025-06", "2025-09", "2026-01"],
  P4: ["2025-05", "2025-07", "2025-08", "2025-10", "2025-11"],
  P5: { month: "2025-12", cgst: 37232, sgst: 37232 },
  P6: { month: "2026-02", cgst: 10000, sgst: 10000 },
} as const;

function rng(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const CUSTOMER_NAMES = [
  "Om Sai Enterprises", "Kaveri Distributors", "Balaji Agencies", "Narmada Industries",
  "Laxmi Wholesale", "Vardhman Retail", "Krishna Supply Co", "Annapurna Stores",
  "Mahalaxmi Exports", "Sunrise Polymers", "Raj Logistics", "Jyoti Packaging",
];
const SUPPLIER_NAMES = [
  "Deccan Chemicals", "Ganga Fabrics", "Bharat Hardware", "Saurashtra Packers",
  "Kutch Salt Works", "Amul Agencies", "Rajhans Steel", "Navkar Plastics",
  "Siddhi Transport", "Uma Electricals",
];
const LETTERS = "ABCDEFGHJKLMNPRSTUVWXYZ";

interface Party { name: string; gstin: string; inter: boolean; code: string }

function makeParties(r: () => number, homeState: string, names: string[]): Party[] {
  return names.map((name, i) => {
    // first party is always inter-state, second always intra-state
    const inter = i === 0 ? true : i === 1 ? false : r() < 0.35;
    const state = inter ? (homeState === "24" ? "27" : "24") : homeState;
    let pan = "";
    for (let k = 0; k < 3; k++) pan += LETTERS[Math.floor(r() * LETTERS.length)];
    pan += i % 2 ? "C" : "F";
    pan += name[0]!.toUpperCase();
    pan += String(1000 + Math.floor(r() * 8999));
    pan += LETTERS[Math.floor(r() * LETTERS.length)];
    const code = name.split(" ").map((w) => w[0]).join("").toUpperCase();
    return { name, gstin: makeGstin(state, pan), inter, code };
  });
}

function heads(taxable: number, rate: number, inter: boolean) {
  const tax = Math.round(taxable * rate);
  const half = Math.round(tax / 2);
  return { taxable, igst: inter ? tax : 0, cgst: inter ? 0 : half, sgst: inter ? 0 : tax - half, cess: 0 };
}

function dateIn(month: string, day: number) {
  return `${month}-${String(day).padStart(2, "0")}`;
}

function makeSales(r: () => number, customers: Party[], prefix: string, idp: string, homeState: string): Invoice[] {
  const list: Invoice[] = [];
  let inv = 0;
  let cn = 0;
  const count = 280;
  for (let i = 0; i < count; i++) {
    const month = MONTHS[Math.floor((i * 12) / count)]!;
    const day = 1 + Math.floor(r() * 27);
    const pos = i % 14;
    const rate = r() < 0.5 ? 0.12 : 0.18;
    if (pos === 5) {
      // B2C small supply (no GSTIN, intra-state)
      inv++;
      const taxable = Math.round((5000 + r() * 40000) / 10) * 10;
      list.push({ id: `${idp}-${i}`, no: `${prefix}/25-26/${String(inv).padStart(4, "0")}`, date: dateIn(month, day), month, party: "Walk-in customers (B2C)", gstin: "", type: "B2CS", ...heads(taxable, rate, false) });
      continue;
    }
    const p = customers[Math.floor(r() * customers.length)]!;
    if (pos === 11 && i % 28 === 11) {
      // credit note — negative values
      cn++;
      const taxable = -Math.round((3000 + r() * 20000) / 10) * 10;
      list.push({ id: `${idp}-${i}`, no: `${prefix}/CN/25-26/${String(cn).padStart(3, "0")}`, date: dateIn(month, day), month, party: p.name, gstin: p.gstin, type: "CDNR", ...heads(taxable, rate, p.inter) });
      continue;
    }
    inv++;
    const taxable = Math.round((20000 + r() * 280000) / 10) * 10;
    list.push({ id: `${idp}-${i}`, no: `${prefix}/25-26/${String(inv).padStart(4, "0")}`, date: dateIn(month, day), month, party: p.name, gstin: p.gstin, type: "B2B", ...heads(taxable, rate, p.inter) });
  }
  void homeState;
  return list;
}

function makePurchases(r: () => number, suppliers: Party[], idp: string): Invoice[] {
  const list: Invoice[] = [];
  const seq = new Map<string, number>();
  const count = 165;
  for (let i = 0; i < count; i++) {
    const month = MONTHS[Math.floor((i * 12) / count)]!;
    const day = 1 + Math.floor(r() * 27);
    const p = suppliers[Math.floor(r() * suppliers.length)]!;
    const n = (seq.get(p.code) ?? 0) + 1;
    seq.set(p.code, n);
    const roll = r();
    const itcType: ItcType = roll < 0.7 ? "Inputs" : roll < 0.8 ? "Capital goods" : "Input services";
    const taxable = Math.round((15000 + r() * 220000) / 10) * 10;
    const rate = itcType === "Input services" ? 0.18 : r() < 0.5 ? 0.12 : 0.18;
    list.push({ id: `${idp}-${i}`, no: `${p.code}/${String(n).padStart(4, "0")}`, date: dateIn(month, day), month, party: p.name, gstin: p.gstin, itcType, itcAvailable: true, ...heads(taxable, rate, p.inter) });
  }
  return list;
}

function sumMonth(list: Invoice[], month: string): TaxHeads {
  const s = { taxable: 0, igst: 0, cgst: 0, sgst: 0, cess: 0 };
  for (const i of list)
    if (i.month === month) {
      s.taxable += i.taxable;
      s.igst += i.igst;
      s.cgst += i.cgst;
      s.sgst += i.sgst;
      s.cess += i.cess;
    }
  return s;
}

const nextMonth = (m: string) => MONTHS[MONTHS.indexOf(m) + 1]!;
const cache = new Map<string, ClientData>();
const merged = new Map<string, ClientData>();

/**
 * Data used by every calculation for a client:
 * demo clients start from their seeded books and returns; uploaded files (or a GSP fetch)
 * replace the months they cover. Other clients use only what was uploaded.
 */
export function getClientData(clientId: string): ClientData {
  const key = `${clientId}|${dataVersion()}`;
  const hit = merged.get(key);
  if (hit) return hit;
  const up = uploadsFor(clientId);
  const base: ClientData = DEMO_IDS.has(clientId)
    ? generateDemoData(clientId)
    : { sales: [], purchases: [], gstr1: [], gstr2b: [], gstr3b: [], missing: { gstr1: [...MONTHS], gstr2b: [...MONTHS], gstr3b: [...MONTHS] } };
  const data = up ? overlay(base, up) : base;
  merged.set(key, data);
  return data;
}

function overlay(base: ClientData, up: UploadedData): ClientData {
  const missing = { gstr1: [...base.missing.gstr1], gstr2b: [...base.missing.gstr2b], gstr3b: [...base.missing.gstr3b] };
  const replace = (list: Invoice[], kind: "gstr1" | "gstr2b") => {
    const months = Object.keys(up[kind]);
    if (!months.length) return list;
    missing[kind] = missing[kind].filter((m) => !months.includes(m));
    return [...list.filter((i) => !months.includes(i.month)), ...months.flatMap((m) => up[kind][m]!)];
  };
  const months3b = Object.keys(up.gstr3b);
  missing.gstr3b = missing.gstr3b.filter((m) => !months3b.includes(m));
  const empty3b = (m: string): Return3B => ({ month: m, out: { taxable: 0, igst: 0, cgst: 0, sgst: 0, cess: 0 }, itc: { taxable: 0, igst: 0, cgst: 0, sgst: 0, cess: 0 } });
  const gstr3b = MONTHS.map((m) => up.gstr3b[m] ?? base.gstr3b.find((r) => r.month === m) ?? empty3b(m));
  return {
    sales: up.sales ?? base.sales,
    purchases: up.purchases ?? base.purchases,
    gstr1: replace(base.gstr1, "gstr1"),
    gstr2b: replace(base.gstr2b, "gstr2b"),
    gstr3b,
    missing,
  };
}

function generateDemoData(clientId: string): ClientData {
  const hit = cache.get(clientId);
  if (hit) return hit;
  const ci = CLIENTS.findIndex((c) => c.id === clientId);
  if (ci < 0) throw new Error(`No data for client ${clientId}`);
  const client = CLIENTS[ci]!;
  const r = rng(1000 + ci * 7919);
  const home = client.gstin.slice(0, 2);
  const customers = makeParties(r, home, CUSTOMER_NAMES);
  const suppliers = makeParties(r, home, SUPPLIER_NAMES);
  const prefix = client.name.split(" ").map((w) => w[0]).join("").slice(0, 3).toUpperCase();
  const sales = makeSales(r, customers, prefix, `${clientId}-s`, home);
  const purchases = makePurchases(r, suppliers, `${clientId}-p`);

  let gstr1 = sales.map((s) => ({ ...s }));
  let gstr2b = purchases.map((p) => ({ ...p }));
  const missing: ClientData["missing"] = { gstr1: [], gstr2b: [], gstr3b: [] };
  const adj3bOut: Record<string, Partial<TaxHeads>> = {};
  const adj3bItc: Record<string, Partial<TaxHeads>> = {};
  const exclude3bOut = new Set<string>();

  if (clientId === "shree-ganesh") {
    const pick = (m: string, inter: boolean, skip: Set<string>) =>
      sales.find((s) => s.month === m && s.type === "B2B" && !skip.has(s.id) && customers.find((c) => c.gstin === s.gstin)!.inter === inter)!;
    const used = new Set<string>();
    const set = (inv: Invoice, v: Partial<Invoice>) => { Object.assign(inv, v); used.add(inv.id); };
    // S1: Aug-25 sale in books, missing in GSTR-1 and GSTR-3B
    const s1 = pick(PLANT.S1.month, true, used);
    set(s1, { taxable: PLANT.S1.taxable, igst: PLANT.S1.igst, cgst: 0, sgst: 0, cess: 0 });
    // S2: Jan-26 sale in books and 3B, not in GSTR-1
    const s2 = pick(PLANT.S2.month, false, used);
    set(s2, { taxable: PLANT.S2.taxable, igst: 0, cgst: PLANT.S2.cgst, sgst: PLANT.S2.sgst, cess: 0 });
    // S4: Mar-26 typed in GSTR-1 as 1,52,000 instead of 1,25,000
    const s4 = pick(PLANT.S4.month, false, used);
    set(s4, heads(PLANT.S4.taxable, 0.18, false));
    // S5: Dec-25 invoice number typo in GSTR-1
    const s5 = pick(PLANT.S5.month, false, used);
    used.add(s5.id);

    gstr1 = sales
      .filter((s) => s.id !== s1.id && s.id !== s2.id)
      .map((s) => {
        if (s.id === s4.id) return { ...s, ...heads(PLANT.S4.typo, 0.18, false) };
        if (s.id === s5.id) return { ...s, no: s.no.replace("/25-26/", "/25-62/") };
        return { ...s };
      });
    exclude3bOut.add(s1.id);
    adj3bOut[PLANT.S3.month] = { taxable: -PLANT.S3.taxable, cgst: -PLANT.S3.cgst, sgst: -PLANT.S3.sgst };

    // Purchases — each plant uses a distinct invoice
    const usedP = new Set<string>();
    const pickP = (m: string) => {
      const p = purchases.find((x) => x.month === m && !usedP.has(x.id))!;
      usedP.add(p.id);
      return p;
    };
    const p1 = new Set(PLANT.P1.map((m) => pickP(m).id));
    const p3 = new Set(PLANT.P3.map((m) => pickP(m).id));
    const p4 = new Set(PLANT.P4.map((m) => pickP(m).id));
    gstr2b = purchases
      .filter((p) => !p1.has(p.id))
      .map((p) => {
        if (p3.has(p.id)) {
          const rate = Math.round(((p.igst + p.cgst + p.sgst) / p.taxable) * 100) / 100;
          return { ...p, ...heads(p.taxable + 10000, rate, p.igst > 0) };
        }
        if (p4.has(p.id)) return { ...p, month: nextMonth(p.month) };
        return { ...p };
      });
    // P2: in GSTR-2B, never booked
    PLANT.P2.forEach((m, k) => {
      const s = suppliers[(k * 3 + 2) % suppliers.length]!;
      gstr2b.push({
        id: `${clientId}-p2-${k}`,
        no: `${s.code}/9${String(k + 1).padStart(3, "0")}`,
        date: dateIn(m, 10 + k),
        month: m,
        party: s.name,
        gstin: s.gstin,
        itcType: "Inputs",
        itcAvailable: true,
        ...heads(42000 + k * 7310, 0.18, s.inter),
      });
    });
    adj3bItc[PLANT.P5.month] = { cgst: PLANT.P5.cgst, sgst: PLANT.P5.sgst };
    adj3bItc[PLANT.P6.month] = { cgst: -PLANT.P6.cgst, sgst: -PLANT.P6.sgst };
  }
  if (clientId === "mehta-textiles") {
    missing.gstr1 = ["2026-03"];
    gstr1 = gstr1.filter((s) => !missing.gstr1.includes(s.month));
  }

  const out3b = sales.filter((s) => !exclude3bOut.has(s.id));
  const avail2b = gstr2b.filter((p) => p.itcAvailable !== false);
  const gstr3b: Return3B[] = MONTHS.map((m) => {
    const out = sumMonth(out3b, m);
    const itc = { ...sumMonth(avail2b, m), taxable: 0 };
    for (const [k, v] of Object.entries(adj3bOut[m] ?? {})) out[k as keyof TaxHeads] += v;
    for (const [k, v] of Object.entries(adj3bItc[m] ?? {})) itc[k as keyof TaxHeads] += v;
    return { month: m, out, itc };
  });

  const data: ClientData = { sales, purchases, gstr1, gstr2b, gstr3b, missing };
  cache.set(clientId, data);
  return data;
}

/* ---------- demo notices ---------- */
type NoticeSeed = Pick<Notice, "id" | "clientId" | "form" | "ref" | "taxPeriod" | "amount" | "source"> & { issued: number; due: number; replied?: boolean; notes?: string };

const NOTICE_SEEDS: NoticeSeed[] = [
  { id: "n1", clientId: "patel-polymers", form: "ADT-01", ref: "ZA240925AUD0112", taxPeriod: "FY 2023-24", issued: -35, due: -5, amount: 0, source: "GSP notices API" },
  { id: "n2", clientId: "shree-ganesh", form: "DRC-01C", ref: "ZD2412250098761", taxPeriod: "Dec-25", issued: -5, due: 2, amount: 74464, source: "GSP notices API", notes: "ITC in 3B exceeds 2B by ₹74,464 for Dec-25 — see R5." },
  { id: "n3", clientId: "shree-ganesh", form: "DRC-01B", ref: "ZD2410250076543", taxPeriod: "Oct-25", issued: -4, due: 3, amount: 9000, source: "GSP notices API", notes: "GSTR-1 liability higher than 3B for Oct-25 — see R1." },
  { id: "n4", clientId: "shree-ganesh", form: "ASMT-10", ref: "ZA2409250012345", taxPeriod: "FY 2024-25", issued: -17, due: 13, amount: 215400, source: "Manual" },
  { id: "n5", clientId: "patel-polymers", form: "GSTR-3A", ref: "ZR2411250054321", taxPeriod: "Sep-25", issued: -3, due: 12, amount: 0, source: "GSP notices API" },
  { id: "n6", clientId: "mehta-textiles", form: "REG-03", ref: "AA240825001122X", taxPeriod: "—", issued: -40, due: -33, amount: 0, source: "Manual", replied: true, notes: "Address proof submitted in REG-04." },
];

function shift(today: Date, n: number) {
  const x = new Date(today);
  x.setDate(x.getDate() + n);
  return isoDay(x);
}

/** Library defaults (nature, priority, action) are filled in by notices.ts → noticeFromLibrary. */
export function makeDemoNotices(today = new Date(), fill: (n: Partial<Notice>) => Notice): Notice[] {
  return NOTICE_SEEDS.map((s) => {
    const c = CLIENTS.find((x) => x.id === s.clientId)!;
    return fill({
      id: s.id,
      clientId: s.clientId,
      gstin: c.gstin,
      form: s.form,
      ref: s.ref,
      taxPeriod: s.taxPeriod,
      issued: shift(today, s.issued),
      due: shift(today, s.due),
      amount: s.amount,
      source: s.source,
      assignedTo: c.staff,
      status: s.replied ? "Replied" : "Open",
      portalStatus: s.replied ? "Reply filed" : "Issued",
      repliedOn: s.replied ? shift(today, s.due + 6) : undefined,
      notes: s.notes ?? "",
    });
  });
}

/** What the simulated GSP notices API returns for a GSTIN (notices and orders of the last 60 days). */
export function gspNoticeFeed(gstin: string, today = new Date()): Partial<Notice>[] {
  const c = CLIENTS.find((x) => x.gstin === gstin);
  if (!c) return [];
  const feed: Partial<Notice>[] = NOTICE_SEEDS.filter((s) => s.clientId === c.id && s.source === "GSP notices API").map((s) => ({
    form: s.form, ref: s.ref, taxPeriod: s.taxPeriod, issued: shift(today, s.issued), due: shift(today, s.due), amount: s.amount, gstin,
  }));
  if (c.id === "patel-polymers") feed.push({ form: "DRC-01A", ref: "ZD2411250061199", taxPeriod: "FY 2022-23", issued: shift(today, -2), due: shift(today, 28), amount: 48200, gstin });
  return feed.filter((n) => daysBetweenIso(n.issued!, isoDay(today)) <= 60);
}
const daysBetweenIso = (a: string, b: string) => Math.round((new Date(b + "T00:00:00").getTime() - new Date(a + "T00:00:00").getTime()) / 86400000);

/* ---------- files list (seeded files + uploads) ---------- */
export interface DemoFile {
  id: string;
  name: string;
  kind: string;
  period: string;
  rows: number;
  status: "Imported" | "Missing" | "Rejected";
  at?: string | undefined;
  by?: string | undefined;
  message?: string | undefined;
  uploaded?: boolean | undefined;
}

export function getClientFiles(clientId: string): DemoFile[] {
  const up = uploadsFor(clientId);
  const uploaded: DemoFile[] = (up?.files ?? []).map((f) => ({ ...f, uploaded: true }));
  if (!DEMO_IDS.has(clientId)) return uploaded;
  const cd = generateDemoData(clientId);
  const files: DemoFile[] = [
    { id: "seed-sales", name: "Sales_Register_FY2025-26.xlsx", kind: "Books — sales", period: "Apr-25 to Mar-26", rows: cd.sales.length, status: "Imported" },
    { id: "seed-purch", name: "Purchase_Register_FY2025-26.xlsx", kind: "Books — purchases", period: "Apr-25 to Mar-26", rows: cd.purchases.length, status: "Imported" },
    { id: "seed-3b", name: "GSTR3B_FY2025-26.json", kind: "GSTR-3B", period: "Apr-25 to Mar-26", rows: 12, status: "Imported" },
  ];
  for (const [kind, list] of [["GSTR-1", cd.gstr1], ["GSTR-2B", cd.gstr2b]] as const) {
    const key = kind === "GSTR-1" ? "gstr1" : "gstr2b";
    for (const m of MONTHS) {
      const miss = cd.missing[key].includes(m) && !up?.[key][m];
      files.push({ id: `seed-${key}-${m}`, name: `${kind.replace("-", "")}_${m.replace("-", "")}.json`, kind, period: m, rows: miss ? 0 : list.filter((p) => p.month === m).length, status: miss ? "Missing" : "Imported" });
    }
  }
  return [...uploaded, ...files];
}

