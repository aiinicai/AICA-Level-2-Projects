import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';
import { ReconciliationItem, ReconStatus, NoticeIssue, NoticeCase, ParsedFigure } from '../types';
import { sumFigures } from './gstReturnParser';

function explain(reconType: string, variance: number, portalKnown: boolean): { status: ReconStatus; reason: string } {
  if (!portalKnown) {
    return {
      status: 'MISSING_DATA',
      reason: 'Awaiting the portal figure — upload the relevant return/ledger or enter the amount to reconcile.',
    };
  }
  const v = 'Rs ' + Math.abs(variance).toLocaleString('en-IN');
  if (Math.abs(variance) <= 1) {
    return { status: 'MATCH', reason: 'Notice figure agrees with the portal/return figure. No variance.' };
  }
  if (/ITC|2B|2A/i.test(reconType)) {
    return { status: 'MISMATCH', reason: `ITC variance of ${v}: GSTR-3B Table 4(A)(5) vs GSTR-2B available ITC. Check timing / supplier filing / Rule 36(4) and Circular 183.` };
  }
  if (/Turnover|GSTR-1/i.test(reconType)) {
    return { status: 'MISMATCH', reason: `Turnover variance of ${v} between GSTR-1 and GSTR-3B. Check credit/debit notes, amendments, and exempt/schedule-III supplies.` };
  }
  if (/Annual|GSTR-9/i.test(reconType)) {
    return { status: 'MISMATCH', reason: `Variance of ${v} between GSTR-9 annual figure and the sum of monthly GSTR-3B. Check DRC-03 payments and returns filed after year-end.` };
  }
  if (/Ledger|Cash|Credit/i.test(reconType)) {
    return { status: 'MISMATCH', reason: `Variance of ${v} between the demand and tax discharged through the cash + credit ledgers.` };
  }
  return { status: 'MISMATCH', reason: `Variance of ${v} between the notice figure and the books of accounts.` };
}

export function calculateReconciliation(
  reconType: string,
  period: string,
  noticeValue: number,
  portalValue: number,
  booksValue: number
): ReconciliationItem {
  const variance = noticeValue - portalValue;
  const { status, reason } = explain(reconType, variance, portalValue > 0);
  return {
    id: 'recon_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
    caseId: '',
    reconType,
    period,
    noticeValue,
    portalValue,
    booksValue,
    variance: Math.abs(variance),
    varianceReason: reason,
    status,
  };
}

/** Recompute variance/status/reason after the CA edits a figure — keeps id, caseId, hints. */
export function recomputeItem(item: ReconciliationItem): ReconciliationItem {
  const variance = item.noticeValue - item.portalValue;
  const { status, reason } = explain(item.reconType, variance, item.portalValue > 0);
  return { ...item, variance: Math.round(Math.abs(variance) * 100) / 100, status, varianceReason: reason };
}

// ── Standard schedule framework, auto-built per notice ───────────────────────
interface ScheduleTemplate {
  key: string;
  reconType: string;
  portalHint: string;
  booksHint: string;
  matches: RegExp | null; // null = always create
  demandFrom: 'principal' | 'issue';
}

const SCHEDULE_TEMPLATES: ScheduleTemplate[] = [
  {
    key: 'itc-2b-3b',
    reconType: 'GSTR-2B vs GSTR-3B — ITC (Table 4A5)',
    portalHint: 'ITC available as per GSTR-2B (Table 3 / Part A)',
    booksHint: 'ITC as per books / GSTR-3B Table 4(A)(5)',
    matches: /itc|input tax credit|2b|2a|16\s*\(2\)|36\s*\(4\)|blocked credit|17\s*\(5\)/i,
    demandFrom: 'issue',
  },
  {
    key: 'turnover-1-3b',
    reconType: 'GSTR-1 vs GSTR-3B — Outward turnover & tax',
    portalHint: 'Outward tax as per GSTR-1 (Tables 4–11)',
    booksHint: 'Outward tax as per GSTR-3B Table 3.1(a) / books',
    matches: /turnover|outward|gstr-?1|3\.1\s*\(a\)|suppress|under[\s-]?report|sales/i,
    demandFrom: 'issue',
  },
  {
    key: 'rcm-books-3b',
    reconType: 'RCM — Books vs GSTR-3B Table 3.1(d)',
    portalHint: 'RCM tax paid as per GSTR-3B Table 3.1(d)',
    booksHint: 'RCM liability as per books (freight, legal, imports, URD)',
    matches: /rcm|reverse charge|9\s*\(3\)|9\s*\(4\)|3\.1\s*\(d\)|gta|import of service/i,
    demandFrom: 'issue',
  },
  {
    key: 'annual-9-3b',
    reconType: 'GSTR-9 Annual vs Σ GSTR-3B',
    portalHint: 'Annual figure as per GSTR-9 (Table 4 / 6 / 9)',
    booksHint: 'Sum of the 12 monthly GSTR-3B returns',
    matches: /annual|gstr-?9|9c|year|2017-18|2018-19|2019-20|2020-21|2021-22|2022-23/i,
    demandFrom: 'principal',
  },
  {
    key: 'demand-ledger',
    reconType: 'Notice demand vs Tax paid (Cash + Credit ledger)',
    portalHint: 'Tax discharged: electronic cash + credit ledger utilisation',
    booksHint: 'Tax paid as per books',
    matches: null,
    demandFrom: 'principal',
  },
  {
    key: 'demand-books',
    reconType: 'Notice demand vs Books of accounts',
    portalHint: 'Liability as recomputed from returns',
    booksHint: 'Liability / turnover / ITC as per audited books',
    matches: null,
    demandFrom: 'principal',
  },
];

export function buildRequiredSchedules(issues: NoticeIssue[], noticeCase: Pick<NoticeCase, 'principalTax' | 'period' | 'financialYear'>): ReconciliationItem[] {
  const blob = issues.map((i) => `${i.title} ${i.allegation} ${i.sectionRule} ${i.figureSource} ${i.factsCategory}`).join(' ');
  const period = noticeCase.period || (noticeCase.financialYear ? `FY ${noticeCase.financialYear}` : '');

  const out: ReconciliationItem[] = [];
  SCHEDULE_TEMPLATES.forEach((tpl) => {
    const matchedIssues = tpl.matches ? issues.filter((i) => tpl.matches!.test(`${i.title} ${i.allegation} ${i.sectionRule} ${i.figureSource} ${i.factsCategory}`)) : [];
    if (tpl.matches && matchedIssues.length === 0 && !tpl.matches.test(blob)) return;

    const demandRaw = tpl.demandFrom === 'principal'
      ? noticeCase.principalTax || 0
      : matchedIssues.reduce((s, i) => s + (Number(i.taxAmount) || 0), 0) || noticeCase.principalTax || 0;
    const demand = Math.round(demandRaw * 100) / 100;

    out.push({
      id: `recon_${tpl.key}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 5)}`,
      caseId: '',
      reconType: tpl.reconType,
      period,
      noticeValue: demand,
      portalValue: 0,
      booksValue: 0,
      variance: demand,
      varianceReason: 'Awaiting the portal figure — upload the relevant return/ledger or enter the amount.',
      status: 'MISSING_DATA',
      issueNumber: matchedIssues[0]?.issueNumber,
      portalHint: tpl.portalHint,
      booksHint: tpl.booksHint,
    });
  });

  return out;
}

// ── Push parsed portal figures into the matching schedule's portal column ────
const FIGURE_TO_SCHEDULE: { schedule: RegExp; figure: RegExp }[] = [
  { schedule: /ITC \(Table 4A5\)/i, figure: /2B — ITC available|comparison — ITC as per|credit ledger/i },
  { schedule: /Outward turnover/i, figure: /GSTR-1 — Total outward|comparison — tax liability declared/i },
  { schedule: /RCM/i, figure: /3\.1\(d\)/i },
  { schedule: /GSTR-9 Annual/i, figure: /GSTR-9 Table (4|9)/i },
  { schedule: /Tax paid \(Cash \+ Credit/i, figure: /(cash|credit) ledger — closing balance|6\.1 — tax paid/i },
];

/** Best-effort auto-fill of portal columns from detected figures. Returns updated items. */
export function applyFiguresToSchedules(items: ReconciliationItem[], figures: ParsedFigure[]): ReconciliationItem[] {
  return items.map((item) => {
    const rule = FIGURE_TO_SCHEDULE.find((r) => r.schedule.test(item.reconType));
    if (!rule) return item;
    const hits = figures.filter((f) => rule.figure.test(f.label));
    if (hits.length === 0) return item;
    // group by label, collapse each group to one amount, then add the groups
    const byLabel = new Map<string, ParsedFigure[]>();
    hits.forEach((f) => byLabel.set(f.label, [...(byLabel.get(f.label) || []), f]));
    const total = [...byLabel.values()].reduce((s, group) => s + sumFigures(group), 0);
    if (total <= 0) return item;
    return recomputeItem({ ...item, portalValue: total });
  });
}

export async function parseExcelReconciliationFile(file: File): Promise<{
  gstr3bItc: number;
  gstr2bItc: number;
  booksItc: number;
  turnoverGstr1: number;
  turnoverGstr3b: number;
  rowCount: number;
}> {
  const data = await file.arrayBuffer();
  const workbook = XLSX.read(data, { type: 'array' });
  const firstSheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[firstSheetName];
  const rows = XLSX.utils.sheet_to_json<any>(worksheet, { header: 1 });

  let gstr3bItc = 0;
  let gstr2bItc = 0;
  let booksItc = 0;
  let turnoverGstr1 = 0;
  let turnoverGstr3b = 0;

  rows.forEach((row: any[]) => {
    if (!Array.isArray(row)) return;
    const rowStr = row.map((cell) => String(cell || '').toLowerCase()).join(' ');

    row.forEach((cell) => {
      const numVal = parseFloat(String(cell).replace(/[^0-9.-]+/g, ''));
      if (!isNaN(numVal) && numVal > 100) {
        if (rowStr.includes('3b') && rowStr.includes('itc') && gstr3bItc === 0) gstr3bItc = numVal;
        else if (rowStr.includes('2b') && gstr2bItc === 0) gstr2bItc = numVal;
        else if (rowStr.includes('book') && booksItc === 0) booksItc = numVal;
        else if (rowStr.includes('gstr-1') || rowStr.includes('gstr1')) turnoverGstr1 = numVal;
        else if (rowStr.includes('sales') || rowStr.includes('outward')) turnoverGstr3b = numVal;
      }
    });
  });

  return {
    gstr3bItc,
    gstr2bItc,
    booksItc,
    turnoverGstr1,
    turnoverGstr3b,
    rowCount: rows.length,
  };
}

export function exportReconciliationsToExcel(
  clientName: string,
  gstin: string,
  noticeNumber: string,
  period: string,
  reconciliations: ReconciliationItem[],
  figures: ParsedFigure[] = [],
  actionPoints: { document: string; category: string; status: string; forIssue: string }[] = [],
): void {
  const wb = XLSX.utils.book_new();

  const headerData = [
    ['GST NOTICE RECONCILIATION WORKPAPER', '', '', '', '', ''],
    ['Taxpayer Legal Name:', clientName, '', 'GSTIN:', gstin, ''],
    ['Notice Reference No:', noticeNumber, '', 'Period / FY:', period, ''],
    ['Generated On:', new Date().toLocaleDateString('en-IN'), '', 'Prepared By:', 'Chartered Accountant', ''],
    [],
    [
      'Sr No',
      'Reconciliation Category',
      'Period',
      'Notice / Claim Figure (Rs)',
      'Portal Report Figure (Rs)',
      'Books Ledger Figure (Rs)',
      'Variance / Difference (Rs)',
      'Recon Status',
      'CA Audit Remarks & Findings',
    ],
  ];

  const dataRows = reconciliations.map((r, idx) => [
    idx + 1,
    r.reconType,
    r.period,
    r.noticeValue,
    r.portalValue,
    r.booksValue,
    r.variance,
    r.status,
    r.varianceReason,
  ]);

  const wsData = [...headerData, ...dataRows];
  const ws = XLSX.utils.aoa_to_sheet(wsData);

  ws['!cols'] = [
    { wch: 6 },
    { wch: 36 },
    { wch: 14 },
    { wch: 22 },
    { wch: 22 },
    { wch: 22 },
    { wch: 22 },
    { wch: 14 },
    { wch: 60 },
  ];

  XLSX.utils.book_append_sheet(wb, ws, 'Reconciliation Schedules');

  // ── Sheet 2: Source figures uploaded from the portal ──
  if (figures.length) {
    const figHeader = [
      ['SOURCE FIGURES — UPLOADED PORTAL RETURNS & LEDGERS'],
      ['Client:', clientName, 'GSTIN:', gstin],
      [],
      ['Source File', 'Document', 'Figure', 'Head', 'Amount (Rs)'],
    ];
    const figRows = figures.map((f) => [f.sourceFile, f.docType, f.label, f.head || '', f.value]);
    const fws = XLSX.utils.aoa_to_sheet([...figHeader, ...figRows]);
    fws['!cols'] = [{ wch: 30 }, { wch: 14 }, { wch: 44 }, { wch: 8 }, { wch: 18 }];
    XLSX.utils.book_append_sheet(wb, fws, 'Source Figures');
  }

  // ── Sheet 3: Action points — documents to collect from the client ──
  if (actionPoints.length) {
    const apHeader = [
      ['ACTION POINTS — DOCUMENTS / DATA TO OBTAIN FROM CLIENT'],
      ['Notice:', noticeNumber, 'Reply due:', period],
      [],
      ['Sr', 'Document / Information Required', 'Category', 'Status', 'Relates to'],
    ];
    const apRows = actionPoints.map((a, i) => [i + 1, a.document, a.category, a.status, a.forIssue]);
    const aws = XLSX.utils.aoa_to_sheet([...apHeader, ...apRows]);
    aws['!cols'] = [{ wch: 5 }, { wch: 48 }, { wch: 18 }, { wch: 16 }, { wch: 40 }];
    XLSX.utils.book_append_sheet(wb, aws, 'Action Points');
  }

  const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
  const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const filename = 'GST_Reconciliation_' + gstin + '_' + period.replace(/\s+/g, '_') + '.xlsx';
  saveAs(blob, filename);
}
