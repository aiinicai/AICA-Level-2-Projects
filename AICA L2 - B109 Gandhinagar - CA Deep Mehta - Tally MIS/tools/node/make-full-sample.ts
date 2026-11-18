// Builds a 4.5-year fictional company (with stock) as files you can IMPORT into TallyPrime.
// Run inside a copy of the original Node project:   npx tsx scripts/make-full-sample.ts <output folder>
// It needs src/server/demo/generator_full.ts = the project's demo generator with three small changes (see tools/node/patch_generator.py).
import fs from 'node:fs';
import path from 'node:path';
import { DemoBooks, RESERVED_GROUPS } from '../src/server/demo/generator_full.js';
import { fyOf, monthEnd, parseIso, toIso, addDays } from '@shared/periods';
import { xmlEscape as e } from '../src/server/connectors/tally/requests.js';

const out = process.argv[2];
const FROM = '2021-04-01', TO = '2025-09-30', COMPANY = 'Full Sample Trading Co';
fs.mkdirSync(out, { recursive: true });
const books = new DemoBooks({ from: FROM, to: TO, companyName: COMPANY, seed: 20251114, vouchersPerMonth: 30 });

// ---------------------------------------------------------------- dates: only the 1st, 2nd and 31st (TallyPrime Educational mode accepts nothing else)
const remap = (iso: string) => {
  const { y, m, d } = parseIso(iso);
  const has31 = monthEnd(iso).endsWith('31');
  return toIso(y, m, d <= 10 ? 1 : d <= 20 ? 2 : has31 ? 31 : 2);
};
for (const v of books.vouchers) v.date = remap(v.date);
books.vouchers.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : a.masterId - b.masterId));

// ---------------------------------------------------------------- checks: stock must never go negative; every voucher balances
const qty = new Map(books.items.map((i) => [i.name, i.openingQty * 1e4]));
let minQty = Infinity, negatives = 0;
for (const v of books.vouchers) {
  for (const l of v.inventory) {
    const q = (qty.get(l.item) ?? 0) + (l.dir === 'in' ? l.qtyE4 : -l.qtyE4);
    qty.set(l.item, q);
    if (q < 0) negatives++;
    minQty = Math.min(minQty, q);
  }
  const sum = [...v.lines, ...v.inventory.map((i) => ({ amount: i.dir === 'out' ? -i.valuePaise : i.valuePaise }))].reduce((a, l: any) => a + l.amount, 0);
  if (sum !== 0) throw new Error(`Voucher ${v.type} ${v.number} (${v.date}) does not balance by ${sum}`);
}
if (negatives) throw new Error(`${negatives} stock movements would make stock negative`);

// ---------------------------------------------------------------- masters (import format)
const amt = (canonical: number) => { const t = -canonical; return `${t < 0 ? '-' : ''}${Math.floor(Math.abs(t) / 100)}.${String(Math.abs(t) % 100).padStart(2, '0')}`; };
const wrap = (report: string, parts: string[]) =>
  `<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>${report}</REPORTNAME></REQUESTDESC><REQUESTDATA>\n` +
  parts.map((p) => `<TALLYMESSAGE xmlns:UDF="TallyUDF">${p}</TALLYMESSAGE>`).join('\n') + `\n</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>\n`;
const named = (tag: string, name: string, inner: string) => `<${tag} NAME="${e(name)}" ACTION="Create"><NAME.LIST><NAME>${e(name)}</NAME></NAME.LIST>${inner}</${tag}>`;

const reserved = new Set(RESERVED_GROUPS.map((g) => g.name));
const parts: string[] = [];
for (const g of books.groups.filter((g) => !reserved.has(g.name))) parts.push(named('GROUP', g.name, `<PARENT>${e(g.parent ?? '')}</PARENT>`));
const units = [...new Set(books.items.map((i) => i.unit))];
for (const u of units) parts.push(`<UNIT NAME="${u}" ACTION="Create"><NAME>${u}</NAME><ISSIMPLEUNIT>Yes</ISSIMPLEUNIT></UNIT>`);
for (const g of [...new Set(books.items.map((i) => i.group))]) parts.push(named('STOCKGROUP', g, '<PARENT></PARENT>'));
parts.push(named('GODOWN', 'Warehouse 2', '<PARENT></PARENT>'));   // "Main Location" exists in every company
for (const c of books.costCentres) parts.push(named('COSTCENTRE', c, '<CATEGORY>Primary Cost Category</CATEGORY>'));
for (const l of books.ledgers as any[]) {
  if (l.name === 'Profit & Loss A/c') continue;     // exists in every company (Cash too, but it is listed so the file also stands alone; it has no opening balance)
  const bills = (l.openingBills ?? []).map((b: any) =>
    `<BILLALLOCATIONS.LIST><NAME>${e(b.name)}</NAME><BILLDATE>20210331</BILLDATE>${b.creditDays ? `<BILLCREDITPERIOD>${b.creditDays} Days</BILLCREDITPERIOD>` : ''}<OPENINGBALANCE>${amt(b.amount)}</OPENINGBALANCE></BILLALLOCATIONS.LIST>`).join('');
  parts.push(named('LEDGER', l.name, `<PARENT>${e(l.parent)}</PARENT>${l.opening ? `<OPENINGBALANCE>${amt(l.opening)}</OPENINGBALANCE>` : ''}` +
    `${l.billwise ? '<ISBILLWISEON>Yes</ISBILLWISEON>' : ''}${l.creditDays ? `<BILLCREDITPERIOD>${l.creditDays} Days</BILLCREDITPERIOD>` : ''}` +
    `${l.creditLimit ? `<CREDITLIMIT>${Math.round(l.creditLimit / 100)}</CREDITLIMIT>` : ''}${bills}`));
}
for (const i of books.items) {
  parts.push(named('STOCKITEM', i.name, `<PARENT>${e(i.group)}</PARENT><BASEUNITS>${i.unit}</BASEUNITS><COSTINGMETHOD>Last Purchase Cost</COSTINGMETHOD>` +
    `<OPENINGBALANCE>${i.openingQty} ${i.unit}</OPENINGBALANCE><OPENINGVALUE>${amt(i.openingQty * i.cost)}</OPENINGVALUE><OPENINGRATE>${(i.cost / 100).toFixed(2)}/${i.unit}</OPENINGRATE>`));
}
fs.writeFileSync(path.join(out, '1_Masters_and_Stock_Items.xml'), wrap('All Masters', parts));

// ---------------------------------------------------------------- vouchers, one file per financial year
// Real TallyPrime ignores the party/tax lines of a stock invoice when they are written as ALLLEDGERENTRIES.LIST
// ("Mismatch in total amount"); it wants LEDGERENTRIES.LIST there. (Checked against TallyPrime EDU.)
const fixInvoice = (x: string) => x.includes('<ALLINVENTORYENTRIES.LIST>') ? x.replace(/ALLLEDGERENTRIES\.LIST/g, 'LEDGERENTRIES.LIST') : x;
// TallyPrime drops a bill's credit period unless JD is the serial number of the bill date (days since 1899-12-31).
const fixCredit = (x: string) => {
  const d = /<DATE>(\d{4})(\d{2})(\d{2})<\/DATE>/.exec(x);
  if (!d) return x;
  const serial = Math.round((Date.UTC(+d[1], +d[2] - 1, +d[3]) - Date.UTC(1899, 11, 31)) / 86400000);
  return x.replace(/<BILLCREDITPERIOD JD="0" P="/g, `<BILLCREDITPERIOD JD="${serial}" P="`);
};
const clean = (x: string) => fixCredit(fixInvoice(x))
  .replace(/ REMOTEID="[^"]*"/, '').replace(/<GUID>[^<]*<\/GUID>/, '').replace(/<MASTERID>[^<]*<\/MASTERID>/, '').replace(/<ALTERID>[^<]*<\/ALTERID>/, '')
  .replace(/<BATCHNAME>[^<]*<\/BATCHNAME>/g, '<BATCHNAME>Primary Batch</BATCHNAME>').replace(/<EXPIRYPERIOD[^>]*>[^<]*<\/EXPIRYPERIOD>/g, '');
const byFy = new Map<string, string[]>();
const counts: Record<string, number> = {};
for (const v of books.vouchers) {
  const fy = fyOf(v.date).label.replace('FY ', '');
  if (!byFy.has(fy)) byFy.set(fy, []);
  byFy.get(fy)!.push(clean(books.voucherXml(v)));
  counts[v.type] = (counts[v.type] ?? 0) + 1;
}
const files: string[] = [];
[...byFy.keys()].sort().forEach((fy, i) => {
  const name = `${i + 2}_Vouchers_FY${fy}${fy === '2025-26' ? '_Apr-Sep' : ''}.xml`;
  fs.writeFileSync(path.join(out, name), wrap('Vouchers', byFy.get(fy)!));
  files.push(`${name} (${byFy.get(fy)!.length} vouchers)`);
});

// ---------------------------------------------------------------- expected figures, worked out from the books (independent of Tally and Tally MIS)
const groupOf = new Map(books.groups.map((g) => [g.name, g]));
const top = (g: string) => { let cur = g; for (let k = 0; k < 10; k++) { const p = groupOf.get(cur)?.parent; if (!p) return cur; cur = p; } return cur; };
const ledgerGroup = new Map((books.ledgers as any[]).map((l) => [l.name, l.parent as string]));
const move = (from: string, to: string) => {
  const m = new Map<string, number>();
  for (const v of books.vouchers) {
    if (v.date < from || v.date > to) continue;
    for (const l of [...v.lines, ...v.inventory.map((i) => ({ ledger: i.ledger, amount: i.dir === 'out' ? -i.valuePaise : i.valuePaise }))]) m.set(l.ledger, (m.get(l.ledger) ?? 0) + l.amount);
  }
  return m;
};
const sumWhere = (m: Map<string, number>, pred: (ledger: string, grp: string) => boolean) => [...m].filter(([l]) => pred(l, top(ledgerGroup.get(l) ?? ''))).reduce((a, [, v]) => a + v, 0);
const stockTotal = (asOf: string) => [...books.stockAt(asOf).values()].reduce((a, s) => a + Math.round(s.val), 0);   // rounded per item, as Tally and Tally MIS do
const exp: any = { company: COMPANY, from: FROM, to: TO, years: {}, balances: {} };
for (let y = 2021; y <= 2025; y++) {
  const from = `${y}-04-01`, fyTo = `${y + 1}-03-31`, to = fyTo > TO ? TO : fyTo;
  const m = move(from, to);
  const sales = -sumWhere(m, (l, g) => g === 'Sales Accounts' && l !== 'Sales Returns');
  const returns = sumWhere(m, (l) => l === 'Sales Returns');
  const purchases = sumWhere(m, (_, g) => g === 'Purchase Accounts');
  const direct = sumWhere(m, (_, g) => g === 'Direct Expenses');
  const indirect = sumWhere(m, (_, g) => g === 'Indirect Expenses');
  const otherIncome = -sumWhere(m, (_, g) => g === 'Indirect Incomes');
  const openingStock = stockTotal(addDays(from, -1)), closingStock = stockTotal(to);
  const cogs = openingStock + purchases + direct - closingStock;
  const net = sales - returns - cogs - indirect + otherIncome;
  exp.years[`${y}-${String((y + 1) % 100).padStart(2, '0')}`] = {
    from, to, sales, returns, netRevenue: sales - returns, purchases, directExpenses: direct, openingStock, closingStock, cogs, grossProfit: sales - returns - cogs,
    indirectExpenses: indirect, depreciation: sumWhere(m, (l) => l === 'Depreciation'), interest: sumWhere(m, (l) => l.startsWith('Interest on ') && !l.endsWith('FD')),
    bankCharges: sumWhere(m, (l) => l === 'Bank Charges'), incomeTax: sumWhere(m, (l) => l === 'Income Tax Expense'), otherIncome, netProfit: net,
  };
}
const closing = books.closingAt(TO);
const bal = (pred: (l: string, g: string) => boolean) => [...closing].filter(([l]) => pred(l, top(ledgerGroup.get(l) ?? ''))).reduce((a, [, v]) => a + v, 0);
const sub = (name: string) => closing.get(name) ?? 0;
exp.balances = {
  asOf: TO, bank: sub('HDFC Bank Current A/c'), cash: sub('Cash'), cashCredit: -sub('SBI Cash Credit A/c'), termLoan: -sub('SBI Term Loan'),
  receivables: bal((l) => (ledgerGroup.get(l) === 'Sundry Debtors')), payables: -bal((l) => (ledgerGroup.get(l) === 'Sundry Creditors')),
  fixedAssets: bal((l) => ledgerGroup.get(l) === 'Fixed Assets'), stock: stockTotal(TO),
  outputGst: -bal((l) => l.startsWith('Output ')), inputGst: bal((l) => l.startsWith('Input ')),
};
exp.vouchers = { total: books.vouchers.length, byType: counts };
exp.minStockQty = minQty / 1e4;
fs.writeFileSync(path.join(out, 'expected_figures.json'), JSON.stringify(exp, null, 1));
console.log(JSON.stringify({ files, vouchers: exp.vouchers, minStockQty: exp.minStockQty, items: books.items.length, ledgers: books.ledgers.length }));
