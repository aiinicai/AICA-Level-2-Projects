/** Row builders shared by each tab's Excel button and the full-workbook export. */
import type { BlockedCredit, Datasets, Row, Supplier } from '../types';
import type { FollowUp, LedgerLine, Recon, SummaryRow, Table4 } from './engine';
import { cdnRecon, followUps, gstinRegister, itc, msmeLabel, nonFilers, PASS_LABEL, rcmRegister, STATUS_LABEL, summarise, timeBarred } from './engine';

const r2 = (n: number) => Math.round((n || 0) * 100) / 100;

export const rowCols = (r: Row) => ({
  GSTIN: r.gstin,
  'Supplier name': r.name,
  'Invoice no.': r.inv,
  'Invoice date': r.date,
  'Taxable value': r2(r.taxable),
  IGST: r2(r.igst),
  CGST: r2(r.cgst),
  'SGST/UTGST': r2(r.sgst),
  'Total ITC': r2(itc(r)),
  'Invoice value': r2(r.total),
});

export const registerRows = (rows: Row[]) =>
  rows.map((r) => ({
    ...rowCols(r),
    Sheet: r.sheet,
    'Row no.': r.rowNum,
    Amended: r.isAmendment ? 'Yes' : '',
    'RCM (auto)': r.rcm ? r.rcmReason || 'Yes' : '',
    'Possible 17(5)': r.blocked ? r.blockedReason || 'Yes' : '',
  }));

export const ledgerRows = (lines: LedgerLine[], remarks: Record<string, string>, blocked: Set<string>) =>
  lines.map((l) => {
    const ref = (l.g2b || l.bk)!;
    return {
      Status: STATUS_LABEL[l.status],
      'Smart pass': l.pass ? PASS_LABEL[l.pass] : '',
      GSTIN: ref.gstin,
      'Supplier name': ref.name,
      'Invoice no. (2B)': l.g2b?.inv ?? '',
      'Invoice no. (books)': l.bk?.inv ?? '',
      'Date (2B)': l.g2b?.date ?? '',
      'Date (books)': l.bk?.date ?? '',
      'Taxable (2B)': l.g2b ? r2(l.g2b.taxable) : '',
      'Taxable (books)': l.bk ? r2(l.bk.taxable) : '',
      'ITC (2B)': l.g2b ? r2(itc(l.g2b)) : '',
      'ITC (books)': l.bk ? r2(itc(l.bk)) : '',
      'Difference (books - 2B)': l.g2b && l.bk ? r2(l.diff) : '',
      RCM: ref.rcm ? 'Yes' : '',
      'Blocked 17(5)': blocked.has(l.key) ? 'Yes' : '',
      Note: remarks[l.key] ?? '',
    };
  });

export const excludedRows = (rows: Row[]) => rows.map((r) => ({ Register: r.source === 'g2b' ? 'GSTR-2B' : 'Books', Sheet: r.sheet, 'Row no.': r.rowNum, Reason: r.reason ?? '', ...rowCols(r) }));

export const summaryRows = (rows: SummaryRow[], by: 'gstin' | 'month') =>
  rows.map((s) => ({
    [by === 'gstin' ? 'GSTIN' : 'Month']: s.label,
    ...(by === 'gstin' ? { 'Supplier name': s.name } : {}),
    'Invoices in 2B': s.g2bInv,
    'Invoices in books': s.bksInv,
    Matched: s.matched,
    'Smart matched': s.smart,
    'ITC mismatch': s.mismatch,
    'Missing in books': s.missBooks,
    'Missing in 2B': s.miss2b,
    'ITC as per 2B': r2(s.itc2b),
    'ITC as per books': r2(s.itcBooks),
    'Difference (books - 2B)': r2(s.itcBooks - s.itc2b),
  }));

export const blockedRows = (b: BlockedCredit[]) =>
  b.map((x) => ({
    Status: x.active ? 'Blocked' : 'Released',
    Section: x.sec,
    Category: x.catLbl,
    GSTIN: x.gstin,
    'Supplier name': x.name,
    'Invoice no.': x.inv,
    'Invoice date': x.date,
    IGST: r2(x.igst),
    CGST: r2(x.cgst),
    'SGST/UTGST': r2(x.sgst),
    'Blocked ITC': r2(x.igst + x.cgst + x.sgst),
    'Detected by': x.origin === 'auto' ? 'Supplier name keywords' : 'Manual',
    Note: x.reason,
    'Blocked on': x.blockedOn,
  }));

export const followUpRows = (list: FollowUp[], sup: Record<string, Supplier>) =>
  list.flatMap((f) =>
    f.items.map((r) => ({
      ...rowCols(r),
      'Supplier e-mail': sup[f.gstin]?.email ?? '',
      MSME: msmeLabel(sup[f.gstin]),
      Issue: r.issue,
    }))
  );

export const table4Rows = (t: Table4) => {
  const line = (label: string, h: { igst: number; cgst: number; sgst: number }, action: string) => ({
    'GSTR-3B Table 4': label,
    IGST: r2(h.igst),
    CGST: r2(h.cgst),
    'SGST/UTGST': r2(h.sgst),
    Total: r2(h.igst + h.cgst + h.sgst),
    Action: action,
  });
  return [
    line('4(A)(5) All other ITC — matched invoices', t.eligible, 'Claim'),
    line('4(A)(3) Inward supplies liable to reverse charge', t.rcm, 'Claim after paying RCM tax in 3.1(d)'),
    line('4(B)(1) Reversal — Section 17(5) blocked credit', t.blocked, 'Reverse'),
    line('4(C) Net ITC available', t.net, ''),
    line('Under review — ITC mismatch and smart matches', t.review, 'Check before claiming'),
    line('In GSTR-2B, not in books', t.missBooks, 'Book the purchase or confirm it is not yours'),
    line('In books, not in GSTR-2B', t.miss2b, 'Do not claim; follow up with supplier'),
    line('Credit / debit notes in GSTR-2B (net)', t.cdn, 'Net off against ITC after review'),
  ];
};

/** Every view in one workbook. */
export function fullWorkbook(ds: Datasets, rc: Recon, blocked: BlockedCredit[], remarks: Record<string, string>, sup: Record<string, Supplier>, tol: number) {
  const c = rc.counts;
  return [
    { name: 'GSTR-3B Table 4', rows: table4Rows(rc.t4) },
    {
      name: 'Summary',
      rows: [
        { Item: 'Invoices in GSTR-2B', Value: ds.g2b.length },
        { Item: 'Invoices in books', Value: ds.bks.length },
        { Item: 'Matched (exact)', Value: c.exact },
        { Item: `Matched (within ₹${tol})`, Value: c.tol },
        { Item: 'Smart matched', Value: c.smart },
        { Item: 'ITC mismatch', Value: c.mismatch },
        { Item: 'Missing in books', Value: c.missBooks },
        { Item: 'Missing in GSTR-2B', Value: c.miss2b },
      ],
    },
    { name: 'Reconciliation ledger', rows: ledgerRows(rc.lines, remarks, rc.activeBlocked) },
    { name: 'Smart matches', rows: ledgerRows(rc.lines.filter((l) => l.status === 'smart'), remarks, rc.activeBlocked) },
    { name: 'Unresolved', rows: ledgerRows(rc.lines.filter((l) => l.status === 'missBooks' || l.status === 'miss2b'), remarks, rc.activeBlocked) },
    { name: 'By GSTIN', rows: summaryRows(summarise(rc.lines, 'gstin'), 'gstin') },
    { name: 'By month', rows: summaryRows(summarise(rc.lines, 'month'), 'month') },
    { name: 'Non-filers', rows: nonFilers(ds.g2b, ds.bks).map((n) => ({ GSTIN: n.gstin, 'Supplier name': n.name, Invoices: n.invCount, 'ITC at risk': r2(n.itc) })) },
    { name: 'Follow-ups', rows: followUpRows(followUps(rc.lines, 'all'), sup) },
    { name: 'Blocked 17(5)', rows: blockedRows(blocked) },
    { name: 'RCM bills', rows: rcmRegister(ds).map((r) => ({ Source: r.origin, ...rowCols(r), Reason: r.rcmReason ?? '' })) },
    {
      name: 'CDN reconciliation',
      rows: cdnRecon(ds, tol).map((x) => {
        const ref = (x.g2b || x.bk)!;
        return {
          Status: { ok: 'Matched', am: 'Tax mismatch', mb: 'Missing in books', m2: 'Missing in 2B' }[x.s],
          GSTIN: ref.gstin,
          'Supplier name': ref.name,
          'Note no.': ref.inv,
          Date: ref.date,
          'ITC (2B)': x.g2b ? r2(itc(x.g2b)) : '',
          'ITC (books)': x.bk ? r2(itc(x.bk)) : '',
          Difference: r2(x.diff),
        };
      }),
    },
    { name: 'Sec 16(4) time-barred', rows: timeBarred(ds.g2b).map((r) => ({ ...rowCols(r), 'Financial year': r.fy, 'Last date': r.deadline, 'Days past': r.daysOver })) },
    {
      name: 'GSTIN check',
      rows: gstinRegister(ds.g2b, ds.bks).map((g) => ({
        GSTIN: g.gstin,
        'Supplier name': g.name,
        Found: g.src.join(', '),
        State: g.state,
        'GSTIN valid': g.valid ? 'Yes' : 'No',
        Problem: g.error,
        MSME: msmeLabel(sup[g.gstin]),
        'Udyam no.': sup[g.gstin]?.udyamNumber ?? '',
      })),
    },
    { name: 'Excluded rows', rows: excludedRows([...ds.g2b_excl, ...ds.bks_excl]) },
    { name: 'GSTR-2B', rows: registerRows(ds.g2b) },
    { name: 'Purchase register', rows: registerRows(ds.bks) },
  ];
}
