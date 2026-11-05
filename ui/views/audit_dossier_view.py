"""
LexSecure India Pro - Phase 5: Tamper-Evident Audit Trail & Defense Dossier
Chained SHA-256 Verification & Board/Regulator Submission Generator
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ui.styles import THEME_COLORS
from services.audit_service import AuditDefenseService
from database.db_engine import DatabaseEngine
from models.entities import TamperAuditLog

class AuditDossierView(QWidget):
    def __init__(self, current_org_id: int = 1):
        super().__init__()
        self.current_org_id = current_org_id
        self.db = DatabaseEngine.get_instance()
        self.audit_service = AuditDefenseService(self.db)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. Top Integrity Banner
        self.banner = QFrame()
        self.banner.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B1120, stop:1 #1E293B);
            border: 1px solid #10B981;
            border-radius: 10px;
            padding: 14px 20px;
        """)
        banner_layout = QHBoxLayout(self.banner)

        # Integrity Status
        status_box = QVBoxLayout()
        self.status_title = QLabel("🛡️ CRYPTOGRAPHIC AUDIT INTEGRITY: VALID & INTACT")
        self.status_title.setStyleSheet("color: #10B981; font-size: 15px; font-weight: bold;")
        status_box.addWidget(self.status_title)

        self.status_desc = QLabel("SHA-256 Chained Hash Algorithm • Zero Tampering Detected • Pan-India Regulatory Evidentiary Standard")
        self.status_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        status_box.addWidget(self.status_desc)

        self.hash_head_lbl = QLabel("Chain Head Hash: <code>loading...</code>")
        self.hash_head_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.hash_head_lbl.setStyleSheet("color: #38BDF8; font-size: 11px; font-family: monospace;")
        status_box.addWidget(self.hash_head_lbl)

        banner_layout.addLayout(status_box)
        banner_layout.addStretch()

        # Download Dossier Button
        self.btn_download = QPushButton("⬇ Download Regulatory Defense Dossier")
        self.btn_download.setProperty("class", "btn-emerald")
        self.btn_download.clicked.connect(self.generate_and_save_dossier)
        banner_layout.addWidget(self.btn_download)

        main_layout.addWidget(self.banner)

        # 2. Splitter: Audit Table (Top/Left) vs Selected Log Payload (Bottom/Right)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #334155;
                height: 4px;
            }
        """)

        # Table Container
        table_widget = QWidget()
        t_layout = QVBoxLayout(table_widget)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(8)

        t_header = QHBoxLayout()
        t_title = QLabel("IMMUTABLE EVENT LOGS (REVERSE CHRONOLOGICAL)")
        t_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        t_header.addWidget(t_title)

        verify_btn = QPushButton("⚡ Re-Verify All Hash Links")
        verify_btn.setProperty("class", "btn-outline")
        verify_btn.clicked.connect(self.verify_and_refresh)
        t_header.addWidget(verify_btn, 0, Qt.AlignmentFlag.AlignRight)
        t_layout.addLayout(t_header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Timestamp (IST)", "Actor", "Event Type", "Target Entity", "Prev SHA-256 Hash", "Current SHA-256 Hash"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 8px;
                gridline-color: #334155;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
        """)
        self.table.cellClicked.connect(self.on_log_clicked)
        t_layout.addWidget(self.table)
        splitter.addWidget(table_widget)

        # Detail Box
        detail_widget = QWidget()
        d_layout = QVBoxLayout(detail_widget)
        d_layout.setContentsMargins(0, 8, 0, 0)
        d_layout.setSpacing(6)

        d_title = QLabel("CRYPTOGRAPHIC EVENT PAYLOAD & VERIFICATION PARAMETERS")
        d_title.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: bold;")
        d_layout.addWidget(d_title)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet("""
            background-color: #0B1120;
            color: #5EEAD4;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 10px;
            font-family: 'Consolas', monospace;
            font-size: 12px;
        """)
        self.detail_text.setPlaceholderText("Click on any audit record above to inspect its cryptographically signed JSON payload...")
        d_layout.addWidget(self.detail_text)
        splitter.addWidget(detail_widget)

        splitter.setSizes([420, 200])
        main_layout.addWidget(splitter, 1)

        self.verify_and_refresh()

    def verify_and_refresh(self):
        # 1. Verify chain
        integrity = self.audit_service.verify_audit_integrity(self.current_org_id)
        if integrity["is_valid"]:
            self.status_title.setText("🛡️ CRYPTOGRAPHIC AUDIT INTEGRITY: VALID & INTACT")
            self.status_title.setStyleSheet("color: #10B981; font-size: 15px; font-weight: bold;")
            self.banner.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B1120, stop:1 #1E293B);
                border: 1px solid #10B981;
                border-radius: 10px;
                padding: 14px 20px;
            """)
        else:
            self.status_title.setText(f"⚠️ INTEGRITY BREACH: TAMPER DETECTED AT LOG #{integrity['broken_at_id']}")
            self.status_title.setStyleSheet("color: #EF4444; font-size: 15px; font-weight: bold;")
            self.banner.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B1120, stop:1 #1E293B);
                border: 1px solid #EF4444;
                border-radius: 10px;
                padding: 14px 20px;
            """)

        self.hash_head_lbl.setText(f"Chain Head SHA-256: <code>{integrity['latest_head_hash']}</code>")

        # 2. Load logs
        self.logs = TamperAuditLog.get_all(self.current_org_id)
        self.table.setRowCount(len(self.logs))

        for row_idx, l in enumerate(self.logs):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(l.id)))
            self.table.setItem(row_idx, 1, QTableWidgetItem(l.timestamp[:19]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(l.actor_name or "System"))
            
            # Event Type
            ev_item = QTableWidgetItem(l.event_type)
            ev_item.setForeground(QColor("#38BDF8"))
            self.table.setItem(row_idx, 3, ev_item)

            self.table.setItem(row_idx, 4, QTableWidgetItem(f"{l.target_model} #{l.target_id}"))

            # Prev Hash
            p_item = QTableWidgetItem(f"{l.prev_hash[:16]}...")
            p_item.setToolTip(l.prev_hash)
            p_item.setForeground(QColor("#94A3B8"))
            self.table.setItem(row_idx, 5, p_item)

            # Curr Hash
            c_item = QTableWidgetItem(f"{l.current_hash[:16]}...")
            c_item.setToolTip(l.current_hash)
            c_item.setForeground(QColor("#10B981"))
            self.table.setItem(row_idx, 6, c_item)

    def on_log_clicked(self, row: int, col: int):
        if 0 <= row < len(self.logs):
            l = self.logs[row]
            payload = f"""--- AUDIT EVENT RECORD #{l.id} ---
Timestamp      : {l.timestamp}
Actor          : {l.actor_name} (ID: {l.actor_id})
Event Type     : {l.event_type}
Target Model   : {l.target_model}
Target ID      : {l.target_id}
IP Address     : {l.ip_address}

PREVIOUS HASH  : {l.prev_hash}
CURRENT HASH   : {l.current_hash}

DETAILS JSON PAYLOAD:
{l.details_json}
"""
            self.detail_text.setPlainText(payload)

    def generate_and_save_dossier(self):
        default_name = f"LexSecure_India_Pro_Defense_Dossier_{self.current_org_id}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Regulatory Defense Dossier", default_name, "PDF Document (*.pdf);;HTML Document (*.html);;All Files (*.*)"
        )
        if not save_path:
            return

        try:
            generated_file = self.audit_service.generate_defense_dossier_pdf(save_path, self.current_org_id)
            QMessageBox.information(
                self, "Dossier Exported",
                f"Regulatory Compliance Defense Dossier generated successfully!\n\nLocation: {generated_file}\nCryptographic verification confirmed."
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate defense dossier: {str(e)}")
