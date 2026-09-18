import React from 'react';
import * as XLSX from 'xlsx';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Upload, FileSpreadsheet, ArrowRight } from 'lucide-react';
import type { ClientRecord } from '../lib/store';
import type { YearActual } from '../types/cma';

interface Props {
  client: ClientRecord;
  onApply: (yearIdx: number, values: Partial<YearActual>) => void;
}

interface ImportRow {
  head: string;
  values: (number | null)[];   // one per detected data column
  mappedKey: keyof YearActual | '';
}

const TARGET_HEADS: { key: keyof YearActual; label: string }[] = [
  { key: 'salesDomestic', label: 'Sales — Domestic' },
  { key: 'salesExport', label: 'Sales — Export' },
  { key: 'otherIncome', label: 'Other Income' },
  { key: 'rmOpening', label: 'Opening Stock' },
  { key: 'rmPurchases', label: 'Purchases / Raw Material' },
  { key: 'rmClosing', label: 'Closing Stock' },
  { key: 'powerFuel', label: 'Power & Fuel' },
  { key: 'directLabour', label: 'Direct Labour & Wages' },
  { key: 'salary', label: 'Salary & Employee Benefits' },
  { key: 'freight', label: 'Freight & Cartage' },
  { key: 'salesPromo', label: 'Sales Promotion & Distribution' },
  { key: 'travelAdmin', label: 'Travelling & Conveyance' },
  { key: 'repairs', label: 'Repairs & Maintenance' },
  { key: 'professionalFees', label: 'Professional Fees' },
  { key: 'operatingExp', label: 'Operating Expenses (General)' },
  { key: 'otherExp', label: 'Other Expenses' },
  { key: 'depreciation', label: 'Depreciation' },
  { key: 'interestCC', label: 'Interest — Cash Credit' },
  { key: 'interestTL', label: 'Interest — Term Loan' },
  { key: 'bankCharges', label: 'Bank Charges' },
  { key: 'tax', label: 'Provision for Tax' },
  { key: 'dividend', label: 'Dividend Paid' },
  { key: 'fixedAssets', label: 'Fixed Assets (Net Block)' },
  { key: 'deposits', label: 'Deposits & Advances' },
  { key: 'investments', label: 'Investments' },
  { key: 'debtors', label: 'Debtors / Receivables' },
  { key: 'cash', label: 'Cash & Bank' },
  { key: 'otherCurrentAssets', label: 'Other Current Assets' },
  { key: 'shareCapital', label: 'Share Capital' },
  { key: 'reserves', label: 'Reserves & Surplus' },
  { key: 'termLoan', label: 'Term Loan (closing)' },
  { key: 'cc', label: 'Cash Credit / Bank WC' },
  { key: 'unsecured', label: 'Unsecured Loans' },
  { key: 'creditors', label: 'Creditors / Payables' },
  { key: 'otherCurrentLiab', label: 'Other Current Liabilities' },
];

// keyword rules — first match wins (order matters)
const RULES: [RegExp, keyof YearActual][] = [
  [/opening.*stock|stock.*opening|op\.*\s*stock/i, 'rmOpening'],
  [/closing.*stock|stock.*closing|cl\.*\s*stock|inventor/i, 'rmClosing'],
  [/purchase|raw material|material consumed/i, 'rmPurchases'],
  [/power|fuel|electric/i, 'powerFuel'],
  [/wages|labour|labor/i, 'directLabour'],
  [/export/i, 'salesExport'],
  [/sales|turnover|revenue from/i, 'salesDomestic'],
  [/other income|misc.*income|interest income/i, 'otherIncome'],
  [/salar|employee benefit|staff/i, 'salary'],
  [/freight|cartage|transport/i, 'freight'],
  [/advertis|promotion|selling|distribution|marketing/i, 'salesPromo'],
  [/travell?ing|conveyance/i, 'travelAdmin'],
  [/repair|maintenance/i, 'repairs'],
  [/professional|legal|audit fee|consult/i, 'professionalFees'],
  [/depreciation|depn|dep\b/i, 'depreciation'],
  [/interest.*(cc|cash credit|working cap|bank)|interest on wc/i, 'interestCC'],
  [/interest.*(term|tl)|term.*interest/i, 'interestTL'],
  [/bank charge|processing fee/i, 'bankCharges'],
  [/interest/i, 'interestCC'],
  [/tax/i, 'tax'],
  [/dividend/i, 'dividend'],
  [/fixed asset|net block|plant|property.*equipment|machinery|building|furniture/i, 'fixedAssets'],
  [/deposit|advance/i, 'deposits'],
  [/investment/i, 'investments'],
  [/debtor|receivable/i, 'debtors'],
  [/cash|bank bal/i, 'cash'],
  [/other current asset|loans? &? advances|other asset/i, 'otherCurrentAssets'],
  [/share capital|capital/i, 'shareCapital'],
  [/reserve|surplus|p\s*&\s*l a\/?c|profit.*loss.*(bal|account)/i, 'reserves'],
  [/term loan|secured loan|long.term|vehicle loan/i, 'termLoan'],
  [/cash credit|working capital (loan|limit|borrow)|bank (borrow|od)|cc a\/?c/i, 'cc'],
  [/unsecured/i, 'unsecured'],
  [/creditor|payable/i, 'creditors'],
  [/other current liab|provision|statutory|duties.*taxes|expenses payable/i, 'otherCurrentLiab'],
  [/operat|office|admin|general|misc|other exp/i, 'operatingExp'],
];

function autoMap(head: string): keyof YearActual | '' {
  for (const [re, key] of RULES) if (re.test(head)) return key;
  return '';
}

function parseNum(v: unknown): number | null {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v === 'number') return v;
  const s = String(v).replace(/,/g, '').trim();
  if (!s) return null;
  const neg = /^\(.*\)$/.test(s);
  const n = parseFloat(s.replace(/[()]/g, ''));
  if (Number.isNaN(n)) return null;
  return neg ? -n : n;
}

export const ImportDialog: React.FC<Props> = ({ client, onApply }) => {
  const [open, setOpen] = React.useState(false);
  const [fileName, setFileName] = React.useState('');
  const [sheetNames, setSheetNames] = React.useState<string[]>([]);
  const [wb, setWb] = React.useState<XLSX.WorkBook | null>(null);
  const [sheet, setSheet] = React.useState('');
  const [rows, setRows] = React.useState<ImportRow[]>([]);
  const [colLabels, setColLabels] = React.useState<string[]>([]);
  const [fileUnit, setFileUnit] = React.useState<'1' | '1000' | '100000'>('1');
  const [colYearMap, setColYearMap] = React.useState<Record<number, number>>({}); // import col → actual year idx

  const loadFile = async (f: File) => {
    const buf = await f.arrayBuffer();
    const book = XLSX.read(buf, { type: 'array' });
    setWb(book);
    setFileName(f.name);
    setSheetNames(book.SheetNames);
    setSheet(book.SheetNames[0]);
    parseSheet(book, book.SheetNames[0]);
  };

  const parseSheet = (book: XLSX.WorkBook, name: string) => {
    const ws = book.Sheets[name];
    const grid: unknown[][] = XLSX.utils.sheet_to_json(ws, { header: 1, raw: true });
    // find header row with ≥2 date/year-like cells to identify data columns
    let dataCols: number[] = [];
    let labels: string[] = [];
    for (const row of grid.slice(0, 30)) {
      const cols: number[] = [];
      const labs: string[] = [];
      (row || []).forEach((cell, ci) => {
        if (ci === 0) return;
        const s = String(cell ?? '');
        const isYear = /(19|20)\d{2}/.test(s) || cell instanceof Date || /\d{2}[-/.]\d{4}/.test(s);
        if (isYear) { cols.push(ci); labs.push(s.slice(0, 20)); }
      });
      if (cols.length >= 2) { dataCols = cols; labels = labs; break; }
    }
    // fallback: columns B,C,D with mostly numeric content
    if (dataCols.length === 0) {
      dataCols = [1, 2, 3];
      labels = ['Col B', 'Col C', 'Col D'];
    }
    setColLabels(labels);

    const out: ImportRow[] = [];
    for (const row of grid) {
      const head = String(row?.[0] ?? row?.[1] ?? '').trim();
      if (!head || head.length < 3) continue;
      if (dataCols.includes(0)) continue;
      const values = dataCols.map(ci => parseNum((row as unknown[])[ci]));
      if (values.every(v => v === null)) continue; // skip pure headings
      // skip total/subtotal-only section rows but keep them skippable via mapping ''
      out.push({ head, values, mappedKey: autoMap(head) });
    }
    setRows(out);
    // default: import col k → actual year (actualYears - n + k), oldest first
    const n = labels.length;
    const map: Record<number, number> = {};
    dataCols.forEach((_, k) => {
      const target = client.config.actualYears - n + k;
      if (target >= 0) map[k] = target;
    });
    setColYearMap(map);
  };

  const apply = () => {
    const mult = Number(fileUnit);
    const groups: Record<number, Partial<YearActual>> = {};
    rows.forEach(r => {
      if (!r.mappedKey) return;
      r.values.forEach((v, k) => {
        const yearIdx = colYearMap[k];
        if (v === null || yearIdx === undefined) return;
        groups[yearIdx] = groups[yearIdx] || {};
        const cur = (groups[yearIdx] as any)[r.mappedKey];
        (groups[yearIdx] as any)[r.mappedKey] = (cur || 0) + v * mult;
      });
    });
    Object.entries(groups).forEach(([yi, vals]) => onApply(Number(yi), vals));
    setOpen(false);
  };

  const mappedCount = rows.filter(r => r.mappedKey).length;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline"><Upload className="mr-2 h-4 w-4" /> Import from Excel</Button>
      </DialogTrigger>
      <DialogContent className="max-w-5xl max-h-[85vh] overflow-y-auto">
        <DialogHeader><DialogTitle>Import Financials from Excel (Bank / Tally format)</DialogTitle></DialogHeader>

        <div className="flex items-center gap-3 flex-wrap">
          <label className="cursor-pointer">
            <input type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={e => e.target.files?.[0] && loadFile(e.target.files[0])} />
            <span className="inline-flex items-center gap-2 border rounded px-3 py-2 text-sm hover:bg-accent">
              <FileSpreadsheet className="h-4 w-4" /> {fileName || 'Choose Excel file…'}
            </span>
          </label>
          {sheetNames.length > 1 && (
            <Select value={sheet} onValueChange={v => { setSheet(v); wb && parseSheet(wb, v); }}>
              <SelectTrigger className="w-48"><SelectValue placeholder="Sheet" /></SelectTrigger>
              <SelectContent>{sheetNames.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          )}
          <Select value={fileUnit} onValueChange={v => setFileUnit(v as any)}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="1">File amounts in ₹ (Rupees)</SelectItem>
              <SelectItem value="1000">File amounts in ₹ '000</SelectItem>
              <SelectItem value="100000">File amounts in ₹ Lakhs</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {rows.length > 0 && (
          <>
            <div className="flex items-center gap-4 mt-2">
              <span className="text-sm text-muted-foreground">{rows.length} rows read · {mappedCount} auto-mapped</span>
              {colLabels.map((l, k) => (
                <div key={k} className="flex items-center gap-1 text-sm">
                  <span className="text-muted-foreground">{l}</span>
                  <ArrowRight className="h-3 w-3" />
                  <Select value={colYearMap[k] !== undefined ? String(colYearMap[k]) : 'skip'} onValueChange={v => setColYearMap(m => ({ ...m, [k]: v === 'skip' ? undefined as any : +v }))}>
                    <SelectTrigger className="w-28 h-7"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="skip">Skip</SelectItem>
                      {client.config.actuals.map((a, i) => <SelectItem key={i} value={String(i)}>{a.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </div>

            <Table className="mt-2">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[38%]">Head in file</TableHead>
                  {colLabels.map((l, k) => <TableHead key={k} className="text-right">{l}</TableHead>)}
                  <TableHead className="w-[30%]">Map to CMA head</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r, i) => (
                  <TableRow key={i} className={r.mappedKey ? '' : 'opacity-60'}>
                    <TableCell className="text-sm">{r.head}</TableCell>
                    {r.values.map((v, k) => (
                      <TableCell key={k} className="text-right text-sm font-mono">
                        {v === null ? '' : v.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                      </TableCell>
                    ))}
                    <TableCell>
                      <Select value={r.mappedKey || 'skip'} onValueChange={v => setRows(rs => rs.map((x, j) => j === i ? { ...x, mappedKey: v === 'skip' ? '' : v as keyof YearActual } : x))}>
                        <SelectTrigger className="h-7"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="skip">— Skip —</SelectItem>
                          {TARGET_HEADS.map(h => <SelectItem key={h.key} value={h.key}>{h.label}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="flex justify-end gap-2 mt-3">
              <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button onClick={apply} disabled={mappedCount === 0}>
                Apply to {new Set(Object.values(colYearMap)).size} year(s) · {mappedCount} heads
              </Button>
            </div>
          </>
        )}
        {rows.length === 0 && <p className="text-sm text-muted-foreground py-6 text-center">Choose an Excel file where row heads are in column A and each year is a column.</p>}
      </DialogContent>
    </Dialog>
  );
};
