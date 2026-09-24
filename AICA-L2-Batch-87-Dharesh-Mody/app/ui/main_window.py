import json
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QTextEdit, QLineEdit, QComboBox,
    QSpinBox, QFormLayout, QGroupBox, QMessageBox, QSplitter, QPlainTextEdit,
    QHeaderView, QFileDialog, QCheckBox,
)

from .. import db, scoring
from ..refresh_worker import run_refresh_in_thread
from ..scrapers import REGISTRY, SOURCE_URLS
from ..scrapers.base import import_text, infer_source

VERDICT_COLORS = {
    "STRONG APPLY": "#0f8f6f", "APPLY": "#1f9d63", "WAIT / WATCH": "#c98a17",
    "CAUTIOUS / HIGH RISK": "#c5622b", "SKIP": "#bc3737", "Research needed": "#607787",
}


def verdict_color(v):
    return QColor(VERDICT_COLORS.get(v, "#607787"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CA IPO Compass — Desktop")
        self.resize(1280, 820)
        self._refresh_thread = None
        self._selected_id = None

        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        tabs.addTab(self._build_dashboard_tab(), "Dashboard")
        tabs.addTab(self._build_issues_tab(), "IPO Issues")
        tabs.addTab(self._build_analysis_tab(), "Analysis")
        tabs.addTab(self._build_import_tab(), "Manual Import")
        tabs.addTab(self._build_sources_tab(), "Data Sources")

        db.init_db()
        self.reload_table()

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self.start_refresh)
        self._apply_auto_refresh_setting()

        # First refresh shortly after launch, quietly.
        QTimer.singleShot(1500, self.start_refresh)

    # ---------------------------------------------------------------- Dashboard
    def _build_dashboard_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        header = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh live data now")
        self.refresh_btn.clicked.connect(self.start_refresh)
        header.addWidget(self.refresh_btn)

        header.addWidget(QLabel("Auto-refresh every"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(5)
        self.interval_spin.setSuffix(" min")
        self.interval_spin.valueChanged.connect(self._apply_auto_refresh_setting)
        header.addWidget(self.interval_spin)

        self.auto_checkbox = QCheckBox("Enabled")
        self.auto_checkbox.setChecked(True)
        self.auto_checkbox.stateChanged.connect(self._apply_auto_refresh_setting)
        header.addWidget(self.auto_checkbox)
        header.addStretch()
        layout.addLayout(header)

        self.status_label = QLabel("Ready.")
        layout.addWidget(self.status_label)

        self.summary_labels = {}
        summary_box = QHBoxLayout()
        for key, title in [("total", "Tracked IPOs"), ("open", "Open now"),
                            ("apply", "APPLY / STRONG APPLY"), ("skip", "SKIP")]:
            box = QGroupBox(title)
            v = QVBoxLayout(box)
            lbl = QLabel("0")
            lbl.setStyleSheet("font-size:26px;font-weight:800;")
            v.addWidget(lbl)
            self.summary_labels[key] = lbl
            summary_box.addWidget(box)
        layout.addLayout(summary_box)

        layout.addWidget(QLabel("Activity log"))
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)
        return w

    def _apply_auto_refresh_setting(self):
        self.auto_timer.stop()
        if self.auto_checkbox.isChecked():
            self.auto_timer.start(self.interval_spin.value() * 60 * 1000)

    def log(self, line):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{stamp}] {line}")

    # ---------------------------------------------------------------- Refresh
    def start_refresh(self):
        if self._refresh_thread is not None:
            return  # already running
        self.refresh_btn.setEnabled(False)
        self.status_label.setText("Refreshing from NSE, BSE, Moneycontrol, Chittorgarh, InvestorGain…")
        self._refresh_thread, self._refresh_worker = run_refresh_in_thread(
            self, list(REGISTRY.keys()), self.log, self._on_source_done, self._on_refresh_finished
        )

    def _on_source_done(self, key, ok, message):
        pass  # per-source detail already goes to the log via `progress`

    def _on_refresh_finished(self, ok_count, blocked_count):
        self.refresh_btn.setEnabled(True)
        self.status_label.setText(
            f"{ok_count} source(s) refreshed · {blocked_count} blocked/unavailable "
            f"(use Manual Import for those). Last run {datetime.now().strftime('%H:%M:%S')}."
        )
        self._refresh_thread = None
        self.reload_table()

    # ---------------------------------------------------------------- Issues
    def _build_issues_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        filters = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by name or symbol…")
        self.search_box.textChanged.connect(self.reload_table)
        filters.addWidget(self.search_box)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All statuses", "Upcoming", "Open", "Closed", "Listed"])
        self.status_filter.currentTextChanged.connect(self.reload_table)
        filters.addWidget(self.status_filter)

        self.board_filter = QComboBox()
        self.board_filter.addItems(["All boards", "Mainboard", "SME"])
        self.board_filter.currentTextChanged.connect(self.reload_table)
        filters.addWidget(self.board_filter)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["IPO", "Board", "Status", "Price band", "Close date", "GMP", "GMP %",
             "Score /10", "Verdict"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self._open_selected_in_analysis)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open in Analysis")
        open_btn.clicked.connect(self._open_selected_in_analysis)
        btn_row.addWidget(open_btn)
        del_btn = QPushButton("Delete selected")
        del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    def _current_ipos(self):
        rows = db.all_ipos()
        q = self.search_box.text().strip().lower() if hasattr(self, "search_box") else ""
        status = self.status_filter.currentText() if hasattr(self, "status_filter") else "All statuses"
        board = self.board_filter.currentText() if hasattr(self, "board_filter") else "All boards"
        out = []
        for r in rows:
            if q and q not in (r["name"] or "").lower() and q not in (r["symbol"] or "").lower():
                continue
            if status != "All statuses" and (r["status"] or "") != status:
                continue
            if board != "All boards" and (r["board"] or "") != board:
                continue
            out.append(r)
        return out

    def reload_table(self):
        rows = self._current_ipos()
        self.table.setRowCount(len(rows))
        counts = {"total": len(db.all_ipos()), "open": 0, "apply": 0, "skip": 0}
        for i, r in enumerate(rows):
            a = scoring.analyse(r)
            if (r.get("status") or "") == "Open":
                counts["open"] += 1
            if a["final"] in ("APPLY", "STRONG APPLY"):
                counts["apply"] += 1
            if a["final"] == "SKIP":
                counts["skip"] += 1

            price = f"{r.get('price_low') or '—'}–{r.get('price_high') or '—'}"
            gmp = r.get("gmp_amount")
            gmp_pct = r.get("gmp_pct")
            score = a["score"]
            values = [
                r.get("name", ""), r.get("board", ""), r.get("status", ""), price,
                r.get("close_date", "") or "—",
                f"{gmp:g}" if gmp is not None else "—",
                f"{gmp_pct:.1f}%" if gmp_pct is not None else "—",
                f"{score:.1f}" if score is not None else "—",
                a["final"],
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.UserRole, r["id"])
                if col == 8:
                    item.setForeground(verdict_color(a["final"]))
                self.table.setItem(i, col, item)
        if hasattr(self, "summary_labels"):
            for k, lbl in self.summary_labels.items():
                lbl.setText(str(counts.get(k, 0)))

    def _selected_id_from_table(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _open_selected_in_analysis(self):
        ipo_id = self._selected_id_from_table()
        if not ipo_id:
            return
        self._selected_id = ipo_id
        self._load_into_analysis(ipo_id)
        self.centralWidget().setCurrentIndex(2)

    def _delete_selected(self):
        ipo_id = self._selected_id_from_table()
        if not ipo_id:
            return
        if QMessageBox.question(self, "Delete IPO", "Remove this IPO record permanently?") == QMessageBox.Yes:
            db.delete_ipo(ipo_id)
            self.reload_table()

    # ---------------------------------------------------------------- Analysis
    def _build_analysis_tab(self):
        w = QWidget()
        layout = QHBoxLayout(w)

        left = QVBoxLayout()
        self.analysis_selector = QComboBox()
        self.analysis_selector.currentIndexChanged.connect(self._analysis_selection_changed)
        left.addWidget(self.analysis_selector)

        self.verdict_label = QLabel("—")
        self.verdict_label.setStyleSheet("font-size:22px;font-weight:800;")
        left.addWidget(self.verdict_label)

        self.score_label = QLabel("Score: — /10  ·  Coverage: —%")
        left.addWidget(self.score_label)

        left.addWidget(QLabel("Key positives"))
        self.positives_box = QPlainTextEdit()
        self.positives_box.setReadOnly(True)
        self.positives_box.setMaximumHeight(100)
        left.addWidget(self.positives_box)

        left.addWidget(QLabel("Key risks"))
        self.risks_box = QPlainTextEdit()
        self.risks_box.setReadOnly(True)
        self.risks_box.setMaximumHeight(100)
        left.addWidget(self.risks_box)

        left.addWidget(QLabel("Missing evidence"))
        self.missing_box = QPlainTextEdit()
        self.missing_box.setReadOnly(True)
        self.missing_box.setMaximumHeight(80)
        left.addWidget(self.missing_box)

        export_btn = QPushButton("Export analysis as HTML report")
        export_btn.clicked.connect(self._export_report)
        left.addWidget(export_btn)
        left.addStretch()

        right = QVBoxLayout()
        right.addWidget(QLabel("Factor score breakdown"))
        self.factor_table = QTableWidget(0, 3)
        self.factor_table.setHorizontalHeaderLabels(["Factor", "Weight", "Score /10"])
        self.factor_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.factor_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right.addWidget(self.factor_table)

        right.addWidget(QLabel("GMP history (most recent first)"))
        self.gmp_history_table = QTableWidget(0, 3)
        self.gmp_history_table.setHorizontalHeaderLabels(["Source", "GMP", "Retrieved"])
        self.gmp_history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.gmp_history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right.addWidget(self.gmp_history_table)

        left_w, right_w = QWidget(), QWidget()
        left_w.setLayout(left)
        right_w.setLayout(right)
        splitter = QSplitter()
        splitter.addWidget(left_w)
        splitter.addWidget(right_w)
        splitter.setSizes([420, 700])
        layout.addWidget(splitter)
        return w

    def _refresh_analysis_selector(self):
        self.analysis_selector.blockSignals(True)
        self.analysis_selector.clear()
        for r in db.all_ipos():
            self.analysis_selector.addItem(r["name"], r["id"])
        self.analysis_selector.blockSignals(False)

    def _analysis_selection_changed(self, idx):
        ipo_id = self.analysis_selector.itemData(idx)
        if ipo_id:
            self._selected_id = ipo_id
            self._load_into_analysis(ipo_id)

    def _load_into_analysis(self, ipo_id):
        self._refresh_analysis_selector()
        pos = self.analysis_selector.findData(ipo_id)
        if pos >= 0:
            self.analysis_selector.blockSignals(True)
            self.analysis_selector.setCurrentIndex(pos)
            self.analysis_selector.blockSignals(False)

        r = db.get(ipo_id)
        if not r:
            return
        a = scoring.analyse(r)
        self.verdict_label.setText(a["final"])
        self.verdict_label.setStyleSheet(
            f"font-size:22px;font-weight:800;color:{VERDICT_COLORS.get(a['final'], '#607787')};"
        )
        score_txt = f"{a['score']:.1f}" if a["score"] is not None else "—"
        self.score_label.setText(f"Score: {score_txt} /10  ·  Coverage: {a['coverage']:.0f}%")
        self.positives_box.setPlainText("\n".join(a["positives"]) or "No positive signal has sufficient evidence.")
        self.risks_box.setPlainText("\n".join(a["flags"]) or "No automated red flag identified from entered data.")
        self.missing_box.setPlainText(", ".join(a["missing"]) or "None identified")

        self.factor_table.setRowCount(len(a["factors"]))
        for i, (k, v) in enumerate(a["factors"].items()):
            weight_pct = scoring.RAW_WEIGHTS[k] / scoring.RAW_TOTAL * 100
            self.factor_table.setItem(i, 0, QTableWidgetItem(scoring.FACTOR_NAMES[k]))
            self.factor_table.setItem(i, 1, QTableWidgetItem(f"{weight_pct:.1f}%"))
            self.factor_table.setItem(i, 2, QTableWidgetItem(f"{v:.1f}" if v is not None else "Pending"))

        hist = db.gmp_history(ipo_id)
        self.gmp_history_table.setRowCount(len(hist))
        for i, h in enumerate(hist):
            self.gmp_history_table.setItem(i, 0, QTableWidgetItem(h["source"] or ""))
            self.gmp_history_table.setItem(i, 1, QTableWidgetItem(str(h["amount"]) if h["amount"] is not None else "—"))
            self.gmp_history_table.setItem(i, 2, QTableWidgetItem(h["at"] or ""))

    def _export_report(self):
        if not self._selected_id:
            return
        r = db.get(self._selected_id)
        a = scoring.analyse(r)
        path, _ = QFileDialog.getSaveFileName(
            self, "Export report", f"{r['name']}_IPO_Analysis.html", "HTML files (*.html)"
        )
        if not path:
            return
        def factor_row(k, v):
            weight_pct = scoring.RAW_WEIGHTS[k] / scoring.RAW_TOTAL * 100
            score_txt = f"{v:.1f}" if v is not None else "Pending"
            return f"<tr><td>{scoring.FACTOR_NAMES[k]}</td><td>{weight_pct:.1f}%</td><td>{score_txt}</td></tr>"

        rows_html = "".join(factor_row(k, v) for k, v in a["factors"].items())
        html = f"""<!doctype html><html><head><meta charset='utf-8'>
<title>{r['name']} IPO Analysis</title>
<style>body{{font:15px/1.5 Arial,sans-serif;max-width:900px;margin:auto;padding:20px}}
table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #ccc;padding:8px;text-align:left}}
.score{{font-size:32px;font-weight:800}}</style></head><body>
<h1>{r['name']}</h1>
<p><strong>{r.get('sector') or 'Sector not recorded'}</strong> · {r.get('location') or 'Location not recorded'}</p>
<div class="score">{a['final']} — {f"{a['score']:.1f}" if a['score'] is not None else '—'}/10 ({a['coverage']:.0f}% coverage)</div>
<h2>Factor scores</h2>
<table><tr><th>Factor</th><th>Weight</th><th>Score</th></tr>{rows_html}</table>
<h2>Key positives</h2><ul>{''.join(f'<li>{p}</li>' for p in a['positives']) or '<li>None recorded</li>'}</ul>
<h2>Key risks</h2><ul>{''.join(f'<li>{f}</li>' for f in a['flags']) or '<li>None recorded</li>'}</ul>
<h2>Missing evidence</h2><p>{', '.join(a['missing']) or 'None identified'}</p>
<h2>Notes</h2><p>{r.get('notes') or 'No notes recorded.'}</p>
<p><small>Independent analytical aid. GMP is unofficial and indicative. Verify issue data on
BSE/NSE and financial figures in the RHP before investing.</small></p>
</body></html>"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        QMessageBox.information(self, "Exported", f"Report saved to:\n{path}")

    # ---------------------------------------------------------------- Manual import
    def _build_import_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel(
            "Paste a CSV table, a JSON export, or the full HTML of a saved IPO/GMP "
            "webpage below — this is the reliable fallback whenever a live source "
            "is blocked or changes its layout."
        ))
        self.import_source = QComboBox()
        self.import_source.addItems(["manual", "nse", "bse", "moneycontrol", "chittorgarh", "ipoji", "investorgain"])
        layout.addWidget(self.import_source)

        self.import_box = QPlainTextEdit()
        self.import_box.setPlaceholderText("Paste CSV / JSON / saved-page HTML here…")
        layout.addWidget(self.import_box)

        btn_row = QHBoxLayout()
        paste_btn = QPushButton("Import pasted text")
        paste_btn.clicked.connect(self._do_paste_import)
        btn_row.addWidget(paste_btn)

        file_btn = QPushButton("Import from file(s)…")
        file_btn.clicked.connect(self._do_file_import)
        btn_row.addWidget(file_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.import_result = QLabel("")
        layout.addWidget(self.import_result)
        return w

    def _do_paste_import(self):
        text = self.import_box.toPlainText()
        key = self.import_source.currentText()
        try:
            records = import_text(text, key)
        except Exception as e:
            QMessageBox.warning(self, "Import failed", f"Could not parse the pasted content:\n{e}")
            return
        module, name, official, _ = REGISTRY.get(key, (None, "Manual import", False, False))
        count = 0
        for rec in records:
            if rec.get("name"):
                db.merge_incoming(rec, key, name, SOURCE_URLS.get(key, ""), "Manual import", official)
                count += 1
        self.import_result.setText(f"Imported/updated {count} record(s).")
        self.import_box.clear()
        self.reload_table()

    def _do_file_import(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose file(s) to import", "", "Data files (*.csv *.json *.html *.htm *.txt)"
        )
        total = 0
        for path in paths:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            key = infer_source(path, text)
            try:
                records = import_text(text, key)
            except Exception as e:
                self.log(f"Could not import {path}: {e}")
                continue
            module, name, official, _ = REGISTRY.get(key, (None, "Manual import", False, False))
            for rec in records:
                if rec.get("name"):
                    db.merge_incoming(rec, key, name, SOURCE_URLS.get(key, ""), "File import", official)
                    total += 1
        self.import_result.setText(f"Imported/updated {total} record(s) from {len(paths)} file(s).")
        self.reload_table()

    # ---------------------------------------------------------------- Sources
    def _build_sources_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Configured live sources"))
        for key, (module, name, official, needs_browser) in REGISTRY.items():
            box = QGroupBox(name)
            v = QFormLayout(box)
            v.addRow("Type", QLabel("Official exchange" if official else "Secondary / unofficial GMP"))
            v.addRow("Method", QLabel("Headless browser (JS-rendered page)" if needs_browser
                                       else "Direct HTTP request"))
            v.addRow("URL", QLabel(SOURCE_URLS.get(key, "")))
            layout.addWidget(box)
        layout.addWidget(QLabel(
            "Note: GMP figures are unofficial grey-market indicators, not a guarantee of "
            "listing performance. Always verify issue terms on BSE/NSE and financials in the RHP."
        ))
        layout.addStretch()
        return w
