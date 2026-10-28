"""Results pages: risk dashboard, adjustment approval, computation preview, export, log."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                               QSplitter, QTabWidget, QVBoxLayout, QWidget)

from ..engine import ROWS
from ..mapping import fs_lines
from ..service import export_all
from . import widgets as W


# ======================================================================================================================
class RiskPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.state = win, win.state
        self._flags = []
        lay = QVBoxLayout(self)
        lay.addWidget(W.heading("Step 5 - Risk review"))
        lay.addWidget(W.hint("These are risk INDICATORS from account names, balances and ledger patterns - not conclusions. Record management's response and your own conclusion "
                             "against each; they flow into the Word report."))
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        # accounts tab
        acc = QWidget()
        al = QVBoxLayout(acc)
        top = QHBoxLayout()
        self.risk_filter = QComboBox()
        self.risk_filter.addItems(["All risk levels", "High", "Medium", "Low"])
        self.risk_filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(QLabel("Show"))
        top.addWidget(self.risk_filter)
        top.addStretch(1)
        al.addLayout(top)
        split = QSplitter(Qt.Vertical)
        self.table = W.make_table(["Risk", "Category", "Code", "Account", "Balance (AED)", "Status", "Proposed adj. (AED)"], stretch_col=3)
        self.table.itemSelectionChanged.connect(self.on_select)
        split.addWidget(self.table)
        det = QWidget()
        dl = QFormLayout(det)
        self.d_reason = QPlainTextEdit()
        self.d_reason.setReadOnly(True)
        self.d_reason.setMaximumHeight(110)
        self.d_mgmt, self.d_rev = QPlainTextEdit(), QPlainTextEdit()
        self.d_mgmt.setMaximumHeight(60)
        self.d_rev.setMaximumHeight(60)
        self.save = QPushButton("Save responses")
        self.save.clicked.connect(self.on_save)
        dl.addRow("Why flagged / implication / documents / GL references", self.d_reason)
        dl.addRow("Management response", self.d_mgmt)
        dl.addRow("Reviewer conclusion", self.d_rev)
        dl.addRow("", self.save)
        split.addWidget(det)
        split.setSizes([360, 260])
        al.addWidget(split, 1)
        self.tabs.addTab(acc, "Accounts")
        # GL tab
        gl = QWidget()
        gll = QVBoxLayout(gl)
        self.gl_note = QLabel("")
        self.gl_note.setWordWrap(True)
        self.gl_table = W.make_table(["Risk", "Date", "Reference", "Account", "Amount (AED)", "Narration", "Counterparty", "Tests triggered"], stretch_col=7)
        gll.addWidget(self.gl_note)
        gll.addWidget(self.gl_table, 1)
        self.tabs.addTab(gl, "GL transactions")
        self.state.analysed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        an = self.state.analysis
        self.table.setRowCount(0)
        self.gl_table.setRowCount(0)
        self._flags = []
        if not an:
            self.gl_note.setText(self.state.error or "Complete steps 1-3 first.")
            return
        sel = self.risk_filter.currentText()
        self._flags = [f for f in an.review.flags if sel.startswith("All") or f.risk == sel]
        W.fill_table(self.table, [[f.risk, f.category_label, f.code, f.name, W.money(f.amount_aed), f.status, W.money(f.proposed_adjustment) if f.proposed_adjustment else ""]
                                  for f in self._flags], colour_col=0, colours=W.RISK_COLOURS, right_cols=(4, 6))
        notes = list(an.review.notes)
        if not an.project.gl:
            notes.append("No GL loaded - transaction tests were not run.")
        self.gl_note.setText(" ".join(notes) or f"{len(an.review.txn_flags)} transaction(s) flagged.")
        W.fill_table(self.gl_table, [[t.risk, t.date, t.reference or t.line_id, f"{t.code} {t.name}", W.money(t.amount_aed), t.description, t.counterparty, "; ".join(t.tests)]
                                     for t in an.review.txn_flags], colour_col=0, colours=W.RISK_COLOURS, right_cols=(4,))

    def on_select(self):
        r = self.table.currentRow()
        if r < 0 or r >= len(self._flags):
            return
        f = self._flags[r]
        self.d_reason.setPlainText(f"{f.reason}\n\nPossible implication: {f.tax_implication}\n\nDocuments to request: {'; '.join(f.documents)}\n\n"
                                   f"GL references: {', '.join(f.gl_refs[:15]) or 'none'}")
        self.d_mgmt.setPlainText(f.mgmt_response)
        self.d_rev.setPlainText(f.reviewer_conclusion)

    def on_save(self):
        r = self.table.currentRow()
        if r < 0 or r >= len(self._flags):
            return
        f = self._flags[r]
        f.mgmt_response, f.reviewer_conclusion = self.d_mgmt.toPlainText(), self.d_rev.toPlainText()
        self.state.project.flag_responses[f.flag_id] = {"mgmt_response": f.mgmt_response, "reviewer_conclusion": f.reviewer_conclusion}
        self.state.project.log("Risk response saved", f.flag_id)
        self.state.mark_dirty()


# ======================================================================================================================
class AdjustmentsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.state = win, win.state
        self._adjs = []
        lay = QVBoxLayout(self)
        lay.addWidget(W.heading("Step 6 - Adjustments: propose, review and approve"))
        lay.addWidget(W.hint("Proposed adjustments are kept OUT of the computation until you confirm them. An adjustment with a blocking issue can be confirmed only with an "
                             "override note explaining why. Rejected adjustments stay on record but never enter the figures."))
        self.impact = QLabel("")
        self.impact.setWordWrap(True)
        lay.addWidget(self.impact)
        split = QSplitter(Qt.Vertical)
        self.table = W.make_table(["Status", "Computation row", "Description", "Amount (AED)", "Report status", "Blocking issue"], stretch_col=2)
        self.table.itemSelectionChanged.connect(self.on_select)
        split.addWidget(self.table)
        det = QWidget()
        dl = QFormLayout(det)
        self.d_info = QPlainTextEdit()
        self.d_info.setReadOnly(True)
        self.d_info.setMaximumHeight(120)
        self.amount = W.money_spin()
        self.support, self.reviewer = QLineEdit(), QLineEdit()
        self.mgmt, self.override = QPlainTextEdit(), QPlainTextEdit()
        self.mgmt.setMaximumHeight(50)
        self.override.setMaximumHeight(50)
        btns = QHBoxLayout()
        self.b_conf, self.b_rej, self.b_reset = QPushButton("Confirm"), QPushButton("Reject"), QPushButton("Reset to Proposed")
        self.b_conf.clicked.connect(lambda: self.decide("Confirmed"))
        self.b_rej.clicked.connect(lambda: self.decide("Rejected"))
        self.b_reset.clicked.connect(lambda: self.decide("Proposed"))
        for b in (self.b_conf, self.b_rej, self.b_reset):
            btns.addWidget(b)
        btns.addStretch(1)
        dl.addRow("Basis", self.d_info)
        dl.addRow("Amount (AED) - change only with a reason", self.amount)
        dl.addRow("Supporting reference (document name / ref)", self.support)
        dl.addRow("Reviewer", self.reviewer)
        dl.addRow("Management response", self.mgmt)
        dl.addRow("Override note (required to confirm a blocked item)", self.override)
        dl.addRow("", btns)
        split.addWidget(det)
        split.setSizes([320, 330])
        lay.addWidget(split, 1)
        self.state.analysed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        an = self.state.analysis
        keep = self.table.currentRow()
        self.table.setRowCount(0)
        self._adjs = []
        if not an:
            self.impact.setText(self.state.error or "Complete steps 1-3 first.")
            return
        self._adjs = list(an.adjs)
        pi = an.pending_impact()
        conf = [a for a in an.adjs if a.status == "Confirmed"]
        self.impact.setText(f"{len(conf)} confirmed (in the computation); {pi['count']} proposed awaiting a decision (illustrative effect if all confirmed: taxable income "
                            f"{pi['delta_taxable']:+,.0f} AED, tax {pi['delta_tax']:+,.0f} AED); {sum(1 for a in an.adjs if a.status == 'Rejected')} rejected.")
        W.fill_table(self.table, [[a.status, ROWS[a.row][2][:60], a.description, W.money(a.amount), a.report_status, a.blocking] for a in self._adjs],
                     colour_col=0, right_cols=(3,))
        if 0 <= keep < len(self._adjs):
            self.table.selectRow(keep)

    def current(self):
        r = self.table.currentRow()
        return self._adjs[r] if 0 <= r < len(self._adjs) else None

    def on_select(self):
        a = self.current()
        if not a:
            return
        self.d_info.setPlainText(f"{a.reason}\nRule: {a.rule_ref or '-'}   Category: {a.category}\nAccounts: {'; '.join((x[0] + ' ' + x[1]).strip() for x in a.accounts)}\n"
                                 f"Documents needed: {'; '.join(a.docs_needed) or '-'}\n" + (f"BLOCKING: {a.blocking}" if a.blocking else "No blocking issue recorded."))
        self.amount.setValue(a.amount)
        self.support.setText(a.support_ref)
        self.reviewer.setText(a.reviewer or self.state.project.settings.reviewer)
        self.mgmt.setPlainText(a.mgmt_response)
        self.override.setPlainText(a.override_note)

    def decide(self, status):
        a = self.current()
        if not a:
            return
        note = self.override.toPlainText().strip()
        if status == "Confirmed":
            if a.blocking and not note:
                W.warn(self, "Cannot confirm yet", f"This item is blocked:\n\n{a.blocking}\n\nObtain the evidence, or enter an override note explaining why it can be confirmed anyway.")
                return
            if not self.support.text().strip() and not note:
                if not W.ask(self, "No supporting reference", "No supporting reference has been entered. Confirm anyway?"):
                    return
        d = {"status": status, "reviewer": self.reviewer.text().strip(), "support_ref": self.support.text().strip(),
             "mgmt_response": self.mgmt.toPlainText().strip(), "override_note": note}
        if abs(self.amount.value() - a.auto_amount) > 0.005:
            d["amount"] = round(self.amount.value(), 2)
        self.state.project.decisions[a.adj_id] = d
        self.state.project.log("Adjustment decision", f"{a.adj_id}: {status}" + (f" amount {d['amount']:,.2f}" if "amount" in d else ""))
        self.state.mark_dirty()
        self.state.reanalyse()


# ======================================================================================================================
class ComputationPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.state = win, win.state
        lay = QVBoxLayout(self)
        lay.addWidget(W.heading("Step 7 - Computation, statements and checks (AED)"))
        self.banner = W.banner("", "#FDE9D9")
        lay.addWidget(self.banner)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self.t_comp = W.make_table(["Ref", "Description", "AED"], stretch_col=1)
        self.t_pl = W.make_table(["Profit and loss", "AED"], stretch_col=0)
        self.t_bs = W.make_table(["Balance sheet", "AED"], stretch_col=0)
        self.t_open = W.make_table(["Topic", "Item", "Status", "Documents"], stretch_col=1)
        self.t_chk = W.make_table(["ID", "Check", "Result", "Detail"], stretch_col=3)
        self.t_scn = W.make_table(["Option", "Deductions", "Additions", "Taxable income", "Tax payable"], stretch_col=0)
        for t, name in ((self.t_comp, "Computation"), (self.t_pl, "Profit and loss"), (self.t_bs, "Balance sheet"), (self.t_open, "Open items"),
                        (self.t_chk, "Reconciliation checks"), (self.t_scn, "Realisation-basis scenarios")):
            self.tabs.addTab(t, name)
        self.state.analysed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        an = self.state.analysis
        for t in (self.t_comp, self.t_pl, self.t_bs, self.t_open, self.t_chk, self.t_scn):
            t.setRowCount(0)
        if not an:
            self.banner.setText(self.state.error or "Complete steps 1-3 first.")
            return
        c = an.comp
        pend = sum(1 for a in an.adjs if a.status == "Proposed")
        self.banner.setText(f"DRAFT. Confirmed adjustments only. {pend} proposed adjustment(s) and {len(an.open_items)} open item(s) are outstanding; figures are preliminary.")
        rows = [["A", "Accounting net profit/(loss)", W.money(c.A)]]
        for sec, title in (("B", "Deductions / exempt income (confirmed)"), ("C", "Non-deductible expenses (confirmed)")):
            items = [(k, v) for k, v in c.rows.items() if ROWS[k][1] == sec and abs(v) > 0.005]
            for k, v in sorted(items, key=lambda kv: ROWS[kv[0]][0]):
                rows.append(["", f"   {ROWS[k][2][:90]}", W.money(v)])
            rows.append([sec, f"Total {title.lower()}", W.money(c.B if sec == 'B' else c.C)])
        if c.o_gain or c.o_loss:
            rows += [["", "   Previously unrealised gains realised", W.money(c.o_gain)], ["", "   Previously unrealised losses realised", W.money(-c.o_loss)]]
        rows += [["D", "Taxable income/(loss)", W.money(c.D)], ["", "   Tax losses utilised (cap 75%)", W.money(-(c.relief_cf + c.relief_group))], ["E", "Net taxable income/(loss)", W.money(c.E)],
                 ["", f"Tax at 0% band / 9% (basis: {c.basis})", W.money(c.tax_0 + c.tax_9)], ["", "   Foreign tax credit", W.money(-c.credit)], ["", "CORPORATE TAX PAYABLE (preliminary)", W.money(c.payable)],
                 ["", "Effective tax rate", f"{c.etr:.2%}" if c.etr is not None else "n/a"]]
        for n in c.notes:
            rows.append(["", "Note: " + n, ""])
        W.fill_table(self.t_comp, rows, right_cols=(2,))
        W.fill_table(self.t_pl, [[("    " if r.kind == "line" else "") + r.label, W.money(r.amount) if r.amount is not None else ""] for r in an.st.pl_rows], right_cols=(1,))
        W.fill_table(self.t_bs, [[("    " if r.kind == "line" else "") + r.label, W.money(r.amount) if r.amount is not None else ""] for r in an.st.bs_rows]
                     + [["Check: assets - (liabilities + equity)", W.money(an.st.bs_difference, 2)]], right_cols=(1,))
        W.fill_table(self.t_open, [[o["topic"], o["item"], o["status"], "; ".join(o.get("documents", []))] for o in an.open_items], colour_col=2)
        W.fill_table(self.t_chk, [[x.id, x.description, x.status, x.detail] for x in an.checks], colour_col=2)
        W.fill_table(self.t_scn, [[s["option"], W.money(s["deductions"]), W.money(s["additions"]), W.money(s["taxable_income"]), W.money(s["tax_payable"])] for s in an.scenarios],
                     right_cols=(1, 2, 3, 4))


# ======================================================================================================================
class ExportPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.state = win, win.state
        self._workers = []
        lay = QVBoxLayout(self)
        lay.addWidget(W.heading("Step 8 - Export"))
        lay.addWidget(W.hint("Creates the client computation workbook (your template, AED, only the sheets that apply), the internal review workbook, the Word tax-risk report "
                             "and the project file. Source files are never modified."))
        g = QGroupBox("Output")
        f = QFormLayout(g)
        self.out = QLineEdit()
        row = QHBoxLayout()
        row.addWidget(self.out, 1)
        b = QPushButton("Browse...")
        b.clicked.connect(self.browse)
        row.addWidget(b)
        w = QWidget()
        w.setLayout(row)
        f.addRow("Output folder", w)
        self.c_client, self.c_review = QCheckBox("Client computation workbook (.xlsx)"), QCheckBox("Internal review workbook (.xlsx)")
        self.c_report, self.c_proj = QCheckBox("Word tax-risk and review report (.docx)"), QCheckBox("Project file (.ctproj) - save and resume")
        for c in (self.c_client, self.c_review, self.c_report, self.c_proj):
            c.setChecked(True)
            f.addRow("", c)
        lay.addWidget(g)
        self.warn = W.banner("", "#FFF2CC")
        lay.addWidget(self.warn)
        r = QHBoxLayout()
        self.go = QPushButton("Export")
        self.go.clicked.connect(self.run)
        self.open_btn = QPushButton("Open output folder")
        self.open_btn.clicked.connect(self.open_folder)
        r.addWidget(self.go)
        r.addWidget(self.open_btn)
        r.addStretch(1)
        lay.addLayout(r)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)
        self.state.analysed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        an = self.state.analysis
        if not self.out.text():
            self.out.setText(self.state.project.settings.output_dir)
        self.go.setEnabled(an is not None)
        if not an:
            self.warn.setText(self.state.error or "Complete steps 1-3 first.")
            return
        msgs = []
        fails = [c for c in an.checks if c.status == "FAIL"]
        if fails:
            msgs.append(f"{len(fails)} reconciliation check(s) FAILED: " + "; ".join(c.id for c in fails))
        pend = sum(1 for a in an.adjs if a.status == "Proposed")
        if pend:
            msgs.append(f"{pend} proposed adjustment(s) are not confirmed and are NOT in the computation.")
        if an.open_items:
            msgs.append(f"{len(an.open_items)} open item(s) remain.")
        self.warn.setText("Before exporting: " + " ".join(msgs) + " Exports will be marked DRAFT." if msgs else "No outstanding issues recorded. Exports are still preliminary.")

    def browse(self):
        p = QFileDialog.getExistingDirectory(self, "Output folder", self.out.text() or str(Path.home()))
        if p:
            self.out.setText(p)
            self.state.project.settings.output_dir = p
            self.state.mark_dirty()

    def run(self):
        an = self.state.analysis
        out = self.out.text().strip()
        if not an or not out:
            W.warn(self, "Export", "Choose an output folder first.")
            return
        which = tuple(k for k, c in (("client", self.c_client), ("review", self.c_review), ("report", self.c_report), ("project", self.c_proj)) if c.isChecked())
        self.state.project.settings.output_dir = out
        self.win.busy("Exporting...")
        wk = W.Worker(export_all, an, out, which, parent=self)
        wk.done.connect(self.done)
        wk.failed.connect(lambda m: (self.win.idle(), self.log.appendPlainText("FAILED: " + m), W.warn(self, "Export failed", m)))
        self._workers.append(wk)
        wk.start()

    def done(self, res):
        self.win.idle()
        for k, v in res.items():
            self.log.appendPlainText(f"{k}: {v}")
        self.state.mark_dirty()
        W.info(self, "Export complete", "\n".join(f"{k}: {Path(v).name}" for k, v in res.items()))

    def open_folder(self):
        p = self.out.text().strip()
        if p and Path(p).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))


# ======================================================================================================================
class LogPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.state = win.state
        lay = QVBoxLayout(self)
        lay.addWidget(W.heading("Log and audit trail"))
        self.table = W.make_table(["Time", "Action", "Detail"], stretch_col=2)
        lay.addWidget(self.table, 1)
        self.warn = QPlainTextEdit()
        self.warn.setReadOnly(True)
        self.warn.setMaximumHeight(110)
        lay.addWidget(QLabel("Decision warnings from the last analysis"))
        lay.addWidget(self.warn)
        self.state.analysed.connect(self.refresh)
        self.state.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        W.fill_table(self.table, [[x["time"], x["action"], x["detail"]] for x in reversed(self.state.project.audit_log)])
        an = self.state.analysis
        self.warn.setPlainText("\n".join(an.warnings) if an else (self.state.error or ""))
