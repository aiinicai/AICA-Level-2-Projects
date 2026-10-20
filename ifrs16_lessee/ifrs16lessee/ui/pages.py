"""Dashboard, lease entry form and calculation schedule pages."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
                               QScrollArea, QSplitter, QSpinBox, QTabWidget, QVBoxLayout, QWidget, QGridLayout)

from ..engine import build_timeline, exemption_check, generate_payments
from ..journals import journal_rows
from ..models import LeaseTerms, Payment
from ..money import COMPOUNDING, DAY_COUNTS, FREQ_MONTHS, RoundingPolicy, dec
from ..sample import load_sample
from .common import (card, combo, confirm, date_edit, dec_of, fill_table, guarded, make_table, money, pydate, qdate, run_busy, title)


class Dashboard(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.addWidget(title('Lease dashboard', 'All data is stored only in a local SQLite file on this computer. Nothing is uploaded.'))
        cards = QHBoxLayout()
        self.c_n, self.c_l, self.c_r, self.c_p = card('Leases', '0'), card('Lease liability (today)', '0.00'), card('ROU carrying amount (today)', '0.00'), card('Journals pending posting', '0')
        for c in (self.c_n, self.c_l, self.c_r, self.c_p):
            cards.addWidget(c)
        lay.addLayout(cards)
        self.table = make_table(['Lease', 'Lessor', 'Asset', 'Currency', 'Commencement', 'End', 'Status', 'Liability today', 'ROU today', 'Events'])
        self.table.doubleClicked.connect(self.open_selected)
        lay.addWidget(self.table)
        row = QHBoxLayout()
        for text, fn, sec in (('New lease', self.win.new_lease, False), ('Open selected', self.open_selected, False), ('Load sample lease', self.load_sample, True),
                              ('Delete selected', self.delete_selected, True)):
            b = QPushButton(text)
            if sec:
                b.setObjectName('secondary')
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

    def selected_ref(self):
        r = self.table.currentRow()
        return self.table.item(r, 0).text() if r >= 0 else None

    def open_selected(self, *_):
        ref = self.selected_ref()
        if ref:
            self.win.set_lease(ref)
            self.win.goto('Calculation schedule')

    def load_sample(self):
        if self.win.store.get_terms_or_none('SAMPLE-001'):
            QMessageBox.information(self, 'Sample lease', 'The sample lease SAMPLE-001 already exists.')
            return
        ok, _ = guarded(self, lambda: run_busy(self.win, 'Creating sample lease…', lambda: load_sample(self.win.store)))
        if ok:
            self.win.set_lease('SAMPLE-001')
            self.win.refresh_all()

    def delete_selected(self):
        ref = self.selected_ref()
        if ref and confirm(self, f'Delete lease {ref} and all its versions, events and journals? This cannot be undone.'):
            ok, _ = guarded(self, self.win.store.delete_lease, ref)
            if ok:
                self.win.refresh_all()

    def refresh(self):
        s = self.win.store
        rows, tot_l, tot_r = [], Decimal(0), Decimal(0)
        today = dt.date.today()
        for l in s.list_leases():
            t = s.get_terms(l['ref'])
            try:
                tl = s.timeline(l['ref'])
                liab = rou = Decimal(0)
                for r in tl.rows:
                    if r.end <= today:
                        liab, rou = r.close_liab, r.close_rou
                if not tl.rows or today < t.commencement:
                    liab = rou = Decimal(0)
                if tl.exempt:
                    status = 'Exempt (' + t.exemption.replace('_', '-') + ')'
                else:
                    status = 'Terminated' if tl.final['terminated'] else 'Active'
                n_ev = len(tl.events)
            except Exception as e:      # noqa: BLE001
                liab = rou = Decimal(0); status = 'Error: ' + str(e)[:40]; n_ev = 0
            tot_l += liab; tot_r += rou
            rows.append([l['ref'], t.lessor, t.asset, t.currency, t.commencement, t.end_date, status, liab, rou, n_ev])
        fill_table(self.table, rows, num_cols=(7, 8))
        self.c_n.value_label.setText(str(len(rows)))
        self.c_l.value_label.setText(money(tot_l))
        self.c_r.value_label.setText(money(tot_r))
        self.c_p.value_label.setText(str(len([j for j in s.journals() if j['posting_state'] != 'posted'])))


class LeaseForm(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        outer = QVBoxLayout(self)
        outer.addWidget(title('Lease entry', 'IFRS 16 judgments (lease term, options, discount rate, exemptions, depreciation) are inputs you control. Fields marked ‡ are policy choices.'))
        sc = QScrollArea(); sc.setWidgetResizable(True)
        host = QWidget(); sc.setWidget(host)
        g = QVBoxLayout(host)
        outer.addWidget(sc, 1)

        def group(name):
            box = QGroupBox(name); f = QFormLayout(box); g.addWidget(box); return f

        f = group('Identification')
        self.ref, self.lessor, self.asset = QLineEdit(), QLineEdit(), QLineEdit()
        self.signing, self.comm, self.end = date_edit(), date_edit(), date_edit(dt.date.today().replace(year=dt.date.today().year + 3))
        self.func_ccy, self.ccy, self.fx = QLineEdit('AED'), QLineEdit('AED'), QLineEdit('1')
        for lab, w in (('Lease reference *', self.ref), ('Lessor *', self.lessor), ('Asset description *', self.asset), ('Contract / signing date', self.signing),
                       ('Commencement date *', self.comm), ('End date (last day of lease term) *', self.end), ('Functional currency', self.func_ccy),
                       ('Lease currency', self.ccy), ('Exchange rate lease → functional (fixed) ‡', self.fx)):
            f.addRow(lab, w)

        f = group('Payments')
        self.amount = QLineEdit('0')
        self.freq = combo(list(FREQ_MONTHS), 'monthly')
        self.timing = combo([('arrears', 'In arrears (end of period)'), ('advance', 'In advance (start of period)')], 'arrears')
        self.use_edited = QCheckBox('Use the edited payment table below instead of the generated pattern')
        f.addRow('Regular payment amount *', self.amount); f.addRow('Frequency', self.freq); f.addRow('Timing', self.timing)
        self.pay_table = make_table(['Date (YYYY-MM-DD)', 'Amount (functional ccy)', 'Kind', 'Note'])
        from PySide6.QtWidgets import QAbstractItemView
        self.pay_table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self.pay_table.setMinimumHeight(180)
        pb = QHBoxLayout()
        b1 = QPushButton('Generate payment dates'); b1.clicked.connect(self.generate); pb.addWidget(b1)
        b2 = QPushButton('Add row'); b2.setObjectName('secondary'); b2.clicked.connect(self.add_row); pb.addWidget(b2)
        b3 = QPushButton('Remove selected row'); b3.setObjectName('secondary'); b3.clicked.connect(self.del_row); pb.addWidget(b3)
        pb.addStretch(1)
        f.addRow(self.use_edited); f.addRow(self.pay_table); f.addRow(pb)

        f = group('Discounting')
        self.rate = QLineEdit('5.00')
        self.rate_basis = combo([('IBR', 'Incremental borrowing rate'), ('implicit', 'Rate implicit in the lease')], 'IBR')
        self.day_count = combo(DAY_COUNTS, 'ACT/365'); self.compounding = combo(COMPOUNDING, 'annual')
        f.addRow('Annual discount rate (%) ‡ *', self.rate); f.addRow('Rate basis ‡', self.rate_basis); f.addRow('Day-count convention ‡', self.day_count); f.addRow('Compounding ‡', self.compounding)

        f = group('Right-of-use asset')
        self.dep_method = combo([('straight_line', 'Straight-line'), ('declining_balance', 'Declining balance (switches to straight-line)')], 'straight_line')
        self.life = QLineEdit('0'); self.db_rate = QLineEdit('0'); self.own = QCheckBox('Ownership transfers at end of lease')
        self.incent, self.prepaid, self.idc, self.rest = QLineEdit('0'), QLineEdit('0'), QLineEdit('0'), QLineEdit('0')
        for lab, w in (('Depreciation method ‡', self.dep_method), ('Useful life (years) – needed if ownership transfers / purchase option', self.life),
                       ('Declining-balance annual rate (%) – 0 = 2 ÷ life', self.db_rate), ('', self.own), ('Lease incentives received', self.incent),
                       ('Payments at or before commencement (not in the schedule)', self.prepaid), ('Initial direct costs', self.idc),
                       ('Restoration obligation (present value, IAS 37)', self.rest)):
            f.addRow(lab, w)

        f = group('Options, guarantees and variable payments (judgments)')
        self.rvg = QLineEdit('0'); self.po_price = QLineEdit('0'); self.po_cert = QCheckBox('Purchase option reasonably certain to be exercised')
        self.pen = QLineEdit('0'); self.pen_inc = QCheckBox('Lease term reflects exercise of a termination option (penalty included)')
        self.idx = QCheckBox('Payments are index-linked'); self.flt = QCheckBox('Payments depend on a floating interest rate')
        for lab, w in (('Residual value guarantee – amount expected payable', self.rvg), ('Purchase option exercise price', self.po_price), ('', self.po_cert),
                       ('Termination penalty', self.pen), ('', self.pen_inc), ('', self.idx), ('', self.flt)):
            f.addRow(lab, w)

        f = group('Recognition exemptions (policy election ‡)')
        self.exemption = combo([('none', 'None – apply the right-of-use model'), ('short_term', 'Short-term lease (≤ 12 months, no purchase option)'), ('low_value', 'Low-value asset lease')], 'none')
        self.elected = QCheckBox('Elect the exemption for this lease (expense straight-line)')
        self.val_new = QLineEdit('0'); self.thr = QLineEdit('5000')
        self.elig = QLabel(''); self.elig.setWordWrap(True)
        bt = QPushButton('Check eligibility'); bt.setObjectName('secondary'); bt.clicked.connect(self.check_elig)
        for lab, w in (('Exemption', self.exemption), ('', self.elected), ('Asset value when new', self.val_new), ('Low-value threshold ‡ (your policy)', self.thr), ('', bt), ('', self.elig)):
            f.addRow(lab, w)

        f = group('Calculation policy')
        self.gran = combo([('monthly', 'Monthly postings'), ('per_payment', 'At each payment date only')], 'monthly')
        self.dec = QSpinBox(); self.dec.setRange(0, 4); self.dec.setValue(2)
        self.mode = combo(['ROUND_HALF_UP', 'ROUND_HALF_EVEN', 'ROUND_DOWN'], 'ROUND_HALF_UP')
        self.notes = QPlainTextEdit(); self.notes.setMaximumHeight(60)
        for lab, w in (('Journal/interest granularity ‡', self.gran), ('Decimal places', self.dec), ('Rounding mode ‡', self.mode), ('Notes', self.notes)):
            f.addRow(lab, w)
        g.addStretch(1)

        bar = QHBoxLayout()
        self.save_btn = QPushButton('Validate and save lease'); self.save_btn.clicked.connect(self.save)
        nb = QPushButton('New / clear'); nb.setObjectName('secondary'); nb.clicked.connect(self.clear)
        self.lock = QLabel(''); self.lock.setObjectName('Hint')
        bar.addWidget(self.save_btn); bar.addWidget(nb); bar.addWidget(self.lock); bar.addStretch(1)
        outer.addLayout(bar)

    # ---- payment table
    def add_row(self, p=None):
        r = self.pay_table.rowCount()
        self.pay_table.insertRow(r)
        vals = [p.date.isoformat(), str(p.amount), p.kind, p.note] if isinstance(p, Payment) else ['', '0', 'lease', '']
        from PySide6.QtWidgets import QTableWidgetItem
        for c, v in enumerate(vals):
            self.pay_table.setItem(r, c, QTableWidgetItem(v))

    def del_row(self):
        r = self.pay_table.currentRow()
        if r >= 0:
            self.pay_table.removeRow(r)

    def generate(self):
        ok, pays = guarded(self, lambda: generate_payments(self.build(include_table=False)))
        if ok:
            self.pay_table.setRowCount(0)
            for p in pays:
                self.add_row(p)

    def table_payments(self):
        out = []
        for r in range(self.pay_table.rowCount()):
            cells = [(self.pay_table.item(r, c).text() if self.pay_table.item(r, c) else '') for c in range(4)]
            try:
                d = dt.date.fromisoformat(cells[0].strip())
            except ValueError:
                raise ValueError(f'Payment row {r + 1}: the date "{cells[0]}" must be in the format YYYY-MM-DD.')
            try:
                a = dec(cells[1].replace(',', ''))
            except Exception:
                raise ValueError(f'Payment row {r + 1}: the amount "{cells[1]}" is not a number.')
            kind = cells[2].strip() or 'lease'
            if kind not in ('lease', 'rvg', 'purchase_option', 'termination_penalty'):
                raise ValueError(f'Payment row {r + 1}: kind must be lease, rvg, purchase_option or termination_penalty.')
            out.append(Payment(d, a, kind, cells[3], True))
        return out

    # ---- build / load
    def build(self, include_table=True) -> LeaseTerms:
        if not self.ref.text().strip():
            raise ValueError('Enter a lease reference.')
        t = LeaseTerms(ref=self.ref.text().strip(), lessor=self.lessor.text().strip(), asset=self.asset.text().strip(), signing_date=pydate(self.signing),
                       commencement=pydate(self.comm), end_date=pydate(self.end), functional_currency=self.func_ccy.text().strip().upper() or 'AED',
                       currency=self.ccy.text().strip().upper() or 'AED', fx_rate=dec_of(self.fx, 'Exchange rate', '1'),
                       payment_amount=dec_of(self.amount, 'Payment amount'), frequency=self.freq.currentData(), timing=self.timing.currentData(),
                       discount_rate=dec_of(self.rate, 'Discount rate') / 100, rate_basis=self.rate_basis.currentData(), day_count=self.day_count.currentData(),
                       compounding=self.compounding.currentData(), depreciation_method=self.dep_method.currentData(), useful_life_years=dec_of(self.life, 'Useful life'),
                       db_rate=dec_of(self.db_rate, 'Declining-balance rate') / 100, ownership_transfers=self.own.isChecked(),
                       incentives_received=dec_of(self.incent, 'Incentives'), prepaid_before_commencement=dec_of(self.prepaid, 'Payments at/before commencement'),
                       initial_direct_costs=dec_of(self.idc, 'Initial direct costs'), restoration_obligation=dec_of(self.rest, 'Restoration obligation'),
                       rvg_expected=dec_of(self.rvg, 'Residual value guarantee'), purchase_option_price=dec_of(self.po_price, 'Purchase option price'),
                       purchase_option_certain=self.po_cert.isChecked(), termination_penalty=dec_of(self.pen, 'Termination penalty'),
                       termination_penalty_included=self.pen_inc.isChecked(), index_linked=self.idx.isChecked(), floating_rate_linked=self.flt.isChecked(),
                       exemption=self.exemption.currentData(), exemption_elected=self.elected.isChecked(), asset_value_new=dec_of(self.val_new, 'Asset value when new'),
                       low_value_threshold=dec_of(self.thr, 'Low-value threshold'), posting_granularity=self.gran.currentData(),
                       rounding=RoundingPolicy(self.dec.value(), self.mode.currentData()), notes=self.notes.toPlainText())
        if include_table and self.use_edited.isChecked():
            t.payments = self.table_payments()
            if not t.payments:
                raise ValueError('The payment table is empty. Generate payment dates or untick "Use the edited payment table".')
        return t

    def check_elig(self):
        ok, t = guarded(self, self.build, False)
        if ok:
            self.elig.setText('\n'.join(exemption_check(t)['messages']) + '\nEligibility is an indicator; the election is your accounting policy decision.')

    def save(self):
        ok, t = guarded(self, self.build)
        if not ok:
            return
        ok, tl = guarded(self, lambda: run_busy(self.win, 'Calculating and saving…', lambda: self.win.store.save_lease(t)))
        if ok:
            self.win.store.set_setting('functional_currency', t.functional_currency)
            self.win.set_lease(t.ref)
            self.win.refresh_all()
            QMessageBox.information(self, 'Saved', f"Lease {t.ref} saved.\nInitial liability: {money(tl.initial['liability'])}\nInitial ROU asset: {money(tl.initial['rou_cost'])}")
            self.win.goto('Calculation schedule')

    def clear(self):
        self.load(LeaseTerms(functional_currency=self.win.store.get_setting('functional_currency'), currency=self.win.store.get_setting('functional_currency'),
                             commencement=dt.date.today(), end_date=dt.date.today().replace(year=dt.date.today().year + 3)))

    def load(self, t: LeaseTerms):
        s = lambda w, v: w.setText(str(v))
        s(self.ref, t.ref); s(self.lessor, t.lessor); s(self.asset, t.asset)
        self.signing.setDate(qdate(t.signing_date)); self.comm.setDate(qdate(t.commencement)); self.end.setDate(qdate(t.end_date))
        s(self.func_ccy, t.functional_currency); s(self.ccy, t.currency); s(self.fx, t.fx_rate); s(self.amount, t.payment_amount)
        for c, v in ((self.freq, t.frequency), (self.timing, t.timing), (self.rate_basis, t.rate_basis), (self.day_count, t.day_count), (self.compounding, t.compounding),
                     (self.dep_method, t.depreciation_method), (self.exemption, t.exemption), (self.gran, t.posting_granularity), (self.mode, t.rounding.mode)):
            c.setCurrentIndex(max(0, c.findData(v)))
        s(self.rate, t.discount_rate * 100); s(self.life, t.useful_life_years); s(self.db_rate, t.db_rate * 100)
        self.own.setChecked(t.ownership_transfers)
        for w, v in ((self.incent, t.incentives_received), (self.prepaid, t.prepaid_before_commencement), (self.idc, t.initial_direct_costs), (self.rest, t.restoration_obligation),
                     (self.rvg, t.rvg_expected), (self.po_price, t.purchase_option_price), (self.pen, t.termination_penalty), (self.val_new, t.asset_value_new), (self.thr, t.low_value_threshold)):
            s(w, v)
        self.po_cert.setChecked(t.purchase_option_certain); self.pen_inc.setChecked(t.termination_penalty_included)
        self.idx.setChecked(t.index_linked); self.flt.setChecked(t.floating_rate_linked); self.elected.setChecked(t.exemption_elected)
        self.dec.setValue(t.rounding.decimals); self.notes.setPlainText(t.notes)
        self.pay_table.setRowCount(0)
        for p in t.payments:
            self.add_row(p)
        self.use_edited.setChecked(bool(t.payments))

    def refresh(self):
        ref = self.win.ref
        if ref and self.win.store.get_terms_or_none(ref) and self.ref.text() != ref:
            self.load(self.win.store.get_terms(ref))
        locked = bool(ref and self.ref.text() == ref and self.win.store.is_locked(ref))
        self.save_btn.setEnabled(not locked)
        self.lock.setText('Terms are locked (approved/posted journals or committed events). Use the reassessment, modification or termination workspaces.' if locked else '')


class Schedule(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.addWidget(title('Calculation schedule', 'Select a row to see its journals and the trace back to the inputs, side by side.'))
        self.tabs = QTabWidget(); lay.addWidget(self.tabs, 1)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.table = make_table(['#', 'Ver', 'From', 'To', 'Days', 'Opening liability', 'Interest', 'Payment', 'Principal', 'Event adj.', 'Closing liability',
                                 'Opening ROU', 'Depreciation', 'ROU adj.', 'Closing ROU', 'Rounding'], stretch_last=False)
        self.table.itemSelectionChanged.connect(self.on_select)
        split.addWidget(self.table)
        right = QWidget(); rl = QVBoxLayout(right)
        rl.addWidget(QLabel('Journals for the selected row'))
        self.jt = make_table(['Account', 'Tally ledger', 'Debit', 'Credit', 'Memo'])
        rl.addWidget(self.jt, 1)
        rl.addWidget(QLabel('Trace to inputs'))
        self.trace = QPlainTextEdit(); self.trace.setReadOnly(True); rl.addWidget(self.trace, 1)
        split.addWidget(right); split.setStretchFactor(0, 3); split.setStretchFactor(1, 2)
        self.tabs.addTab(split, 'Schedule and journals')
        init = QWidget(); il = QVBoxLayout(init)
        self.init_text = QPlainTextEdit(); self.init_text.setReadOnly(True); self.init_text.setMaximumHeight(130)
        il.addWidget(self.init_text)
        self.pv = make_table(['Payment date', 'Kind', 'Amount', 'Days from commencement', 'Discount factor', 'Present value'])
        il.addWidget(self.pv, 1)
        self.tabs.addTab(init, 'Initial measurement (PV)')
        self.tl = None

    def refresh(self):
        ref = self.win.ref
        self.table.setRowCount(0); self.jt.setRowCount(0); self.trace.clear(); self.pv.setRowCount(0); self.init_text.clear()
        if not ref:
            return
        ok, tl = guarded(self, self.win.store.timeline, ref)
        if not ok:
            return
        self.tl = tl
        rows = [[r.row_no, f'V{r.version}', r.start, r.end, r.days, r.open_liab, r.interest, r.payment, r.principal, r.adjustment, r.close_liab,
                 r.open_rou, r.depreciation, r.rou_adjustment, r.close_rou, r.rounding_adj] for r in tl.rows]
        colors = {i: '#fff4d6' for i, r in enumerate(tl.rows) if r.kind == 'event'}
        fill_table(self.table, rows, num_cols=(5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15), colors=colors)
        self.init_text.setPlainText('\n'.join(tl.initial.get('trace', [])) + ('\n' + '\n'.join(tl.warnings) if tl.warnings else ''))
        fill_table(self.pv, [[p['date'], p['kind'], p['amount'], p['days'], f"{p['discount_factor']:.8f}", p['pv']] for p in tl.pv_lines], num_cols=(2, 5))

    def on_select(self):
        r = self.table.currentRow()
        if self.tl is None or r < 0 or r >= len(self.tl.rows):
            return
        row = self.tl.rows[r]
        amap = self.win.store.get_setting('account_map')
        lines = []
        for j in self.tl.journals:
            if j.row_no == row.row_no or (row.kind == 'event' and j.date == row.start and j.source in ('REASSESS', 'MODIFICATION', 'TERMINATION') and j.version == row.version):
                for (a, led, d, c, m) in journal_rows(j, amap):
                    lines.append([a, led, d, c, f'{j.ref}  {m}'])
        fill_table(self.jt, lines, num_cols=(2, 3))
        tr = [f'{k}: {v}' for k, v in row.trace.items()]
        for j in self.tl.journals:
            if j.row_no == row.row_no and j.trace and j.source not in ('INTEREST', 'PAYMENT', 'DEPRECIATION'):
                tr += j.trace
        self.trace.setPlainText('\n\n'.join(tr) or 'No amounts on this row.')
