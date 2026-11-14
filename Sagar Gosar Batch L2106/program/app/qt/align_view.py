"""'Align & edit' – manual control over how the two documents are paired (Qt version)."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QListWidget, QMessageBox,
                               QPlainTextEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QToolButton)

from .. import adjust
from .theme import icon, pal
from .widgets import ScanPanel, label


def _words(s):
    return set(w for w in "".join(c.lower() if c.isalnum() else " " for c in s).split() if len(w) > 2)


def _sim(a, b):
    return len(a & b) / max(1, len(a | b)) if a and b else 0.0


class AlignView(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win; self.work_a = self.work_b = None; self.links = []; self.active = "A"; self._edit = None
        self._edited = {"A": set(), "B": set()}; self._words = {"A": {}, "B": {}}; self._busy = False
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(10)
        self.info = label("Run a comparison first – the paragraphs of both documents then appear here.", "muted", True); v.addWidget(self.info)

        bar = QFrame(); bar.setObjectName("cardflat"); bv = QVBoxLayout(bar); bv.setContentsMargins(10, 8, 10, 8); bv.setSpacing(6)
        h = QHBoxLayout(); h.setSpacing(6); bv.addLayout(h); h2 = QHBoxLayout(); h2.setSpacing(6); bv.addLayout(h2)
        self.btns = []
        def mk(text, ic, tip, cb, kind=None):
            b = QPushButton(" " + text); b.setToolTip(tip); b.clicked.connect(cb)
            if kind:
                b.setProperty("kind", kind)
            b._ic = ic; h.addWidget(b); self.btns.append(b); return b
        def sep():
            f = QFrame(); f.setFixedWidth(1); f.setStyleSheet(f"background:{pal()['border']};"); h.addWidget(f)
        mk("Merge", "merge", "Merge the selected consecutive paragraphs", self.do_merge)
        mk("Split", "split", "Split the selected paragraph at the text cursor in the editor below", self.do_split)
        mk("Ignore / restore", "eyeoff", "Leave the selected paragraphs out of the comparison (or bring them back)", self.do_ignore)
        mk("Ignore above", "eyeoff", "Ignore every paragraph above the selection", lambda: self.do_range(True))
        mk("Ignore below", "eyeoff", "Ignore every paragraph below the selection", lambda: self.do_range(False))
        sep()
        mk("Find match", "search", "Jump to the most similar paragraph in the other document (or double-click a row)", self.do_find)
        mk("Link", "link", "Pair the selected draft paragraph(s) with the selected executed paragraph(s)", self.do_link, "gold")
        mk("Unlink", "unlink", "Remove the selected link", self.do_unlink)
        h.addStretch(1)
        h = h2
        h.addWidget(label("Session", "small"))
        mk("Reset", "rotl", "Discard all manual edits, ignores and links", self.do_reset)
        mk("Save", "save", "Save this alignment session", self.do_save)
        mk("Load", "upload", "Open a saved alignment session", self.do_load)
        h.addStretch(1)
        self.re = mk("Re-compare with adjustments", "play", "Run the comparison again using your edits and links", self.do_recompare, "primary")
        v.addWidget(bar)

        sp = QSplitter(Qt.Horizontal); sp.setChildrenCollapsible(False)
        self.tab = {}
        for side, title in (("A", "Word draft"), ("B", "Executed copy (scan)")):
            card = QFrame(); card.setObjectName("card"); cv = QVBoxLayout(card); cv.setContentsMargins(12, 10, 12, 10); cv.setSpacing(6)
            cv.addWidget(label(title, "h2"))
            t = QTableWidget(0, 5); t.setHorizontalHeaderLabels(["#", "Pg", "Clause", "State", "Text"])
            t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setSelectionMode(QAbstractItemView.ExtendedSelection)
            t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setShowGrid(False); t.setWordWrap(False)
            hd = t.horizontalHeader(); hd.setStretchLastSection(True)
            for i, w in enumerate((40, 34, 54, 72)):
                hd.setSectionResizeMode(i, QHeaderView.Fixed); t.setColumnWidth(i, w)
            t.itemSelectionChanged.connect(lambda s=side: self._on_select(s)); t.cellDoubleClicked.connect(lambda r, c, s=side: self.do_find(s))
            cv.addWidget(t); self.tab[side] = t; sp.addWidget(card)
        self.scan = ScanPanel("Scan preview"); self.scan.rotateRequested.connect(lambda d: self.rotate_page(d))
        sp.addWidget(self.scan); sp.setStretchFactor(0, 5); sp.setStretchFactor(1, 5); sp.setStretchFactor(2, 3); sp.setSizes([480, 480, 330])
        v.addWidget(sp, 1)

        bottom = QHBoxLayout(); bottom.setSpacing(10)
        ec = QFrame(); ec.setObjectName("card"); ev = QVBoxLayout(ec); ev.setContentsMargins(14, 10, 14, 10); ev.setSpacing(6)
        eh = QHBoxLayout(); self.lbl_edit = label("Selected paragraph text – edit it, then press Apply", "h2"); eh.addWidget(self.lbl_edit, 1)
        self.apply = QPushButton(" Apply edit"); self.apply.setProperty("kind", "gold"); self.apply.clicked.connect(self.do_apply_edit); eh.addWidget(self.apply)
        ev.addLayout(eh)
        self.txt = QPlainTextEdit(); self.txt.setObjectName("editor"); self.txt.setFixedHeight(92); ev.addWidget(self.txt)
        bottom.addWidget(ec, 3)
        lc = QFrame(); lc.setObjectName("card"); lv = QVBoxLayout(lc); lv.setContentsMargins(14, 10, 14, 10); lv.setSpacing(6)
        lv.addWidget(label("Links (fixed anchors)", "h2")); self.lst = QListWidget(); self.lst.setFixedHeight(92); lv.addWidget(self.lst)
        bottom.addWidget(lc, 2); v.addLayout(bottom)
        self.refresh_theme()

    def refresh_theme(self):
        for b in self.btns:
            b.setIcon(icon(b._ic, "#FFFFFF" if b.property("kind") == "primary" else (("#2A1B00") if b.property("kind") == "gold" else pal()["text"]), 17))
        self.apply.setIcon(icon("check", "#2A1B00", 17)); self.scan.refresh_theme()

    # ------------------------------------------------------------------ data
    def load(self, result):
        self.work_a = adjust.working_copy(result.raw_a); self.work_b = adjust.working_copy(result.raw_b)
        self.links = []; self._edited = {"A": set(), "B": set()}; self.refresh()

    def loaded(self):
        return self.work_a is not None

    def _doc(self, s):
        return self.work_a if s == "A" else self.work_b

    def _num(self, s, uid):
        i = adjust.index_of(self._doc(s), uid); return i + 1 if i >= 0 else "?"

    def _sel(self, s):
        t = self.tab[s]; rows = sorted(set(i.row() for i in t.selectedItems()))
        return [t.item(r, 0).data(Qt.UserRole) for r in rows]

    def _select(self, s, uids):
        t = self.tab[s]; t.clearSelection(); first = None
        for r in range(t.rowCount()):
            if t.item(r, 0).data(Qt.UserRole) in uids:
                t.selectRow(r) if first is None else t.item(r, 0).setSelected(True)
                for c in range(5):
                    t.item(r, c).setSelected(True)
                first = r if first is None else first
        if first is not None:
            t.scrollToItem(t.item(first, 0))

    def refresh(self):
        if not self.work_a:
            return
        linked = {"A": set(u for la, _ in self.links for u in la), "B": set(u for _, lb in self.links for u in lb)}
        c = pal(); green = QBrush(QColor(52, 211, 153, 46)); amber = QBrush(QColor(246, 196, 83, 46)); mute = QBrush(QColor(c["muted"]))
        for s in "AB":
            t = self.tab[s]; keep = set(self._sel(s)); t.blockSignals(True); t.setRowCount(0)
            d = self._doc(s); self._words[s] = {b.uid: _words(b.body) for b in d.blocks}
            for i, b in enumerate(d.blocks, 1):
                r = t.rowCount(); t.insertRow(r)
                state = "ignored" if b.ignored else "linked" if b.uid in linked[s] else "edited" if b.uid in self._edited[s] else ""
                for col, val in enumerate((i, b.page or "", b.label, state, b.body[:220])):
                    it = QTableWidgetItem(str(val)); it.setToolTip(b.body[:600]); t.setItem(r, col, it)
                    if state == "linked":
                        it.setBackground(green)
                    elif state == "edited":
                        it.setBackground(amber)
                    elif state == "ignored":
                        it.setForeground(mute); f = it.font(); f.setStrikeOut(True); it.setFont(f)
                t.item(r, 0).setData(Qt.UserRole, b.uid)
                t.setRowHeight(r, 30)
            t.blockSignals(False)
            if keep:
                self._select(s, keep)
        self.lst.clear()
        for la, lb in self.links:
            self.lst.addItem("Draft " + ", ".join("#" + str(self._num("A", u)) for u in la) + "   ⇄   Executed " + ", ".join("#" + str(self._num("B", u)) for u in lb))
        na = sum(b.ignored for b in self.work_a.blocks); nb = sum(b.ignored for b in self.work_b.blocks)
        self.info.setText(f"Draft: {len(self.work_a.blocks)} paragraphs ({na} ignored)   ·   Executed: {len(self.work_b.blocks)} paragraphs ({nb} ignored)   ·   "
                          f"Links: {len(self.links)}.   Tip: select a draft paragraph and double-click it to jump to its best match, then select the executed paragraph(s) and press Link. "
                          f"Green = linked · amber = edited · struck-through = ignored.")

    # ------------------------------------------------------------------ selection / preview
    def _on_select(self, s):
        self.active = s; sel = self._sel(s)
        if not sel:
            return
        d = self._doc(s); bl = [d.blocks[adjust.index_of(d, u)] for u in sel if adjust.index_of(d, u) >= 0]
        if not bl:
            return
        self._edit = (s, bl[0].uid) if len(bl) == 1 else None
        self.txt.setPlainText(bl[0].body if len(bl) == 1 else "\n\n".join(b.body for b in bl))
        self.lbl_edit.setText(f"{'Draft' if s == 'A' else 'Executed'} paragraph #{adjust.index_of(d, bl[0].uid) + 1}" + (f" (+{len(bl) - 1} more)" if len(bl) > 1 else "") + " – edit, then Apply")
        if s == "B":
            self._preview(d, bl)

    def _preview(self, doc, blocks):
        regs = [r for b in blocks for r in b.regions]
        v = self.scan.view
        if doc.kind not in ("pdf", "image") or not regs:
            v.clear_msg("No scan location for this paragraph."); return
        try:
            from .. import config
            from ..preview import page_with_highlight
            page = regs[0][0]
            img, y = page_with_highlight(doc, page, regs, dpi=config.PREVIEW_DPI)
            if img is None:
                return
            v.set_image(img, y); self.scan.caption.setText(f"Executed copy – page {page} of {doc.n_pages}")
        except Exception as ex:   # noqa
            v.clear_msg(f"Preview unavailable: {ex}")

    def _need(self):
        if not self.work_a:
            QMessageBox.information(self, "Agreement Compare", "Run a comparison first."); return False
        return True

    # ------------------------------------------------------------------ actions
    def _drop_links(self, s, uids):
        u = set(uids); k = 0 if s == "A" else 1
        self.links = [l for l in self.links if not (u & set(l[k]))]

    def do_merge(self):
        if not self._need():
            return
        s = self.active; sel = self._sel(s); new = adjust.merge(self._doc(s), sel)
        if new is None:
            QMessageBox.information(self, "Merge", "Select two or more consecutive paragraphs (Ctrl / Shift-click) in one list."); return
        self._drop_links(s, sel); self._edited[s].add(new); self.refresh(); self._select(s, {new})

    def do_split(self):
        if not self._need():
            return
        s = self.active; sel = self._sel(s)
        if len(sel) != 1:
            QMessageBox.information(self, "Split", "Select one paragraph, click inside the text box at the split point, then press Split."); return
        d = self._doc(s); b = d.blocks[adjust.index_of(d, sel[0])]
        if self.txt.toPlainText().strip() != b.body:
            QMessageBox.information(self, "Split", "Press 'Apply edit' first, then place the cursor and split."); return
        r = adjust.split(d, sel[0], self.txt.textCursor().position())
        if not r:
            QMessageBox.information(self, "Split", "Place the text cursor inside the paragraph (not at its very start or end)."); return
        self._drop_links(s, sel); self._edited[s].update(r); self.refresh(); self._select(s, set(r))

    def do_ignore(self):
        if not self._need():
            return
        s = self.active; sel = self._sel(s); d = self._doc(s)
        if sel:
            flag = not all(d.blocks[adjust.index_of(d, u)].ignored for u in sel); adjust.set_ignored(d, sel, flag); self.refresh()

    def do_range(self, above):
        if self._need():
            s = self.active; sel = self._sel(s)
            if sel:
                adjust.ignore_range(self._doc(s), sel[0] if above else sel[-1], above=above); self.refresh()

    def do_apply_edit(self):
        if self._edit and self._need():
            s, uid = self._edit
            if adjust.edit(self._doc(s), uid, self.txt.toPlainText()):
                self._edited[s].add(uid); self.refresh(); self._select(s, {uid})

    def do_find(self, side=None):
        if not self._need():
            return
        s = side if isinstance(side, str) else self.active; sel = self._sel(s)
        if not sel:
            return
        o = "B" if s == "A" else "A"; w = set().union(*[self._words[s].get(u, set()) for u in sel]); od = self._doc(o)
        best = sorted(((_sim(w, ws), u) for u, ws in self._words[o].items() if not od.blocks[adjust.index_of(od, u)].ignored), reverse=True)[:3]
        t = self.tab[o]
        for sc, u in best:
            for r in range(t.rowCount()):
                if t.item(r, 0).data(Qt.UserRole) == u and not t.item(r, 3).text():
                    t.item(r, 3).setText(f"≈ {sc:.0%}")
        if best and best[0][0] > 0:
            self.active = o; self._select(o, {best[0][1]}); self._on_select(o)
        else:
            QMessageBox.information(self, "Find match", "No similar paragraph found in the other document.")

    def do_link(self):
        if not self._need():
            return
        ua, ub = self._sel("A"), self._sel("B")
        if not ua or not ub:
            QMessageBox.information(self, "Link", "Select the draft paragraph(s) in the left list AND the matching executed paragraph(s) in the middle list."); return
        self._drop_links("A", ua); self._drop_links("B", ub)
        self.links.append((sorted(ua, key=lambda u: adjust.index_of(self.work_a, u)), sorted(ub, key=lambda u: adjust.index_of(self.work_b, u))))
        self.links.sort(key=lambda l: adjust.index_of(self.work_a, l[0][0])); self.refresh()
        self.win.toast.show_msg("Linked – press “Re-compare with adjustments” to apply")

    def do_unlink(self):
        r = self.lst.currentRow()
        if r >= 0:
            del self.links[r]
        else:
            self._drop_links("A", self._sel("A")); self._drop_links("B", self._sel("B"))
        self.refresh()

    def do_reset(self):
        if self.win.result and QMessageBox.question(self, "Reset", "Discard all manual edits, ignores and links?") == QMessageBox.Yes:
            self.load(self.win.result)

    # ------------------------------------------------------------------ re-compare / sessions
    def do_recompare(self):
        if not self._need():
            return
        da, db, anchors = adjust.build_inputs(self.work_a, self.work_b, self.links)
        self.win.recompare(da, db, anchors)

    def do_save(self):
        if not self._need():
            return
        p, _ = QFileDialog.getSaveFileName(self, "Save alignment session", "alignment.agrsession", "Agreement Compare session (*.agrsession)")
        if p:
            adjust.save_session(p, self.work_a, self.work_b, self.links, self.win.options()); self.win.toast.show_msg("Session saved")

    def do_load(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open alignment session", "", "Agreement Compare session (*.agrsession *.json);;All files (*.*)")
        if not p:
            return
        try:
            a, b, links, _o = adjust.load_session(p)
        except Exception as ex:   # noqa
            QMessageBox.critical(self, "Agreement Compare", f"Could not open the session: {ex}"); return
        self.work_a, self.work_b, self.links = a, b, links; self._edited = {"A": set(), "B": set()}; self.refresh()
        self.win.toast.show_msg("Session loaded – press “Re-compare with adjustments”", "info")

    # ------------------------------------------------------------------ rotate a scanned page
    def current_page(self):
        sel = self._sel("B")
        if not sel or not self.work_b:
            return None
        i = adjust.index_of(self.work_b, sel[0]); return self.work_b.blocks[i].page if i >= 0 else None

    def rotate_page(self, delta, page=None, recompare=False):
        if not self._need():
            return
        page = page or self.current_page()
        if not page:
            QMessageBox.information(self, "Rotate page", "Select a paragraph of the executed copy on the page you want to rotate."); return
        if self.work_b.kind not in ("pdf", "image"):
            return
        cur = self.work_b.page_transform.get(page, (0, 0))[0]; new = (cur + delta) % 360; opts = self.win.options()

        def job(progress, cancel):
            from ..extract_pdf import reocr_page
            progress(0.2, f"Rotating page {page} and reading it again…")
            return reocr_page(self.work_b, page, new, opts)
        self.win.run_task(job, lambda res: self.apply_rotation(page, new, res, recompare), f"Rotating page {page}…")

    def apply_rotation(self, page, rot, res, recompare):
        blocks, transform, size, conf, nwords = res; d = self.work_b
        old = [b for b in d.blocks if b.page == page]
        first = adjust.index_of(d, old[0].uid) if old else sum(1 for b in d.blocks if b.page < page)
        gone = {b.uid for b in old}; d.blocks = [b for b in d.blocks if b.page != page]; nxt = adjust.next_uid(d)
        for k, b in enumerate(blocks):
            b.uid = nxt + k; self._edited["B"].add(b.uid)
        d.blocks[first:first] = blocks
        for i, b in enumerate(d.blocks):
            b.idx = i
        d.page_transform[page] = transform; d.page_pixels[page] = size; d.page_conf[page] = conf; d.page_words[page] = nwords
        gone |= set(adjust.drop_repeated_heads(d)); blocks = [b for b in blocks if b.uid not in gone]
        self.links = [l for l in self.links if not (gone & set(l[1]))]; self.refresh()
        if blocks:
            self._select("B", {blocks[0].uid}); self._on_select("B")
        self.win.toast.show_msg(f"Page {page} rotated {rot}° and re-read ({conf}% confidence)")
        if recompare:
            self.do_recompare()
