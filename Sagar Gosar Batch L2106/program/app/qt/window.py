"""Main window of the 2026 interface."""
import csv
import dataclasses
import os
from collections import Counter

from PySide6.QtCore import QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSplitter,
                               QStackedWidget, QTableView, QTextBrowser, QToolButton, QVBoxLayout, QWidget)

from .. import __version__, config
from .. import report_model as rm
from . import theme
from .align_view import AlignView
from .dialogs import CommandPalette, PageSelectDialog
from .diffs import COLS, DiffModel, DiffProxy, PillDelegate, runs_html
from .theme import SEV, THEMES, icon, pal, qss
from .widgets import (BarList, DonutChart, DropCard, Ring, ScanPanel, StatCard, Toast, Toggle, Worker, label, repolish)

NAV = [("compare", "New comparison", "play", "Select the two documents and run the comparison"),
       ("dash", "Dashboard", "dash", "Overview of the comparison"),
       ("diff", "Differences", "list", "Review every difference against the scan"),
       ("red", "Redline", "pen", "Full executed text marked against the draft"),
       ("align", "Align & edit", "align", "Fix paragraph pairing, OCR text and page rotation manually"),
       ("rep", "Reports", "report", "Export Word / PDF reports and the register"),
       ("set", "Settings", "settings", "Appearance and defaults")]


def rgba(hexcol, a=0.18):
    c = QColor(hexcol); return f"rgba({c.red()},{c.green()},{c.blue()},{a})"


def card(layout_cls=QVBoxLayout, margins=(20, 16, 20, 16), spacing=10, name="card"):
    f = QFrame(); f.setObjectName(name); l = layout_cls(f); l.setContentsMargins(*margins); l.setSpacing(spacing); return f, l


def scroll(widget):
    s = QScrollArea(); s.setWidgetResizable(True); s.setFrameShape(QFrame.NoFrame); s.setWidget(widget)
    widget.setObjectName("page"); s.viewport().setAutoFillBackground(False); s.setStyleSheet("QScrollArea{background:transparent;}")
    return s


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.st = QSettings("AgreementCompare", "QtUI")
        self.setWindowTitle(f"{config.APP_NAME}  ·  v{__version__}")
        self.resize(1480, 940); self.setMinimumSize(1120, 720)
        self.result = None; self.worker = None; self.page_sel = None; self.page_total = 0
        self._scan_cache = {}; self._cur_item = None; self.collapsed = False; self.recent_exports = []
        theme_name = self.st.value("theme", "Royal Night")
        self.theme_name = theme_name if theme_name in THEMES else "Royal Night"
        self.scale = float(self.st.value("scale", 1.0))
        theme.set_pal(self.theme_name)

        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        h = QHBoxLayout(root); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        h.addWidget(self._build_sidebar())
        col = QVBoxLayout(); col.setContentsMargins(0, 0, 0, 0); col.setSpacing(0); h.addLayout(col, 1)
        col.addWidget(self._build_topbar())
        self.stack = QStackedWidget(); col.addWidget(self.stack, 1)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.pages = {}
        for key, builder in (("compare", self._build_compare), ("dash", self._build_dashboard), ("diff", self._build_diff),
                             ("red", self._build_redline), ("align", self._build_align), ("rep", self._build_reports), ("set", self._build_settings)):
            w = builder(); host = QWidget(); hl = QVBoxLayout(host); hl.setContentsMargins(28, 22, 28, 12); hl.addWidget(w)
            self.stack.addWidget(host); self.pages[key] = host
        col.addWidget(self._build_activity())
        self.toast = Toast(root)
        self._shortcuts()
        self.apply_theme(self.theme_name, save=False)
        self.goto("compare")
        g = self.st.value("geometry")
        if g:
            self.restoreGeometry(g)
        self._load_recent()
        if not config.configure_tesseract():
            self.set_status("Tesseract OCR not found – scanned PDFs cannot be read until it is installed (see README).", "warn")

    # ============================================================================ chrome
    def _build_sidebar(self):
        sb = QFrame(); sb.setObjectName("sidebar"); sb.setFixedWidth(232); self.sidebar = sb
        v = QVBoxLayout(sb); v.setContentsMargins(14, 18, 14, 14); v.setSpacing(4)
        brand = QHBoxLayout(); brand.setSpacing(10)
        self.crown = QLabel(); self.crown.setFixedSize(42, 42); self.crown.setAlignment(Qt.AlignCenter); brand.addWidget(self.crown)
        bt = QVBoxLayout(); bt.setSpacing(0)
        self.brand_t = label("Agreement\nCompare", "brand"); self.brand_v = label(f"v{__version__} · 2026 edition", "small")
        bt.addWidget(self.brand_t); bt.addWidget(self.brand_v); brand.addLayout(bt, 1); v.addLayout(brand); v.addSpacing(18)
        self.nav_group = QButtonGroup(self); self.nav_group.setExclusive(True); self.nav_btns = {}
        for i, (key, text, ic, _tip) in enumerate(NAV):
            b = QPushButton("  " + text.replace("&", "&&")); b.setCheckable(True); b.setProperty("kind", "nav"); b._ic = ic; b._text = "  " + text.replace("&", "&&"); b.setToolTip(text)
            b.setIconSize(QSize(20, 20)); b.setCursor(Qt.PointingHandCursor); b.clicked.connect(lambda _=False, k=key: self.goto(k))
            self.nav_group.addButton(b, i); self.nav_btns[key] = b; v.addWidget(b)
            if key == "rep":
                v.addSpacing(10)
        v.addStretch(1)
        self.btn_cmd = QPushButton("  Commands (Ctrl+K)"); self.btn_cmd.setProperty("kind", "ghost"); self.btn_cmd.clicked.connect(self.open_palette); v.addWidget(self.btn_cmd)
        self.btn_theme = QPushButton("  Switch theme"); self.btn_theme.setProperty("kind", "ghost"); self.btn_theme.clicked.connect(self.cycle_theme); v.addWidget(self.btn_theme)
        self.btn_collapse = QPushButton("  Collapse menu"); self.btn_collapse.setProperty("kind", "ghost"); self.btn_collapse.clicked.connect(self.toggle_sidebar); v.addWidget(self.btn_collapse)
        return sb

    def _build_topbar(self):
        tb = QFrame(); tb.setObjectName("topbar"); tb.setFixedHeight(76)
        h = QHBoxLayout(tb); h.setContentsMargins(28, 10, 28, 10)
        t = QVBoxLayout(); t.setSpacing(0); self.page_title = label("", "title"); self.page_sub = label("", "muted"); t.addWidget(self.page_title); t.addWidget(self.page_sub)
        h.addLayout(t, 1)
        self.chip = QLabel("Ready"); self.chip.setProperty("role", "pill"); self.chip.setFixedHeight(30); h.addWidget(self.chip, 0, Qt.AlignVCenter)
        return tb

    def _build_activity(self):
        f = QFrame(); f.setObjectName("topbar"); f.setStyleSheet("QFrame#topbar{border-top:1px solid %s;border-bottom:none;}" % pal()["border"])
        self.activity = f; h = QHBoxLayout(f); h.setContentsMargins(28, 8, 28, 8); h.setSpacing(14)
        self.msg = label("Select the two documents and press Compare.", "muted"); h.addWidget(self.msg, 1)
        self.bar = QProgressBar(); self.bar.setRange(0, 1000); self.bar.setFixedWidth(340); self.bar.setTextVisible(False); h.addWidget(self.bar)
        self.btn_cancel = QPushButton(" Cancel"); self.btn_cancel.setProperty("kind", "danger"); self.btn_cancel.clicked.connect(self.cancel_task); h.addWidget(self.btn_cancel)
        self.bar.hide(); self.btn_cancel.hide()
        return f

    def goto(self, key):
        i = [k for k, *_ in NAV].index(key); self.stack.setCurrentIndex(i); self.nav_btns[key].setChecked(True)
        k, text, ic, tip = NAV[i]; self.page_title.setText(text); self.page_sub.setText(tip); self._nav_icons()

    def _nav_icons(self):
        for b in self.nav_btns.values():
            b.setIcon(icon(b._ic, "#FFFFFF" if b.isChecked() else pal()["muted"], 20))

    def toggle_sidebar(self):
        self.collapsed = not self.collapsed
        self.sidebar.setFixedWidth(76 if self.collapsed else 232)
        for b in self.nav_btns.values():
            b.setText("" if self.collapsed else b._text)
        for b, t in ((self.btn_cmd, "  Commands (Ctrl+K)"), (self.btn_theme, "  Switch theme"), (self.btn_collapse, "  Collapse menu")):
            b.setText("" if self.collapsed else t)
        self.brand_t.setVisible(not self.collapsed); self.brand_v.setVisible(not self.collapsed)

    def set_status(self, text, kind="info"):
        self.msg.setText(text)

    def set_chip(self, text, kind="info"):
        c = pal(); col = {"ok": c["ok"], "warn": "#F2CF55", "err": "#FF5C7A", "info": c["primary"]}[kind]
        self.chip.setText(text); self.chip.setStyleSheet(f"background:{rgba(col)};color:{col};border:1px solid {col};border-radius:12px;padding:3px 12px;font-weight:700;")

    # ============================================================================ tasks
    def run_task(self, fn, on_ok, text="Working…", cancellable=True):
        if self.worker and self.worker.isRunning():
            self.toast.show_msg("Another task is still running", "info"); return
        try:
            from ..extract_pdf import Cancelled
        except Exception:   # noqa
            Cancelled = None
        w = Worker(fn, self, cancel_exc=Cancelled); self.worker = w
        w.progress.connect(self._progress); w.succeeded.connect(lambda r: (self._busy(False), on_ok(r)))
        w.failed.connect(self._failed); w.cancelled.connect(lambda: (self._busy(False), self.toast.show_msg("Cancelled", "info"), self.set_status("Cancelled.")))
        self._busy(True, text, cancellable); w.start()

    def _busy(self, on, text="", cancellable=True):
        self.bar.setVisible(on); self.btn_cancel.setVisible(on and cancellable); self.bar.setValue(0)
        if on:
            self.msg.setText(text); self.set_chip("Working…", "info")
        else:
            self._refresh_chip()
        for b in (self.btn_go, self.btn_go_more):
            b.setEnabled(not on)

    def _progress(self, f, m):
        self.bar.setValue(int(max(0.0, min(1.0, f)) * 1000)); self.msg.setText(m)

    def _failed(self, msg, tb):
        self._busy(False); self.set_chip("Failed", "err"); self.msg.setText("Failed: " + msg.splitlines()[0][:160]); print(tb)
        box = QMessageBox(self); box.setIcon(QMessageBox.Critical); box.setWindowTitle(config.APP_NAME); box.setText(msg[:900]); box.setDetailedText(tb); box.exec()

    def cancel_task(self):
        if self.worker:
            self.worker.cancel(); self.msg.setText("Cancelling…")

    def _refresh_chip(self):
        if self.result:
            s = self.result.stats; self.set_chip(f"{s['total']} differences · {s['by_severity']['Critical']} critical", "warn" if s["by_severity"]["Critical"] else "ok")
        else:
            self.set_chip("Ready", "info")

    # ============================================================================ page: compare
    def _build_compare(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 8, 0); v.setSpacing(16)
        hero, hv = card(name="hero", margins=(26, 22, 26, 22), spacing=6)
        hv.addWidget(label("Compare a Word draft with the executed scanned copy", "h2"))
        hv.addWidget(label("Drop the files below (or click a card). The executed copy can be a PDF or scanned images – stamps and signatures are ignored, "
                           "paragraph breaks do not have to agree, and you can fine-tune the pairing afterwards in “Align & edit”.", "muted", True))
        v.addWidget(hero)
        row = QHBoxLayout(); row.setSpacing(16)
        self.drop_a = DropCard("Word draft (.docx)", "Drop the Word agreement here, or click to browse", "doc", (".docx",))
        self.drop_b = DropCard("Executed copy (PDF / image)", "Drop the signed, scanned agreement here", "scan", (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"))
        self.drop_b.fileChosen.connect(self._file_b_changed)
        row.addWidget(self.drop_a, 1); row.addWidget(self.drop_b, 1); v.addLayout(row)

        pr, pl = card(QHBoxLayout, (18, 12, 18, 12), 12, "cardflat")
        self.btn_pages = QPushButton(" Select pages of the executed copy…"); self.btn_pages.setEnabled(False); self.btn_pages.clicked.connect(self.pick_pages); pl.addWidget(self.btn_pages)
        self.pages_lbl = label("Choose the executed PDF first – you can then leave out stamp-paper, blank or annexure pages.", "muted", True); pl.addWidget(self.pages_lbl, 1)
        v.addWidget(pr)

        oc, ol = card(spacing=12)
        ol.addWidget(label("Comparison settings", "h2"))
        g = QGridLayout(); g.setHorizontalSpacing(34); g.setVerticalSpacing(14); self.tg = {}
        spec = [("ignore_case", "Ignore capitalisation", True), ("compare_punct", "Compare punctuation", False),
                ("ocr_tolerance", "Treat OCR look-alikes as OCR variance", True), ("force_ocr", "Force OCR on every page", False),
                ("reflow", "Smart paragraph alignment", True), ("ignore_stamps", "Ignore stamps & registration text", True),
                ("ignore_colour_ink", "Remove coloured ink (seals / pen)", True), ("enhance_scan", "Enhance scan before reading", True),
                ("upright", "Pages are already upright (skip rotation check)", False)]
        for i, (k, t, d) in enumerate(spec):
            tg = Toggle(t); tg.setChecked(self.st.value("opt_" + k, d, type=bool)); tg.toggled.connect(lambda x, k=k: self.st.setValue("opt_" + k, x))
            self.tg[k] = tg; g.addWidget(tg, i // 3, i % 3)
        ol.addLayout(g)
        r2 = QHBoxLayout(); r2.setSpacing(10); r2.addWidget(label("OCR resolution", "muted"))
        self.dpi = QComboBox(); self.dpi.addItems(["200", "300", "400"]); self.dpi.setCurrentText(str(self.st.value("dpi", "300"))); r2.addWidget(self.dpi)
        r2.addSpacing(16); r2.addWidget(label("Language", "muted")); self.lang = QLineEdit(str(self.st.value("lang", "eng"))); self.lang.setFixedWidth(90); r2.addWidget(self.lang)
        r2.addStretch(1); ol.addLayout(r2); v.addWidget(oc)

        ar = QHBoxLayout(); ar.setSpacing(0)
        self.btn_go = QPushButton("  Compare documents"); self.btn_go.setProperty("kind", "primary"); self.btn_go.setCursor(Qt.PointingHandCursor); self.btn_go.clicked.connect(lambda: self.start_compare())
        self.btn_go.setMinimumHeight(48); ar.addWidget(self.btn_go)
        self.btn_go_more = QToolButton(); self.btn_go_more.setIcon(icon("chev", "#FFFFFF", 18)); self.btn_go_more.setPopupMode(QToolButton.InstantPopup)
        self.btn_go_more.setStyleSheet("QToolButton{border:none;border-top-right-radius:10px;border-bottom-right-radius:10px;padding:0 12px;background:%s;}" % pal()["primary2"])
        m = QMenu(self)
        m.addAction("Compare now", lambda: self.start_compare())
        m.addAction("Quick compare (skip scan enhancement)", lambda: self.start_compare(quick=True))
        m.addAction("Compare selected pages only…", lambda: (self.pick_pages(), self.start_compare()))
        m.addSeparator(); m.addAction("Swap draft / executed fields", self.swap_files); m.addAction("Clear both files", self.clear_files)
        self.btn_go_more.setMenu(m); self.btn_go_more.setMinimumHeight(48); ar.addWidget(self.btn_go_more); ar.addStretch(1); v.addLayout(ar)

        self.recent_card, self.recent_l = card(spacing=8); self.recent_l.addWidget(label("Recent comparisons", "h2")); self.recent_box = QVBoxLayout(); self.recent_l.addLayout(self.recent_box)
        v.addWidget(self.recent_card); v.addStretch(1)
        return scroll(w)

    def _file_b_changed(self, p):
        self.page_sel = None; ok = bool(p) and os.path.isfile(p)
        self.btn_pages.setEnabled(ok)
        if not ok:
            self.page_total = 0; return
        try:
            from ..pages import page_count
            self.page_total = page_count(p)
            self.pages_lbl.setText(f"All {self.page_total} page(s) will be compared – use the button to leave out stamp-paper, blank or annexure pages.")
        except Exception:   # noqa
            self.page_total = 0; self.pages_lbl.setText("")

    def pick_pages(self):
        p = self.drop_b.path
        if not (p and os.path.isfile(p)):
            self.toast.show_msg("Choose the executed copy first", "info"); return
        if not self.page_total:
            self._file_b_changed(p)
        if not self.page_total:
            return
        dlg = PageSelectDialog(self, p, self.page_total, self.page_sel)
        if dlg.exec() and dlg.selected:
            from ..pages import format_pages
            if len(dlg.selected) == self.page_total:
                self.page_sel = None; self.pages_lbl.setText(f"All {self.page_total} page(s) will be compared.")
            else:
                self.page_sel = dlg.selected; left = [x for x in range(1, self.page_total + 1) if x not in dlg.selected]
                self.pages_lbl.setText(f"Comparing {len(dlg.selected)} of {self.page_total} page(s) (p. {format_pages(dlg.selected)}); left out: p. {format_pages(left)}")

    def swap_files(self):
        a, b = self.drop_a.path, self.drop_b.path; self.drop_a.set_path(b); self.drop_b.set_path(a)

    def clear_files(self):
        self.drop_a.set_path(""); self.drop_b.set_path(""); self.page_sel = None; self.btn_pages.setEnabled(False)

    def options(self):
        from ..models import CompareOptions
        t = self.tg
        kw = dict(ignore_case=t["ignore_case"].isChecked(), compare_punct=t["compare_punct"].isChecked(), ocr_tolerance=t["ocr_tolerance"].isChecked(),
                  force_ocr=t["force_ocr"].isChecked(), ocr_dpi=int(self.dpi.currentText()), ocr_lang=self.lang.text().strip() or "eng",
                  pages=list(self.page_sel) if self.page_sel else None, reflow=t["reflow"].isChecked(), ignore_stamps=t["ignore_stamps"].isChecked(),
                  ignore_colour_ink=t["ignore_colour_ink"].isChecked(), enhance_scan=t["enhance_scan"].isChecked(), seal_recovery=t["seal_recovery"].isChecked() if "seal_recovery" in t else True, second_engine=t["second_engine"].isChecked() if "second_engine" in t else True, auto_rotate=not t["upright"].isChecked())
        names = {f.name for f in dataclasses.fields(CompareOptions)}
        self.st.setValue("dpi", self.dpi.currentText()); self.st.setValue("lang", self.lang.text())
        return CompareOptions(**{k: v for k, v in kw.items() if k in names})

    def start_compare(self, quick=False):
        a, b = self.drop_a.path, self.drop_b.path
        if not (a and os.path.isfile(a)):
            self.toast.show_msg("Please choose the Word draft (.docx)", "err"); self.goto("compare"); return
        if not (b and os.path.isfile(b)):
            self.toast.show_msg("Please choose the executed copy (PDF or image)", "err"); self.goto("compare"); return
        opts = self.options()
        if quick and hasattr(opts, "enhance_scan"):
            opts.enhance_scan = False
        from ..pipeline import run_comparison
        self._remember_recent(a, b)
        self.run_task(lambda progress, cancel: run_comparison(a, b, opts, progress=progress, cancel=cancel),
                      lambda r: self.set_result(r, fresh=True), "Comparing documents…")

    def recompare(self, da, db, anchors):
        from ..comparer import compare_documents
        opts = self.options()
        self.run_task(lambda progress, cancel: compare_documents(da, db, opts, progress=progress, cancel=cancel, anchors=anchors),
                      lambda r: self.set_result(r, fresh=False), "Re-comparing with your adjustments…")

    def rotate_page(self, delta, page, recompare=True):
        if not self.align.loaded():
            self.toast.show_msg("Run a comparison first", "info"); return
        self.align.rotate_page(delta, page=page, recompare=recompare)

    # ---- recent
    def _recent_list(self):
        r = self.st.value("recent", []) or []
        r = [r] if isinstance(r, str) else list(r)
        return [x for x in r if isinstance(x, str) and "|" in x]

    def _remember_recent(self, a, b):
        r = [x for x in self._recent_list() if x != a + "|" + b]; r.insert(0, a + "|" + b); self.st.setValue("recent", r[:6]); self._load_recent()

    def _load_recent(self):
        while self.recent_box.count():
            it = self.recent_box.takeAt(0); w = it.widget()
            if w:
                w.deleteLater()
        rec = self._recent_list()
        self.recent_card.setVisible(bool(rec))
        for x in rec[:5]:
            a, b = x.split("|", 1)
            btn = QPushButton(f"  {os.path.basename(a)}   ⇄   {os.path.basename(b)}"); btn.setProperty("kind", "ghost"); btn.setStyleSheet("text-align:left;")
            btn.setToolTip(f"{a}\n{b}"); btn.clicked.connect(lambda _=False, a=a, b=b: self._use_recent(a, b)); self.recent_box.addWidget(btn)

    def _use_recent(self, a, b):
        if os.path.isfile(a):
            self.drop_a.set_path(a)
        if os.path.isfile(b):
            self.drop_b.set_path(b); self._file_b_changed(b)

    # ============================================================================ page: dashboard
    def _build_dashboard(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 8, 0); v.setSpacing(16)
        self.dash_empty = label("No comparison yet – start one from “New comparison”.", "muted"); self.dash_empty.setAlignment(Qt.AlignCenter); v.addWidget(self.dash_empty)
        self.dash_body = QWidget(); b = QVBoxLayout(self.dash_body); b.setContentsMargins(0, 0, 0, 0); b.setSpacing(16)
        hero, hv = card(QHBoxLayout, (24, 18, 24, 18), 16, "hero")
        ht = QVBoxLayout(); ht.setSpacing(2); self.dash_names = label("", "h2"); self.dash_lines = label("", "muted", True); ht.addWidget(self.dash_names); ht.addWidget(self.dash_lines)
        hv.addLayout(ht, 1)
        self.dash_export = QToolButton(); self.dash_export.setText("  Export report"); self.dash_export.setIcon(icon("download", "#2A1B00", 18)); self.dash_export.setPopupMode(QToolButton.InstantPopup); self.dash_export.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.dash_export.setStyleSheet(f"QToolButton{{background:{pal()['gold']};color:#2A1B00;font-weight:800;border:none;border-radius:10px;padding:10px 18px;}}")
        em = QMenu(self); em.addAction("Word report (.docx)", lambda: self.export("word")); em.addAction("PDF report", lambda: self.export("pdf")); em.addAction("Both (choose a folder)", lambda: self.export("both"))
        em.addSeparator(); em.addAction("Register as CSV (Excel)", self.export_csv); self.dash_export.setMenu(em); hv.addWidget(self.dash_export); b.addWidget(hero)
        kr = QHBoxLayout(); kr.setSpacing(14); self.kpis = {}
        for k, t, c in (("total", "Total differences", pal()["gold"]), ("Critical", "Critical", SEV["Critical"]), ("Major", "Major", SEV["Major"]),
                        ("Minor", "Minor", SEV["Minor"]), ("Info", "Information", SEV["Info"])):
            s = StatCard(t, c); self.kpis[k] = s; kr.addWidget(s, 1)
        b.addLayout(kr)
        mid = QHBoxLayout(); mid.setSpacing(14)
        c1, l1 = card(); l1.addWidget(label("By severity", "h2")); self.donut = DonutChart(); l1.addWidget(self.donut, 1); self.legend = QHBoxLayout(); l1.addLayout(self.legend); mid.addWidget(c1, 2)
        c2, l2 = card(); l2.addWidget(label("By category", "h2")); self.cats = BarList(); l2.addWidget(self.cats, 1); mid.addWidget(c2, 4)
        c3, l3 = card(); l3.addWidget(label("Review progress", "h2")); self.ring = Ring(); l3.addWidget(self.ring, 0, Qt.AlignHCenter); self.ring_lbl = label("0 of 0 reviewed", "small"); self.ring_lbl.setAlignment(Qt.AlignCenter)
        l3.addWidget(self.ring_lbl); gb = QPushButton(" Start reviewing"); gb.setProperty("kind", "gold"); gb.clicked.connect(lambda: self.goto("diff")); l3.addWidget(gb); l3.addStretch(1); mid.addWidget(c3, 2)
        b.addLayout(mid)
        lo = QHBoxLayout(); lo.setSpacing(14)
        c4, l4 = card(); l4.addWidget(label("Observations on the documents", "h2")); self.obs_box = QVBoxLayout(); self.obs_box.setSpacing(8); l4.addLayout(self.obs_box); lo.addWidget(c4, 3)
        c5, l5 = card(); l5.addWidget(label("Documents", "h2")); self.doc_box = QVBoxLayout(); self.doc_box.setSpacing(8); l5.addLayout(self.doc_box); lo.addWidget(c5, 2)
        b.addLayout(lo)
        self.dash_note = label(rm.DISCLAIMER, "small", True); b.addWidget(self.dash_note)
        v.addWidget(self.dash_body); v.addStretch(1); self.dash_body.hide()
        return scroll(w)

    def _clear(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def _fill_dashboard(self):
        r = self.result; s = r.stats; self.dash_empty.hide(); self.dash_body.show()
        self.dash_names.setText(f"{r.doc_a.name}   ⇄   {r.doc_b.name}")
        self.dash_lines.setText("   ·   ".join(rm.summary_lines(r)))
        self.kpis["total"].set_value(s["total"], "after OCR-variance filtering")
        for k in ("Critical", "Major", "Minor", "Info"):
            self.kpis[k].set_value(s["by_severity"][k], "")
        self.donut.set_data(s["by_severity"]); self._clear(self.legend)
        for k in ("Critical", "Major", "Minor", "Info"):
            l = QLabel(f"<span style='color:{SEV[k]}'>●</span> {k}"); l.setProperty("role", "small"); self.legend.addWidget(l)
        cnt = Counter(c for it in r.items if not it.ocr_only for c in it.categories); self.cats.set_rows(cnt.most_common(8))
        self._clear(self.obs_box)
        for sev, tx in r.observations or [("Info", "No observations.")]:
            row = QHBoxLayout(); p = QLabel(sev); p.setProperty("role", "pill"); col = SEV.get(sev, SEV["Info"])
            p.setStyleSheet(f"background:{rgba(col)};color:{col};border-radius:10px;padding:2px 10px;font-weight:700;"); p.setFixedWidth(74); p.setAlignment(Qt.AlignCenter)
            t = QLabel(tx); t.setWordWrap(True); row.addWidget(p, 0, Qt.AlignTop); row.addWidget(t, 1)
            wd = QWidget(); wd.setLayout(row); row.setContentsMargins(0, 0, 0, 0); self.obs_box.addWidget(wd)
        self._clear(self.doc_box)
        for role, lab, (name, size, mod, sha, extra) in rm.meta_rows(r):
            l = QLabel(f"<b>{role}</b> — {name}<br><span style='color:{pal()['muted']}'>{size}, {extra}<br>SHA-256 {sha[:24]}…</span>"); l.setWordWrap(True); l.setTextInteractionFlags(Qt.TextSelectableByMouse); self.doc_box.addWidget(l)
        self._update_review()

    def _update_review(self):
        if not self.result:
            return
        vis = [it for it in self.model.items if not it.ocr_only]; n = len(vis); d = sum(1 for it in vis if it.id in self.model.reviewed)
        self.ring.set_value(d / n if n else 0); self.ring_lbl.setText(f"{d} of {n} reviewed"); self.rev_lbl.setText(f"{d}/{n} reviewed")

    # ============================================================================ page: differences
    def _build_diff(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(12)
        fb, fv = card(QVBoxLayout, (14, 10, 14, 10), 8, "cardflat"); fl = QHBoxLayout(); fl.setSpacing(8); fv.addLayout(fl); fl2 = QHBoxLayout(); fl2.setSpacing(8); fv.addLayout(fl2)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search differences…  (Ctrl+F)"); self.search.setClearButtonEnabled(True); self.search.setFixedWidth(280)
        self.search.addAction(icon("search", pal()["muted"], 16), QLineEdit.LeadingPosition); fl.addWidget(self.search)
        self.chips = {}; grp = QButtonGroup(self); grp.setExclusive(True)
        for k in ("All", "Critical", "Major", "Minor", "Info"):
            b = QPushButton(k); b.setCheckable(True); b.setProperty("kind", "chip"); b.setChecked(k == "All"); grp.addButton(b); self.chips[k] = b; fl.addWidget(b)
            b.clicked.connect(lambda _=False, k=k: self._filter(sev=None if k == "All" else k))
        fl.addSpacing(14)
        self.t_ocr = Toggle("OCR variances"); self.t_hide = Toggle("Hide reviewed"); fl.addWidget(self.t_ocr); fl.addSpacing(10); fl.addWidget(self.t_hide); fl.addStretch(1)
        self.count_lbl = label("", "muted"); self.rev_lbl = label("", "gold"); fl2.addWidget(self.count_lbl); fl2.addSpacing(10); fl2.addWidget(self.rev_lbl); fl2.addStretch(1)
        self.btn_prev = QPushButton(" Previous"); self.btn_next = QPushButton(" Next"); self.btn_rev = QPushButton(" Mark reviewed"); self.btn_rev.setProperty("kind", "gold")
        self.btn_prev.setToolTip("Previous difference  (Shift+F3)"); self.btn_next.setToolTip("Next difference  (F3)"); self.btn_rev.setToolTip("Tick this difference as reviewed  (Space)")
        self.btn_prev.clicked.connect(lambda: self.step(-1)); self.btn_next.clicked.connect(lambda: self.step(1)); self.btn_rev.clicked.connect(self.toggle_reviewed)
        for bt in (self.btn_prev, self.btn_next, self.btn_rev):
            fl2.addWidget(bt)
        v.addWidget(fb)
        sp = QSplitter(Qt.Horizontal); sp.setChildrenCollapsible(False)
        left = QSplitter(Qt.Vertical); left.setChildrenCollapsible(False)
        self.model = DiffModel(); self.proxy = DiffProxy(); self.proxy.setSourceModel(self.model)
        self.table = QTableView(); self.table.setModel(self.proxy); self.table.setSelectionBehavior(QTableView.SelectRows); self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.verticalHeader().setVisible(False); self.table.setShowGrid(False); self.table.setAlternatingRowColors(False); self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(36); self.table.setEditTriggers(QTableView.NoEditTriggers)
        hd = self.table.horizontalHeader(); hd.setStretchLastSection(False)
        for i, wd in enumerate((38, 42, 64, 112, 150, 0, 44)):
            if wd:
                hd.setSectionResizeMode(i, QHeaderView.Fixed); self.table.setColumnWidth(i, wd)
            else:
                hd.setSectionResizeMode(i, QHeaderView.Stretch)
        self.table.setItemDelegateForColumn(0, PillDelegate(self.table)); self.table.setItemDelegateForColumn(3, PillDelegate(self.table))
        self.table.selectionModel().currentRowChanged.connect(lambda cur, _p: self._on_diff_select())
        self.table.clicked.connect(lambda ix: self.toggle_reviewed() if ix.column() == 0 else None)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu); self.table.customContextMenuRequested.connect(self._diff_menu)
        tc, tl = card(margins=(8, 8, 8, 8)); tl.addWidget(self.table); left.addWidget(tc)
        dc, dl = card(margins=(16, 12, 16, 14), spacing=8)
        self.detail_head = label("Select a difference to compare both versions", "h2"); dl.addWidget(self.detail_head)
        pair = QHBoxLayout(); pair.setSpacing(10)
        self.t_left = QTextBrowser(); self.t_right = QTextBrowser()
        for tb, ttl in ((self.t_left, "Draft (Word)"), (self.t_right, "Executed (scan / PDF)")):
            tb.setObjectName("paper"); tb.setOpenLinks(False); col = QVBoxLayout(); col.setSpacing(4); col.addWidget(label(ttl, "small")); col.addWidget(tb, 1); pair.addLayout(col, 1)
        dl.addLayout(pair, 1)
        dl.addWidget(label("Red strike-through = in the draft but changed / removed  ·  Green underline = only in the executed copy  ·  Amber italic = probable OCR variance", "small", True))
        left.addWidget(dc); left.setStretchFactor(0, 5); left.setStretchFactor(1, 3); sp.addWidget(left)
        self.scan = ScanPanel("Executed copy – scan preview"); self.scan.rotateRequested.connect(self._rotate_shown); sp.addWidget(self.scan)
        sp.setStretchFactor(0, 7); sp.setStretchFactor(1, 4); v.addWidget(sp, 1)
        self.search.textChanged.connect(lambda t: self._filter(text=t)); self.t_ocr.toggled.connect(lambda x: self._filter(show_ocr=x)); self.t_hide.toggled.connect(lambda x: self._filter(hide_reviewed=x))
        return w

    def _filter(self, **kw):
        self.proxy.set_filters(**kw); self.count_lbl.setText(f"{self.proxy.rowCount()} shown")

    def _fill_diff(self):
        self.model.set_items(self.result.items); self.proxy.set_filters(sev=None, text="", show_ocr=False, hide_reviewed=False)
        self.search.clear(); self.chips["All"].setChecked(True); self.t_ocr.setChecked(False); self.t_hide.setChecked(False)
        self.count_lbl.setText(f"{self.proxy.rowCount()} shown"); self._scan_cache.clear(); self._cur_item = None
        self.t_left.clear(); self.t_right.clear(); self.detail_head.setText("Select a difference to compare both versions")
        self.scan.view.clear_msg("Select a difference to see where it sits on the scan.")
        if self.proxy.rowCount():
            self.table.selectRow(0)

    def _cur_row(self):
        ix = self.table.currentIndex()
        return self.proxy.mapToSource(ix).row() if ix.isValid() else -1

    def step(self, d):
        n = self.proxy.rowCount()
        if not n:
            return
        r = max(0, min(n - 1, self.table.currentIndex().row() + d if self.table.currentIndex().isValid() else 0)); self.table.selectRow(r)
        self.table.scrollTo(self.proxy.index(r, 0))

    def toggle_reviewed(self):
        r = self._cur_row()
        if r >= 0:
            self.model.toggle(r); self._update_review()
            if self.t_hide.isChecked():
                self.proxy.invalidateFilter()

    def _on_diff_select(self):
        r = self._cur_row()
        if r < 0:
            return
        it = self.model.item(r); self._cur_item = it
        col = SEV.get(it.severity, SEV["Info"])
        self.detail_head.setText(f"<span style='color:{col}'>●</span> #{it.id}  ·  Clause {rm.clause_label(it)}  ·  {it.severity}  ·  {', '.join(it.categories)}")
        left, right = rm.runs_for_item(it)
        self.t_left.setHtml(runs_html(left)); self.t_right.setHtml(runs_html(right)); self._show_scan()

    def _show_scan(self):
        it = self._cur_item; v = self.scan.view
        if not (self.result and it):
            return
        doc = self.result.doc_b
        if doc.kind not in ("pdf", "image") or not it.regions_b:
            v.clear_msg("No scan location is available for this item" + (" (the text is missing from the executed copy)." if it.kind == "deleted" else "."))
            self.scan.caption.setText(""); return
        try:
            from ..preview import page_with_highlight
            page = it.regions_b[0][0]
            if it.id not in self._scan_cache:
                if len(self._scan_cache) > 30:
                    self._scan_cache.clear()
                self._scan_cache[it.id] = page_with_highlight(doc, page, it.regions_b, dpi=config.PREVIEW_DPI)
            img, y = self._scan_cache[it.id]
            if img is not None:
                v.set_image(img, y); self.scan.caption.setText(f"Executed copy – page {page} of {doc.n_pages}")
        except Exception as ex:   # noqa
            v.clear_msg(f"Scan preview unavailable: {ex}")

    def _rotate_shown(self, delta):
        it = self._cur_item
        if not (self.result and it and it.regions_b):
            self.toast.show_msg("Select a difference that has a scan location first", "info"); return
        self.rotate_page(delta, it.regions_b[0][0], recompare=True)

    def _diff_menu(self, pos):
        r = self._cur_row()
        if r < 0:
            return
        it = self.model.item(r); m = QMenu(self)
        m.addAction("Mark / unmark reviewed", self.toggle_reviewed)
        m.addAction("Copy summary", lambda: QGuiApplication.clipboard().setText(f"#{it.id} {rm.clause_label(it)} [{it.severity}] {it.summary}"))
        m.addAction("Copy draft text", lambda: QGuiApplication.clipboard().setText(it.text_a)); m.addAction("Copy executed text", lambda: QGuiApplication.clipboard().setText(it.text_b))
        m.exec(self.table.viewport().mapToGlobal(pos))

    # ============================================================================ page: redline
    def _build_redline(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(12)
        bar, bl = card(QHBoxLayout, (14, 10, 14, 10), 8, "cardflat")
        self.red_find = QLineEdit(); self.red_find.setPlaceholderText("Find in redline…"); self.red_find.setClearButtonEnabled(True); self.red_find.setFixedWidth(280)
        self.red_find.returnPressed.connect(lambda: self.red.find(self.red_find.text())); bl.addWidget(self.red_find)
        fb = QPushButton("Find next"); fb.clicked.connect(lambda: self.red.find(self.red_find.text())); bl.addWidget(fb); bl.addStretch(1)
        self.red_size = 14
        for t, d in (("A−", -1), ("A+", 1)):
            b = QPushButton(t); b.setProperty("kind", "ghost"); b.clicked.connect(lambda _=False, d=d: self._red_font(d)); bl.addWidget(b)
        bl.addWidget(label("Red strike = draft wording removed or changed   ·   Green underline = executed copy only", "small"))
        v.addWidget(bar)
        self.red = QTextBrowser(); self.red.setObjectName("paper"); v.addWidget(self.red, 1)
        return w

    def _red_font(self, d):
        self.red_size = max(10, min(22, self.red_size + d)); self._fill_redline()

    def _fill_redline(self):
        if not self.result:
            return
        parts = []
        for row in self.result.rows:
            lab = row.label_b or row.label_a
            runs = ([(lab + " ", "plain")] if lab else []) + [(tx + " ", st) for tx, st in rm.redline_runs(row)]
            parts.append(runs_html(runs, self.red_size) + "<div style='height:8px'></div>")
        self.red.setHtml("".join(parts))

    # ============================================================================ page: align
    def _build_align(self):
        self.align = AlignView(self); return self.align

    # ============================================================================ page: reports
    def _build_reports(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 8, 0); v.setSpacing(16)
        oc, ol = card(spacing=12); ol.addWidget(label("What to include in the report", "h2")); g = QGridLayout(); g.setHorizontalSpacing(34); g.setVerticalSpacing(12); self.xt = {}
        for i, (k, t, d) in enumerate((("scans", "Scan extracts next to each difference", True), ("info", "Information items", True), ("ocr", "Probable OCR variances", False), ("red", "Full redline appendix", False))):
            tg = Toggle(t); tg.setChecked(d); self.xt[k] = tg; g.addWidget(tg, i // 2, i % 2)
        ol.addLayout(g); v.addWidget(oc)
        row = QHBoxLayout(); row.setSpacing(14)
        for kind, title, sub, ic in (("word", "Word report", "Editable .docx with the register, detailed comparison and scan extracts", "doc"),
                                     ("pdf", "PDF report", "Print-ready PDF with colour-coded severity", "report"),
                                     ("both", "Word + PDF", "Create both reports in one go in a folder you choose", "download")):
            c, l = card(spacing=8); l.addWidget(label(title, "h2")); l.addWidget(label(sub, "muted", True)); l.addStretch(1)
            b = QPushButton("  Create " + title); b.setProperty("kind", "primary" if kind != "both" else "gold"); b.setIcon(icon(ic, "#FFFFFF" if kind != "both" else "#2A1B00", 18)); b.clicked.connect(lambda _=False, k=kind: self.export(k)); l.addWidget(b); row.addWidget(c, 1)
        v.addLayout(row)
        rc, rl = card(spacing=8); rl.addWidget(label("Register of differences", "h2")); rl.addWidget(label("Export the list (with your “reviewed” ticks) to open in Excel, or copy it to the clipboard.", "muted", True))
        rr = QHBoxLayout(); b1 = QPushButton(" Export CSV (Excel)"); b1.setIcon(icon("table", pal()["text"], 18)); b1.clicked.connect(self.export_csv)
        b2 = QPushButton(" Copy to clipboard"); b2.setIcon(icon("copy", pal()["text"], 18)); b2.clicked.connect(self.copy_register); rr.addWidget(b1); rr.addWidget(b2); rr.addStretch(1); rl.addLayout(rr); v.addWidget(rc)
        self.exp_card, self.exp_l = card(spacing=8); self.exp_l.addWidget(label("Reports created in this session", "h2")); self.exp_box = QVBoxLayout(); self.exp_l.addLayout(self.exp_box); v.addWidget(self.exp_card); self.exp_card.hide()
        v.addStretch(1); return scroll(w)

    def _kw(self):
        return dict(include_info=self.xt["info"].isChecked(), include_ocr=self.xt["ocr"].isChecked(), include_scans=self.xt["scans"].isChecked(), include_redline=self.xt["red"].isChecked())

    def export(self, kind):
        if not self.result:
            self.toast.show_msg("Run a comparison first", "err"); return
        base = os.path.splitext(os.path.basename(self.drop_b.path or self.result.doc_b.name or "comparison"))[0]; res = self.result; kw = self._kw()
        if kind == "both":
            d = QFileDialog.getExistingDirectory(self, "Choose a folder for the reports")
            if not d:
                return
            jobs = [("word", os.path.join(d, f"Comparison_Report_{base}.docx")), ("pdf", os.path.join(d, f"Comparison_Report_{base}.pdf"))]
        else:
            ext = ".docx" if kind == "word" else ".pdf"
            p, _ = QFileDialog.getSaveFileName(self, "Save comparison report", f"Comparison_Report_{base}{ext}", "Word document (*.docx)" if kind == "word" else "PDF (*.pdf)")
            if not p:
                return
            jobs = [(kind, p)]

        def job(progress, cancel):
            out = []
            for i, (k, path) in enumerate(jobs):
                sub = lambda f, m, i=i: progress((i + f) / len(jobs), m)
                if k == "word":
                    from ..export_word import export_word; export_word(res, path, progress=sub, **kw)
                else:
                    from ..export_pdf import export_pdf; export_pdf(res, path, progress=sub, **kw)
                out.append(path)
            return out
        self.run_task(job, self._exported, "Creating the report…", cancellable=False)

    def _exported(self, paths):
        self.toast.show_msg(f"Saved {len(paths)} report(s)"); self.exp_card.show()
        for p in paths:
            b = QPushButton(f"  {p}"); b.setProperty("kind", "ghost"); b.setStyleSheet("text-align:left;"); b.setToolTip("Open the folder")
            b.clicked.connect(lambda _=False, p=p: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(p)))); self.exp_box.addWidget(b)

    def _register_rows(self):
        rows = [["Accepted", "#", "Clause", "Severity", "Category", "Nature of difference", "Draft text", "Executed text", "Pages (executed)"]]
        for it in self.result.items:
            if it.ocr_only:
                continue
            rows.append(["Yes" if it.id in self.model.reviewed else "", it.id, rm.clause_label(it), it.severity, ", ".join(it.categories), it.summary, it.text_a, it.text_b, ",".join(str(p) for p in it.pages_b)])
        return rows

    def export_csv(self):
        if not self.result:
            self.toast.show_msg("Run a comparison first", "err"); return
        p, _ = QFileDialog.getSaveFileName(self, "Save register", "Register_of_differences.csv", "CSV (*.csv)")
        if p:
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerows(self._register_rows())
            self.toast.show_msg("Register saved")

    def copy_register(self):
        if self.result:
            QGuiApplication.clipboard().setText("\n".join("\t".join(str(x).replace("\t", " ").replace("\n", " ") for x in r) for r in self._register_rows())); self.toast.show_msg("Register copied")

    # ============================================================================ page: settings
    def _build_settings(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 8, 0); v.setSpacing(16)
        c, l = card(spacing=12); l.addWidget(label("Theme", "h2")); row = QHBoxLayout(); row.setSpacing(14); self.theme_btns = {}
        for name, p in THEMES.items():
            b = QPushButton(); b.setCheckable(True); b.setFixedSize(220, 96); b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"QPushButton{{border:2px solid {p['border']};border-radius:16px;text-align:left;padding:12px 16px;font-weight:800;color:{p['text']};"
                            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {p['bg']},stop:0.55 {p['surface2']},stop:1 {p['primary']});}}"
                            f"QPushButton:checked{{border:2px solid {p['gold']};}}")
            b.setText(name + ("\n●  dark" if p["dark"] else "\n○  light")); b.clicked.connect(lambda _=False, n=name: self.apply_theme(n)); row.addWidget(b); self.theme_btns[name] = b
        row.addStretch(1); l.addLayout(row)
        r2 = QHBoxLayout(); r2.addWidget(label("Text size", "muted")); self.scale_cb = QComboBox(); self.scale_cb.addItems(["Compact (90%)", "Normal (100%)", "Large (112%)", "Extra large (125%)"])
        self.scale_cb.setCurrentIndex({0.9: 0, 1.0: 1, 1.12: 2, 1.25: 3}.get(round(self.scale, 2), 1)); self.scale_cb.currentIndexChanged.connect(self._scale_changed); r2.addWidget(self.scale_cb); r2.addStretch(1); l.addLayout(r2)
        v.addWidget(c)
        kc, kl = card(spacing=6); kl.addWidget(label("Keyboard shortcuts", "h2"))
        for k, t in (("Ctrl + K", "Command palette – every action in one searchable list"), ("Ctrl + Enter", "Run the comparison"), ("Ctrl + O / Ctrl + Shift + O", "Choose the draft / executed copy"),
                     ("Ctrl + 1 … 7", "Jump between the pages"), ("F3 / Shift + F3", "Next / previous difference"), ("Space (in the table)", "Mark the selected difference as reviewed"),
                     ("Ctrl + E / Ctrl + Shift + E", "Create Word / PDF report"), ("Ctrl + T", "Switch theme"), ("Ctrl + B", "Collapse / expand the menu")):
            r = QHBoxLayout(); a = label(k, "gold"); a.setMinimumWidth(240); r.addWidget(a); r.addWidget(label(t, "muted"), 1); wd = QWidget(); wd.setLayout(r); r.setContentsMargins(0, 0, 0, 0); kl.addWidget(wd)
        v.addWidget(kc)
        ac, al = card(spacing=4); al.addWidget(label("About", "h2"))
        al.addWidget(label(f"Agreement Compare {__version__} · Qt 6 interface (PySide6). Everything runs on this computer – no document leaves it.", "muted", True))
        al.addWidget(label(rm.DISCLAIMER, "small", True)); v.addWidget(ac); v.addStretch(1)
        return scroll(w)

    def _scale_changed(self, i):
        self.scale = [0.9, 1.0, 1.12, 1.25][i]; self.st.setValue("scale", self.scale); self.apply_theme(self.theme_name, save=False)

    def apply_theme(self, name, save=True):
        self.theme_name = name; p = theme.set_pal(name)
        if save:
            self.st.setValue("theme", name)
        QApplication.instance().setStyleSheet(qss(p, self.scale))
        self.crown.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {p['primary']},stop:1 {p['primary2']});border-radius:14px;")
        self.crown.setPixmap(icon("crown", p["gold"], 26, 2.1).pixmap(26, 26)); self._nav_icons()
        self.btn_cmd.setIcon(icon("cmd", p["muted"], 18)); self.btn_theme.setIcon(icon("moon" if p["dark"] else "sun", p["muted"], 18)); self.btn_collapse.setIcon(icon("menu", p["muted"], 18))
        self.btn_go.setIcon(icon("play", "#FFFFFF", 20)); self.btn_pages.setIcon(icon("list", p["text"], 18)); self.btn_cancel.setIcon(icon("x", "#FF8DA0", 16))
        self.btn_go_more.setIcon(icon("chev", "#FFFFFF", 18)); self.btn_go_more.setStyleSheet("QToolButton{border:none;border-top-right-radius:10px;border-bottom-right-radius:10px;padding:0 12px;background:%s;}" % p["primary2"])
        self.dash_export.setIcon(icon("download", "#2A1B00", 18)); self.dash_export.setStyleSheet(f"QToolButton{{background:{p['gold']};color:#2A1B00;font-weight:800;border:none;border-radius:10px;padding:10px 18px;}}")
        self.activity.setStyleSheet("QFrame#topbar{border-top:1px solid %s;border-bottom:none;}" % p["border"])
        for b, ic in ((self.btn_prev, "up"), (self.btn_next, "chev"), (self.btn_rev, "done")):
            b.setIcon(icon(ic, "#2A1B00" if b is self.btn_rev else p["text"], 17))
        for d in (self.drop_a, self.drop_b):
            d.refresh_theme()
        self.scan.refresh_theme(); self.align.refresh_theme()
        for n, b in self.theme_btns.items():
            b.setChecked(n == name)
        self._refresh_chip()
        for wdg in self.findChildren(QWidget):
            if wdg.property("role") or wdg.property("kind"):
                repolish(wdg)
        if self.result:
            self._fill_redline(); self._on_diff_select() if self._cur_row() >= 0 else None

    def cycle_theme(self):
        names = list(THEMES); self.apply_theme(names[(names.index(self.theme_name) + 1) % len(names)])

    # ============================================================================ results
    def set_result(self, r, fresh=True):
        self.result = r; self._scan_cache.clear()
        self._fill_diff(); self._fill_dashboard(); self._fill_redline()
        if fresh:
            self.align.load(r); self.goto("dash")
            self.toast.show_msg(f"Comparison complete – {r.stats['total']} difference(s) found")
        else:
            self.toast.show_msg(f"Re-comparison complete – {r.stats['total']} difference(s)" + (f" · {r.anchors_used} link(s) applied" if getattr(r, "anchors_used", 0) else ""))
            self.goto("diff")
        self.msg.setText(f"Comparison complete – {r.stats['total']} difference(s) found."); self._refresh_chip()

    # ============================================================================ palette & shortcuts
    def commands(self):
        return [("New comparison", "Ctrl+1", "play", lambda: self.goto("compare")), ("Run the comparison", "Ctrl+Enter", "bolt", self.start_compare),
                ("Choose Word draft…", "Ctrl+O", "doc", self.drop_a.browse), ("Choose executed copy…", "Ctrl+Shift+O", "scan", self.drop_b.browse),
                ("Select pages of the executed copy…", "", "list", self.pick_pages),
                ("Dashboard", "Ctrl+2", "dash", lambda: self.goto("dash")), ("Differences", "Ctrl+3", "list", lambda: self.goto("diff")), ("Redline", "Ctrl+4", "pen", lambda: self.goto("red")),
                ("Align & edit", "Ctrl+5", "align", lambda: self.goto("align")), ("Reports", "Ctrl+6", "report", lambda: self.goto("rep")), ("Settings", "Ctrl+7", "settings", lambda: self.goto("set")),
                ("Export Word report", "Ctrl+E", "download", lambda: self.export("word")), ("Export PDF report", "Ctrl+Shift+E", "download", lambda: self.export("pdf")),
                ("Export Word + PDF", "", "download", lambda: self.export("both")), ("Export register as CSV", "", "table", self.export_csv),
                ("Re-compare with adjustments", "", "play", lambda: self.align.do_recompare()), ("Save alignment session…", "", "save", lambda: self.align.do_save()),
                ("Load alignment session…", "", "upload", lambda: self.align.do_load()), ("Next difference", "F3", "chev", lambda: (self.goto("diff"), self.step(1))),
                ("Previous difference", "Shift+F3", "chev", lambda: (self.goto("diff"), self.step(-1))), ("Mark difference as reviewed", "Space", "done", self.toggle_reviewed),
                ("Switch theme", "Ctrl+T", "moon", self.cycle_theme), ("Collapse / expand menu", "Ctrl+B", "menu", self.toggle_sidebar), ("Swap draft and executed files", "", "rotl", self.swap_files)]

    def open_palette(self):
        CommandPalette(self, self.commands()).show()

    def _shortcuts(self):
        def sc(keys, fn):
            QShortcut(QKeySequence(keys), self, activated=fn)
        sc("Ctrl+K", self.open_palette); sc("Ctrl+Return", self.start_compare); sc("Ctrl+O", self.drop_a.browse); sc("Ctrl+Shift+O", self.drop_b.browse)
        for i, (k, *_r) in enumerate(NAV):
            sc(f"Ctrl+{i + 1}", lambda k=k: self.goto(k))
        sc("F3", lambda: self.step(1)); sc("Shift+F3", lambda: self.step(-1)); sc("Ctrl+E", lambda: self.export("word")); sc("Ctrl+Shift+E", lambda: self.export("pdf"))
        sc("Ctrl+T", self.cycle_theme); sc("Ctrl+B", self.toggle_sidebar); sc("Ctrl+F", lambda: (self.goto("diff"), self.search.setFocus()))
        QShortcut(QKeySequence(Qt.Key_Space), self.table, activated=self.toggle_reviewed, context=Qt.WidgetShortcut)

    def resizeEvent(self, e):
        super().resizeEvent(e)

    def closeEvent(self, e):
        self.st.setValue("geometry", self.saveGeometry())
        if self.worker and self.worker.isRunning():
            self.worker.cancel(); self.worker.wait(1500)
        super().closeEvent(e)


def run():
    from .classic import run as _run
    return _run()
