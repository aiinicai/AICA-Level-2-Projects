"""Reassessment/modification workspace, termination workspace, journals, Tally settings and reports pages."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPlainTextEdit,
                               QPushButton, QSpinBox, QSplitter, QTabWidget, QTableWidgetItem, QVBoxLayout, QWidget, QDialog, QDialogButtonBox)

from .. import tally
from ..journals import journal_rows
from ..models import EVENT_TYPES, Event
from ..money import dec, parse_date
from ..reports import export_workbook
from .common import (combo, confirm, date_edit, dec_of, fill_table, guarded, make_table, money, pydate, run_busy, title)


class EventWorkspace(QWidget):
    """kind = 'reassess' (reassessment + modification) or 'termination'."""

    def __init__(self, win, kind):
        super().__init__()
        self.win, self.kind = win, kind
        self.pending = None
        lay = QVBoxLayout(self)
        if kind == 'reassess':
            lay.addWidget(title('Reassessment and modification workspace',
                                'A reassessment applies the existing contract (IFRS 16.39-43). A modification is a change to the contract terms (IFRS 16.44-46) and is first tested for a separate lease. Only the future schedule changes; posted history is preserved.'))
        else:
            lay.addWidget(title('Termination workspace', 'Full or partial termination: proportionate derecognition, gain or loss, then remeasurement of any remaining lease where payments or term change. Review the bridge and journals before committing.'))
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split, 1)
        left = QWidget(); ll = QVBoxLayout(left)
        box = QGroupBox('Event inputs'); f = QFormLayout(box); ll.addWidget(box)
        if kind == 'reassess':
            self.type = combo([(k, v) for k, v in EVENT_TYPES.items() if k != 'termination'], 'term_reassessment')
            self.type.currentIndexChanged.connect(self.toggle)
            f.addRow('Event type', self.type)
        self.eff = date_edit(dt.date.today()); self.label = QLineEdit()
        f.addRow('Effective date *', self.eff); f.addRow('Description', self.label)
        self.new_end_on = QCheckBox('Change lease end date'); self.new_end = date_edit(dt.date.today())
        self.new_amt = QLineEdit(); self.new_amt.setPlaceholderText('leave blank for no change (lease currency)')
        self.idx_pct = QLineEdit(); self.idx_pct.setPlaceholderText('e.g. 3.5')
        self.rate = QLineEdit(); self.rate.setPlaceholderText('revised annual rate % (required where IFRS 16 needs one)')
        self.float_chk = QCheckBox('Change results from a floating interest-rate change')
        self.new_rvg = QLineEdit(); self.new_rvg.setPlaceholderText('revised amount expected payable')
        self.po = combo([('', 'No change to purchase option assessment'), ('yes', 'Now reasonably certain to exercise'), ('no', 'No longer reasonably certain')], '')
        self.po_price = QLineEdit(); self.po_price.setPlaceholderText('exercise price if now certain')
        self.override = QPlainTextEdit(); self.override.setPlaceholderText('Optional irregular future payments, one per line: YYYY-MM-DD, amount'); self.override.setMaximumHeight(70)
        self.rows = {}

        def add(key, label, w):
            f.addRow(label, w); self.rows[key] = (f.labelForField(w), w)
        if kind == 'reassess':
            add('end_on', '', self.new_end_on); add('end', 'New lease end date', self.new_end)
            add('amt', 'New regular payment', self.new_amt); add('idx', 'Index / rate change (%)', self.idx_pct)
            add('float', '', self.float_chk); add('rvg', 'Revised residual value guarantee', self.new_rvg)
            add('po', 'Purchase option', self.po); add('pop', 'Purchase option price', self.po_price)
            self.adds = QCheckBox('Modification adds the right to use one or more additional assets')
            self.cons = QLineEdit(); self.stand = QLineEdit(); self.tol = QLineEdit('0'); self.scope_dec = QLineEdit(); self.scope_dec.setPlaceholderText('% reduction in scope, if any')
            add('adds', '', self.adds); add('cons', 'Increase in consideration', self.cons); add('stand', 'Stand-alone price of the added right ‡', self.stand)
            add('tol', 'Commensurate-price tolerance (%) ‡', self.tol); add('scope', 'Reduction in scope (%)', self.scope_dec)
        else:
            self.scope = QLineEdit('100'); self.cash = QLineEdit('0')
            f.addRow('Reduction in scope (%) * (100 = full termination)', self.scope); f.addRow('Termination payment to lessor', self.cash)
            add('end_on', '', self.new_end_on); add('end', 'New end date for the remaining lease', self.new_end); add('amt', 'New payment for the remaining lease', self.new_amt)
        f.addRow('Revised discount rate (%)', self.rate)
        f.addRow('Irregular payments', self.override)
        pb = QHBoxLayout()
        self.prev_btn = QPushButton('Preview calculation and journals'); self.prev_btn.clicked.connect(self.preview)
        self.commit_btn = QPushButton('Commit event'); self.commit_btn.setEnabled(False); self.commit_btn.clicked.connect(self.commit)
        pb.addWidget(self.prev_btn); pb.addWidget(self.commit_btn); pb.addStretch(1)
        ll.addLayout(pb)
        ll.addWidget(QLabel('Committed events and version history'))
        self.hist = make_table(['Ver', 'Type', 'Effective', 'Description', 'Decision', 'Committed at'])
        ll.addWidget(self.hist, 1)
        split.addWidget(left)
        right = QWidget(); rl = QVBoxLayout(right)
        self.out_head = QPlainTextEdit(); self.out_head.setReadOnly(True); self.out_head.setMaximumHeight(160)
        rl.addWidget(self.out_head)
        tabs = QTabWidget(); rl.addWidget(tabs, 1)
        self.ba = make_table(['Measure', 'Before', 'After', 'Change'])
        self.bridge = make_table(['Calculation bridge', 'Amount', 'Trace'])
        self.jt = make_table(['Date', 'Account', 'Tally ledger', 'Debit', 'Credit', 'Memo'])
        tabs.addTab(self.ba, 'Before / after'); tabs.addTab(self.bridge, 'Bridge'); tabs.addTab(self.jt, 'Journals (preview)')
        split.addWidget(right); split.setStretchFactor(0, 2); split.setStretchFactor(1, 3)
        self.toggle()

    def etype(self):
        return self.type.currentData() if self.kind == 'reassess' else 'termination'

    def toggle(self):
        t = self.etype()
        show = {
            'term_reassessment': {'end_on', 'end', 'amt', 'po', 'pop'},
            'index_change': {'amt', 'idx', 'float'},
            'rvg_change': {'rvg'},
            'modification': {'end_on', 'end', 'amt', 'adds', 'cons', 'stand', 'tol', 'scope'},
            'termination': {'end_on', 'end', 'amt'},
        }[t]
        for k, (lab, w) in self.rows.items():
            w.setVisible(k in show)
            if lab:
                lab.setVisible(k in show)
        self.commit_btn.setEnabled(False)

    def build_event(self) -> Event:
        t, p = self.etype(), {}
        if self.new_end_on.isChecked() and 'end_on' in self.rows:
            p['new_end_date'] = pydate(self.new_end).isoformat()
        if self.new_amt.text().strip():
            p['new_payment_amount'] = str(dec_of(self.new_amt, 'New payment'))
        if self.rate.text().strip():
            p['revised_rate'] = str(dec_of(self.rate, 'Revised discount rate'))
        if self.override.toPlainText().strip():
            lst = []
            for i, line in enumerate(self.override.toPlainText().strip().splitlines(), 1):
                try:
                    a, b = [x.strip() for x in line.split(',')]
                    lst.append({'date': parse_date(a).isoformat(), 'amount': str(dec(b.replace(',', '')))})
                except Exception:
                    raise ValueError(f'Irregular payments line {i}: use "YYYY-MM-DD, amount".')
            p['payments_override'] = lst
        if t == 'termination':
            p['scope_pct'] = str(dec_of(self.scope, 'Reduction in scope'))
            p['termination_payment'] = str(dec_of(self.cash, 'Termination payment'))
        elif t == 'index_change':
            if self.idx_pct.text().strip():
                p['index_change_pct'] = str(dec_of(self.idx_pct, 'Index change'))
            p['floating_rate_linked'] = self.float_chk.isChecked()
        elif t == 'rvg_change':
            if self.new_rvg.text().strip():
                p['new_rvg'] = str(dec_of(self.new_rvg, 'Revised residual value guarantee'))
        elif t == 'term_reassessment':
            v = self.po.currentData()
            if v:
                p['purchase_option_certain'] = v == 'yes'
                if v == 'yes' and self.po_price.text().strip():
                    p['purchase_option_price'] = str(dec_of(self.po_price, 'Purchase option price'))
        elif t == 'modification':
            p.update({'adds_right_of_use': self.adds.isChecked(), 'added_consideration': str(dec_of(self.cons, 'Increase in consideration')),
                      'standalone_price': str(dec_of(self.stand, 'Stand-alone price')), 'price_tolerance_pct': str(dec_of(self.tol, 'Tolerance')),
                      'scope_decrease_pct': str(dec_of(self.scope_dec, 'Reduction in scope'))})
        return Event(t, pydate(self.eff), p, self.label.text().strip())

    def preview(self):
        ref = self.win.ref
        if not ref:
            QMessageBox.information(self, 'Select a lease', 'Choose a lease in the toolbar first.')
            return
        ok, ev = guarded(self, self.build_event)
        if not ok:
            return
        ok, out = guarded(self, lambda: run_busy(self.win, 'Calculating preview…', lambda: self.win.store.preview(ref, ev)))
        if not ok:
            self.commit_btn.setEnabled(False)
            return
        tl, res = out
        self.pending = ev
        amap = self.win.store.get_setting('account_map')
        notes = '\n'.join('• ' + n for n in res.notes)
        self.out_head.setPlainText(f"Decision: {res.decision.replace('_', ' ').upper()}\nDiscount rate: {'' if res.rate_used is None else f'{res.rate_used * 100:.4f}%'} – {res.rate_reason}\n{notes}")
        keys = [('Lease liability', 'liability'), ('ROU cost', 'rou_cost'), ('Accumulated depreciation', 'accumulated_depreciation'), ('ROU carrying amount', 'rou_carrying'),
                ('Undiscounted remaining payments', 'remaining_payments'), ('Number of remaining payments', 'number_of_payments'), ('Regular payment', 'next_regular_payment'),
                ('Discount rate', 'rate'), ('Lease end', 'lease_end'), ('Depreciation end', 'depreciation_end')]
        rows = []
        for lab, k in keys:
            b, a = res.before.get(k), res.after.get(k)
            ch = (a - b) if hasattr(a, '__sub__') and not isinstance(a, dt.date) and a is not None and b is not None else ''
            rows.append([lab, b, a, ch])
        fill_table(self.ba, rows, num_cols=(1, 2, 3))
        fill_table(self.bridge, [[b['label'], b['amount'], b['trace']] for b in res.bridge], num_cols=(1,))
        jl = []
        for j in res.journals:
            for (a, led, d, c, m) in journal_rows(j, amap):
                jl.append([j.date, a, led, d, c, f'{j.ref} {m}'])
        fill_table(self.jt, jl, num_cols=(3, 4))
        if res.new_lease_template:
            QMessageBox.information(self, 'Separate lease', 'This modification is accounted for as a SEPARATE LEASE (IFRS 16.44). The existing lease is not adjusted.\nCreate a new lease for the additional right of use:\n\n' +
                                    '\n'.join(f'{k}: {v}' for k, v in res.new_lease_template.items()))
        self.commit_btn.setEnabled(not res.new_lease_template)

    def commit(self):
        ref = self.win.ref
        if not (ref and self.pending):
            return
        if not confirm(self, 'Commit this event? It becomes part of the lease version history (events are append-only) and creates the journals shown.'):
            return
        ok, _ = guarded(self, lambda: run_busy(self.win, 'Committing event…', lambda: self.win.store.commit_event(ref, self.pending)))
        if ok:
            self.pending = None
            self.commit_btn.setEnabled(False)
            self.win.refresh_all()
            QMessageBox.information(self, 'Committed', 'Event committed. New journals are in Draft status in the Journals page.')

    def refresh(self):
        ref = self.win.ref
        if not ref:
            self.hist.setRowCount(0); return
        ev = self.win.store.event_rows(ref)
        import json
        rows = []
        for e in ev:
            res = json.loads(e['result_json'])
            rows.append([f"V{e['version']}", e['type'], e['effective_date'], e['label'], res.get('decision', ''), e['committed_at']])
        fill_table(self.hist, rows)


class VoucherDialog(QDialog):
    def __init__(self, parent, xml):
        super().__init__(parent)
        self.setWindowTitle('Tally voucher preview (nothing has been sent)')
        self.resize(900, 520)
        lay = QVBoxLayout(self)
        te = QPlainTextEdit(xml); te.setReadOnly(True); lay.addWidget(te)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); bb.rejected.connect(self.reject); bb.accepted.connect(self.accept); lay.addWidget(bb)


class JournalsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.addWidget(title('Journal preview and posting', 'Approve journals, preview the Tally voucher, then post on explicit confirmation. Posting never alters calculations.'))
        top = QHBoxLayout()
        self.flt = combo([('', 'All (excluding superseded)'), ('draft', 'Draft'), ('approved', 'Approved – pending posting'), ('posted', 'Posted'), ('superseded', 'Superseded')], '')
        self.flt.currentIndexChanged.connect(self.refresh)
        top.addWidget(QLabel('Show:')); top.addWidget(self.flt); top.addStretch(1)
        lay.addLayout(top)
        split = QSplitter(Qt.Orientation.Vertical)
        self.table = make_table(['Reference', 'Date', 'Source', 'Narration', 'Debit total', 'Status', 'Posting', 'Voucher id'])
        self.table.itemSelectionChanged.connect(self.on_select)
        split.addWidget(self.table)
        low = QSplitter(Qt.Orientation.Horizontal)
        self.lines = make_table(['Account', 'Tally ledger', 'Debit', 'Credit', 'Memo'])
        self.trace = QPlainTextEdit(); self.trace.setReadOnly(True)
        low.addWidget(self.lines); low.addWidget(self.trace)
        split.addWidget(low)
        lay.addWidget(split, 1)
        bar = QHBoxLayout()
        for text, fn, sec in (('Approve selected', self.approve, False), ('Approve all drafts', self.approve_all, True), ('Preview voucher', self.preview, False),
                              ('Post to Tally…', self.post, False), ('Resolve unconfirmed…', self.resolve, True), ('Export Tally XML (approved, unposted)', self.export_xml, True)):
            b = QPushButton(text)
            if sec:
                b.setObjectName('secondary')
            b.clicked.connect(fn); bar.addWidget(b)
        bar.addStretch(1)
        lay.addLayout(bar)
        self.items = []

    def selected(self):
        rows = sorted({i.row() for i in self.table.selectedItems()})
        return [self.items[r] for r in rows if r < len(self.items)]

    def refresh(self):
        s, ref = self.win.store, self.win.ref
        st = self.flt.currentData() or None
        self.items = s.journals(ref, status=st, include_superseded=(st == 'superseded')) if ref else []
        rows = [[j['ref'], j['jdate'], j['source'], j['narration'], sum(dec(l['debit']) for l in j['lines']), j['status'], j['posting_state'], j['voucher_id'] or ''] for j in self.items]
        colors = {i: {'posted': '#e3f5e8', 'approved': '#eaf1fb', 'superseded': '#eeeeee'}.get(j['status'], '') for i, j in enumerate(self.items)}
        fill_table(self.table, rows, num_cols=(4,), colors=colors)
        self.lines.setRowCount(0); self.trace.clear()

    def on_select(self):
        sel = self.selected()
        if not sel:
            return
        j = sel[0]
        amap = self.win.store.get_setting('account_map')
        fill_table(self.lines, [[amap.get(l['account'], {}).get('label', l['account']), amap.get(l['account'], {}).get('ledger', ''), dec(l['debit']), dec(l['credit']), l['memo']] for l in j['lines']], num_cols=(2, 3))
        self.trace.setPlainText('\n\n'.join(j['trace']))

    def approve(self):
        sel = self.selected()
        if sel:
            ok, n = guarded(self, self.win.store.approve_journals, [j['ref'] for j in sel])
            if ok:
                self.refresh()

    def approve_all(self):
        refs = [j['ref'] for j in self.items if j['status'] == 'draft']
        if refs and confirm(self, f'Approve {len(refs)} draft journals?'):
            ok, _ = guarded(self, self.win.store.approve_journals, refs)
            if ok:
                self.refresh()

    def cfg(self):
        return tally.TallyConfig.from_dict(self.win.store.get_setting('tally'))

    def preview(self):
        sel = self.selected()
        if not sel:
            return
        ok, xml = guarded(self, tally.preview, self.win.store, sel[0]['ref'], self.cfg())
        if ok:
            VoucherDialog(self, xml).exec()

    def post(self):
        sel = [j for j in self.selected()]
        if not sel:
            return
        if not confirm(self, f'Post {len(sel)} journal(s) to TallyPrime company "{self.cfg().company}" at {self.cfg().url}?\nOnly journals reported as created by Tally are marked Posted.', 'Post to Tally'):
            return
        results = []

        def work():
            out = []
            for j in sel:
                try:
                    out.append((j['ref'], tally.post_journal(self.win.store, j['ref'], self.cfg(), confirmed=True)))
                except (tally.TallyConfigError, ValueError) as e:
                    out.append((j['ref'], {'outcome': 'not sent', 'reason': str(e)}))
            return out
        ok, results = guarded(self, lambda: run_busy(self.win, 'Posting to Tally…', work))
        self.refresh()
        if ok:
            QMessageBox.information(self, 'Posting result', '\n'.join(f"{r}: {x['outcome']}" + (f" – {x['reason']}" if x.get('reason') else '') for r, x in results))

    def resolve(self):
        sel = [j for j in self.selected() if j['posting_state'] == 'unconfirmed']
        if not sel:
            QMessageBox.information(self, 'Resolve', 'Select a journal whose posting state is "unconfirmed".')
            return
        j = sel[0]
        if confirm(self, f"Tally did not confirm voucher {j['ref']}.\nCheck the Day Book in Tally. Does the voucher EXIST there?\n\nYes = mark as posted. No = return to pending.", 'Resolve unconfirmed'):
            self.win.store.resolve_unconfirmed(j['ref'], True)
        else:
            self.win.store.resolve_unconfirmed(j['ref'], False)
        self.refresh()

    def export_xml(self):
        items = [j for j in self.items if j['status'] == 'approved' and j['posting_state'] != 'posted']
        if not items:
            QMessageBox.information(self, 'Export', 'There are no approved, unposted journals to export.'); return
        path, _ = QFileDialog.getSaveFileName(self, 'Save Tally import file', 'tally_vouchers.xml', 'XML files (*.xml)')
        if path:
            ok, n = guarded(self, tally.export_xml_file, items, self.cfg(), self.win.store.get_setting('account_map'), path)
            if ok:
                QMessageBox.information(self, 'Exported', f'{n} voucher(s) written to {path}.\nImport in TallyPrime: Gateway of Tally > Import > Vouchers. Posting state stays "pending" until you confirm.')


class TallyPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.addWidget(title('TallyPrime connector settings', 'Local XML over HTTP. Enable the server in TallyPrime (F1 Help > Settings > Connectivity) and open the company. JSON import is not enabled in this release because the voucher JSON schema was not verified.'))
        box = QGroupBox('Endpoint'); f = QFormLayout(box); lay.addWidget(box)
        self.host, self.port, self.company, self.vtype = QLineEdit(), QSpinBox(), QLineEdit(), QLineEdit()
        self.port.setRange(1, 65535); self.timeout = QSpinBox(); self.timeout.setRange(1, 120); self.prefix = QLineEdit()
        for lab, w in (('Host', self.host), ('Port', self.port), ('Company name (exactly as in Tally) *', self.company), ('Voucher type', self.vtype), ('Timeout (seconds)', self.timeout), ('Narration prefix', self.prefix)):
            f.addRow(lab, w)
        self.mapt = make_table(['Account code', 'Account (app)', 'Tally ledger (editable)'])
        from PySide6.QtWidgets import QAbstractItemView
        self.mapt.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        lay.addWidget(QLabel('Account → Tally ledger mapping (double-click a ledger name to edit; ledger names are also what journals use)'))
        lay.addWidget(self.mapt, 1)
        bar = QHBoxLayout()
        for text, fn, sec in (('Save settings', self.save, False), ('Test connection', self.test, True), ('Validate ledgers', self.validate, True)):
            b = QPushButton(text)
            if sec:
                b.setObjectName('secondary')
            b.clicked.connect(fn); bar.addWidget(b)
        bar.addStretch(1)
        lay.addLayout(bar)
        self.status = QLabel(''); self.status.setWordWrap(True); lay.addWidget(self.status)
        lay.addWidget(QLabel('Posting log'))
        self.log = make_table(['Time', 'Journal', 'Mode', 'Outcome', 'HTTP', 'Voucher id', 'Failure reason'])
        lay.addWidget(self.log, 1)

    def refresh(self):
        s = self.win.store
        c = tally.TallyConfig.from_dict(s.get_setting('tally'))
        self.host.setText(c.host); self.port.setValue(c.port); self.company.setText(c.company); self.vtype.setText(c.voucher_type)
        self.timeout.setValue(c.timeout); self.prefix.setText(c.narration_prefix)
        m = s.get_setting('account_map')
        self.mapt.setRowCount(len(m))
        for r, (k, v) in enumerate(m.items()):
            a, b, c2 = QTableWidgetItem(k), QTableWidgetItem(v['label']), QTableWidgetItem(v['ledger'])
            a.setFlags(a.flags() & ~Qt.ItemFlag.ItemIsEditable); b.setFlags(b.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapt.setItem(r, 0, a); self.mapt.setItem(r, 1, b); self.mapt.setItem(r, 2, c2)
        self.mapt.resizeColumnsToContents()
        fill_table(self.log, [[p['attempted_at'], p['journal_ref'], p['mode'], p['outcome'], p['http_status'], p['voucher_id'], p['failure_reason']] for p in s.posting_rows()])

    def collect(self):
        s = self.win.store
        m = s.get_setting('account_map')
        for r in range(self.mapt.rowCount()):
            m[self.mapt.item(r, 0).text()]['ledger'] = self.mapt.item(r, 2).text().strip()
        cfg = {'host': self.host.text().strip() or 'localhost', 'port': self.port.value(), 'company': self.company.text().strip(), 'voucher_type': self.vtype.text().strip() or 'Journal',
               'timeout': self.timeout.value(), 'use_json': False, 'narration_prefix': self.prefix.text().strip()}
        return cfg, m

    def save(self):
        cfg, m = self.collect()
        self.win.store.set_setting('tally', cfg); self.win.store.set_setting('account_map', m)
        self.status.setText('Settings saved.')

    def test(self):
        self.save()
        cfg = tally.TallyConfig.from_dict(self.win.store.get_setting('tally'))
        ok, r = guarded(self, lambda: run_busy(self.win, 'Contacting Tally…', lambda: tally.test_connection(cfg)))
        if ok:
            self.status.setText(('✔ Connected: ' if r['ok'] else '✘ Not connected: ') + r['message'])

    def validate(self):
        self.save()
        cfg = tally.TallyConfig.from_dict(self.win.store.get_setting('tally'))
        m = self.win.store.get_setting('account_map')
        ok, r = guarded(self, lambda: run_busy(self.win, 'Checking ledgers in Tally…', lambda: tally.validate_ledgers(cfg, m)))
        if ok:
            self.status.setText(('✔ ' if r['ok'] else '✘ ') + r['message'])


class ReportsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.addWidget(title('Reports', 'Export a formatted Excel workbook: schedules, liability and ROU roll-forwards, reassessment bridges, termination calculations, journals, posting log and audit history.'))
        self.company = QLineEdit(); self.company.setPlaceholderText('Company name for the report heading (optional)')
        lay.addWidget(self.company)
        self.lst = QListWidget(); self.lst.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        lay.addWidget(QLabel('Leases to include (select one or more; none selected = all)'))
        lay.addWidget(self.lst, 1)
        b = QPushButton('Export Excel workbook…'); b.clicked.connect(self.export); lay.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(QLabel('Audit history'))
        self.aud = make_table(['Time', 'Lease', 'Action', 'Detail'])
        lay.addWidget(self.aud, 1)

    def refresh(self):
        self.lst.clear()
        for l in self.win.store.list_leases():
            self.lst.addItem(l['ref'])
        fill_table(self.aud, [[a['ts'], a['lease_ref'] or '', a['action'], a['detail']] for a in self.win.store.audit_rows(self.win.ref)])

    def export(self):
        refs = [i.text() for i in self.lst.selectedItems()] or [l['ref'] for l in self.win.store.list_leases()]
        if not refs:
            QMessageBox.information(self, 'Reports', 'There are no leases to export.'); return
        path, _ = QFileDialog.getSaveFileName(self, 'Save workbook', 'IFRS16_lease_report.xlsx', 'Excel workbook (*.xlsx)')
        if path:
            ok, _ = guarded(self, lambda: run_busy(self.win, 'Building workbook…', lambda: export_workbook(self.win.store, refs, path, self.company.text().strip())))
            if ok:
                QMessageBox.information(self, 'Exported', f'Saved {path}')
