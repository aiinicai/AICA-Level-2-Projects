from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableView,
    QHeaderView,
    QComboBox,
    QLineEdit,
    QLabel,
    QGroupBox,
    QSplitter,
    QFrame,
    QTextEdit,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QItemSelection, QModelIndex

from reconai.models.session import ReconciliationSession
from reconai.models.transaction import AuditFlag, AuditSeverity, AuditCategory
from reconai.ui.components.stat_card import StatCard
from reconai.ui.components.table_models import AuditFlagsTableModel


class AuditView(QWidget):
    """Expense and compliance exception analysis view."""

    def __init__(self, session: ReconciliationSession, parent=None):
        super().__init__(parent)
        self.session = session
        self.table_model = AuditFlagsTableModel()
        self._filtered_flags: List[AuditFlag] = []
        self._current_flag: Optional[AuditFlag] = None
        self._is_updating_ui = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Summary KPI Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_total = StatCard("Total Exceptions", "0", "Flags raised for review")
        self.card_high = StatCard("High Severity", "0", "Critical compliance & risk")
        self.card_medium = StatCard("Medium Severity", "0", "Policy & threshold breaches")
        self.card_low = StatCard("Low / Info", "0", "Operational observations")

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_high)
        cards_layout.addWidget(self.card_medium)
        cards_layout.addWidget(self.card_low)
        layout.addLayout(cards_layout)

        # 2. Filter Bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Severity:"))

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["ALL SEVERITIES", "HIGH", "MEDIUM", "LOW", "INFO"])
        self.severity_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.severity_combo)

        filter_layout.addSpacing(15)
        filter_layout.addWidget(QLabel("Search Particulars / Reason:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter by voucher ref, vendor, rule name...")
        self.search_edit.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_edit, 1)

        layout.addLayout(filter_layout)

        # 3. Main Splitter (Table on left, Deep Editable Explanation Card on right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Table View with full row selection
        self.table = QTableView()
        self.table.setModel(self.table_model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.selectionModel().selectionChanged.connect(self._on_row_selected)
        self.table.clicked.connect(self._on_table_clicked)
        splitter.addWidget(self.table)

        # Forensic Detail Card (Fully Editable)
        detail_frame = QFrame()
        detail_frame.setObjectName("cardFrame")
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(14, 14, 14, 14)
        detail_layout.setSpacing(8)

        self.detail_title = QLabel("Forensic Risk & Regulatory Analysis (Editable)")
        self.detail_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #93C5FD;")
        detail_layout.addWidget(self.detail_title)

        # Severity & Info Row
        sev_row = QHBoxLayout()
        self.detail_sev_label = QLabel("Select an exception from the table to view/edit.")
        self.detail_sev_label.setWordWrap(True)
        sev_row.addWidget(self.detail_sev_label, 1)

        sev_row.addWidget(QLabel("Severity:"))
        self.edit_sev_combo = QComboBox()
        self.edit_sev_combo.addItems(["HIGH", "MEDIUM", "LOW", "INFO"])
        self.edit_sev_combo.setEnabled(False)
        self.edit_sev_combo.currentTextChanged.connect(self._on_severity_edited)
        sev_row.addWidget(self.edit_sev_combo)
        detail_layout.addLayout(sev_row)

        detail_layout.addWidget(QLabel("<b>✏️ Auditor Finding / Legal Reasoning (Click to Edit):</b>"))
        self.reason_text = QTextEdit()
        self.reason_text.setReadOnly(False)
        self.reason_text.setEnabled(False)
        self.reason_text.setPlaceholderText("Select an exception from the table to edit auditor findings...")
        self.reason_text.textChanged.connect(self._on_detail_edited)
        detail_layout.addWidget(self.reason_text, 1)

        detail_layout.addWidget(QLabel("<b>✏️ Recommended Action for CA Team (Click to Edit):</b>"))
        self.action_text = QTextEdit()
        self.action_text.setReadOnly(False)
        self.action_text.setEnabled(False)
        self.action_text.setFixedHeight(85)
        self.action_text.setPlaceholderText("Select an exception to edit recommended CA action...")
        self.action_text.textChanged.connect(self._on_detail_edited)
        detail_layout.addWidget(self.action_text)

        # Save / Feedback Bar
        btn_bar = QHBoxLayout()
        self.save_finding_btn = QPushButton("💾 Save & Apply Finding Changes")
        self.save_finding_btn.setObjectName("primaryBtn")
        self.save_finding_btn.setEnabled(False)
        self.save_finding_btn.clicked.connect(self._save_finding_explicit)
        btn_bar.addWidget(self.save_finding_btn)
        detail_layout.addLayout(btn_bar)

        splitter.addWidget(detail_frame)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, 1)

    def refresh_data(self):
        flags = self.session.audit_flags
        high_cnt = len([f for f in flags if f.severity == AuditSeverity.HIGH])
        med_cnt = len([f for f in flags if f.severity == AuditSeverity.MEDIUM])
        low_cnt = len([f for f in flags if f.severity in (AuditSeverity.LOW, AuditSeverity.INFO)])

        self.card_total.set_value(str(len(flags)), "Across all rules")
        self.card_high.set_value(str(high_cnt), "Requires mandatory sign-off")
        self.card_medium.set_value(str(med_cnt), "Review documentation")
        self.card_low.set_value(str(low_cnt), "Information notes")

        self._apply_filters()

    def _apply_filters(self):
        flags = self.session.audit_flags
        sev_filter = self.severity_combo.currentText()
        search_query = self.search_edit.text().strip().lower()

        filtered = []
        for f in flags:
            if sev_filter != "ALL SEVERITIES" and f.severity.value != sev_filter:
                continue
            if search_query:
                q_text = f"{f.source_row_ref} {f.rule_name} {f.category.value} {f.plain_english_reason}".lower()
                if search_query not in q_text:
                    continue
            filtered.append(f)

        self._filtered_flags = filtered
        self.table_model.set_data(filtered)

        # Auto-load the first exception so the editor is never blank
        if filtered:
            self.table.selectRow(0)
            self._load_flag_for_row(0)
        else:
            self._clear_detail_panel()

    def _on_table_clicked(self, index: QModelIndex):
        if index.isValid():
            self._load_flag_for_row(index.row())

    def _on_row_selected(self, selected: QItemSelection, deselected: QItemSelection):
        indexes = self.table.selectionModel().selectedIndexes()
        if not indexes:
            return
        row = indexes[0].row()
        self._load_flag_for_row(row)

    def _load_flag_for_row(self, row: int):
        flag = self.table_model.get_flag(row)
        if not flag:
            self._clear_detail_panel()
            return

        self._current_flag = flag
        self._is_updating_ui = True

        self.reason_text.setEnabled(True)
        self.action_text.setEnabled(True)
        self.edit_sev_combo.setEnabled(True)
        self.save_finding_btn.setEnabled(True)

        sev_color = "#EF4444" if flag.severity == AuditSeverity.HIGH else "#F59E0B" if flag.severity == AuditSeverity.MEDIUM else "#3B82F6"
        self.detail_sev_label.setText(
            f"<b style='color:{sev_color}'>[{flag.severity.value} SEVERITY]</b> "
            f"Rule: <b>{flag.rule_name}</b> | Ref: <b>{flag.source_row_ref}</b>"
        )
        self.edit_sev_combo.setCurrentText(flag.severity.value)
        self.reason_text.setPlainText(flag.plain_english_reason)
        self.action_text.setPlainText(flag.suggested_action)

        self._is_updating_ui = False

    def _clear_detail_panel(self):
        self._current_flag = None
        self._is_updating_ui = True
        self.reason_text.clear()
        self.reason_text.setEnabled(False)
        self.action_text.clear()
        self.action_text.setEnabled(False)
        self.edit_sev_combo.setEnabled(False)
        self.save_finding_btn.setEnabled(False)
        self.detail_sev_label.setText("Select an exception from the table to view/edit.")
        self._is_updating_ui = False

    def _on_detail_edited(self):
        if self._is_updating_ui or not self._current_flag:
            return
        self._current_flag.plain_english_reason = self.reason_text.toPlainText().strip()
        self._current_flag.suggested_action = self.action_text.toPlainText().strip()
        self.table_model.layoutChanged.emit()

    def _on_severity_edited(self, new_sev: str):
        if self._is_updating_ui or not self._current_flag or not new_sev:
            return
        try:
            self._current_flag.severity = AuditSeverity(new_sev)
            sev_color = "#EF4444" if self._current_flag.severity == AuditSeverity.HIGH else "#F59E0B" if self._current_flag.severity == AuditSeverity.MEDIUM else "#3B82F6"
            self.detail_sev_label.setText(
                f"<b style='color:{sev_color}'>[{self._current_flag.severity.value} SEVERITY]</b> "
                f"Rule: <b>{self._current_flag.rule_name}</b> | Ref: <b>{self._current_flag.source_row_ref}</b>"
            )
            self.table_model.layoutChanged.emit()
            self._is_updating_ui = True
            flags = self.session.audit_flags
            self.card_total.set_value(str(len(flags)), "Across all rules")
            self.card_high.set_value(str(len([f for f in flags if f.severity == AuditSeverity.HIGH])), "Requires mandatory sign-off")
            self.card_medium.set_value(str(len([f for f in flags if f.severity == AuditSeverity.MEDIUM])), "Review documentation")
            self.card_low.set_value(str(len([f for f in flags if f.severity in (AuditSeverity.LOW, AuditSeverity.INFO)])), "Information notes")
            self._is_updating_ui = False
        except Exception:
            pass

    def _save_finding_explicit(self):
        if not self._current_flag:
            return
        self._on_detail_edited()
        self.table_model.layoutChanged.emit()
        QMessageBox.information(
            self,
            "Finding Saved",
            f"Custom audit finding and recommended action for Ref '{self._current_flag.source_row_ref}' saved and updated for report export.",
        )
