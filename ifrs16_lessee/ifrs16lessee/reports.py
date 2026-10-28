"""Formatted Excel export (openpyxl). All values come from the stored/recomputed Decimal results; amounts are written as numbers
with a 2-decimal format (conversion to float happens only at the file boundary)."""
from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .journals import default_map
from .money import ZERO

BLUE, LIGHT, WHITE = '1F4E9C', 'EAF1FB', 'FFFFFF'
HDR = PatternFill('solid', fgColor=BLUE)
ALT = PatternFill('solid', fgColor=LIGHT)
THIN = Side(style='thin', color='C9D6EA')
NUM = '#,##0.00;[Red](#,##0.00);-'


def _sheet(wb, title, heading, headers, rows, widths=None, num_cols=(), note=None):
    ws = wb.create_sheet(title[:31])
    ws.sheet_view.showGridLines = False
    ws['A1'] = heading
    ws['A1'].font = Font(size=14, bold=True, color=BLUE)
    r0 = 3
    if note:
        ws['A2'] = note
        ws['A2'].font = Font(italic=True, color='5A6B85')
    for c, h in enumerate(headers, 1):
        cell = ws.cell(r0, c, h)
        cell.fill, cell.font = HDR, Font(bold=True, color=WHITE)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for i, row in enumerate(rows, 1):
        for c, v in enumerate(row, 1):
            if isinstance(v, Decimal):
                v = float(v)
            cell = ws.cell(r0 + i, c, v)
            cell.border = Border(bottom=THIN)
            if c in num_cols:
                cell.number_format = NUM
                cell.alignment = Alignment(horizontal='right')
            elif isinstance(v, str) and len(v) > 60:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
            if i % 2 == 0:
                cell.fill = ALT
    for c, h in enumerate(headers, 1):
        w = (widths or {}).get(c) or max(12, min(48, max([len(str(h))] + [len(str(r[c - 1])) for r in rows[:200] if len(r) >= c]) + 2))
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    ws.row_dimensions[r0].height = 30
    return ws


def rollforward(timeline):
    """Per calendar year, from journals: liability and ROU roll-forwards that reconcile to the schedule."""
    liab, cost, acc = defaultdict(lambda: defaultdict(Decimal)), defaultdict(lambda: defaultdict(Decimal)), defaultdict(lambda: defaultdict(Decimal))
    years = set()
    for j in timeline.journals:
        y = j.date.year
        years.add(y)
        for l in j.lines:
            net = l.debit - l.credit
            if l.account == 'LEASE_LIAB':
                liab[y][j.source] += -net
            elif l.account == 'ROU_COST':
                cost[y][j.source] += net
            elif l.account == 'ROU_ACCDEP':
                acc[y][j.source] += -net
    L, R = [], []
    ol = oc = oa = ZERO
    for y in sorted(years):
        a = liab[y]
        add, intr, pay = a.get('INITIAL', ZERO), a.get('INTEREST', ZERO), -a.get('PAYMENT', ZERO)
        rem = a.get('REASSESS', ZERO) + a.get('MODIFICATION', ZERO)
        ter = a.get('TERMINATION', ZERO)
        cl = ol + add + intr - pay + rem + ter
        L.append([y, ol, add, intr, -pay, rem, ter, cl])
        ol = cl
        c = cost[y]
        cadd, crem, cter = c.get('INITIAL', ZERO), c.get('REASSESS', ZERO) + c.get('MODIFICATION', ZERO), c.get('TERMINATION', ZERO)
        dep = acc[y].get('DEPRECIATION', ZERO)
        dis = acc[y].get('TERMINATION', ZERO)
        cc, ca = oc + cadd + crem + cter, oa + dep + dis
        R.append([y, oc - oa, cadd, crem, cter + dis, -dep, cc - ca])
        oc, oa = cc, ca
    return L, R


def export_workbook(store, refs, path, company=''):
    wb = Workbook()
    wb.remove(wb.active)
    summary, sched, lrf, rrf, bridges, terms_rows, jr, tr_rows = [], [], [], [], [], [], [], []
    amap = store.get_setting('account_map')
    for ref in refs:
        t = store.get_terms(ref)
        tl = store.timeline(ref)
        summary.append([ref, t.lessor, t.asset, t.currency, t.functional_currency, t.commencement, t.end_date, tl.initial['liability'], tl.initial['rou_cost'],
                        tl.final['liability'], tl.final['rou_carrying'], len(tl.events), 'Exempt' if tl.exempt else ('Terminated' if tl.final['terminated'] else 'Active')])
        for r in tl.rows:
            sched.append([ref, r.version, r.row_no, r.start, r.end, r.days, r.open_liab, r.interest, r.payment, r.principal, r.close_liab, r.rounding_adj,
                          r.open_rou, r.depreciation, r.close_rou, r.adjustment, r.rou_adjustment, '; '.join(r.trace.values())])
        if not tl.exempt:
            Lr, Rr = rollforward(tl)
            lrf += [[ref] + x for x in Lr]
            rrf += [[ref] + x for x in Rr]
        for e in tl.events:
            tag = 'Termination' if e.type == 'termination' or e.decision in ('partial_termination', 'full_termination', 'modification_scope_decrease') else None
            b = [[ref, e.index, e.type, e.effective_date, e.decision, (str(e.rate_used * 100) + '%') if e.rate_used is not None else '', x['label'], x['amount'], x['trace']] for x in e.bridge]
            bridges += b
            if tag:
                terms_rows += b
            for n in e.notes:
                bridges.append([ref, e.index, e.type, e.effective_date, e.decision, '', 'Note', None, n])
        for j in tl.journals:
            for l in j.lines:
                m = amap.get(l.account, {})
                jr.append([ref, j.ref, j.date, j.source, j.narration, m.get('label', l.account), m.get('ledger', ''), l.debit, l.credit, l.memo])
    stored = {j['ref']: j for ref in refs for j in store.journals(ref, include_superseded=True)}
    for j in stored.values():
        pass
    for p in store.posting_rows():
        tr_rows.append([p['journal_ref'], p['attempted_at'], p['mode'], p['outcome'], p['http_status'], p['voucher_id'], p['failure_reason'], (p['response_text'] or '')[:300]])
    ws = wb.create_sheet('Summary')
    ws.sheet_view.showGridLines = False
    ws['A1'] = (company + ' – ' if company else '') + 'IFRS 16 Lessee Accounting – Summary'
    ws['A1'].font = Font(size=16, bold=True, color=BLUE)
    wb.remove(ws)
    _sheet(wb, 'Summary', (company + ' – ' if company else '') + 'IFRS 16 lessee accounting – lease summary',
           ['Lease', 'Lessor', 'Asset', 'Lease ccy', 'Functional ccy', 'Commencement', 'End date', 'Initial liability', 'Initial ROU', 'Closing liability', 'Closing ROU', 'Events', 'Status'],
           summary, num_cols=(8, 9, 10, 11), note='Amounts in functional currency. Generated locally; no data leaves this computer.')
    _sheet(wb, 'Schedules', 'Lease liability and ROU schedules (all versions, latest calculation)',
           ['Lease', 'Version', 'Row', 'From', 'To', 'Days', 'Opening liability', 'Interest', 'Payment', 'Principal', 'Closing liability', 'Rounding adj.', 'Opening ROU', 'Depreciation', 'Closing ROU', 'Event adj. – liability', 'Event adj. – ROU', 'Trace to inputs'],
           sched, num_cols=(7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17), widths={18: 70})
    _sheet(wb, 'Liability roll-forward', 'Lease liability roll-forward by calendar year', ['Lease', 'Year', 'Opening', 'New leases', 'Interest', 'Payments', 'Remeasurement / modification', 'Termination derecognition', 'Closing'], lrf, num_cols=(3, 4, 5, 6, 7, 8, 9))
    _sheet(wb, 'ROU roll-forward', 'Right-of-use asset roll-forward by calendar year (net carrying amount)', ['Lease', 'Year', 'Opening', 'Additions', 'Remeasurement / modification', 'Derecognition (net)', 'Depreciation', 'Closing'], rrf, num_cols=(3, 4, 5, 6, 7, 8))
    _sheet(wb, 'Reassessment bridges', 'Reassessment, modification and termination bridges', ['Lease', 'Event #', 'Type', 'Effective', 'Decision', 'Rate used', 'Line', 'Amount', 'Trace / explanation'], bridges, num_cols=(8,), widths={9: 80})
    _sheet(wb, 'Termination calcs', 'Termination and scope-reduction calculations', ['Lease', 'Event #', 'Type', 'Effective', 'Decision', 'Rate used', 'Line', 'Amount', 'Trace / explanation'], terms_rows, num_cols=(8,), widths={9: 80})
    _sheet(wb, 'Journals', 'Journal entries (debit / credit by account)', ['Lease', 'Reference', 'Date', 'Source', 'Narration', 'Account', 'Tally ledger', 'Debit', 'Credit', 'Memo'], jr, num_cols=(8, 9), widths={5: 50})
    _sheet(wb, 'Posting log', 'Tally posting log', ['Journal ref', 'Attempted at', 'Mode', 'Outcome', 'HTTP', 'Voucher id', 'Failure reason', 'Response (first 300 chars)'], tr_rows, widths={7: 50, 8: 60})
    aud = [[a['ts'], a['lease_ref'] or '', a['action'], a['detail']] for a in store.audit_rows()]
    _sheet(wb, 'Audit history', 'Audit history', ['Time', 'Lease', 'Action', 'Detail'], aud, widths={4: 90})
    wb.save(path)
    return path
