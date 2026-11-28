"""ITC Analysis: ITC in books vs GSTR-2B per document, with the user's eligibility review (never automatic)."""
from __future__ import annotations

import calendar
from decimal import Decimal
from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout)

from ipt.core.money import format_inr
from ipt.core.permissions import PermissionDenied, has_permission
from ipt.services.recon.recon_service import ELIGIBILITY, ITC_BANNER, ReconError
from ipt.ui.helpers import error, fill_table, info, make_table, muted, selected_id, title
from ipt.ui.pages.base import BasePage
from ipt.ui.pages.recon import nice


class ReviewDialog(QDialog):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"ITC review – {item['doc_no']}")
        f = QFormLayout(self)
        f.addRow(muted(f"{item['supplier']} ({item['gstin']})  ·  ITC in books {format_inr(item['itc_books'])}  ·  "
                       f"in GSTR-2B {format_inr(item['itc_2b'])}  ·  2B says ITC available: "
                       f"{item['itc_available_2b'] or '—'}"))
        self.elig = QComboBox()
        self.elig.addItems(ELIGIBILITY)
        self.elig.setCurrentText(item["eligibility"])
        self.reason = QLineEdit(item["reason"])
        self.action = QLineEdit(item["action_taken"])
        self.remarks = QPlainTextEdit(item["remarks"])
        f.addRow("Eligibility (your decision)", self.elig)
        f.addRow("Reason", self.reason)
        f.addRow("Action taken", self.action)
        f.addRow("Remarks", self.remarks)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)


def _month_name(period: str) -> str:
    return f"{calendar.month_name[int(period[5:])]} {period[:4]}"


class Gstr3bDialog(QDialog):
    """GSTR-3B Table 4 working for one month: the table, the bills to check, and an Excel export."""

    def __init__(self, services, parent=None):
        super().__init__(parent)
        from ipt.services.recon.gstr3b import DISCLAIMER, GROUPS, HEADS
        self.s, self.groups, self.heads = services, GROUPS, HEADS
        self.setWindowTitle("GSTR-3B ITC working (Table 4)")
        self.resize(1100, 720)
        lay = QVBoxLayout(self)
        banner = QLabel("⚠ " + DISCLAIMER)
        banner.setWordWrap(True)
        banner.setStyleSheet("background:#fef3c7; color:#78350f; padding:8px; border-radius:6px;")
        lay.addWidget(banner)
        bar = QHBoxLayout()
        self.period = QComboBox()
        for per in services.recon.gstr3b_periods():
            self.period.addItem(_month_name(per), per)
        self.btn_export = QPushButton("Export to Excel…")
        self.btn_export.setObjectName("Primary")
        bar.addWidget(QLabel("Return period"))
        bar.addWidget(self.period)
        bar.addStretch(1)
        bar.addWidget(self.btn_export)
        lay.addLayout(bar)
        self.warn = muted("")
        self.warn.setWordWrap(True)
        lay.addWidget(self.warn)
        self.lines = make_table(["Table", "Details", "IGST", "CGST", "SGST/UTGST", "Cess", "Total"])
        self.lines.setMinimumHeight(330)
        lay.addWidget(self.lines, 5)
        self.filter = QComboBox()
        self.filter.addItem("All bills to check", None)
        for k, v in GROUPS.items():
            self.filter.addItem(v, k)
        lay.addWidget(self.filter)
        self.bills = make_table(["List", "Supplier", "GSTIN", "Document", "Date", "Type", "Tax", "Note"])
        lay.addWidget(self.bills, 3)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        lay.addWidget(close)
        self.w = None
        self.period.currentIndexChanged.connect(self._load)
        self.filter.currentIndexChanged.connect(self._show_bills)
        self.btn_export.clicked.connect(self._export)
        self._load()

    def _load(self) -> None:
        per = self.period.currentData()
        self.btn_export.setEnabled(per is not None)
        if per is None:
            self.warn.setText("No GSTR-2B loaded yet. Upload GSTR-2B (and fetch the purchase register) first.")
            fill_table(self.lines, [], sortable=False)
            fill_table(self.bills, [])
            return
        try:
            self.w = self.s.recon.gstr3b_working(per)
        except (ReconError, PermissionDenied) as e:
            error(self, str(e))
            return
        self.warn.setText("  ".join("⚠ " + m for m in self.w.warnings) or
                          "4(A) is what GSTR-2B carries; 4(B) and 4(C) are suggestions from the lists below.")
        fill_table(self.lines, [[ln.code, ln.label] + [format_inr(ln.amounts[h]) for h in self.heads] +
                                [format_inr(sum(ln.amounts.values(), Decimal("0")))] for ln in self.w.lines],
                   sortable=False)                # keep the order of Table 4
        self._show_bills()

    def _show_bills(self) -> None:
        if self.w is None:
            return
        g = self.filter.currentData()
        shown = [b for b in self.w.bills if g is None or b.group == g]
        fill_table(self.bills, [[self.groups[b.group], b.supplier, b.gstin, b.doc_no,
                                 b.doc_date.strftime("%d-%m-%Y") if b.doc_date else "", b.doc_type,
                                 format_inr(sum(b.amounts.values(), Decimal("0"))), b.note] for b in shown],
                   sortable=False)

    def _export(self) -> None:
        per = self.period.currentData()
        path, _ = QFileDialog.getSaveFileName(self, "GSTR-3B ITC working", f"GSTR3B_ITC_working_{per}.xlsx",
                                              "Excel (*.xlsx)")
        if not path:
            return
        try:
            self.s.recon.export_gstr3b(per, Path(path))
        except (ReconError, PermissionDenied) as e:
            error(self, str(e))
            return
        info(self, f"Saved {path}\n\nSheet 1: Table 4 working. Sheet 2: every bill to check before filing.")


class ItcPage(BasePage):
    title_text = "ITC Analysis"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("ITC Analysis"))
        banner = QLabel("⚠ " + ITC_BANNER)
        banner.setWordWrap(True)
        banner.setStyleSheet("background:#fef3c7; color:#78350f; padding:8px; border-radius:6px;")
        self.layout_.addWidget(banner)
        bar = QHBoxLayout()
        self.filter = QComboBox()
        self.filter.addItem("All documents", None)
        for e in ELIGIBILITY:
            self.filter.addItem(e, e)
        self.btn_review = QPushButton("Review selected…")
        self.btn_review.setObjectName("Primary")
        self.btn_3b = QPushButton("GSTR-3B working…")
        bar.addWidget(self.filter)
        bar.addWidget(self.btn_review)
        bar.addWidget(self.btn_3b)
        bar.addStretch(1)
        self.totals = muted("")
        bar.addWidget(self.totals)
        self.layout_.addLayout(bar)
        self.table = make_table(["Supplier", "GSTIN", "Document", "Date", "Type", "Recon status", "ITC in books",
                                 "ITC in 2B", "Difference", "2B: ITC available", "Timing / note", "Eligibility", "Reason",
                                 "Action taken", "Reviewed by"])
        self.layout_.addWidget(self.table, 1)
        self.layout_.addWidget(muted("Figures come from the latest reconciliation run. Run it again after loading new "
                                     "GSTR-2B or Tally data."))
        self.filter.currentIndexChanged.connect(self.refresh)
        self.btn_review.clicked.connect(self._review)
        self.btn_3b.clicked.connect(lambda: Gstr3bDialog(self.s, self).exec())
        self.table.doubleClicked.connect(lambda _: self._review())
        self.items: list[dict] = []

    def refresh(self) -> None:
        role = self.s.ctx.user.role if self.s.ctx.user else None
        self.btn_review.setEnabled(has_permission(role, "recon.edit"))
        self.items = self.s.recon.itc_rows() if self.s.ctx.fy_id else []
        f = self.filter.currentData()
        shown = [x for x in self.items if f is None or x["eligibility"] == f]
        fill_table(self.table, [[x["supplier"], x["gstin"], x["doc_no"],
                                 x["doc_date"].strftime("%d-%m-%Y") if x["doc_date"] else "", x["doc_type"],
                                 nice(x["status"]), format_inr(x["itc_books"]), format_inr(x["itc_2b"]),
                                 format_inr(x["difference"]), x["itc_available_2b"], x["timing"], x["eligibility"],
                                 x["reason"],
                                 x["action_taken"], x["reviewed_by"]] for x in shown], [x["row_id"] for x in shown])
        tb = sum((x["itc_books"] or Decimal("0")) for x in shown)
        t2 = sum((x["itc_2b"] or Decimal("0")) for x in shown)
        self.totals.setText(f"ITC in books {format_inr(tb)} · in GSTR-2B {format_inr(t2)} · difference "
                            f"{format_inr(t2 - tb)}")

    def _review(self) -> None:
        rid = selected_id(self.table)
        item = next((x for x in self.items if x["row_id"] == rid), None)
        if item is None:
            error(self, "Select a document")
            return
        dlg = ReviewDialog(item, self)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            self.s.recon.save_itc_review(rid, dlg.elig.currentText(), dlg.reason.text(), dlg.remarks.toPlainText(),
                                         dlg.action.text())
        except (ReconError, PermissionDenied) as e:
            error(self, str(e))
        self.refresh()
