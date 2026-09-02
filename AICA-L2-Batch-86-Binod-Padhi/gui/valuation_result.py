"""
gui/valuation_result.py
Displays the full "PROPERTY ANALYSIS" verdict screen (spec section 19),
with supporting charts and a report-generation action.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QGroupBox,
    QPushButton, QScrollArea, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from gui.charts import (
    MplCanvas, price_vs_fair_value_chart, rent_range_chart, yield_comparison_chart,
)

VERDICT_COLORS = {
    "UNDERPRICED": ("#2E7D32", "🟢"),
    "FAIRLY PRICED": ("#1565C0", "🔵"),
    "MODERATELY OVERPRICED": ("#EF6C00", "🟠"),
    "SIGNIFICANTLY OVERPRICED": ("#C62828", "🔴"),
}


def _stat_label(title, value):
    box = QVBoxLayout()
    t = QLabel(title); t.setStyleSheet("color: #666; font-size: 11px;")
    v = QLabel(value); v.setFont(QFont("Arial", 13, QFont.Weight.Bold))
    box.addWidget(t); box.addWidget(v)
    w = QWidget(); w.setLayout(box)
    return w


def fmt_inr(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"
    if value >= 1_00_00_000:
        return f"₹{value/1_00_00_000:.2f} Cr"
    if value >= 1_00_000:
        return f"₹{value/1_00_000:.2f} L"
    return f"₹{value:,.0f}"


class ValuationResultScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.current_context = None  # stores last (property_input, city_name, valuation_output) for reports
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        content = QWidget(); scroll.setWidget(content)
        self.layout_ = QVBoxLayout(content)

        self.header = QLabel("PROPERTY ANALYSIS")
        self.header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.layout_.addWidget(self.header)

        self.location_label = QLabel("")
        self.property_label = QLabel("")
        self.layout_.addWidget(self.location_label)
        self.layout_.addWidget(self.property_label)

        self.verdict_box = QGroupBox("Valuation Verdict")
        self.verdict_layout = QVBoxLayout(self.verdict_box)
        self.verdict_label = QLabel("")
        self.verdict_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.premium_label = QLabel("")
        self.negotiation_label = QLabel("")
        self.confidence_label = QLabel("")
        for w in (self.verdict_label, self.premium_label, self.negotiation_label, self.confidence_label):
            self.verdict_layout.addWidget(w)
        self.layout_.addWidget(self.verdict_box)

        stats_box = QGroupBox("Key Figures")
        self.stats_grid = QGridLayout(stats_box)
        self.layout_.addWidget(stats_box)

        charts_row = QHBoxLayout()
        self.chart1 = MplCanvas(); self.chart2 = MplCanvas(); self.chart3 = MplCanvas()
        for c in (self.chart1, self.chart2, self.chart3):
            charts_row.addWidget(c)
        self.layout_.addLayout(charts_row)

        notes_box = QGroupBox("Methodology & Data Notes")
        notes_layout = QVBoxLayout(notes_box)
        self.methodology_label = QLabel("")
        self.methodology_label.setWordWrap(True)
        self.sources_label = QLabel("")
        self.sources_label.setWordWrap(True)
        notes_layout.addWidget(self.methodology_label)
        notes_layout.addWidget(self.sources_label)
        self.layout_.addWidget(notes_box)

        self.disclaimer_label = QLabel("")
        self.disclaimer_label.setWordWrap(True)
        self.disclaimer_label.setStyleSheet("color: #777; font-size: 10px; font-style: italic;")
        self.layout_.addWidget(self.disclaimer_label)

        btn_row = QHBoxLayout()
        self.report_word_btn = QPushButton("Export Word Report")
        self.report_pdf_btn = QPushButton("Export PDF Report")
        self.report_excel_btn = QPushButton("Export Excel Report")
        btn_row.addWidget(self.report_word_btn)
        btn_row.addWidget(self.report_pdf_btn)
        btn_row.addWidget(self.report_excel_btn)
        self.layout_.addLayout(btn_row)

        self.report_word_btn.clicked.connect(lambda: self._export("word"))
        self.report_pdf_btn.clicked.connect(lambda: self._export("pdf"))
        self.report_excel_btn.clicked.connect(lambda: self._export("excel"))

        self.layout_.addStretch()

    def display(self, property_input, city_name, valuation_output, locality_name="", db=None):
        from config import DISCLAIMER
        self.current_context = (property_input, city_name, valuation_output, locality_name)
        result = valuation_output["result"]

        self.location_label.setText(f"<b>Location:</b> {locality_name}, {city_name}")
        self.property_label.setText(
            f"<b>Property:</b> {property_input.bhk} BHK {property_input.property_type} · "
            f"{property_input.builtup_area:.0f} sqft"
        )

        color, icon = VERDICT_COLORS.get(result.verdict, ("#000", ""))
        self.verdict_label.setText(f"{icon} {result.verdict}")
        self.verdict_label.setStyleSheet(f"color: {color};")
        self.premium_label.setText(
            f"Estimated Premium/Discount vs Fair Value: {result.premium_pct:+.1f}%"
        )
        nudge_low = result.fair_value_low
        nudge_high = result.fair_value_high
        self.negotiation_label.setText(
            f"Suggested Negotiation Range: {fmt_inr(nudge_low)} – {fmt_inr(nudge_high)}"
        )
        self.confidence_label.setText(f"Confidence: {result.confidence_pct:.0f}%")

        # Clear and repopulate stats grid
        while self.stats_grid.count():
            item = self.stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = [
            ("Asking Price", fmt_inr(property_input.asking_price)),
            ("Estimated Fair Value", f"{fmt_inr(result.fair_value_low)} – {fmt_inr(result.fair_value_high)}"),
            ("Expected Market Rent", f"₹{result.market_rent_low:,.0f} – ₹{result.market_rent_high:,.0f}/mo"),
            ("Gross Rental Yield", f"{result.gross_yield:.2f}%"),
            ("Net Rental Yield", f"{result.net_yield:.2f}%"),
            ("Price-to-Rent Ratio", f"{result.price_to_rent:.1f} years"),
            ("Investment Score", f"{result.investment_score:.0f}/100 ({result.investment_score_label})"),
            ("Comparable Properties Used", f"{result.n_comparables}"),
        ]
        for i, (title, value) in enumerate(stats):
            self.stats_grid.addWidget(_stat_label(title, value), i // 4, i % 4)

        price_vs_fair_value_chart(self.chart1, property_input.asking_price,
                                   result.fair_value_low or 0, result.fair_value_high or 0)
        rent_range_chart(self.chart2, result.market_rent_low, result.market_rent_median, result.market_rent_high)
        yield_comparison_chart(self.chart3, result.gross_yield,
                                (valuation_output["rent_stats"].get("median") or 0) and result.gross_yield)

        self.methodology_label.setText(f"<b>Methodology:</b> {result.methodology_notes}")
        self.sources_label.setText(
            f"<b>Data sources used:</b> {', '.join(valuation_output['sources']) if valuation_output['sources'] else 'None (insufficient data — import market data first)'}"
        )
        self.disclaimer_label.setText(DISCLAIMER)

    def _export(self, fmt):
        if not self.current_context:
            QMessageBox.information(self, "No analysis yet", "Run a valuation first.")
            return
        property_input, city_name, valuation_output, locality_name = self.current_context
        ext = {"word": "docx", "pdf": "pdf", "excel": "xlsx"}[fmt]
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", f"property_report.{ext}", f"*.{ext}")
        if not path:
            return
        try:
            if fmt == "word":
                from reports.word_report import generate_word_report
                generate_word_report(path, property_input, city_name, locality_name, valuation_output)
            elif fmt == "pdf":
                from reports.pdf_report import generate_pdf_report
                generate_pdf_report(path, property_input, city_name, locality_name, valuation_output)
            else:
                from reports.excel_report import generate_excel_report
                generate_excel_report(path, property_input, city_name, locality_name, valuation_output)
            QMessageBox.information(self, "Report generated", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Report generation failed", str(e))
