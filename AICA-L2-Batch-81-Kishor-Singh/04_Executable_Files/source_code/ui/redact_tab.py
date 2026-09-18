"""Edit/Redact tab: find sensitive values, review, and permanently remove them."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.redaction_engine import (
    DEFAULT_ENABLED_PATTERNS,
    RedactionCandidate,
    RedactionPatternKind,
    apply_redactions,
    find_redaction_candidates,
    verify_redaction,
)
from ui.app_context import AppContext
from ui.widgets.dialogs import show_error
from ui.widgets.pdf_preview_widget import PdfPreviewWidget
from utils.database import AuditEntry
from utils.logging_utils import get_logger, log_operation
from utils.validation import ValidationError

logger = get_logger("redact_tab")

_ALL_PATTERNS = [
    RedactionPatternKind.PAN,
    RedactionPatternKind.GSTIN,
    RedactionPatternKind.AADHAAR_LIKE,
    RedactionPatternKind.EMAIL,
    RedactionPatternKind.PHONE,
    RedactionPatternKind.BANK_ACCOUNT_LIKE,
]


class RedactTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.source_path: str | None = None
        self.candidates: list[RedactionCandidate] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "Open a PDF, scan it for sensitive values, review each match, then apply. Redaction "
            "genuinely removes the underlying content (not a cosmetic overlay) and is saved to a "
            "new file -- the original is never modified."
        ))

        toolbar = QHBoxLayout()
        self.btn_open = QPushButton("Open PDF")
        self.btn_scan = QPushButton("Find Sensitive Data")
        self.btn_scan.setObjectName("SecondaryButton")
        toolbar.addWidget(self.btn_open)
        toolbar.addWidget(self.btn_scan)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        pattern_group = QGroupBox("Patterns to Search For")
        pattern_layout = QHBoxLayout(pattern_group)
        self.pattern_checkboxes: dict[str, QCheckBox] = {}
        for pattern in _ALL_PATTERNS:
            chk = QCheckBox(pattern)
            chk.setChecked(pattern in DEFAULT_ENABLED_PATTERNS)
            self.pattern_checkboxes[pattern] = chk
            pattern_layout.addWidget(chk)
        root.addWidget(pattern_group)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Approve", "Page", "Type", "Matched Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellClicked.connect(self._on_row_clicked)
        root.addWidget(self.table, 1)

        self.preview = PdfPreviewWidget()
        self.preview.setMaximumHeight(260)
        root.addWidget(self.preview)

        button_row = QHBoxLayout()
        self.btn_select_all = QPushButton("Approve All")
        self.btn_select_all.setObjectName("SecondaryButton")
        self.btn_select_none = QPushButton("Approve None")
        self.btn_select_none.setObjectName("SecondaryButton")
        self.btn_apply = QPushButton("APPLY REDACTION")
        button_row.addWidget(self.btn_select_all)
        button_row.addWidget(self.btn_select_none)
        button_row.addStretch(1)
        button_row.addWidget(self.btn_apply)
        root.addLayout(button_row)

        self.btn_open.clicked.connect(self.open_pdf)
        self.btn_scan.clicked.connect(self.scan_for_sensitive_data)
        self.btn_select_all.clicked.connect(lambda: self._set_all_approved(True))
        self.btn_select_none.clicked.connect(lambda: self._set_all_approved(False))
        self.btn_apply.clicked.connect(self.apply_redaction)

    def open_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", self.ctx.config.settings.last_used_folder, "PDF Files (*.pdf)")
        if not path:
            return
        self.source_path = path
        self.candidates = []
        self.table.setRowCount(0)
        try:
            self.preview.load_pdf(path)
        except ValidationError as exc:
            show_error(self, "Cannot Open File", str(exc))

    def scan_for_sensitive_data(self) -> None:
        if not self.source_path:
            QMessageBox.information(self, "No Document", "Open a PDF first.")
            return
        enabled = [name for name, chk in self.pattern_checkboxes.items() if chk.isChecked()]
        if not enabled:
            QMessageBox.information(self, "No Patterns Selected", "Select at least one pattern to search for.")
            return
        try:
            self.candidates = find_redaction_candidates(self.source_path, pattern_names=enabled)
        except ValidationError as exc:
            show_error(self, "Scan Failed", str(exc))
            return
        self._refresh_table()
        if not self.candidates:
            QMessageBox.information(self, "No Matches", "No sensitive values matching the selected patterns were found.")

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self.candidates))
        for row, c in enumerate(self.candidates):
            chk = QCheckBox()
            chk.setChecked(c.approved)
            chk.stateChanged.connect(lambda state, cand=c: setattr(cand, "approved", state == Qt.CheckState.Checked.value))
            self.table.setCellWidget(row, 0, chk)
            self.table.setItem(row, 1, QTableWidgetItem(str(c.page_index + 1)))
            self.table.setItem(row, 2, QTableWidgetItem(c.pattern_name))
            self.table.setItem(row, 3, QTableWidgetItem(c.matched_text))

    def _set_all_approved(self, approved: bool) -> None:
        for c in self.candidates:
            c.approved = approved
        self._refresh_table()

    def _on_row_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self.candidates):
            self.preview.go_to_page(self.candidates[row].page_index)

    def process(self) -> None:
        self.apply_redaction()

    def apply_redaction(self) -> None:
        if not self.source_path:
            QMessageBox.information(self, "No Document", "Open a PDF first.")
            return
        approved_count = sum(1 for c in self.candidates if c.approved)
        if approved_count == 0:
            QMessageBox.information(self, "Nothing Approved", "Approve at least one match before applying redaction.")
            return

        proceed = QMessageBox.warning(
            self,
            "Permanently Redact?",
            f"This will permanently remove {approved_count} approved value(s) from a new copy of the "
            "document. This cannot be undone on that copy, though your original file is never touched. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if proceed != QMessageBox.StandardButton.Yes:
            return

        default_out = str(Path(self.source_path).with_name(f"{Path(self.source_path).stem}_Redacted.pdf"))
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Redacted PDF As", default_out, "PDF Files (*.pdf)")
        if not out_path:
            return

        try:
            applied_values = [c.matched_text for c in self.candidates if c.approved]
            applied = apply_redactions(self.source_path, out_path, self.candidates)
            still_present = verify_redaction(out_path, applied_values)
        except ValidationError as exc:
            show_error(self, "Redaction Failed", str(exc))
            return

        log_operation(logger, operation="redact", input_file=self.source_path, output_file=out_path, result="success")
        if self.ctx.config.settings.enable_activity_register:
            from datetime import datetime

            self.ctx.database.add_audit_entry(
                AuditEntry(
                    timestamp=datetime.now().isoformat(), operator=self.ctx.operator, operation="Redact PDF",
                    source_document=self.source_path, output_document=out_path,
                    pages_processed=f"{applied} redaction(s) applied", template_used="", result="Success",
                )
            )

        if still_present:
            QMessageBox.warning(
                self, "Verification Warning",
                f"{applied} redaction box(es) were applied, but {len(still_present)} value(s) could still be "
                "found in the output (they may appear elsewhere on the page in a form the search didn't match). "
                "Please review the output document manually before relying on it.",
            )
        else:
            QMessageBox.information(
                self, "Redaction Complete",
                f"{applied} value(s) permanently removed and verified absent from the output:\n{out_path}",
            )
