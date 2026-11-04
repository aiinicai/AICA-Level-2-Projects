# -*- coding: utf-8 -*-
"""
PyQt5 user interface for "Second hand vessel valuation".

Inputs are arranged in logical order across eight tabs:
  1 Vessel & dates -> 2 Acquisition -> 3 Operations & revenue -> 4 Running costs
  -> 5 Dry-docking -> 6 Financing -> 7 Exit & scrap -> 8 Decision criteria
"""
import json
import os
import sys
import traceback

from PyQt5.QtCore import QDate, Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from ship_model import (
    APP_TITLE, DD_SLOTS, DEFAULT_INPUTS, PAYMENT_FREQ, TCE_LABELS, TCE_SLOTS, VESSEL_TYPES,
    ModelError, build_html, preview, run_model, safe_filename,
)

OUTPUT_FOLDER = "Ship_Analysis_Output"

SPIN_CFG = {
    "usd": dict(dec=0, lo=0, hi=1e12, step=10000, prefix="USD ", group=True),
    "usd_day": dict(dec=0, lo=0, hi=1e7, step=100, prefix="USD ", suffix=" / day", group=True),
    "tonnes": dict(dec=0, lo=0, hi=1e6, step=100, suffix=" t", group=True),
    "pct": dict(dec=2, lo=0, hi=100, step=0.25, suffix=" %"),
    "pct_signed": dict(dec=2, lo=-100, hi=500, step=0.25, suffix=" %"),
    "years": dict(dec=2, lo=0, hi=50, step=0.5, suffix=" years"),
    "days": dict(dec=1, lo=0, hi=365, step=1, suffix=" days"),
    "ratio": dict(dec=2, lo=0, hi=10, step=0.05, suffix=" x"),
    "int": dict(integer=True, lo=0, hi=600, step=1, suffix=" months"),
    "count": dict(integer=True, lo=0, hi=20, step=1, suffix=""),
}

GRADIENTS = [
    ("#7c3aed", "#a855f7"), ("#0ea5e9", "#22d3ee"), ("#f97316", "#facc15"),
    ("#ec4899", "#f43f5e"), ("#10b981", "#84cc16"), ("#6366f1", "#3b82f6"),
]

QSS = """
QWidget#root { background: #f4f0ff; }
QFrame#header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:0.5 #db2777, stop:1 #f59e0b);
    border-radius: 12px;
}
QLabel#title { color: #ffffff; font-size: 22px; font-weight: 700; background: transparent; }
QLabel#subtitle { color: #fdf4ff; font-size: 12px; background: transparent; }
QTabWidget::pane { border: 2px solid #c4b5fd; border-radius: 10px; background: #ffffff; }
QTabBar::tab {
    background: #ede9fe; color: #4c1d95; padding: 8px 14px; margin-right: 3px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600;
}
QTabBar::tab:selected { background: #7c3aed; color: #ffffff; }
QTabBar::tab:hover:!selected { background: #ddd6fe; }
QGroupBox {
    font-weight: 700; color: #3b0764; border: 1px solid #ddd6fe; border-radius: 10px;
    margin-top: 16px; padding: 14px 10px 10px 10px; background: #fdfcff;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left; left: 12px;
    padding: 2px 10px; background: #14b8a6; color: #ffffff; border-radius: 6px;
}
QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox {
    background: #ffffff; border: 1.5px solid #c4b5fd; border-radius: 6px;
    padding: 4px 6px; min-height: 24px; color: #1e1b4b;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1.5px solid #f97316; background: #fff7ed;
}
QCheckBox { color: #3b0764; font-weight: 600; }
QLabel#derived {
    background: #ecfeff; color: #0e7490; border: 1px solid #67e8f9;
    border-radius: 6px; padding: 4px 8px; font-weight: 600;
}
QPushButton { border-radius: 8px; padding: 9px 16px; color: #ffffff; font-weight: 700; border: none; }
QPushButton#primary { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #0ea5e9); }
QPushButton#secondary { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #ec4899); }
QPushButton#neutral { background: #475569; }
QFrame#panel { background: #ffffff; border-radius: 12px; border: 1px solid #ddd6fe; }
QTextEdit { background: #ffffff; border: 1px solid #ddd6fe; border-radius: 8px; color: #312e81; }
QStatusBar { color: #4c1d95; font-weight: 600; }
"""


def _build_spec():
    """Input layout: (tab title, [(group title, [(row label, [(key, kind), ...]), ...]), ...])."""
    tce_rows = [
        (TCE_LABELS[k - 1], [(f"tce{k}_months", "int"), (f"tce{k}_rate", "usd_day")])
        for k in range(1, TCE_SLOTS + 1)
    ]
    dd_rows = [
        (f"Future dry-dock {k} cost (USD)", [(f"dd_{k}_cost", "usd"), (f"@dd_{k}_date", "derived")])
        for k in range(1, DD_SLOTS + 1)
    ]
    return [
        ("1 - Vessel & Dates", [
            ("Vessel details", [
                ("Vessel name", [("vessel_name", "text")]),
                ("Vessel type", [("vessel_type", "vtype")]),
                ("Date of analysis", [("analysis_date", "date")]),
            ]),
            ("Key dates", [
                ("2. Expected date of purchase", [("purchase_date", "date")]),
                ("3. Date of delivery from yard", [("delivery_date", "date")]),
                ("4. Next dry-dock date (class records, cross-check)", [("next_drydock_date", "date")]),
                ("Age at purchase", [("@age", "derived")]),
                ("Remaining useful life (25 years less age)", [("@rul", "derived")]),
            ]),
        ]),
        ("2 - Acquisition", [
            ("General assumptions", [
                ("1. Purchase price", [("purchase_price", "usd")]),
                ("5. Light-weight tonnage (LWT)", [("lwt", "tonnes")]),
            ]),
            ("6. Extra costs", [
                ("6A. Working capital", [("working_capital", "usd")]),
                ("6B. Upfront finance cost (rate set in tab 6)", [("@upfront", "derived")]),
                ("6C. Legal / documentation fees", [("legal_fees", "usd")]),
                ("Total acquisition outlay", [("@uses", "derived")]),
            ]),
        ]),
        ("3 - Operations & Revenue", [
            ("Operating period & exit", [
                ("Operate for full remaining useful life?", [("use_full_life", "bool")]),
                ("Operating period if not full life", [("operating_years", "years")]),
                ("Maximum operating period (remaining useful life)", [("@rul_max", "derived")]),
                ("Operating months required", [("@op_months", "derived")]),
                ("Exit date", [("@exit_date", "derived")]),
            ]),
            ("Off-hire", [
                ("Off-hire days per annum", [("offhire_days", "days")]),
            ]),
            ("Revenue commissions (% of gross TCE revenue)", [
                ("Address commission", [("addr_comm_pct", "pct")]),
                ("Broker commission", [("broker_comm_pct", "pct")]),
            ]),
            ("1. Time charter equivalent (TCE) periods", tce_rows + [
                ("TCE months entered vs operating months", [("@tce_check", "derived")]),
            ]),
        ]),
        ("4 - Running Costs", [
            ("Ship manager", [
                ("Ship manager cost per day", [("mgr_cost_day", "usd_day")]),
                ("Escalation p.a.", [("mgr_escalation", "pct")]),
            ]),
            ("Insurance", [
                ("Insurance cost per day", [("ins_cost_day", "usd_day")]),
                ("Escalation p.a.", [("ins_escalation", "pct")]),
            ]),
        ]),
        ("5 - Dry-docking", [
            ("Dry-dock frequency (counted from delivery date)", [
                ("Standard interval while vessel is younger than threshold (years)", [("dd_std_interval", "years")]),
                ("Vessel age threshold (years)", [("dd_threshold_age", "years")]),
                ("Interval once vessel is older than threshold (years)", [("dd_alt_interval", "years")]),
            ]),
            ("Future dry-dock cost estimates (only dockings inside the operating period are costed)", dd_rows),
        ]),
        ("6 - Financing", [
            ("Capital structure", [
                ("Equity portion (% of purchase price)", [("equity_pct", "pct")]),
                ("Equity infusion", [("@equity", "derived")]),
                ("Debt portion (purchase price less equity)", [("@debt", "derived")]),
                ("6B. Upfront finance cost (% of purchase price)", [("upfront_fee_pct", "pct")]),
            ]),
            ("Loan terms", [
                ("Rate of interest p.a.", [("interest_rate", "pct")]),
                ("Loan tenure (years, cannot exceed operating period)", [("loan_tenure", "years")]),
                ("Balloon payment (% of debt, paid at maturity)", [("balloon_pct", "pct")]),
                ("Payment terms", [("payment_freq", "freq")]),
            ]),
        ]),
        ("7 - Exit & Scrap", [
            ("Scrap & depreciation", [
                ("Scrap rate (USD per LWT tonne)", [("scrap_rate", "usd")]),
                ("Scrap value (LWT x scrap rate)", [("@scrap", "derived")]),
            ]),
            ("Exit", [
                ("Exit premium / (discount) over book value", [("exit_premium", "pct_signed")]),
                ("S&P commission at exit (% of sale value)", [("sp_fee_pct", "pct")]),
            ]),
        ]),
        ("8 - Decision Criteria", [
            ("Investment criteria", [
                ("Target equity XIRR (hurdle)", [("target_irr", "pct")]),
                ("Minimum DSCR", [("min_dscr", "ratio")]),
            ]),
        ]),
    ]


SPEC = _build_spec()


def _f(p, key, fmt):
    return fmt(p[key]) if key in p else "-"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1450, 880)
        self._loading = False
        self.widgets = {}
        self.derived = {}
        self.kpi_values = {}

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.addWidget(self._header())

        body = QHBoxLayout()
        self.tabs = QTabWidget()
        for title, groups in SPEC:
            self.tabs.addTab(self._build_tab(groups), title)
        body.addWidget(self.tabs, 3)
        body.addWidget(self._results_panel(), 2)
        layout.addLayout(body, 1)
        layout.addLayout(self._button_bar())

        self.set_inputs(DEFAULT_INPUTS)
        self.statusBar().showMessage("Ready. Enter the inputs, then press Calculate & Generate Report.")

    # ------------------------------------------------------------ layout
    def _header(self):
        frame = QFrame()
        frame.setObjectName("header")
        lay = QVBoxLayout(frame)
        title = QLabel(APP_TITLE)
        title.setObjectName("title")
        sub = QLabel("Secondhand vessel acquisition - financial model  |  Equity XIRR, MOIC, payback, "
                     "ROI, DSCR and an HTML investment report saved to your output folder")
        sub.setObjectName("subtitle")
        lay.addWidget(title)
        lay.addWidget(sub)
        return frame

    def _build_tab(self, groups):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)
        for gtitle, rows in groups:
            box = QGroupBox(gtitle)
            form = QFormLayout(box)
            form.setHorizontalSpacing(18)
            form.setVerticalSpacing(8)
            for label, fields in rows:
                holder = QWidget()
                h = QHBoxLayout(holder)
                h.setContentsMargins(0, 0, 0, 0)
                for key, kind in fields:
                    h.addWidget(self._make(key, kind), 1)
                form.addRow(label, holder)
            lay.addWidget(box)
        lay.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _make(self, key, kind):
        if kind == "derived":
            lbl = QLabel("-")
            lbl.setObjectName("derived")
            self.derived[key] = lbl
            return lbl
        if kind == "text":
            w = QLineEdit()
            w.textChanged.connect(self.update_live)
        elif kind == "vtype":
            w = QComboBox()
            w.addItems(VESSEL_TYPES)
            w.currentIndexChanged.connect(self.update_live)
        elif kind == "freq":
            w = QComboBox()
            w.addItems(PAYMENT_FREQ)
            w.currentIndexChanged.connect(self.update_live)
        elif kind == "date":
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setDisplayFormat("dd-MMM-yyyy")
            w.dateChanged.connect(self.update_live)
        elif kind == "bool":
            w = QCheckBox("Yes - operate for the full remaining useful life")
            w.toggled.connect(self.update_live)
        else:
            cfg = SPIN_CFG[kind]
            if cfg.get("integer"):
                w = QSpinBox()
                w.setRange(int(cfg["lo"]), int(cfg["hi"]))
            else:
                w = QDoubleSpinBox()
                w.setDecimals(cfg["dec"])
                w.setRange(cfg["lo"], cfg["hi"])
            w.setSingleStep(cfg["step"])
            w.setPrefix(cfg.get("prefix", ""))
            w.setSuffix(cfg.get("suffix", ""))
            if cfg.get("group"):
                w.setGroupSeparatorShown(True)
            w.valueChanged.connect(self.update_live)
        self.widgets[key] = w
        return w

    def _results_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        title = QLabel("Results dashboard")
        title.setStyleSheet("font-size:16px; font-weight:700; color:#3b0764; background:transparent;")
        lay.addWidget(title)

        grid = QGridLayout()
        cards = [("irr", "Equity XIRR"), ("moic", "MOIC"), ("payback", "Payback period"),
                 ("roi", "ROI (annualised)"), ("dscr", "Minimum DSCR"), ("equity", "Equity invested")]
        for i, (key, text) in enumerate(cards):
            frame, value = self._card(text, GRADIENTS[i])
            self.kpi_values[key] = value
            grid.addWidget(frame, i // 2, i % 2)
        lay.addLayout(grid)

        self.verdict = QLabel("Run the model to see the investment verdict")
        self.verdict.setWordWrap(True)
        self.verdict.setAlignment(Qt.AlignCenter)
        self.verdict.setStyleSheet("padding:14px; border-radius:10px; background:#e0e7ff; "
                                   "color:#312e81; font-size:14px; font-weight:700;")
        lay.addWidget(self.verdict)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Model messages, checks and warnings appear here.")
        lay.addWidget(self.log, 1)
        return panel

    def _card(self, title, colors):
        frame = QFrame()
        frame.setObjectName("card")
        frame.setStyleSheet(
            "QFrame#card { border-radius:12px; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            f"stop:0 {colors[0]}, stop:1 {colors[1]}); }}")
        v = QVBoxLayout(frame)
        t = QLabel(title)
        t.setStyleSheet("color:#ffffff; font-size:12px; font-weight:600; background:transparent;")
        val = QLabel("-")
        val.setStyleSheet("color:#ffffff; font-size:20px; font-weight:800; background:transparent;")
        v.addWidget(t)
        v.addWidget(val)
        return frame, val

    def _button_bar(self):
        bar = QHBoxLayout()
        specs = [
            ("Calculate & Generate Report", "primary", self.on_calculate),
            ("Save Inputs", "secondary", self.save_inputs),
            ("Load Inputs", "secondary", self.load_inputs),
            ("Reset to Sample", "neutral", lambda: self.set_inputs(DEFAULT_INPUTS)),
            ("Open Output Folder", "neutral", self.open_output_folder),
        ]
        for text, obj, slot in specs:
            btn = QPushButton(text)
            btn.setObjectName(obj)
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        return bar

    # ------------------------------------------------------------ inputs
    @staticmethod
    def _read(w):
        if isinstance(w, QLineEdit):
            return w.text()
        if isinstance(w, QComboBox):
            return w.currentText()
        if isinstance(w, QDateEdit):
            return w.date().toString("yyyy-MM-dd")
        if isinstance(w, QCheckBox):
            return w.isChecked()
        return w.value()

    @staticmethod
    def _write(w, v):
        if isinstance(w, QLineEdit):
            w.setText(str(v))
        elif isinstance(w, QComboBox):
            w.setCurrentIndex(max(w.findText(str(v)), 0))
        elif isinstance(w, QDateEdit):
            w.setDate(QDate.fromString(str(v)[:10], "yyyy-MM-dd"))
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(v))
        elif isinstance(w, QSpinBox):
            w.setValue(int(round(float(v))))
        else:
            w.setValue(float(v))

    def get_inputs(self):
        return {key: self._read(w) for key, w in self.widgets.items()}

    def set_inputs(self, data):
        self._loading = True
        try:
            for key, w in self.widgets.items():
                if key in data:
                    self._write(w, data[key])
        finally:
            self._loading = False
        self.update_live()

    def update_live(self, *_):
        if self._loading or not self.derived:
            return
        if "use_full_life" in self.widgets and "operating_years" in self.widgets:
            self.widgets["operating_years"].setEnabled(not self.widgets["use_full_life"].isChecked())

        p = preview(self.get_inputs())

        # Operating period cannot exceed the remaining useful life: cap the input.
        if "rul" in p and "operating_years" in self.widgets:
            cap = min(50.0, max(0.0, round(p["rul"], 2)))
            w = self.widgets["operating_years"]
            if abs(w.maximum() - cap) > 1e-9:
                self._loading = True
                try:
                    w.setMaximum(cap)
                finally:
                    self._loading = False
        # Loan tenure cannot exceed the operating period: cap the input.
        if "op_years" in p and "loan_tenure" in self.widgets:
            tcap = min(50.0, max(0.0, round(p["op_years"], 2)))
            tw = self.widgets["loan_tenure"]
            if abs(tw.maximum() - tcap) > 1e-9:
                self._loading = True
                try:
                    tw.setMaximum(tcap)
                finally:
                    self._loading = False
        if "op_years" in p or "rul" in p:
            p = preview(self.get_inputs())

        def money(v):
            return f"USD {v:,.0f}"

        texts = {
            "@age": _f(p, "age", lambda v: f"{v:.2f} years"),
            "@rul": _f(p, "rul", lambda v: f"{v:.2f} years"),
            "@rul_max": _f(p, "rul", lambda v: f"{v:.2f} years"),
            "@op_months": _f(p, "op_months", lambda v: f"{v} months"),
            "@exit_date": _f(p, "exit_date", lambda v: f"{v:%d-%b-%Y}"),
            "@upfront": _f(p, "upfront", money),
            "@uses": _f(p, "uses", money),
            "@equity": _f(p, "equity", money),
            "@debt": _f(p, "debt", money),
            "@scrap": _f(p, "scrap", money),
        }
        dd_dates = p.get("dd_dates", [])
        for k in range(1, DD_SLOTS + 1):
            if "dd_dates" not in p:
                texts[f"@dd_{k}_date"] = "-"
            elif k <= len(dd_dates):
                d, age = dd_dates[k - 1]
                texts[f"@dd_{k}_date"] = f"{d:%d-%b-%Y} (vessel age {age:.1f} yrs)"
            else:
                texts[f"@dd_{k}_date"] = "Not in operating period"
        for key, text in texts.items():
            if key in self.derived:
                self.derived[key].setText(text)

        if "tce_months" in p and "op_months" in p and "@tce_check" in self.derived:
            ok = p["tce_months"] == p["op_months"]
            self.derived["@tce_check"].setText(
                f"{p['tce_months']} of {p['op_months']} months entered - " + ("OK" if ok else "MISMATCH"))
            self.derived["@tce_check"].setStyleSheet(
                "color:#047857; font-weight:700;" if ok else "color:#be123c; font-weight:700;")

    # ------------------------------------------------------------ actions
    def output_dir(self):
        base = os.path.dirname(os.path.abspath(__file__))
        folder = os.path.join(base, OUTPUT_FOLDER)
        os.makedirs(folder, exist_ok=True)
        return folder

    def on_calculate(self):
        inputs = self.get_inputs()
        try:
            res = run_model(inputs)
        except ModelError as exc:
            text = "\n".join("- " + e for e in exc.errors)
            self.log.setPlainText("The model cannot run yet:\n\n" + text)
            QMessageBox.warning(self, "Please review the inputs", "The model cannot run yet:\n\n" + text)
            return
        except Exception:
            QMessageBox.critical(self, "Unexpected error", traceback.format_exc())
            return

        try:
            doc = build_html(inputs, res)
            base = safe_filename(f"{inputs['vessel_name']} {int(round(inputs['purchase_price']))}")
            folder = self.output_dir()
            html_path = os.path.join(folder, base + ".html")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(doc)
            with open(os.path.join(folder, base + " - inputs.json"), "w", encoding="utf-8") as fh:
                json.dump(inputs, fh, indent=2)
        except Exception:
            QMessageBox.critical(self, "Report could not be saved", traceback.format_exc())
            return

        self.show_results(res)
        self.statusBar().showMessage("Report saved: " + html_path)
        QDesktopServices.openUrl(QUrl.fromLocalFile(html_path))

    def show_results(self, res):
        def pct(v):
            return "-" if v is None else f"{v * 100:.1f}%"

        self.kpi_values["irr"].setText(pct(res["irr"]))
        self.kpi_values["moic"].setText("-" if res["moic"] is None else f"{res['moic']:.2f}x")
        self.kpi_values["payback"].setText(
            "Not reached" if res["payback_years"] is None else f"{res['payback_years']:.2f} yrs")
        self.kpi_values["roi"].setText(pct(res["roi_annual"]))
        self.kpi_values["dscr"].setText("-" if res["min_dscr"] is None else f"{res['min_dscr']:.2f}x")
        self.kpi_values["equity"].setText(f"USD {res['total_outflows']:,.0f}")

        if res["viable"]:
            self.verdict.setText("VIABLE - returns meet the investment criteria")
            self.verdict.setStyleSheet("padding:14px; border-radius:10px; background:#d1fae5; "
                                       "color:#065f46; font-size:14px; font-weight:700;")
        else:
            self.verdict.setText("NOT VIABLE on the current assumptions")
            self.verdict.setStyleSheet("padding:14px; border-radius:10px; background:#ffe4e6; "
                                       "color:#9f1239; font-size:14px; font-weight:700;")

        lines = ["Investment criteria:"] + ["  - " + r for r in res["reasons"]]
        lines += ["", "Model checks:"]
        for c in res["checks"]:
            lines.append(("  [PASS] " if c["ok"] else "  [CHECK] ") + c["label"] + ": " + c["detail"])
        if res["warnings"]:
            lines += ["", "Warnings:"] + ["  - " + w for w in res["warnings"]]
        self.log.setPlainText("\n".join(lines))

    def save_inputs(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save inputs", os.path.join(self.output_dir(), "inputs.json"), "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.get_inputs(), fh, indent=2)
            self.statusBar().showMessage("Inputs saved: " + path)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def load_inputs(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load inputs", self.output_dir(), "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Load failed", str(exc))
            return
        self.set_inputs(data)
        self.statusBar().showMessage("Inputs loaded: " + path)

    def open_output_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_dir()))


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
