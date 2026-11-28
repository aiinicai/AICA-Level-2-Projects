"""Dashboard: purchase and reconciliation figures from real records only (no sample data)."""
from __future__ import annotations

from datetime import date

from PySide6.QtCharts import (QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QHorizontalBarSeries,
                              QValueAxis)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from ipt.core.money import format_inr
from ipt.core.states import state_name
from ipt.ui.helpers import muted, title
from ipt.ui.pages.base import BasePage
from ipt.ui.pages.recon import fy_months, nice


def _card(caption: str) -> tuple[QFrame, QLabel]:
    f = QFrame(); f.setObjectName("Card")
    lay = QVBoxLayout(f)
    cap = QLabel(caption); cap.setObjectName("Muted")
    val = QLabel("-"); val.setObjectName("CardValue")
    lay.addWidget(cap); lay.addWidget(val)
    return f, val


def _chart(title_text: str) -> tuple[QChart, QChartView]:
    c = QChart()
    c.setTitle(title_text)
    c.legend().setVisible(False)
    c.setBackgroundRoundness(6)
    v = QChartView(c)
    v.setRenderHint(QPainter.Antialiasing)
    v.setMinimumHeight(260)
    return c, v


class DashboardPage(BasePage):
    title_text = "Dashboard"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Dashboard"))
        self.info = muted("")
        self.layout_.addWidget(self.info)
        bar = QHBoxLayout()
        self.source = QComboBox()
        self.source.addItem("Tally books (purchase register)", "books")
        self.source.addItem("IPT invoices", "ipt")
        self.month = QComboBox()
        self.supplier = QLineEdit()
        self.supplier.setPlaceholderText("Filter supplier / GSTIN")
        for w in (muted("Figures from"), self.source, muted("Month"), self.month, self.supplier):
            bar.addWidget(w)
        bar.addStretch(1)
        self.layout_.addLayout(bar)
        grid = QGridLayout()
        cards = [("Documents", "docs"), ("Suppliers", "sups"), ("Taxable value", "taxable"), ("GST", "tax"),
                 ("Invoice value", "total"), ("ITC in books", "itc_b"), ("ITC in GSTR-2B", "itc_2b"),
                 ("Open reconciliation items", "open")]
        self.v: dict[str, QLabel] = {}
        for i, (cap, key) in enumerate(cards):
            f, lbl = _card(cap)
            self.v[key] = lbl
            grid.addWidget(f, i // 4, i % 4)
        self.layout_.addLayout(grid)
        charts = QHBoxLayout()
        self.c_month, v1 = _chart("Taxable value by month")
        self.c_sup, v2 = _chart("Top 5 suppliers (taxable)")
        self.c_recon, v3 = _chart("Reconciliation status")
        for v in (v1, v2, v3):
            charts.addWidget(v, 1)
        self.layout_.addLayout(charts, 1)
        self.empty = muted("")
        self.layout_.addWidget(self.empty)
        self.source.currentIndexChanged.connect(self._load)
        self.month.currentIndexChanged.connect(self._load)
        self.supplier.returnPressed.connect(self._load)

    def refresh(self) -> None:
        cid, fid = self.s.ctx.company_id, self.s.ctx.fy_id
        company = self.s.companies.get_company(cid) if cid else None
        if company is None:
            self.info.setText("No company selected. Add one under Company Settings.")
            for lbl in self.v.values():
                lbl.setText("-")
            return
        fy = next((f for f in self.s.companies.list_fys(company.id) if f.id == fid), None)
        self.info.setText(f"{company.name}  |  FY {fy.label if fy else '-'}  |  GSTIN: {company.gstin or 'Not registered'}"
                          f"  |  State: {company.state_code} {state_name(company.state_code)}  |  "
                          f"Tally company: {company.tally_company_name or 'not set'}")
        self.month.blockSignals(True)
        cur = self.month.currentData()
        self.month.clear()
        self.month.addItem("Whole year", None)
        for m in (fy_months(fy) if fy else []):
            self.month.addItem(f"{m:%b %Y}", m)
        self.month.setCurrentIndex(max(0, self.month.findData(cur)))
        self.month.blockSignals(False)
        self._load()

    def _range(self):
        m = self.month.currentData()
        if m is None:
            return None, None
        nxt = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        return m, date.fromordinal(nxt.toordinal() - 1)

    def _load(self) -> None:
        if not self.s.ctx.fy_id:
            return
        start, end = self._range()
        k = self.s.reports.kpis(self.source.currentData(), start, end, self.supplier.text())
        self.v["docs"].setText(str(k["documents"]))
        self.v["sups"].setText(str(k["suppliers"]))
        self.v["taxable"].setText(format_inr(k["taxable"]))
        self.v["tax"].setText(format_inr(k["tax"]))
        self.v["total"].setText(format_inr(k["total"]))
        self.v["itc_b"].setText(format_inr(k["itc_books"]))
        self.v["itc_2b"].setText(format_inr(k["itc_2b"]))
        self.v["open"].setText(str(sum(v for s, v in k["recon"].items() if s != "MATCHED")))
        self._bar(self.c_month, list(k["months"].keys()), [float(v[0]) for v in k["months"].values()], "#2563eb")
        self._hbar(self.c_sup, [n[:28] for n, _ in reversed(k["top_suppliers"])],
                   [float(v) for _, v in reversed(k["top_suppliers"])])
        self._recon(k["recon"])
        src = "purchase register" if self.source.currentData() == "books" else "IPT invoices"
        self.empty.setText("" if k["documents"] else f"No {src} for this selection yet. Load them under "
                           f"{'GST → Purchase Register' if src == 'purchase register' else 'Invoice Processing'}.")

    @staticmethod
    def _reset(chart: QChart) -> None:
        chart.removeAllSeries()
        for ax in chart.axes():
            chart.removeAxis(ax)

    def _bar(self, chart: QChart, cats: list[str], vals: list[float], colour: str) -> None:
        self._reset(chart)
        if not cats:
            return
        st = QBarSet("Taxable")
        st.append(vals)
        st.setColor(QColor(colour))
        series = QBarSeries()
        series.append(st)
        chart.addSeries(series)
        ax = QBarCategoryAxis()
        ax.append(cats)
        ay = QValueAxis()
        ay.setLabelFormat("%.0f")
        ay.setMin(0)
        chart.addAxis(ax, Qt.AlignBottom)
        chart.addAxis(ay, Qt.AlignLeft)
        series.attachAxis(ax)
        series.attachAxis(ay)

    def _hbar(self, chart: QChart, cats: list[str], vals: list[float]) -> None:
        self._reset(chart)
        if not cats:
            return
        st = QBarSet("Taxable")
        st.append(vals)
        st.setColor(QColor("#0d9488"))
        series = QHorizontalBarSeries()
        series.append(st)
        chart.addSeries(series)
        ay = QBarCategoryAxis()
        ay.append(cats)
        ax = QValueAxis()
        ax.setLabelFormat("%.0f")
        ax.setMin(0)
        chart.addAxis(ay, Qt.AlignLeft)
        chart.addAxis(ax, Qt.AlignBottom)
        series.attachAxis(ax)
        series.attachAxis(ay)

    def _recon(self, counts: dict[str, int]) -> None:
        self._reset(self.c_recon)
        if not counts:
            self.c_recon.setTitle("Reconciliation status (not run yet)")
            return
        self.c_recon.setTitle("Reconciliation status (latest run)")
        series = QHorizontalBarSeries()
        cats = []
        st = QBarSet("Documents")
        for s_, n in reversed(list(counts.items())):
            cats.append(nice(s_))
            st.append(n)
        st.setColor(QColor("#f59e0b"))
        series.append(st)
        self.c_recon.addSeries(series)
        ay = QBarCategoryAxis()
        ay.append(cats)
        ax = QValueAxis()
        ax.setLabelFormat("%d")
        ax.setMin(0)
        top = max(counts.values())
        ax.setMax(top)
        ax.setTickCount(min(top, 5) + 1)
        self.c_recon.addAxis(ay, Qt.AlignLeft)
        self.c_recon.addAxis(ax, Qt.AlignBottom)
        series.attachAxis(ax)
        series.attachAxis(ay)
