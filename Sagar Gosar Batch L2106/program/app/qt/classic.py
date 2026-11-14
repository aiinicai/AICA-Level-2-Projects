"""Classic interface – flat, one-accent (navy), built for full-screen analysis.

Tabs:  Setup | Summary | Analysis | Side-by-side | Redline | Align & edit | Reports
"""
import os
import sys
from collections import Counter
from html import escape

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMainWindow, QMenu, QMessageBox, QFileDialog, QProgressBar, QPushButton, QScrollArea, QSplitter, QStackedWidget,
                               QTableView, QTextBrowser, QVBoxLayout, QWidget)

from .. import __version__, config
from .. import report_model as rm
from . import theme
from .align_view import AlignView
from .diffs import DiffModel, DiffProxy, PillDelegate, runs_html
from .theme import SEV, icon, pal, qss_classic
from .widgets import DropCard, ScanPanel, Toast, label
from .window import MainWindow

TABS = [("setup", "Setup"), ("summary", "Summary"), ("analysis", "Analysis"), ("sbs", "Side-by-side"),
        ("redline", "Redline"), ("align", "Align & edit"), ("reports", "Reports")]
ALIAS = {"compare": "setup", "dash": "summary", "diff": "analysis", "red": "redline", "rep": "reports", "set": "setup"}

RED, GREEN, AMBER = "#B42318", "#067647", "#92400E"
RED_BG, GREEN_BG, AMBER_BG = "#FDE4E1", "#D9F2E3", "#FEF3C7"
GREY_BG = "#F1F2F4"


def _cell(runs, size):
    """Runs -> inline html with the classic red / green marking (no wrapper block)."""
    out = []
    for text, style in runs:
        t = escape(text).replace("\n", "<br>")
        if style == "del":
            out.append(f'<span style="color:{RED};background-color:{RED_BG};text-decoration:line-through">{t}</span>')
        elif style == "ins":
            out.append(f'<span style="color:{GREEN};background-color:{GREEN_BG};text-decoration:underline">{t}</span>')
        elif style == "ocr":
            out.append(f'<span style="color:{AMBER};background-color:{AMBER_BG};font-style:italic">{t}</span>')
        else:
            out.append(t)
    return f'<div style="font-size:{size}px;line-height:140%">' + "".join(out) + "</div>"


def _pane_html(runs, size):
    return _cell(runs, size).replace("line-height:140%", "line-height:150%")


def row_changed(row, show_ocr):
    return any(t not in ("equal",) and (t != "ocr" or show_ocr) for t, *_ in row.ops)


def side_runs(row, show_ocr):
    """-> (left_runs, right_runs) for one Row, red = removed from old, green = new in executed."""
    L, R = [], []
    for tag, ta, tb in row.ops:
        if tag == "equal":
            if ta:
                L.append((ta + " ", "plain"))
            if tb:
                R.append((tb + " ", "plain"))
        elif tag == "ocr":
            st = "ocr" if show_ocr else "plain"
            if ta:
                L.append((ta + " ", st))
            if tb:
                R.append((tb + " ", st))
        else:
            if ta and tag in ("delete", "replace"):
                L.append((ta + " ", "del"))
            if tb and tag in ("insert", "replace"):
                R.append((tb + " ", "ins"))
    return L, R


def red_runs(row, show_ocr):
    out = []
    for tag, ta, tb in row.ops:
        if tag == "equal":
            out.append(((tb or ta) + " ", "plain"))
        elif tag == "ocr":
            out.append(((tb or ta) + " ", "ocr" if show_ocr else "plain"))
        else:
            if ta and tag in ("delete", "replace"):
                out.append((ta + " ", "del"))
            if tb and tag in ("insert", "replace"):
                out.append((tb + " ", "ins"))
    return out


class ClassicWindow(MainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.st = QSettings("AgreementCompare", "ClassicUI")
        self.setWindowTitle(f"{config.APP_NAME}  ·  v{__version__}")
        self.setMinimumSize(1000, 640)
        self.result = None; self.worker = None; self.page_sel = None; self.page_total = 0
        self._scan_cache = {}; self._cur_item = None; self.scale = float(self.st.value("scale", 1.0))
        self.theme_name = "Classic"; theme.use_classic()
        self._sbs_anchors = []; self._sbs_pos = -1; self._red_anchors = []; self._red_pos = -1; self.red_size = 15; self.sbs_size = 14
        self._first_show = True

        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        v = QVBoxLayout(root); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        v.addWidget(self._build_navbar())
        self.stack = QStackedWidget(); v.addWidget(self.stack, 1)
        self.keys = [k for k, _ in TABS]
        for key, builder in (("setup", self._build_setup), ("summary", self._build_summary), ("analysis", self._build_analysis),
                             ("sbs", self._build_sbs), ("redline", self._build_redline_tab), ("align", self._build_align), ("reports", self._build_reports)):
            self.stack.addWidget(builder())
        v.addWidget(self._build_status())
        self.toast = Toast(root)
        self._shortcuts()
        self.apply_theme()
        self.goto("setup")
        self._load_recent()
        from .. import ocr_boost
        if not ocr_boost.have_cv():
            self.set_status("OpenCV is not available – seal-aware recovery runs in a reduced mode (colour seals only).", "warn")
        if not config.configure_tesseract():
            self.set_status("Tesseract OCR was not found – scanned PDFs cannot be read. Re-extract the package or see README.", "warn")

    # ------------------------------------------------------------------ chrome
    def _build_navbar(self):
        nb = QFrame(); nb.setObjectName("navbar"); nb.setFixedHeight(48); self.navbar = nb
        h = QHBoxLayout(nb); h.setContentsMargins(14, 0, 12, 0); h.setSpacing(0)
        nm = QLabel("AGREEMENT COMPARE"); nm.setObjectName("appname"); h.addWidget(nm); h.addSpacing(26)
        self.tab_group = QButtonGroup(self); self.tab_group.setExclusive(True); self.tab_btns = {}
        for key, text in TABS:
            b = QPushButton(text.replace("&", "&&")); b.setCheckable(True); b.setProperty("kind", "tab"); b.setFixedHeight(48); b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.goto(k)); self.tab_group.addButton(b); self.tab_btns[key] = b; h.addWidget(b)
        h.addStretch(1)
        self.chip = QLabel("Ready"); self.chip.setObjectName("navinfo"); h.addWidget(self.chip); h.addSpacing(16)
        self.btn_full = QPushButton("Full screen  (F11)"); self.btn_full.setProperty("kind", "navbtn"); self.btn_full.clicked.connect(self.toggle_full); h.addWidget(self.btn_full)
        return nb

    def _build_status(self):
        f = QFrame(); f.setObjectName("statusbar"); f.setFixedHeight(34); self.activity = f
        h = QHBoxLayout(f); h.setContentsMargins(14, 0, 14, 0); h.setSpacing(12)
        self.msg = label("Choose the two documents on the Setup tab and press Compare.", "muted"); h.addWidget(self.msg, 1)
        self.bar = QProgressBar(); self.bar.setRange(0, 1000); self.bar.setFixedWidth(320); self.bar.setFixedHeight(12); self.bar.setTextVisible(False); h.addWidget(self.bar)
        self.btn_cancel = QPushButton("Cancel"); self.btn_cancel.setProperty("kind", "danger"); self.btn_cancel.clicked.connect(self.cancel_task); h.addWidget(self.btn_cancel)
        self.bar.hide(); self.btn_cancel.hide()
        return f

    def goto(self, key):
        key = ALIAS.get(key, key); self.stack.setCurrentIndex(self.keys.index(key)); self.tab_btns[key].setChecked(True)
        if key == "sbs" and self.result and not self._sbs_anchors and not self._sbs_html_done:
            self._fill_sbs()

    def toggle_full(self):
        if self.isFullScreen():
            self.showMaximized(); self.btn_full.setText("Full screen  (F11)")
        else:
            self.showFullScreen(); self.btn_full.setText("Exit full screen  (Esc)")

    def set_status(self, text, kind="info"):
        self.msg.setText(text)

    def set_chip(self, text, kind="info"):
        self.chip.setText(text)

    def _busy(self, on, text="", cancellable=True):
        self.bar.setVisible(on); self.btn_cancel.setVisible(on and cancellable); self.bar.setValue(0)
        if on:
            self.msg.setText(text); self.set_chip("Working…")
        else:
            self._refresh_chip()
        for b in (self.btn_go, self.btn_quick):
            b.setEnabled(not on)

    def _refresh_chip(self):
        if self.result:
            s = self.result.stats; b = s["by_severity"]
            self.set_chip(f"{s['total']} differences   ·   Critical {b['Critical']}   Major {b['Major']}   Minor {b['Minor']}   Info {b['Info']}")
        else:
            self.set_chip("Ready")

    # ------------------------------------------------------------------ setup tab
    def _build_setup(self):
        w = QWidget(); w.setObjectName("page"); v = QVBoxLayout(w); v.setContentsMargins(40, 28, 40, 20); v.setSpacing(14)
        t = label("New comparison", "title"); v.addWidget(t)
        v.addWidget(label("Select the Word draft and the executed (signed, scanned) copy. Stamps, seals and signatures are ignored; paragraph breaks "
                          "need not agree. Everything runs on this computer.", "muted", True))
        row = QHBoxLayout(); row.setSpacing(16)
        self.drop_a = DropCard("Old agreement – Word draft (.docx)", "Drop the Word file here, or click to browse", "doc", (".docx",))
        self.drop_b = DropCard("New agreement – executed copy (PDF / image)", "Drop the signed, scanned PDF here, or click to browse", "scan",
                               (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"))
        self.drop_b.fileChosen.connect(self._file_b_changed)
        row.addWidget(self.drop_a, 1); row.addWidget(self.drop_b, 1); v.addLayout(row)

        pr = QHBoxLayout(); self.btn_pages = QPushButton("Select pages of the executed copy…"); self.btn_pages.setEnabled(False); self.btn_pages.clicked.connect(self.pick_pages)
        pr.addWidget(self.btn_pages); self.pages_lbl = label("Choose the executed PDF first – you can then leave out stamp-paper, blank or annexure pages.", "muted", True)
        pr.addWidget(self.pages_lbl, 1); v.addLayout(pr)

        box = QFrame(); box.setObjectName("card"); bl = QVBoxLayout(box); bl.setContentsMargins(18, 14, 18, 14); bl.setSpacing(10)
        bl.addWidget(label("Comparison settings", "h2"))
        g = QGridLayout(); g.setHorizontalSpacing(30); g.setVerticalSpacing(8); self.tg = {}
        spec = [("ignore_case", "Ignore capitalisation", True), ("compare_punct", "Compare punctuation", False),
                ("ocr_tolerance", "Treat OCR look-alikes as OCR variance", True), ("force_ocr", "Force OCR on every page", False),
                ("reflow", "Smart paragraph alignment", True), ("ignore_stamps", "Ignore stamps && registration text", True),
                ("ignore_colour_ink", "Remove coloured ink (seals / pen)", True), ("enhance_scan", "Enhance scan before reading", True),
                ("upright", "Pages are already upright (skip rotation check)", False),
                ("seal_recovery", "Seal-aware recovery (text under / after round seals)", True),
                ("second_engine", "Deep-learning second opinion if installed (slower)", True)]
        for i, (k, tx, d) in enumerate(spec):
            c = QCheckBox(tx); c.setChecked(self.st.value("opt_" + k, d, type=bool)); c.toggled.connect(lambda x, k=k: self.st.setValue("opt_" + k, x))
            self.tg[k] = c; g.addWidget(c, i // 3, i % 3)
        bl.addLayout(g)
        r2 = QHBoxLayout(); r2.setSpacing(8); r2.addWidget(label("OCR resolution (dpi)", "muted"))
        self.dpi = QComboBox(); self.dpi.addItems(["200", "300", "400"]); self.dpi.setCurrentText(str(self.st.value("dpi", "300"))); r2.addWidget(self.dpi)
        r2.addSpacing(18); r2.addWidget(label("OCR language", "muted")); self.lang = QLineEdit(str(self.st.value("lang", "eng"))); self.lang.setFixedWidth(80); r2.addWidget(self.lang)
        r2.addStretch(1); bl.addLayout(r2); v.addWidget(box)

        ar = QHBoxLayout(); ar.setSpacing(10)
        self.btn_go = QPushButton("Compare documents"); self.btn_go.setProperty("kind", "primary"); self.btn_go.setMinimumHeight(44); self.btn_go.setCursor(Qt.PointingHandCursor)
        self.btn_go.clicked.connect(lambda: self.start_compare()); ar.addWidget(self.btn_go)
        self.btn_quick = QPushButton("Quick compare (skip enhancement)"); self.btn_quick.clicked.connect(lambda: self.start_compare(quick=True)); ar.addWidget(self.btn_quick)
        b = QPushButton("Swap files"); b.clicked.connect(self.swap_files); ar.addWidget(b)
        b = QPushButton("Clear"); b.clicked.connect(self.clear_files); ar.addWidget(b); ar.addStretch(1); v.addLayout(ar)

        self.recent_card = QFrame(); self.recent_card.setObjectName("card"); rl = QVBoxLayout(self.recent_card); rl.setContentsMargins(18, 12, 18, 12); rl.setSpacing(4)
        rl.addWidget(label("Recent comparisons", "h2")); self.recent_box = QVBoxLayout(); rl.addLayout(self.recent_box); v.addWidget(self.recent_card)
        v.addStretch(1)
        s = QScrollArea(); s.setWidgetResizable(True); s.setFrameShape(QFrame.NoFrame); s.setWidget(w); return s

    def _load_recent(self):
        while self.recent_box.count():
            it = self.recent_box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        rec = self._recent_list(); self.recent_card.setVisible(bool(rec))
        for x in rec[:5]:
            a, b = x.split("|", 1)
            btn = QPushButton(f"{os.path.basename(a)}   ⇄   {os.path.basename(b)}"); btn.setProperty("kind", "ghost"); btn.setStyleSheet("text-align:left;border:none;background:transparent;")
            btn.setToolTip(f"{a}\n{b}"); btn.clicked.connect(lambda _=False, a=a, b=b: self._use_recent(a, b)); self.recent_box.addWidget(btn)

    # ------------------------------------------------------------------ summary tab
    def _build_summary(self):
        self.summary = QTextBrowser(); self.summary.setObjectName("paper"); self.summary.setOpenLinks(False)
        self.summary.setHtml("<p style='color:#586272;font-size:15px'>No comparison yet – start one on the Setup tab.</p>")
        return self.summary

    def _fill_summary(self):
        r = self.result; s = r.stats; b = s["by_severity"]
        cnt = Counter(c for it in r.items if not it.ocr_only for c in it.categories)
        th = "background:#1F3A5F;color:white;padding:6px 10px;text-align:left"; td = "padding:6px 10px;border-bottom:1px solid #D5D9DF"
        h = [f"<div style='font-size:13px'><h2 style='color:#1F3A5F;margin-bottom:2px'>Comparison summary</h2>",
             f"<p style='color:#586272'>{escape(r.doc_a.name)} &nbsp;⇄&nbsp; {escape(r.doc_b.name)}</p>",
             "<table cellspacing=0 cellpadding=0 width=100%><tr>"]
        for k, col in (("Total", "#1F3A5F"), ("Critical", SEV["Critical"]), ("Major", SEV["Major"]), ("Minor", SEV["Minor"]), ("Info", SEV["Info"])):
            n = s["total"] if k == "Total" else b[k]
            h.append(f"<td align=center style='border:1px solid #C5CBD3;padding:10px'><span style='font-size:30px;font-weight:700;color:{col}'>{n}</span><br>"
                     f"<span style='color:#586272'>{'Total differences' if k == 'Total' else k}</span></td>")
        h.append("</tr></table><br>")
        h.append("<p>" + "<br>".join(escape(x) for x in rm.summary_lines(r)) + "</p>")
        if cnt:
            h.append(f"<h3 style='color:#1F3A5F'>Differences by category</h3><table width=60% cellspacing=0><tr><td style='{th}'>Category</td><td style='{th}' align=right>Count</td></tr>")
            for c, n in cnt.most_common():
                h.append(f"<tr><td style='{td}'>{escape(c)}</td><td style='{td}' align=right>{n}</td></tr>")
            h.append("</table>")
        h.append("<h3 style='color:#1F3A5F'>Observations</h3><table width=100% cellspacing=0>")
        for sev, tx in r.observations or [("Info", "No observations.")]:
            h.append(f"<tr><td style='{td};color:{SEV.get(sev, SEV['Info'])};font-weight:700' width=80>{escape(sev)}</td><td style='{td}'>{escape(tx)}</td></tr>")
        h.append("</table>")
        kl, kr = rm.keyfigure_rows(r)
        if kl:
            h.append("<h3 style='color:#1F3A5F'>Key figures reconciliation</h3><p>" + "<br>".join(escape(x) for x in kl) + "</p>")
            if kr:
                h.append(f"<table width=100% cellspacing=0><tr>" + "".join(f"<td style='{th}'>{x}</td>" for x in ("Figure", "Draft", "Executed copy", "Clause", "Status")) + "</tr>")
                for kind, a_, b_, cl, stt in kr:
                    col = "#B42318" if stt.startswith(("Changed", "Missing")) else "#B54708"
                    h.append(f"<tr><td style='{td}'>{kind}</td><td style='{td}'>{escape(a_)}</td><td style='{td}'>{escape(b_)}</td><td style='{td}'>{escape(cl)}</td><td style='{td};color:{col};font-weight:600'>{escape(stt)}</td></tr>")
                h.append("</table>")
        oq = rm.ocr_quality(r)
        if oq:
            h.append("<h3 style='color:#1F3A5F'>Scan reading quality (executed copy)</h3><table width=60% cellspacing=0><tr>" + "".join(f"<td style='{th}'>{x}</td>" for x in ("Page", "OCR confidence", "Words read", "Assessment")) + "</tr>")
            for p_, cf, nw, note in oq:
                col = "#B42318" if cf < 80 else ("#B54708" if cf < 88 else "#1F7A4D")
                h.append(f"<tr><td style='{td}'>{p_}</td><td style='{td}'>{cf:.0f}%</td><td style='{td}'>{nw}</td><td style='{td};color:{col};font-weight:600'>{note}</td></tr>")
            h.append("</table>")
        if r.doc_b.warnings:
            h.append("<h3 style='color:#1F3A5F'>Reading notes</h3><p>" + "<br>".join(escape(x) for x in r.doc_b.warnings) + "</p>")
        h.append("<h3 style='color:#1F3A5F'>Documents</h3><table width=100% cellspacing=0>")
        for role, lab, (name, size, mod, sha, extra) in rm.meta_rows(r):
            h.append(f"<tr><td style='{td}' width=110><b>{escape(role)}</b></td><td style='{td}'>{escape(name)}<br><span style='color:#586272'>{size}, {escape(extra)}<br>SHA-256 {sha}</span></td></tr>")
        h.append(f"</table><p style='color:#586272;font-size:11px'>{escape(rm.DISCLAIMER)}</p></div>")
        self.summary.setHtml("".join(h))

    # ------------------------------------------------------------------ analysis tab
    def _build_analysis(self):
        w = QWidget(); w.setObjectName("page"); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        tb = QFrame(); tb.setObjectName("toolbar"); h = QHBoxLayout(tb); h.setContentsMargins(10, 6, 10, 6); h.setSpacing(8)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search…  (Ctrl+F)"); self.search.setClearButtonEnabled(True); self.search.setFixedWidth(210); h.addWidget(self.search)
        self.chips = {}; grp = QButtonGroup(self); grp.setExclusive(True)
        for k in ("All", "Critical", "Major", "Minor", "Info"):
            b = QPushButton(k); b.setCheckable(True); b.setProperty("kind", "chip"); b.setChecked(k == "All"); grp.addButton(b); self.chips[k] = b; h.addWidget(b)
            b.clicked.connect(lambda _=False, k=k: self._filter(sev=None if k == "All" else k))
        h.addSpacing(4)
        self.cat_box = QComboBox(); self.cat_box.setMinimumWidth(150); self.cat_box.setToolTip("Filter by type of difference (amount, date, legal-effect wording …)")
        self.page_box = QComboBox(); self.page_box.setToolTip("Filter by page of the executed copy")
        self.cat_box.currentIndexChanged.connect(lambda _i: self._filter(cat=self.cat_box.currentData())); self.page_box.currentIndexChanged.connect(lambda _i: self._filter(page=self.page_box.currentData()))
        h.addWidget(self.cat_box); h.addWidget(self.page_box); h.addSpacing(4)
        self.t_ocr = QCheckBox("OCR variances"); self.t_hide = QCheckBox("Hide accepted"); h.addWidget(self.t_ocr); h.addWidget(self.t_hide)
        h.addStretch(1)
        self.count_lbl = label("", "muted"); self.rev_lbl = label("", "gold"); h.addWidget(self.count_lbl); h.addSpacing(6); h.addWidget(self.rev_lbl); h.addSpacing(10)
        self.btn_prev = QPushButton("◀  Previous"); self.btn_next = QPushButton("Next  ▶"); self.btn_rev = QPushButton("✓  Accept change"); self.btn_rev.setProperty("kind", "gold")
        self.btn_prev.setToolTip("Previous difference  (Shift+F3)"); self.btn_next.setToolTip("Next difference  (F3)"); self.btn_rev.setToolTip("Accept this difference as proper – accepted changes can be saved into an updated Word file  (Space)")
        self.btn_prev.clicked.connect(lambda: self.step(-1)); self.btn_next.clicked.connect(lambda: self.step(1)); self.btn_rev.clicked.connect(self.toggle_reviewed)
        self.btn_more = QPushButton("Accept ▾"); mn = QMenu(self.btn_more)
        mn.addAction("Accept all shown", self.accept_shown); mn.addAction("Accept all shown Critical + Major", lambda: self.accept_shown(("Critical", "Major")))
        mn.addAction("Clear all accepted", self.clear_accepted); self.btn_more.setMenu(mn)
        for b in (self.btn_prev, self.btn_next, self.btn_rev, self.btn_more):
            h.addWidget(b)
        v.addWidget(tb)

        self.an_split = QSplitter(Qt.Horizontal); self.an_split.setChildrenCollapsible(False)
        self.an_left = QSplitter(Qt.Vertical); self.an_left.setChildrenCollapsible(False)
        self.model = DiffModel(); self.proxy = DiffProxy(); self.proxy.setSourceModel(self.model)
        self.table = QTableView(); self.table.setModel(self.proxy); self.table.setSelectionBehavior(QTableView.SelectRows); self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.verticalHeader().setVisible(False); self.table.setShowGrid(False); self.table.setWordWrap(False); self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(30); hd = self.table.horizontalHeader(); hd.setStretchLastSection(False)
        for i, wd in enumerate((34, 40, 70, 100, 170, 0, 40)):
            if wd:
                hd.setSectionResizeMode(i, QHeaderView.Fixed); self.table.setColumnWidth(i, wd)
            else:
                hd.setSectionResizeMode(i, QHeaderView.Stretch)
        self.table.setItemDelegateForColumn(0, PillDelegate(self.table)); self.table.setItemDelegateForColumn(3, PillDelegate(self.table))
        self.table.selectionModel().currentRowChanged.connect(lambda cur, _p: self._on_diff_select())
        self.table.clicked.connect(lambda ix: self.toggle_reviewed() if ix.column() == 0 else None)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu); self.table.customContextMenuRequested.connect(self._diff_menu)
        self.an_left.addWidget(self.table)

        panes = QSplitter(Qt.Horizontal); panes.setChildrenCollapsible(False)
        self.t_left, self.head_left = self._pane(panes, RED, "OLD AGREEMENT", "Word draft")
        self.t_right, self.head_right = self._pane(panes, GREEN, "NEW AGREEMENT", "executed copy")
        self.an_left.addWidget(panes); self.an_left.setStretchFactor(0, 4); self.an_left.setStretchFactor(1, 6)
        self.an_split.addWidget(self.an_left)

        self.scan = ScanPanel("Executed copy – scan", rotate=True); self.scan.view.setAlignment(Qt.AlignTop | Qt.AlignHCenter); self.scan.rotateRequested.connect(self._rotate_shown)
        row = QHBoxLayout(); row.setSpacing(0); self.mode_btns = {}
        for key, text in (("page", "Whole page"), ("zoom", "Zoom to difference")):
            b = QPushButton(text); b.setCheckable(True); b.setProperty("kind", "chip"); b.setChecked(key == "zoom" if self.st.value("scan_zoom", True, type=bool) else key == "page")
            b.clicked.connect(lambda _=False, k=key: self._set_scan_mode(k)); self.mode_btns[key] = b; row.addWidget(b)
        row.addStretch(1); self.scan.layout().insertLayout(1, row)
        self.an_split.addWidget(self.scan)
        v.addWidget(self.an_split, 1)
        self.search.textChanged.connect(lambda t: self._filter(text=t)); self.t_ocr.toggled.connect(lambda x: self._filter(show_ocr=x)); self.t_hide.toggled.connect(lambda x: self._filter(hide_reviewed=x))
        return w

    def _pane(self, splitter, colour, title, sub):
        box = QFrame(); box.setObjectName("card"); l = QVBoxLayout(box); l.setContentsMargins(0, 0, 0, 0); l.setSpacing(0)
        head = QLabel(); head.setTextFormat(Qt.RichText); head.setStyleSheet(f"background:{pal()['bg2']};border:none;border-bottom:1px solid {pal()['border']};padding:7px 12px;")
        head.setText(f"<b style='color:{colour}'>■</b>&nbsp;<b>{title}</b> <span style='color:#586272'>– {sub}</span>")
        tbw = QTextBrowser(); tbw.setObjectName("paper"); tbw.setOpenLinks(False); tbw.setStyleSheet("QTextBrowser#paper{border:none;border-radius:0;padding:10px 14px;}")
        l.addWidget(head); l.addWidget(tbw, 1); splitter.addWidget(box); return tbw, head

    def _set_scan_mode(self, k):
        for kk, b in self.mode_btns.items():
            b.setChecked(kk == k)
        self.st.setValue("scan_zoom", k == "zoom"); self._show_scan()

    def _fill_diff(self):
        self.model.set_items(self.result.items); self.proxy.set_filters(sev=None, text="", show_ocr=False, hide_reviewed=False)
        self._row_for = {}
        for rw in self.result.rows:
            self._row_for.setdefault((rw.text_a, rw.text_b), rw)
        self.search.clear(); self.chips["All"].setChecked(True); self.t_ocr.setChecked(False); self.t_hide.setChecked(False)
        self._fill_filters()
        self.count_lbl.setText(f"{self.proxy.rowCount()} shown"); self._scan_cache.clear(); self._cur_item = None
        self.t_left.clear(); self.t_right.clear(); self.scan.view.clear_msg("Select a difference to see where it sits on the scan.")
        self._update_review()
        if self.proxy.rowCount():
            self.table.selectRow(0)
        else:
            self.t_left.setHtml("<p style='color:#586272'>No differences found.</p>")

    def _fill_filters(self):
        vis = [it for it in self.result.items if not it.ocr_only]
        for box, first in ((self.cat_box, "All types"), (self.page_box, "All pages")):
            box.blockSignals(True); box.clear(); box.addItem(first, None)
        for k in sorted({c for it in vis for c in it.categories}):
            self.cat_box.addItem(k, k)
        for p in sorted({p for it in vis for p in (it.pages_b or [])}):
            self.page_box.addItem(f"Page {p}", p)
        self.cat_box.blockSignals(False); self.page_box.blockSignals(False)
        self.proxy.set_filters(cat=None, page=None)

    def _model_refresh(self):
        n = self.model.rowCount()
        if n:
            self.model.dataChanged.emit(self.model.index(0, 0), self.model.index(n - 1, self.model.columnCount() - 1))

    def accept_shown(self, sevs=None):
        for r in range(self.proxy.rowCount()):
            it = self.proxy.index(r, 0).data(Qt.UserRole)
            if it and not it.ocr_only and (sevs is None or it.severity in sevs):
                self.model.reviewed.add(it.id)
        self._model_refresh(); self.table.viewport().update(); self._update_review(); self.proxy.invalidateFilter()
        self.count_lbl.setText(f"{self.proxy.rowCount()} shown")

    def clear_accepted(self):
        self.model.reviewed.clear(); self._model_refresh(); self.table.viewport().update(); self._update_review(); self.proxy.invalidateFilter()

    def _update_review(self):
        if not self.result:
            return
        vis = [it for it in self.model.items if not it.ocr_only]; n = len(vis); d = sum(1 for it in vis if it.id in self.model.reviewed)
        self.rev_lbl.setText(f"{d} of {n} accepted")

    def _on_diff_select(self):
        r = self._cur_row()
        if r < 0:
            return
        it = self.model.item(r); self._cur_item = it
        lab = rm.clause_label(it); col = SEV.get(it.severity, SEV["Info"])
        clause = f" · Clause {escape(lab)}" if lab not in ("—", "") else ""
        pg = f" · page {it.pages_b[0]}" if it.pages_b else ""
        self.head_left.setText(f"<b style='color:{RED}'>■</b>&nbsp;<b>OLD AGREEMENT</b> <span style='color:#586272'>– Word draft{clause}</span>")
        self.head_right.setText(f"<b style='color:{GREEN}'>■</b>&nbsp;<b>NEW AGREEMENT</b> <span style='color:#586272'>– executed copy{clause}{pg}</span>"
                                f"&nbsp;&nbsp;<b style='color:{col}'>[{it.severity}]</b>")
        show_ocr = self.t_ocr.isChecked(); row = getattr(self, "_row_for", {}).get((it.text_a, it.text_b))
        if row is not None:          # the whole clause of both documents, every change marked in place
            left, right = side_runs(row, show_ocr)
            la, lb = row.label_a, row.label_b
            left = ([(la + "  ", "plain")] if la else []) + left; right = ([(lb + "  ", "plain")] if lb else []) + right
        else:
            left, right = rm.runs_for_item(it)
            if not show_ocr:
                left = [(t, "plain" if s_ == "ocr" else s_) for t, s_ in left]; right = [(t, "plain" if s_ == "ocr" else s_) for t, s_ in right]
        empty = lambda m: [(m, "plain")]
        self.t_left.setHtml(_pane_html(left or empty("— this clause is not in the old agreement —"), 15))
        self.t_right.setHtml(_pane_html(right or empty("— this clause is not found in the executed copy —"), 15))
        self.setWindowTitle(f"{config.APP_NAME}  ·  #{it.id} {it.summary[:80]}")
        self._show_scan()

    def _show_scan(self):
        it = self._cur_item; v = self.scan.view
        if not (self.result and it):
            return
        doc = self.result.doc_b
        if doc.kind not in ("pdf", "image") or not it.regions_b:
            v.clear_msg("No scan location for this item" + (" – the text is missing from the executed copy." if it.kind == "deleted" else "."))
            self.scan.caption.setText(""); return
        zoom = self.mode_btns["zoom"].isChecked(); page = it.regions_b[0][0]; key = (it.id, zoom)
        try:
            from ..preview import crop_for_report, page_with_highlight
            if key not in self._scan_cache:
                if len(self._scan_cache) > 24:
                    self._scan_cache.clear()
                if zoom:
                    self._scan_cache[key] = (self._crop(doc, page, it.regions_b), 0)
                else:
                    self._scan_cache[key] = page_with_highlight(doc, page, it.regions_b, dpi=150)
            img, y = self._scan_cache[key]
            if img is not None:
                v.set_image(img, y); self.scan.caption.setText(f"Executed copy – page {page} of {doc.n_pages}" + ("   ·   difference outlined in red" if True else ""))
            else:
                v.clear_msg("Scan preview unavailable for this page.")
        except Exception as ex:   # noqa
            v.clear_msg(f"Scan preview unavailable: {ex}")

    @staticmethod
    def _crop(doc, page, regions):
        """The scan around the difference, outlined, cropped tightly so it fills the panel."""
        from PIL import ImageDraw
        from ..extract_pdf import render_page_image
        img = render_page_image(doc, page, 220)
        if img is None:
            return None
        img = img.convert("RGB"); W, H = img.size; d = ImageDraw.Draw(img, "RGBA"); rs = [r for r in regions if r[0] == page]
        for r in rs:
            d.rectangle([r[1] * W - 3, r[2] * H - 3, r[3] * W + 3, r[4] * H + 3], outline=(220, 30, 30, 255), width=4, fill=(220, 30, 30, 40))
        x0 = min(r[1] for r in rs); y0 = min(r[2] for r in rs); x1 = max(r[3] for r in rs); y1 = max(r[4] for r in rs)
        cx0, cx1 = max(0.0, x0 - 0.05), min(1.0, x1 + 0.05)
        if cx1 - cx0 < 0.55:
            mid = (cx0 + cx1) / 2; cx0, cx1 = max(0.0, mid - 0.275), min(1.0, mid + 0.275)
        cy0, cy1 = max(0.0, y0 - 0.10), min(1.0, y1 + 0.10)
        if (cy1 - cy0) * H < 260:
            mid = (cy0 + cy1) / 2; cy0, cy1 = max(0.0, mid - 130 / H), min(1.0, mid + 130 / H)
        return img.crop((int(cx0 * W), int(cy0 * H), int(cx1 * W), int(cy1 * H)))

    # ------------------------------------------------------------------ side-by-side tab
    _sbs_html_done = False

    def _tool_row(self, parent_layout, with_changed_only=False):
        tb = QFrame(); tb.setObjectName("toolbar"); h = QHBoxLayout(tb); h.setContentsMargins(10, 6, 10, 6); h.setSpacing(8); parent_layout.addWidget(tb); return h

    def _legend(self):
        return (f"<span style='background:{RED_BG};color:{RED};text-decoration:line-through'>&nbsp;deleted&nbsp;</span>&nbsp;&nbsp;"
                f"<span style='background:{GREEN_BG};color:{GREEN};text-decoration:underline'>&nbsp;added&nbsp;</span>&nbsp;&nbsp;"
                f"<span style='background:{AMBER_BG};color:{AMBER}'><i>&nbsp;OCR variance&nbsp;</i></span>")

    def _build_sbs(self):
        w = QWidget(); w.setObjectName("page"); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        h = self._tool_row(v)
        self.sbs_changed = QCheckBox("Changed clauses only"); self.sbs_ocr = QCheckBox("Show OCR variances"); h.addWidget(self.sbs_changed); h.addWidget(self.sbs_ocr)
        h.addSpacing(10); lg = QLabel(self._legend()); lg.setTextFormat(Qt.RichText); h.addWidget(lg); h.addStretch(1)
        self.sbs_count = label("", "muted"); h.addWidget(self.sbs_count)
        for t, d in (("A−", -1), ("A+", 1)):
            b = QPushButton(t); b.setFixedWidth(40); b.clicked.connect(lambda _=False, d=d: self._sbs_font(d)); h.addWidget(b)
        b1 = QPushButton("◀  Previous change"); b2 = QPushButton("Next change  ▶"); b1.clicked.connect(lambda: self._jump("sbs", -1)); b2.clicked.connect(lambda: self._jump("sbs", 1)); h.addWidget(b1); h.addWidget(b2)
        self.sbs = QTextBrowser(); self.sbs.setObjectName("paper"); self.sbs.setOpenLinks(False); self.sbs.setStyleSheet("QTextBrowser#paper{border:none;border-radius:0;padding:0;}")
        v.addWidget(self.sbs, 1)
        self.sbs_changed.setChecked(self.st.value("sbs_changed", False, type=bool))
        self.sbs_changed.toggled.connect(lambda x: (self.st.setValue("sbs_changed", x), self._fill_sbs())); self.sbs_ocr.toggled.connect(lambda _: (self._fill_sbs(), self._fill_redline()))
        return w

    def _sbs_font(self, d):
        self.sbs_size = max(10, min(24, self.sbs_size + d)); self._fill_sbs()

    def _fill_sbs(self):
        if not self.result:
            return
        show_ocr = self.sbs_ocr.isChecked(); only = self.sbs_changed.isChecked(); size = self.sbs_size
        hd = "background:#1F3A5F;color:white;padding:8px 12px;font-size:%dpx" % (size - 1)
        out = [f'<table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse"><tr>'
               f'<td width="7%" style="{hd}">Clause</td><td width="46%" style="{hd}">OLD AGREEMENT – Word draft</td><td width="47%" style="{hd}">NEW AGREEMENT – executed copy</td></tr>']
        self._sbs_anchors = []; n_ch = 0
        for i, row in enumerate(self.result.rows):
            ch = row_changed(row, show_ocr)
            if only and not ch:
                continue
            L, R = side_runs(row, show_ocr)
            lab = escape(row.label_b or row.label_a or "")
            if row.kind == "added":
                lbg, rbg = GREY_BG, GREEN_BG if False else "#EEF8F2"; L = [("— not in the old agreement —", "plain")]
            elif row.kind == "deleted":
                lbg, rbg = "#FCEFED", GREY_BG; R = [("— not found in the executed copy —", "plain")]
            elif ch:
                lbg, rbg = "#FCEFED" if any(s == "del" for _t, s in L) else "#FFFFFF", "#EEF8F2" if any(s == "ins" for _t, s in R) else "#FFFFFF"
            else:
                lbg = rbg = "#FFFFFF"
            anchor = ""
            if ch:
                n_ch += 1; self._sbs_anchors.append(f"s{i}"); anchor = f'<a name="s{i}"></a>'
            bd = "border-bottom:1px solid #D5D9DF;padding:8px 12px;vertical-align:top"
            muted = "color:#6B7686" if not ch else ""
            out.append(f'<tr><td bgcolor="#F6F7F9" style="{bd};{muted};font-weight:700;border-right:1px solid #D5D9DF">{anchor}{lab}</td>'
                       f'<td bgcolor="{lbg}" style="{bd};border-right:1px solid #D5D9DF">{_cell(L, size)}</td><td bgcolor="{rbg}" style="{bd}">{_cell(R, size)}</td></tr>')
        out.append("</table>")
        self.sbs.setHtml("".join(out)); self._sbs_pos = -1; self._sbs_html_done = True
        self.sbs_count.setText(f"{n_ch} changed clause(s)")

    def _jump(self, which, d):
        anchors = self._sbs_anchors if which == "sbs" else self._red_anchors; view = self.sbs if which == "sbs" else self.red
        if not anchors:
            return
        pos = self._sbs_pos if which == "sbs" else self._red_pos
        pos = max(0, min(len(anchors) - 1, pos + d if pos >= 0 else (0 if d > 0 else len(anchors) - 1)))
        if which == "sbs":
            self._sbs_pos = pos
        else:
            self._red_pos = pos
        view.scrollToAnchor(anchors[pos])

    # ------------------------------------------------------------------ redline tab
    def _build_redline_tab(self):
        w = QWidget(); w.setObjectName("page"); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        h = self._tool_row(v)
        self.red_find = QLineEdit(); self.red_find.setPlaceholderText("Find in redline…"); self.red_find.setClearButtonEnabled(True); self.red_find.setFixedWidth(220)
        self.red_find.returnPressed.connect(lambda: self.red.find(self.red_find.text())); h.addWidget(self.red_find)
        fb = QPushButton("Find next"); fb.clicked.connect(lambda: self.red.find(self.red_find.text())); h.addWidget(fb)
        h.addSpacing(10); lg = QLabel(self._legend()); lg.setTextFormat(Qt.RichText); h.addWidget(lg); h.addStretch(1)
        self.red_count = label("", "muted"); h.addWidget(self.red_count)
        for t, d in (("A−", -1), ("A+", 1)):
            b = QPushButton(t); b.setFixedWidth(40); b.clicked.connect(lambda _=False, d=d: self._red_font(d)); h.addWidget(b)
        b1 = QPushButton("◀  Previous change"); b2 = QPushButton("Next change  ▶"); b1.clicked.connect(lambda: self._jump("red", -1)); b2.clicked.connect(lambda: self._jump("red", 1)); h.addWidget(b1); h.addWidget(b2)
        self.red = QTextBrowser(); self.red.setObjectName("paper"); self.red.setOpenLinks(False)
        self.red.setStyleSheet("QTextBrowser#paper{border:none;border-radius:0;padding:24px 8%;}")
        v.addWidget(self.red, 1)
        return w

    def _red_font(self, d):
        self.red_size = max(10, min(26, self.red_size + d)); self._fill_redline()

    def _fill_redline(self):
        if not self.result:
            return
        show_ocr = self.sbs_ocr.isChecked(); parts = []; self._red_anchors = []; n = 0
        for i, row in enumerate(self.result.rows):
            lab = row.label_b or row.label_a
            runs = ([(f"{lab}  ", "plain")] if lab else []) + red_runs(row, show_ocr)
            a = ""
            if row_changed(row, show_ocr):
                n += 1; self._red_anchors.append(f"r{i}"); a = f'<a name="r{i}"></a>'
            parts.append(f'<div style="margin-bottom:10px">{a}{_cell(runs, self.red_size)}</div>')
        self.red.setHtml("".join(parts)); self._red_pos = -1; self.red_count.setText(f"{n} changed paragraph(s)")

    # ------------------------------------------------------------------ updated Word
    def _build_reports(self):
        s = MainWindow._build_reports(self)
        lay = s.widget().layout()
        card = QFrame(); card.setObjectName("card"); v = QVBoxLayout(card); v.setContentsMargins(18, 14, 18, 14); v.setSpacing(8)
        v.addWidget(label("Save an updated Word file", "h2"))
        v.addWidget(label("Conform the draft to the executed copy for the changes you have accepted. “Tracked changes” writes real Word revisions (insertions / "
                          "deletions) that you can accept or reject inside Word; “Clean” simply applies them. Probable OCR variances are never applied – the draft "
                          "wording stays. Only paragraphs with an accepted change are touched.", "muted", True))
        r = QHBoxLayout(); r.setSpacing(10)
        self.up_scope = QComboBox(); self.up_scope.addItems(["Changes I have accepted (Analysis tab)", "All differences (except OCR variances)", "Accepted + all Critical and Major"])
        self.up_mode = QComboBox(); self.up_mode.addItems(["Tracked changes (review in Word)", "Clean – changes applied"])
        self.up_author = QLineEdit(str(self.st.value("author", "Agreement Compare"))); self.up_author.setFixedWidth(170); self.up_author.setPlaceholderText("Author of the revisions")
        for w_ in (self.up_scope, self.up_mode, self.up_author):
            r.addWidget(w_)
        b = QPushButton("  Save updated Word file…"); b.setProperty("kind", "primary"); b.clicked.connect(self.save_updated_word); r.addWidget(b); r.addStretch(1)
        v.addLayout(r)
        lay.insertWidget(2, card)
        return s

    def save_updated_word(self):
        if not self.result:
            self.toast.show_msg("Run a comparison first", "err"); return
        src = self.drop_a.path or self.result.doc_a.path
        if not (src and os.path.isfile(src) and src.lower().endswith(".docx")):
            self.toast.show_msg("The original Word draft is not available", "err"); return
        sc = self.up_scope.currentIndex(); acc = set(self.model.reviewed)
        vis = {it.id: it for it in self.result.items if not it.ocr_only}
        if sc == 0:
            ids = acc & set(vis)
            if not ids:
                self.toast.show_msg("Accept at least one change on the Analysis tab first (✓ Accept change), or choose another scope", "err"); self.goto("analysis"); return
        elif sc == 1:
            ids = None
        else:
            ids = acc | {i for i, it in vis.items() if it.severity in ("Critical", "Major")}
        low = [i for i in (ids if ids is not None else vis) if i in vis and (vis[i].low_conf or "low OCR confidence" in vis[i].summary)]
        mode = "tracked" if self.up_mode.currentIndex() == 0 else "clean"
        base = os.path.splitext(os.path.basename(src))[0]
        p, _ = QFileDialog.getSaveFileName(self, "Save updated Word file", os.path.join(os.path.dirname(src), f"{base}_updated_{mode}.docx"), "Word document (*.docx)")
        if not p:
            return
        self.st.setValue("author", self.up_author.text()); res = self.result; author = self.up_author.text().strip() or "Agreement Compare"
        from ..apply_word import build_updated_word

        def job(progress, cancel):
            st = build_updated_word(res, src, p, ids, mode, author, progress)
            return p, st

        def done(out):
            path, st = out
            self._exported([path])
            msg = (f"Updated Word file saved.\n\n{st['applied']} paragraph(s) changed, {st['inserted']} clause(s) inserted, {st['deleted']} clause(s) deleted"
                   + (" – as tracked changes." if mode == "tracked" else "."))
            if st["skipped"]:
                msg += "\n\nNot applied (paragraph not located):\n" + "\n".join(st["skipped"][:8])
            if low:
                msg += f"\n\nCaution: {len(low)} applied difference(s) were read from the scan with low OCR confidence – verify each against the scan before relying on the file."
            QMessageBox.information(self, "Updated Word file", msg)
        self.run_task(job, done, "Writing the updated Word file…", cancellable=False)

    # ------------------------------------------------------------------ misc
    def apply_theme(self, *_a, **_k):
        p = theme.use_classic()
        QApplication.instance().setStyleSheet(qss_classic(p, self.scale))
        for d in (getattr(self, "drop_a", None), getattr(self, "drop_b", None)):
            if d:
                d.refresh_theme()
        self.scan.refresh_theme(); self.align.refresh_theme()

    def set_result(self, r, fresh=True):
        self.result = r; self._scan_cache.clear(); self._sbs_html_done = False
        self._fill_diff(); self._fill_summary(); self._fill_sbs(); self._fill_redline()
        if fresh:
            self.align.load(r)
            self.toast.show_msg(f"Comparison complete – {r.stats['total']} difference(s) found")
        else:
            self.toast.show_msg(f"Re-comparison complete – {r.stats['total']} difference(s)")
        self.goto("analysis"); self.msg.setText(f"Comparison complete – {r.stats['total']} difference(s) found."); self._refresh_chip()

    def _shortcuts(self):
        def sc(keys, fn, ctx=None):
            s = QShortcut(QKeySequence(keys), self, activated=fn)
            if ctx is not None:
                s.setContext(ctx)
        for i, (k, _t) in enumerate(TABS):
            sc(f"Ctrl+{i + 1}", lambda k=k: self.goto(k))
        sc("F11", self.toggle_full); sc("Esc", lambda: self.isFullScreen() and self.toggle_full())
        sc("Ctrl+Return", self.start_compare); sc("Ctrl+O", self.drop_a.browse); sc("Ctrl+Shift+O", self.drop_b.browse)
        sc("F3", lambda: (self.goto("analysis"), self.step(1))); sc("Shift+F3", lambda: (self.goto("analysis"), self.step(-1)))
        sc("Ctrl+E", lambda: self.export("word")); sc("Ctrl+Shift+E", lambda: self.export("pdf")); sc("Ctrl+F", lambda: (self.goto("analysis"), self.search.setFocus()))
        QShortcut(QKeySequence(Qt.Key_Space), self.table, activated=self.toggle_reviewed, context=Qt.WidgetShortcut)

    def showEvent(self, e):
        super().showEvent(e)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(0, self._init_split)

    def _init_split(self):
        w = max(1000, self.width()); self.an_split.setSizes([int(w * 0.56), int(w * 0.44)])
        h = max(600, self.height()); self.an_left.setSizes([int(h * 0.36), int(h * 0.50)])

    def resizeEvent(self, e):
        QMainWindow.resizeEvent(self, e)

    def closeEvent(self, e):
        if self.worker and self.worker.isRunning():
            self.worker.cancel(); self.worker.wait(1500)
        QMainWindow.closeEvent(self, e)


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME); app.setStyle("Fusion")
    w = ClassicWindow(); w.showMaximized()
    return app.exec()
