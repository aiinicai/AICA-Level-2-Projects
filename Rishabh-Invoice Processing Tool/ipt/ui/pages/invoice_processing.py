"""Invoice Processing: upload queue + background extraction with pause/resume/cancel."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton)

from ipt.core.permissions import has_permission
from ipt.services.document_service import DocumentError
from ipt.services.extraction.pipeline import MODES, ExtractionPipeline
from ipt.services.extraction.sources import find_tesseract
from ipt.ui.helpers import (checked_ids, confirm, error, fill_table, make_checkable, make_table, muted,
                            set_all_checked, title)
from ipt.ui.pages.base import BasePage

STATUS_LABEL = {"queued": "Queued", "processing": "Processing...", "extracted": "Extracted",
                "needs_review": "Needs review", "failed": "Failed", "archived": "Archived"}


class _Signals(QObject):
    progress = Signal(int, int, str)      # done, total, message
    file_done = Signal(int, bool, str)    # document id, ok, message
    finished = Signal(int, int, bool)     # ok count, failed count, cancelled
    file_started = Signal(int)            # document id


class ExtractionJob(QRunnable):
    """Runs the pipeline over documents one by one. Pause/cancel take effect between files."""

    def __init__(self, services, doc_ids: list[int], mode: str):
        super().__init__()
        self.s, self.doc_ids, self.mode = services, doc_ids, mode
        self.signals = _Signals()
        self._resume = threading.Event()
        self._resume.set()
        self._cancel = False

    def pause(self):
        self._resume.clear()

    def resume(self):
        self._resume.set()

    def cancel(self):
        self._cancel = True
        self._resume.set()

    def run(self):
        pipeline = ExtractionPipeline(self.s)
        ok = failed = 0
        total = len(self.doc_ids)
        done_ids = []
        for n, did in enumerate(self.doc_ids):
            self._resume.wait()
            if self._cancel:
                break
            head = f"Extracting file {n + 1} of {total}"
            self.signals.progress.emit(n, total, head)
            self.signals.file_started.emit(did)
            out = pipeline.run(did, self.mode,
                               progress=lambda msg, n=n, head=head: self.signals.progress.emit(n, total,
                                                                                            f"{head} – {msg}"))
            ok += out.ok
            failed += not out.ok
            self.signals.file_done.emit(did, out.ok, out.message)
            done_ids.append(did)
        self.claude_message = ""
        if done_ids:
            from ipt.services import claude_assist
            try:
                self.claude_message = claude_assist.after_extraction(self.s, done_ids)
            except Exception as e:  # noqa: BLE001 - the extraction itself is done; report and go on
                self.claude_message = f"Claude Code check could not start: {e}"
        self.signals.finished.emit(ok, failed, self._cancel)


class InvoiceProcessingPage(BasePage):
    title_text = "Invoice Processing"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.job: ExtractionJob | None = None
        self.setAcceptDrops(True)
        self.layout_.addWidget(title("Invoice Processing"))
        self.layout_.addWidget(muted("Add PDF / JPG / PNG invoices (or drag them here). Originals are copied into "
                                     "the company's folder and never changed. Extraction starts only when you "
                                     "click Start extraction. All processing happens on this computer."))
        bar = QHBoxLayout()
        self.btn_files = QPushButton("Add files")
        self.btn_folder = QPushButton("Add folder")
        self.btn_all = QPushButton("Select all")
        self.btn_remove = QPushButton("Remove ticked")
        self.btn_remove.setToolTip("Files without invoices are removed; files whose bills are already extracted are "
                                   "archived (hidden, never read again – their invoices stay)")
        self.btn_clear = QPushButton("Clear queue")
        self.show_archived = QCheckBox("Show archived")
        for b in (self.btn_files, self.btn_folder, self.btn_all, self.btn_remove, self.btn_clear):
            bar.addWidget(b)
        bar.addStretch(1)
        bar.addWidget(self.show_archived)
        self.layout_.addLayout(bar)

        run = QHBoxLayout()
        run.addWidget(QLabel("Mode"))
        self.mode = QComboBox()
        for key, label in MODES.items():
            self.mode.addItem(label, key)
        run.addWidget(self.mode)
        self.btn_start = QPushButton("Extract ticked")
        self.btn_start.setObjectName("Primary")
        self.btn_pause = QPushButton("Pause")
        self.btn_resume = QPushButton("Resume")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_retry = QPushButton("Retry failed")
        for b in (self.btn_start, self.btn_pause, self.btn_resume, self.btn_cancel, self.btn_retry):
            run.addWidget(b)
        run.addStretch(1)
        self.layout_.addLayout(run)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.status = muted("")
        self.ocr_note = muted("")
        self.layout_.addWidget(self.progress)
        self.layout_.addWidget(self.status)
        self.layout_.addWidget(self.ocr_note)

        self.table = make_table(["", "File", "Pages", "Size (KB)", "Status", "Method", "Duplicate", "Message"])
        self.layout_.addWidget(self.table, 1)

        self.btn_files.clicked.connect(self._add_files)
        self.btn_folder.clicked.connect(self._add_folder)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_start.clicked.connect(self._start_ticked)
        self.btn_all.clicked.connect(self._toggle_all)
        self.show_archived.toggled.connect(lambda _: self.refresh())
        self.table.itemChanged.connect(lambda _: self._update_count())
        self._tick_next: set[int] = set()
        self.btn_retry.clicked.connect(lambda: self._start(("failed",)))
        self.btn_pause.clicked.connect(self._pause)
        self.btn_resume.clicked.connect(self._resume)
        self.btn_cancel.clicked.connect(self._cancel)

    # ------------------------------------------------------------ helpers
    def _can(self) -> bool:
        return has_permission(self.s.ctx.user.role if self.s.ctx.user else None, "invoice.process")

    def _set_running(self, running: bool):
        can = self._can() and bool(self.s.ctx.fy_id)
        for b in (self.btn_files, self.btn_folder, self.btn_all, self.btn_remove, self.btn_clear, self.btn_start,
                  self.btn_retry, self.mode):
            b.setEnabled(can and not running)
        self.btn_pause.setEnabled(running)
        self.btn_resume.setEnabled(False)
        self.btn_cancel.setEnabled(running)
        self.progress.setVisible(running)

    def refresh(self) -> None:
        keep = set(checked_ids(self.table)) | self._tick_next
        self._tick_next = set()
        docs = self.s.documents.list_documents(include_archived=self.show_archived.isChecked())
        self._ids = [d.id for d in docs]
        self._status = {d.id: d.status for d in docs}
        self.table.blockSignals(True)
        fill_table(self.table, [["", d.original_filename, d.pages, round(d.size_bytes / 1024, 1),
                                 STATUS_LABEL.get(d.status, d.status), {"pdf_text": "PDF text", "ocr": "OCR"}.get(
                                     d.method, d.method), f"Same file as #{d.duplicate_of_id}" if d.duplicate_of_id
                                 else "", d.error] for d in docs], self._ids)
        make_checkable(self.table)
        set_all_checked(self.table, True, lambda r: self.table.item(r, 0).data(Qt.UserRole) in keep)
        self.table.blockSignals(False)
        self._update_count()
        self._set_running(self.job is not None)
        if not self.s.ctx.fy_id:
            self.status.setText("Select a company and financial year first.")
        self.ocr_note.setText("" if find_tesseract() else
                              "Note: Tesseract OCR is not installed, so scanned PDFs and photos cannot be read yet. "
                              "Digital PDFs work. See docs/OCR_SETUP.md.")

    def _selected_ids(self) -> list[int]:
        return checked_ids(self.table)

    def _update_count(self):
        n = len(checked_ids(self.table))
        self.btn_start.setText(f"Extract ticked ({n})" if n else "Extract ticked")
        self.btn_all.setText("Deselect all" if n and n == self.table.rowCount() else "Select all")

    def _toggle_all(self):
        self.table.blockSignals(True)
        set_all_checked(self.table, self.btn_all.text() == "Select all")
        self.table.blockSignals(False)
        self._update_count()

    def _start_ticked(self):
        ids = [i for i in checked_ids(self.table) if self._status.get(i) in ("queued", "failed")]
        if not ids:
            error(self, "Tick the file(s) to extract (new files are ticked when you add them). Files already "
                        "extracted are left alone.")
            return
        self._run(sorted(ids))

    def _add(self, paths: list[Path]):
        try:
            res = self.s.documents.add_files(paths)
        except DocumentError as e:
            error(self, str(e))
            return
        self._tick_next = {d.id for d in res.added}        # new files come ticked, old ones do not
        msg = f"{len(res.added)} file(s) added and ticked – click 'Extract ticked'."
        dups = [d for d in res.added if d.duplicate_of_id]
        if dups:
            msg += f" {len(dups)} of them were uploaded before (marked as duplicate)."
        if res.skipped:
            msg += " Skipped: " + "; ".join(f"{n} ({r})" for n, r in res.skipped[:5])
        self.status.setText(msg)
        self.refresh()

    # ------------------------------------------------------------ actions
    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Add invoices", "", "Invoices (*.pdf *.jpg *.jpeg *.png)")
        if files:
            self._add([Path(f) for f in files])

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add all invoices in a folder")
        if folder:
            self._add([Path(folder)])

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        if self._can() and self.job is None:
            self._add([Path(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()])

    def _remove(self):
        ids = self._selected_ids()
        if not ids:
            error(self, "Select one or more files first")
            return
        if confirm(self, f"Remove {len(ids)} ticked file(s) from the list?\n\nFiles without extracted bills are "
                         "removed (the copy inside IPT is deleted). Files whose bills are already extracted are "
                         "archived: hidden and never read again; their invoices stay.\nYour original files are "
                         "not touched."):
            try:
                removed, archived = self.s.documents.remove(ids)
            except DocumentError as e:
                error(self, str(e))
                return
            self.status.setText(f"{removed} removed, {archived} archived.")
            self.refresh()

    def _clear(self):
        ids = [d.id for d in self.s.documents.list_documents(("queued", "failed"))]
        if not ids:
            self.status.setText("Nothing to clear (only queued and failed files are cleared).")
            return
        if confirm(self, f"Remove all {len(ids)} queued/failed file(s) from the queue?"):
            self.s.documents.remove(ids)
            self.refresh()

    def _start(self, statuses):
        ids = [d.id for d in self.s.documents.list_documents(statuses)]
        ids.reverse()  # oldest first
        if not ids:
            self.status.setText("No files to extract." if statuses == ("queued",) else "No failed files.")
            return
        self._run(ids)

    def _run(self, ids):
        self.job = ExtractionJob(self.s, ids, self.mode.currentData())
        self.job.signals.progress.connect(self._on_progress)
        self.job.signals.file_started.connect(lambda *_: self.refresh())
        self.job.signals.file_done.connect(lambda *_: self.refresh())
        self.job.signals.finished.connect(self._on_finished)
        self.progress.setRange(0, len(ids))
        self.progress.setValue(0)
        self._set_running(True)
        QThreadPool.globalInstance().start(self.job)

    def _on_progress(self, done, total, message):
        self.progress.setValue(done)
        self.status.setText(message)

    def _on_finished(self, ok, failed, cancelled):
        self.progress.setVisible(False)
        word = "Cancelled" if cancelled else "Finished"
        msg = getattr(self.job, "claude_message", "") if self.job else ""
        self.status.setText(f"{word}: {ok} extracted, {failed} failed. Review them in Processed Invoices."
                            + (f"  {msg}" if msg else ""))
        self.job = None
        self.refresh()

    def _pause(self):
        if self.job:
            self.job.pause()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)
            self.status.setText("Paused after the current file.")

    def _resume(self):
        if self.job:
            self.job.resume()
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)

    def _cancel(self):
        if self.job and confirm(self, "Stop extraction after the current file?"):
            self.job.cancel()
