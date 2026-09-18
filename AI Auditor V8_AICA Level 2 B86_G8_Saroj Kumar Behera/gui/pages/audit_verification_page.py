"""
AI Auditor V8 - Audit Verification Checklist Page
Interactive document checklist and corroborative evidence matrix explaining WHY each document is required.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
from core.models import FinancialModel

class AuditVerificationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: FinancialModel = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_vbox = QVBoxLayout()
        lbl_title = QLabel("Audit Verification & Corroborative Evidence Checklist")
        lbl_title.setProperty("class", "page-title")
        lbl_sub = QLabel("Substantive audit documents required for material variations, with statutory auditing rationale.")
        lbl_sub.setProperty("class", "page-subtitle")
        header_vbox.addWidget(lbl_title)
        header_vbox.addWidget(lbl_sub)
        top_bar.addLayout(header_vbox)
        top_bar.addStretch()

        btn_mark_all = QPushButton("Select / Clear All")
        btn_mark_all.setProperty("class", "secondary-btn")
        btn_mark_all.clicked.connect(self._toggle_select_all)
        top_bar.addWidget(btn_mark_all)
        main_layout.addLayout(top_bar)

        # Verification Table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.table)

    def load_model(self, model: FinancialModel):
        self.model = model
        
        flat_reqs = []
        for v in model.variations:
            for item in v.get("audit_verification", []):
                flat_reqs.append({
                    "particulars": v["particulars"],
                    "direction": v["direction"],
                    "change": f"{v['percentage_change']:+.1f}%",
                    "doc": item["doc"],
                    "why": item["why"]
                })

        headers = ["Status", "Financial Line Item", "Movement", "Required Audit Document / Evidence", "WHY Required (Audit Rationale)"]
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setRowCount(len(flat_reqs))
        self.table.setHorizontalHeaderLabels(headers)

        for r_idx, r in enumerate(flat_reqs):
            # Checkbox Status
            chk = QCheckBox("Pending")
            chk.stateChanged.connect(lambda state, c=chk: c.setText("Verified" if state == Qt.Checked else "Pending"))
            self.table.setCellWidget(r_idx, 0, chk)

            # Particulars
            c_part = QTableWidgetItem(r["particulars"])
            c_part.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(r_idx, 1, c_part)

            # Movement
            c_mov = QTableWidgetItem(f"{r['direction']} ({r['change']})")
            c_mov.setTextAlignment(Qt.AlignCenter)
            c_mov.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(r_idx, 2, c_mov)

            # Doc
            c_doc = QTableWidgetItem(r["doc"])
            c_doc.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(r_idx, 3, c_doc)

            # Why
            c_why = QTableWidgetItem(r["why"])
            c_why.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(r_idx, 4, c_why)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(3, 260)
        self.table.setColumnWidth(4, 380)

    def _toggle_select_all(self):
        for r in range(self.table.rowCount()):
            chk = self.table.cellWidget(r, 0)
            if isinstance(chk, QCheckBox):
                chk.setChecked(not chk.isChecked())
