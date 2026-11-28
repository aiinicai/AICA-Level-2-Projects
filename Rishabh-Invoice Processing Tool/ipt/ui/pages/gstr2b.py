"""GSTR-2B Upload: load the Excel / JSON downloaded from the GST portal, one current file per month."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QPushButton, QSplitter

from ipt.core.money import format_inr
from ipt.core.permissions import PermissionDenied, has_permission
from ipt.core.timefmt import fmt
from ipt.services.recon.gstr2b_service import (Gstr2bError, NeedsGstinConfirm, NeedsReplace,
                                               period_label)
from ipt.ui.helpers import confirm, error, fill_table, info, make_table, muted, selected_id, title
from ipt.ui.pages.base import BasePage

SECTION_NAMES = {"B2B": "B2B invoices", "B2BA": "B2B amendments", "CDNR": "Credit/debit notes",
                 "CDNRA": "Note amendments", "ISD": "ISD", "ISDA": "ISD amendments", "IMPG": "Imports",
                 "IMPGSEZ": "Imports from SEZ"}


class Gstr2bPage(BasePage):
    title_text = "GSTR-2B Upload"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("GSTR-2B Upload"))
        self.layout_.addWidget(muted("Upload the GSTR-2B Excel (or JSON) downloaded from the GST portal. One file "
                                     "per month is current; uploading the same month again replaces it after you "
                                     "confirm, and the old file is kept as history."))
        bar = QHBoxLayout()
        self.btn_upload = QPushButton("Upload GSTR-2B (Excel / JSON)…")
        self.btn_upload.setObjectName("Primary")
        self.history = QCheckBox("Show replaced files")
        bar.addWidget(self.btn_upload)
        bar.addWidget(self.history)
        bar.addStretch(1)
        self.layout_.addLayout(bar)
        split = QSplitter(Qt.Vertical)
        self.uploads = make_table(["Month", "File", "Format", "Documents", "Current", "Uploaded by", "Uploaded at",
                                   "Not read"])
        split.addWidget(self.uploads)
        self.records = make_table(["Supplier GSTIN", "Supplier", "Table", "Type", "Document no", "Date", "Taxable",
                                   "IGST", "CGST", "SGST", "Cess", "ITC available", "Reason", "Original no"])
        split.addWidget(self.records)
        self.layout_.addWidget(split, 1)
        rec_bar = QHBoxLayout()
        self.section = QComboBox()
        self.section.addItem("All tables", None)
        for k, v in SECTION_NAMES.items():
            self.section.addItem(v, k)
        rec_bar.addWidget(muted("Documents of the selected month (or of every current month):"))
        rec_bar.addWidget(self.section)
        rec_bar.addStretch(1)
        self.summary = muted("")
        rec_bar.addWidget(self.summary)
        self.layout_.addLayout(rec_bar)
        self.btn_upload.clicked.connect(self._upload)
        self.history.toggled.connect(self.refresh)
        self.section.currentIndexChanged.connect(self._load_records)
        self.uploads.itemSelectionChanged.connect(self._load_records)

    def refresh(self) -> None:
        role = self.s.ctx.user.role if self.s.ctx.user else None
        self.btn_upload.setEnabled(has_permission(role, "gst.upload"))
        ups = self.s.gstr2b.uploads(self.history.isChecked())
        rows = []
        for u in ups:
            counts = json.loads(u.counts_json or "{}")
            skipped = json.loads(u.skipped_json or "[]")
            rows.append([period_label(u.period), u.file_name, u.source_format.upper(),
                         ", ".join(f"{k} {v}" for k, v in counts.items()) or "0",
                         "Yes" if u.is_current else "Replaced", u.uploaded_by, fmt(u.uploaded_at),
                         len([x for x in skipped if "row" in x])])
        fill_table(self.uploads, rows, [u.id for u in ups])
        self._load_records()

    def _load_records(self) -> None:
        uid = selected_id(self.uploads)
        recs = self.s.gstr2b.records(uid, self.section.currentData())
        rows = [[r.supplier_gstin, r.supplier_name, r.section, r.doc_type, r.doc_no,
                 r.doc_date.strftime("%d-%m-%Y") if r.doc_date else "", format_inr(r.taxable_value),
                 format_inr(r.igst), format_inr(r.cgst), format_inr(r.sgst), format_inr(r.cess), r.itc_available,
                 r.itc_reason, r.original_doc_no] for r in recs]
        fill_table(self.records, rows, [r.id for r in recs])
        tx = sum((r.taxable_value or 0) for r in recs)
        tax = sum((r.igst or 0) + (r.cgst or 0) + (r.sgst or 0) + (r.cess or 0) for r in recs)
        self.summary.setText(f"{len(recs)} document(s) · taxable {format_inr(tx)} · tax {format_inr(tax)}")

    def _fy_months(self) -> list[str]:
        fy = next((f for f in self.s.companies.list_fys(self.s.ctx.company_id) if f.id == self.s.ctx.fy_id), None)
        if fy is None:
            return []
        out, y, m = [], fy.start_date.year, fy.start_date.month
        while date(y, m, 1) <= fy.end_date:
            out.append(f"{y}-{m:02d}")
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return out

    def _upload(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose GSTR-2B file(s) – several months at once is fine", "",
                                                "GSTR-2B (*.xlsx *.json *.zip)")
        if not paths:
            return
        plan, months = [], self._fy_months()
        for path in paths:
            try:
                parsed = self.s.gstr2b.preview(Path(path))
            except Gstr2bError as e:
                error(self, f"{Path(path).name}: {e}")
                return
            period = parsed.period
            if not period:
                labels = [period_label(p) for p in months]
                label, ok = QInputDialog.getItem(self, "Which month?", f"{Path(path).name} does not show its return "
                                                 "period. Choose the GSTR-2B month:", labels, 0, False)
                if not ok:
                    return
                period = months[labels.index(label)]
            plan.append((path, period, parsed))
        periods = [p for _, p, _ in plan]
        if len(set(periods)) != len(periods):
            error(self, "Two of the chosen files are for the same month. Choose one file per month.")
            return
        lines = []
        for path, period, parsed in sorted(plan, key=lambda x: x[1]):
            counts = ", ".join(f"{SECTION_NAMES.get(k, k)}: {v}" for k, v in parsed.counts().items()) or "no documents"
            notes = [x for x in parsed.skipped if "row" in x]
            lines.append(f"{period_label(period)} – {Path(path).name}\n   {counts}"
                         + (f" · {len(notes)} row(s) unreadable" if notes else ""))
        if not confirm(self, "Import these GSTR-2B file(s)?\n\n" + "\n".join(lines)):
            return
        done, replace_all = [], None
        for path, period, parsed in sorted(plan, key=lambda x: x[1]):
            kw = {"period": period, "parsed": parsed}
            while True:
                try:
                    self.s.gstr2b.upload(Path(path), **kw)
                    done.append(f"✅ {period_label(period)}: {sum(parsed.counts().values())} documents")
                    break
                except NeedsReplace as e:
                    if replace_all is None:
                        replace_all = confirm(self, f"{e}\n\nReplace the current file for every month that already "
                                                    "has one? (The current files stay in history.)")
                    if not replace_all:
                        done.append(f"– {period_label(period)}: skipped, a file is already loaded")
                        break
                    kw["replace"] = True
                except NeedsGstinConfirm as e:
                    if not confirm(self, f"{Path(path).name}\n\n{e}\n\nImport it anyway?"):
                        done.append(f"– {period_label(period)}: not imported (GSTIN not confirmed)")
                        break
                    kw["gstin_confirmed"] = True
                except (Gstr2bError, PermissionDenied) as e:
                    done.append(f"⛔ {period_label(period)}: {e}")
                    break
        self.refresh()
        info(self, "GSTR-2B import\n\n" + "\n".join(done))
