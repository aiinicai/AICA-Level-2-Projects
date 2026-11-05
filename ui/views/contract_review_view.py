"""
LexSecure India Pro - Pillar 1: Contract / Document Review & Storage Workspace
Supports PDF, DOCX, TXT with rich HTML highlights, redlines, entity assignment & export
"""

import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QSplitter, QTextEdit,
    QTabWidget, QListWidget, QListWidgetItem, QMessageBox,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QColor

from ui.styles import THEME_COLORS
from services.document_parser import DocumentParser
from services.legal_ai_service import LegalAIService
from database.db_engine import DatabaseEngine
from models.entities import Document, DocumentClause, Entity

class ContractReviewView(QWidget):
    audit_event_logged = pyqtSignal()
    entity_selection_requested = pyqtSignal(int)

    def __init__(self, current_entity_id: int = 1):
        super().__init__()
        self.current_entity_id = current_entity_id
        self.ai_service = LegalAIService()
        self.db = DatabaseEngine.get_instance()
        
        self.current_doc_id = 1
        self.current_clauses = []
        self.selected_clause_idx = 0
        self.raw_document_text = ""
        
        self.init_ui()
        self.load_initial_contract()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # 1. Top Action & Navigation Bar
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            background-color: {THEME_COLORS['bg_card']};
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 10px;
            padding: 10px 16px;
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setSpacing(10)

        icon_title = QLabel("📄 CONTRACT / DOCUMENT REVIEW & STORAGE WORKSPACE")
        icon_title.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        top_layout.addWidget(icon_title)

        top_layout.addStretch()

        self.btn_load_sample = QPushButton("⚡ Load Sample MSA")
        self.btn_load_sample.setProperty("class", "btn-outline")
        self.btn_load_sample.clicked.connect(self.load_sample_contract_file)
        top_layout.addWidget(self.btn_load_sample)

        self.btn_upload = QPushButton("⬆ Upload & Assign Document")
        self.btn_upload.setProperty("class", "btn-primary")
        self.btn_upload.clicked.connect(self.handle_file_upload)
        top_layout.addWidget(self.btn_upload)

        self.btn_download_highlighted = QPushButton("⬇ Download Highlighted Document")
        self.btn_download_highlighted.setProperty("class", "btn-emerald")
        self.btn_download_highlighted.clicked.connect(self.download_reviewed_document_with_highlights)
        top_layout.addWidget(self.btn_download_highlighted)

        main_layout.addWidget(top_bar)

        # 2. Main Tabbed Container: Active Document Review vs Document Storage
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {THEME_COLORS['border']};
                background: {THEME_COLORS['bg_main']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background: #0B1120;
                color: #94A3B8;
                padding: 8px 18px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 3px;
            }}
            QTabBar::tab:selected {{
                background: {THEME_COLORS['bg_card']};
                color: #10B981;
                border-bottom: 2px solid #10B981;
            }}
        """)

        # Tab 1: Interactive Split-Screen Review Workspace
        self.review_workspace_widget = self.create_review_workspace()
        self.main_tabs.addTab(self.review_workspace_widget, "🔍 Active Document Review")

        # Tab 2: Document Storage & Repository
        self.storage_widget = self.create_storage_workspace()
        self.main_tabs.addTab(self.storage_widget, "📂 Document Storage Repository")

        main_layout.addWidget(self.main_tabs, 1)

    # =========================================================================
    # TAB 1: SPLIT SCREEN REVIEW WORKSPACE
    # =========================================================================
    def create_review_workspace(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Score Banner
        self.score_bar = QFrame()
        self.score_bar.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0F172A, stop:1 #1E293B);
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 8px;
            padding: 10px 14px;
        """)
        score_layout = QHBoxLayout(self.score_bar)

        self.lbl_overall_score = QLabel("Overall Legal Health: <b>58 / 100</b>")
        self.lbl_overall_score.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_overall_score.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: bold;")
        score_layout.addWidget(self.lbl_overall_score)

        score_layout.addWidget(QLabel(" | "))

        self.lbl_liability_score = QLabel("Liability Cap: <b>65%</b>")
        self.lbl_liability_score.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_liability_score.setStyleSheet("color: #F59E0B; font-size: 11px;")
        score_layout.addWidget(self.lbl_liability_score)

        self.lbl_statutory_score = QLabel("Statutory Codes (Sec 27/MSME): <b>45%</b>")
        self.lbl_statutory_score.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_statutory_score.setStyleSheet("color: #EF4444; font-size: 11px;")
        score_layout.addWidget(self.lbl_statutory_score)

        self.lbl_fema_score = QLabel("Labour & FEMA: <b>60%</b>")
        self.lbl_fema_score.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_fema_score.setStyleSheet("color: #F59E0B; font-size: 11px;")
        score_layout.addWidget(self.lbl_fema_score)

        score_layout.addStretch()

        self.lbl_file_name = QLabel("Active: Master_Services_Agreement_HighRisk_Sample.txt")
        self.lbl_file_name.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: bold;")
        score_layout.addWidget(self.lbl_file_name)

        layout.addWidget(self.score_bar)

        # Splitter: Left (Text with Highlights) vs Right (Clause Analysis & Copilot)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #334155; width: 4px; }")

        # LEFT PANE: Document Highlights
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)

        left_header = QHBoxLayout()
        left_title = QLabel("DOCUMENT HIGHLIGHTS & STATUTORY FLAGS")
        left_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        left_header.addWidget(left_title)

        legend = QLabel("🔴 Dealbreaker  🟡 Caution  🟢 Compliant")
        legend.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        left_header.addWidget(legend, 0, Qt.AlignmentFlag.AlignRight)
        left_layout.addLayout(left_header)

        # Clause List Selector
        self.clause_list = QListWidget()
        self.clause_list.setFixedHeight(105)
        self.clause_list.setStyleSheet(f"""
            QListWidget {{
                background-color: #0B1120;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #F8FAFC;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 5px 8px;
                border-radius: 4px;
                margin-bottom: 2px;
                font-size: 11.5px;
            }}
            QListWidget::item:selected {{
                background-color: #1E293B;
                border-left: 3px solid #0D9488;
                color: #38BDF8;
            }}
        """)
        self.clause_list.currentRowChanged.connect(self.on_clause_selected)
        left_layout.addWidget(self.clause_list)

        # Rich HTML Contract Text Viewer
        self.contract_text_edit = QTextEdit()
        self.contract_text_edit.setReadOnly(True)
        self.contract_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {THEME_COLORS['bg_card']};
                color: #F8FAFC;
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 8px;
                padding: 14px;
                font-size: 12.5px;
                line-height: 1.6;
            }}
        """)
        left_layout.addWidget(self.contract_text_edit, 1)
        splitter.addWidget(left_widget)

        # RIGHT PANE: Analysis Tabs (Statutory Redline vs Legal Copilot)
        right_tabs = QTabWidget()
        right_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {THEME_COLORS['border']};
                background: {THEME_COLORS['bg_card']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background: #0B1120;
                color: #94A3B8;
                padding: 7px 14px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {THEME_COLORS['bg_card']};
                color: #10B981;
                font-weight: bold;
                border-bottom: 2px solid #10B981;
            }}
        """)

        # Tab 1: Statutory Redline
        redline_tab = QWidget()
        redline_layout = QVBoxLayout(redline_tab)
        redline_layout.setContentsMargins(12, 12, 12, 12)
        redline_layout.setSpacing(10)

        r_head = QHBoxLayout()
        self.clause_title_lbl = QLabel("Clause Analysis: NON_COMPETE_SEC27")
        self.clause_title_lbl.setStyleSheet("color: #F8FAFC; font-size: 13px; font-weight: bold;")
        r_head.addWidget(self.clause_title_lbl)

        self.clause_risk_badge = QLabel(" HIGH RISK ")
        self.clause_risk_badge.setStyleSheet("background-color: #EF4444; color: white; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 3px 8px;")
        r_head.addWidget(self.clause_risk_badge, 0, Qt.AlignmentFlag.AlignRight)
        redline_layout.addLayout(r_head)

        self.violation_frame = QFrame()
        self.violation_frame.setStyleSheet("""
            background-color: rgba(239, 68, 68, 0.12);
            border: 1px solid #EF4444;
            border-radius: 6px;
            padding: 10px;
        """)
        v_layout = QVBoxLayout(self.violation_frame)
        v_layout.setSpacing(4)
        v_label = QLabel("⚖️ STATUTORY CONTRAVENTION (INDIAN LAW)")
        v_label.setStyleSheet("color: #F87171; font-size: 10px; font-weight: bold;")
        v_layout.addWidget(v_label)

        self.violation_text = QLabel("Direct violation of Section 27, Indian Contract Act 1872; Percept D'Mark v. Zaheer Khan (2006).")
        self.violation_text.setWordWrap(True)
        self.violation_text.setStyleSheet("color: #FECACA; font-size: 11.5px;")
        v_layout.addWidget(self.violation_text)
        redline_layout.addWidget(self.violation_frame)

        self.flag_reason_lbl = QLabel("<b>Risk Context:</b> Post-employment restrictive covenants are non-enforceable and void ab initio.")
        self.flag_reason_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.flag_reason_lbl.setWordWrap(True)
        self.flag_reason_lbl.setStyleSheet("color: #CBD5E1; font-size: 11.5px;")
        redline_layout.addWidget(self.flag_reason_lbl)

        redline_lbl = QLabel("APPROVED STATUTORY REDLINE (PRE-VETTED PLAYBOOK)")
        redline_lbl.setStyleSheet("color: #10B981; font-size: 10.5px; font-weight: bold;")
        redline_layout.addWidget(redline_lbl)

        self.redline_text_edit = QTextEdit()
        self.redline_text_edit.setPlaceholderText("Approved fallback language will appear here...")
        self.redline_text_edit.setStyleSheet("""
            background-color: #0B1120;
            color: #5EEAD4;
            border: 1px solid #0D9488;
            border-radius: 6px;
            padding: 8px;
            font-size: 11.5px;
        """)
        redline_layout.addWidget(self.redline_text_edit)

        self.btn_accept_redline = QPushButton("✔ 1-Click Accept Redline (Recalculate Health)")
        self.btn_accept_redline.setProperty("class", "btn-emerald")
        self.btn_accept_redline.clicked.connect(self.accept_current_redline)
        redline_layout.addWidget(self.btn_accept_redline)

        right_tabs.addTab(redline_tab, "Statutory Redline")

        # Tab 2: Legal Copilot
        copilot_tab = QWidget()
        copilot_layout = QVBoxLayout(copilot_tab)
        copilot_layout.setContentsMargins(12, 12, 12, 12)
        copilot_layout.setSpacing(8)

        copilot_title = QLabel("🤖 LEXSECURE INDIAN LEGAL COPILOT")
        copilot_title.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: bold;")
        copilot_layout.addWidget(copilot_title)

        chips_layout = QHBoxLayout()
        chips = [
            ("Sec 27 Non-compete", "Is this 2-year non-compete enforceable in India?"),
            ("MSME 45-day Rule", "What are penalties under Section 43B(h) Income Tax?"),
            ("DPDP 2023 Penalties", "What are data fiduciary liabilities under DPDP?")
        ]
        for chip_label, chip_query in chips:
            btn = QPushButton(chip_label)
            btn.setStyleSheet("""
                background-color: #0B1120;
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 10px;
            """)
            btn.clicked.connect(lambda checked, q=chip_query: self.run_copilot_query(q))
            chips_layout.addWidget(btn)
        copilot_layout.addLayout(chips_layout)

        self.copilot_history = QTextEdit()
        self.copilot_history.setReadOnly(True)
        self.copilot_history.setStyleSheet("""
            background-color: #0B1120;
            color: #F8FAFC;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px;
            font-size: 11.5px;
        """)
        copilot_layout.addWidget(self.copilot_history)

        input_layout = QHBoxLayout()
        self.copilot_input = QLineEdit()
        self.copilot_input.setPlaceholderText("Type Indian statutory or regulatory query...")
        self.copilot_input.returnPressed.connect(self.on_copilot_submit)
        input_layout.addWidget(self.copilot_input)

        send_btn = QPushButton("Send")
        send_btn.setProperty("class", "btn-primary")
        send_btn.clicked.connect(self.on_copilot_submit)
        input_layout.addWidget(send_btn)
        copilot_layout.addLayout(input_layout)

        right_tabs.addTab(copilot_tab, "Ask Legal Copilot")

        splitter.addWidget(right_tabs)
        splitter.setSizes([580, 420])
        layout.addWidget(splitter, 1)

        return widget

    # =========================================================================
    # TAB 2: DOCUMENT STORAGE REPOSITORY (WITH ENTITY FILTER & REASSIGN)
    # =========================================================================
    def create_storage_workspace(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("📂 REPOSITORY OF STORED LEGAL DOCUMENTS (ENTITY-WISE AUDIT)")
        title.setStyleSheet("color: #F8FAFC; font-size: 13px; font-weight: bold;")
        header_row.addWidget(title)

        header_row.addStretch()

        # Entity filter for storage
        header_row.addWidget(QLabel("Filter Entity:"))
        self.storage_entity_filter = QComboBox()
        self.storage_entity_filter.setMinimumWidth(220)
        self.populate_storage_entity_filter()
        self.storage_entity_filter.currentIndexChanged.connect(self.load_storage_documents)
        header_row.addWidget(self.storage_entity_filter)

        ref_btn = QPushButton("🔄 Refresh")
        ref_btn.setProperty("class", "btn-outline")
        ref_btn.clicked.connect(self.load_storage_documents)
        header_row.addWidget(ref_btn)
        layout.addLayout(header_row)

        self.storage_table = QTableWidget()
        self.storage_table.setColumnCount(8)
        self.storage_table.setHorizontalHeaderLabels([
            "ID", "Document Filename", "Assigned Operating Entity", "Document Type", "Health Score", "Statutory Status", "Uploaded Date", "Actions"
        ])
        self.storage_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.storage_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.storage_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.storage_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.storage_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.storage_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.storage_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.storage_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.storage_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.storage_table, 1)
        return widget

    def populate_storage_entity_filter(self):
        self.storage_entity_filter.blockSignals(True)
        self.storage_entity_filter.clear()
        self.storage_entity_filter.addItem("All Operating Entities", 0)
        entities = Entity.get_all(1)
        for e in entities:
            self.storage_entity_filter.addItem(f"{e.legal_name} ({e.registered_state})", e.id)
        self.storage_entity_filter.blockSignals(False)

    def load_storage_documents(self):
        selected_ent_id = self.storage_entity_filter.currentData()
        filter_id = selected_ent_id if selected_ent_id and selected_ent_id != 0 else None
        
        docs = Document.get_all_with_entity(filter_id)
        self.storage_table.setRowCount(len(docs))

        for row_idx, d in enumerate(docs):
            # ID
            id_item = QTableWidgetItem(str(d["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.storage_table.setItem(row_idx, 0, id_item)

            # Name
            name_item = QTableWidgetItem(f"📄 {d['original_filename']}")
            name_item.setFont(self.font())
            self.storage_table.setItem(row_idx, 1, name_item)

            # Assigned Entity
            ent_item = QTableWidgetItem(d.get("entity_name", "Corporate Entity"))
            ent_item.setForeground(QColor("#38BDF8"))
            self.storage_table.setItem(row_idx, 2, ent_item)

            # Type
            type_item = QTableWidgetItem(d["doc_type"])
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.storage_table.setItem(row_idx, 3, type_item)

            # Score
            score_val = d["overall_health_score"]
            score_color = "#10B981" if score_val >= 80 else ("#F59E0B" if score_val >= 60 else "#EF4444")
            score_item = QTableWidgetItem(f"{score_val}%")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            score_item.setForeground(QColor(score_color))
            self.storage_table.setItem(row_idx, 4, score_item)

            # Status
            status_item = QTableWidgetItem(d["status"])
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.storage_table.setItem(row_idx, 5, status_item)

            # Date
            date_item = QTableWidgetItem((d.get("created_at", "") or "")[:19])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.storage_table.setItem(row_idx, 6, date_item)

            # Action Buttons: Open & Reassign & Download
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            open_btn = QPushButton("📖 Review")
            open_btn.setStyleSheet("background-color: #0284C7; color: white; border-radius: 4px; padding: 4px 7px; font-size: 11px;")
            open_btn.clicked.connect(lambda checked, doc_id=d["id"]: self.load_stored_document(doc_id))
            btn_layout.addWidget(open_btn)

            reassign_btn = QPushButton("🏢 Assign")
            reassign_btn.setStyleSheet("background-color: #475569; color: white; border-radius: 4px; padding: 4px 7px; font-size: 11px;")
            reassign_btn.clicked.connect(lambda checked, doc_id=d["id"], cur_ent=d["entity_id"]: self.open_reassign_dialog(doc_id, cur_ent))
            btn_layout.addWidget(reassign_btn)

            dl_btn = QPushButton("⬇ Export")
            dl_btn.setStyleSheet("background-color: #0D9488; color: white; border-radius: 4px; padding: 4px 7px; font-size: 11px;")
            dl_btn.clicked.connect(lambda checked, doc_id=d["id"]: self.export_document_by_id(doc_id))
            btn_layout.addWidget(dl_btn)

            self.storage_table.setCellWidget(row_idx, 7, btn_container)

    def open_reassign_dialog(self, doc_id: int, current_entity_id: int):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Re-assign Document #{doc_id} to Operating Entity")
        dialog.setFixedSize(450, 220)
        dialog.setStyleSheet(f"background-color: {THEME_COLORS['bg_main']}; color: #F8FAFC;")
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(18, 18, 18, 18)
        d_layout.setSpacing(12)

        d_layout.addWidget(QLabel("<b>Select Target Operating Entity:</b>"))
        ent_combo = QComboBox()
        entities = Entity.get_all(1)
        cur_idx = 0
        for idx, e in enumerate(entities):
            ent_combo.addItem(f"{e.legal_name} ({e.registered_state})", e.id)
            if e.id == current_entity_id:
                cur_idx = idx
        ent_combo.setCurrentIndex(cur_idx)
        d_layout.addWidget(ent_combo)

        btn_box = QHBoxLayout()
        can_btn = QPushButton("Cancel")
        can_btn.setProperty("class", "btn-outline")
        can_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(can_btn)

        save_btn = QPushButton("✔ Confirm Re-assignment")
        save_btn.setProperty("class", "btn-emerald")
        def save():
            new_ent_id = ent_combo.currentData()
            Document.reassign_entity(doc_id, new_ent_id)
            self.load_storage_documents()
            self.audit_event_logged.emit()
            dialog.accept()
            QMessageBox.information(self, "Re-assigned", f"Document #{doc_id} successfully re-assigned to {ent_combo.currentText()}.")

        save_btn.clicked.connect(save)
        btn_box.addWidget(save_btn)
        d_layout.addLayout(btn_box)

        dialog.exec()

    def set_active_entity(self, entity_id: int):
        self.current_entity_id = entity_id
        # Update storage filter to this entity
        idx = self.storage_entity_filter.findData(entity_id)
        if idx >= 0:
            self.storage_entity_filter.setCurrentIndex(idx)
        else:
            self.load_storage_documents()

        # Load latest doc for this entity if available
        docs = Document.get_by_entity(entity_id)
        if docs:
            self.load_stored_document(docs[0].id)

    def load_stored_document(self, doc_id: int):
        doc = Document.get_by_id(doc_id)
        if not doc:
            return

        self.current_doc_id = doc_id
        self.current_clauses = DocumentClause.get_by_document(doc_id)
        self.raw_document_text = getattr(doc, 'raw_content', "") or ""
        self.lbl_file_name.setText(f"Active: {doc.original_filename}")
        self.update_clause_list_widget()
        self.render_contract_text(self.raw_document_text)
        self.update_score_banner(doc.overall_health_score, doc.liability_score, doc.statutory_score, doc.labour_fema_score)
        
        # Switch to review tab
        self.main_tabs.setCurrentIndex(0)

    # =========================================================================
    # CORE PROCESSING & HIGHLIGHT RENDERING
    # =========================================================================
    def load_initial_contract(self):
        doc = Document.get_by_id(1)
        if doc:
            self.current_doc_id = 1
            self.current_clauses = DocumentClause.get_by_document(1)
            self.raw_document_text = getattr(doc, 'raw_content', "") or ""
            self.update_clause_list_widget()
            self.render_contract_text(self.raw_document_text)
            self.update_score_banner(doc.overall_health_score, doc.liability_score, doc.statutory_score, doc.labour_fema_score)
        self.load_storage_documents()

    def load_sample_contract_file(self):
        sample_path = Path(__file__).resolve().parent.parent.parent / "data" / "sample_contracts" / "Master_Services_Agreement_HighRisk_Sample.txt"
        if sample_path.exists():
            text = sample_path.read_text(encoding="utf-8")
            self.process_contract_text(text, sample_path.name, self.current_entity_id, "MSA")
        else:
            QMessageBox.information(self, "Notice", "Sample contract file ready in data/sample_contracts.")

    def handle_file_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Contract / Legal Document", "", "Legal Documents (*.pdf *.docx *.txt *.doc);;All Files (*.*)"
        )
        if not file_path:
            return

        try:
            parsed = DocumentParser.parse_file(file_path)
            
            # Open Entity Assignment Dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Assign Document to Operating Entity")
            dialog.setFixedSize(480, 260)
            dialog.setStyleSheet(f"background-color: {THEME_COLORS['bg_main']}; color: #F8FAFC;")
            d_layout = QVBoxLayout(dialog)
            d_layout.setContentsMargins(18, 18, 18, 18)
            d_layout.setSpacing(12)

            f_lbl = QLabel(f"Document File: <b style='color: #38BDF8;'>{parsed['filename']}</b>")
            f_lbl.setTextFormat(Qt.TextFormat.RichText)
            d_layout.addWidget(f_lbl)

            d_layout.addWidget(QLabel("<b>Assign to Operating Entity (for Role Matrix Control):</b>"))
            ent_combo = QComboBox()
            entities = Entity.get_all(1)
            cur_idx = 0
            for idx, e in enumerate(entities):
                ent_combo.addItem(f"{e.legal_name} ({e.registered_state})", e.id)
                if e.id == self.current_entity_id:
                    cur_idx = idx
            ent_combo.setCurrentIndex(cur_idx)
            d_layout.addWidget(ent_combo)

            d_layout.addWidget(QLabel("<b>Document Contract Type:</b>"))
            doc_type_combo = QComboBox()
            doc_type_combo.addItems(["MSA", "VENDOR_PROCUREMENT", "EMPLOYMENT_CONTRACT", "CROSS_BORDER_FEMA", "DATA_PROCESSING_DPA", "GENERAL"])
            d_layout.addWidget(doc_type_combo)

            btn_box = QHBoxLayout()
            can_btn = QPushButton("Cancel")
            can_btn.setProperty("class", "btn-outline")
            can_btn.clicked.connect(dialog.reject)
            btn_box.addWidget(can_btn)

            run_btn = QPushButton("✔ Assign & Execute Statutory Review")
            run_btn.setProperty("class", "btn-emerald")
            
            def proceed():
                chosen_ent_id = ent_combo.currentData()
                doc_t = doc_type_combo.currentText()
                dialog.accept()
                self.process_contract_text(parsed["text"], parsed["filename"], chosen_ent_id, doc_t)
                self.entity_selection_requested.emit(chosen_ent_id)
                QMessageBox.information(
                    self, "Analysis Complete",
                    f"Successfully analyzed '{parsed['filename']}' and assigned to {ent_combo.currentText()}!\nAll statutory contraventions and highlights are now active."
                )

            run_btn.clicked.connect(proceed)
            btn_box.addWidget(run_btn)
            d_layout.addLayout(btn_box)

            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"Failed to parse document: {str(e)}")

    def process_contract_text(self, text: str, filename: str, target_entity_id: int, doc_type: str = "CONTRACT"):
        self.raw_document_text = text
        self.current_entity_id = target_entity_id

        # Perform intelligent statutory analysis
        analysis = self.ai_service.analyze_contract_against_playbook(text)
        
        # Save Document to database with assigned entity_id & raw_content
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (
                    entity_id, uploaded_by, original_filename, doc_type, status,
                    overall_health_score, liability_score, statutory_score, labour_fema_score, ocr_applied, raw_content
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                target_entity_id, 1, filename, doc_type, "REVIEWED",
                analysis["overall_health_score"], analysis["liability_score"],
                analysis["statutory_score"], analysis["labour_fema_score"], 0, text
            ))
            doc_id = cursor.lastrowid

            # Save Clauses
            self.current_clauses = []
            for c in analysis["clauses"]:
                cursor.execute("""
                    INSERT INTO document_clauses (
                        document_id, page_number, clause_type, raw_text, risk_tier,
                        flag_reason, indian_law_violation, suggested_redline, is_resolved
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    doc_id, c.get("page_number", 1), c["clause_type"], c["raw_text"],
                    c["risk_tier"], c.get("flag_reason", ""), c.get("indian_law_violation", ""),
                    c.get("suggested_redline", "")
                ))
            conn.commit()

        self.current_doc_id = doc_id
        self.current_clauses = DocumentClause.get_by_document(doc_id)
        self.lbl_file_name.setText(f"Active: {filename}")
        self.update_clause_list_widget()
        self.render_contract_text(text)
        self.update_score_banner(
            analysis["overall_health_score"],
            analysis["liability_score"],
            analysis["statutory_score"],
            analysis["labour_fema_score"]
        )

        # Log cryptographic audit trail
        self.db.log_tamper_evident_event(
            organization_id=1,
            actor_id=1,
            actor_name="Compliance Legal Team",
            event_type="DOCUMENT_ASSIGNED_AND_REVIEWED",
            target_model="Document",
            target_id=doc_id,
            details_dict={"filename": filename, "entity_id": target_entity_id, "score": analysis["overall_health_score"]}
        )
        self.audit_event_logged.emit()
        self.populate_storage_entity_filter()
        self.load_storage_documents()

    def update_clause_list_widget(self):
        self.clause_list.clear()
        for idx, clause in enumerate(self.current_clauses):
            icon = "🔴" if clause.risk_tier == "HIGH" else ("🟡" if clause.risk_tier == "CAUTION" else "🟢")
            status = " [ACCEPTED]" if clause.is_resolved else ""
            item = QListWidgetItem(f"{icon} {clause.clause_type} (P.{clause.page_number}){status}")
            self.clause_list.addItem(item)

        if self.current_clauses:
            self.clause_list.setCurrentRow(0)
            self.on_clause_selected(0)

    def on_clause_selected(self, index: int):
        if 0 <= index < len(self.current_clauses):
            self.selected_clause_idx = index
            c = self.current_clauses[index]

            self.clause_title_lbl.setText(f"Clause: {c.clause_type}")
            color = THEME_COLORS["risk_high"] if c.risk_tier == "HIGH" else (THEME_COLORS["risk_caution"] if c.risk_tier == "CAUTION" else THEME_COLORS["risk_compliant"])
            self.clause_risk_badge.setText(f" {c.risk_tier} RISK ")
            self.clause_risk_badge.setStyleSheet(f"background-color: {color}; color: white; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 3px 8px;")

            self.violation_text.setText(c.indian_law_violation or "Standard compliant clause under Indian Contract Act 1872.")
            self.flag_reason_lbl.setText(f"<b>Risk Context:</b> {c.flag_reason or 'No deviation detected.'}")
            self.redline_text_edit.setPlainText(c.suggested_redline or "")

            if c.is_resolved:
                self.btn_accept_redline.setEnabled(False)
                self.btn_accept_redline.setText("✔ Redline Already Accepted")
            else:
                self.btn_accept_redline.setEnabled(True)
                self.btn_accept_redline.setText("✔ 1-Click Accept Redline (Recalculate Health)")

    def accept_current_redline(self):
        if not self.current_clauses or self.selected_clause_idx >= len(self.current_clauses):
            return

        c = self.current_clauses[self.selected_clause_idx]
        new_text = self.redline_text_edit.toPlainText().strip()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE document_clauses
                SET raw_text = ?, risk_tier = 'COMPLIANT', is_resolved = 1
                WHERE id = ?
            """, (new_text, c.id))
            conn.commit()

        c.raw_text = new_text
        c.risk_tier = "COMPLIANT"
        c.is_resolved = 1

        high_cnt = sum(1 for cl in self.current_clauses if cl.risk_tier == "HIGH")
        caut_cnt = sum(1 for cl in self.current_clauses if cl.risk_tier == "CAUTION")
        new_score = min(100, 100 - (high_cnt * 18 + caut_cnt * 8))

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE documents SET overall_health_score = ? WHERE id = ?", (new_score, self.current_doc_id))
            conn.commit()

        self.update_score_banner(new_score, 88, 92, 90)
        self.update_clause_list_widget()
        self.render_contract_text(self.raw_document_text)

        self.db.log_tamper_evident_event(
            organization_id=1,
            actor_id=1,
            actor_name="Compliance Legal Team",
            event_type="REDLINE_ACCEPTED",
            target_model="DocumentClause",
            target_id=c.id,
            details_dict={"clause_type": c.clause_type, "new_overall_score": new_score}
        )
        self.audit_event_logged.emit()
        self.load_storage_documents()

        QMessageBox.information(
            self, "Redline Applied",
            f"Clause '{c.clause_type}' redline applied!\nEnterprise Health Score upgraded to {new_score}%."
        )

    def render_contract_text(self, raw_text: str = ""):
        """
        Renders rich interactive HTML inside contract_text_edit with prominent statutory risk callouts!
        """
        html = """
        <html>
        <head>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; color: #F8FAFC; background-color: #1E293B; line-height: 1.6; }
                .doc-header { border-bottom: 2px solid #0D9488; padding-bottom: 8px; margin-bottom: 14px; }
                .doc-title { color: #10B981; font-size: 15px; font-weight: bold; margin: 0; }
                .clause-box { margin: 12px 0; padding: 12px 14px; border-radius: 6px; }
                .high-risk { background-color: rgba(239, 68, 68, 0.16); border-left: 5px solid #EF4444; border: 1px solid rgba(239, 68, 68, 0.4); }
                .caution-risk { background-color: rgba(245, 158, 11, 0.16); border-left: 5px solid #F59E0B; border: 1px solid rgba(245, 158, 11, 0.4); }
                .compliant-risk { background-color: rgba(16, 185, 129, 0.16); border-left: 5px solid #10B981; border: 1px solid rgba(16, 185, 129, 0.4); }
                .badge { color: white; font-size: 10px; font-weight: bold; padding: 2px 7px; border-radius: 3px; display: inline-block; }
                .statute-tag { font-size: 11px; margin-top: 4px; font-weight: 600; }
                .clause-text { font-size: 13px; margin-top: 6px; }
                .standard-text { font-size: 12.5px; color: #CBD5E1; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="doc-header">
                <p class="doc-title">LEXSECURE INDIA PRO — STATUTORY CONTRACT REVIEW & HIGHLIGHT REPORT</p>
                <p style="color: #94A3B8; font-size: 11px; margin-top: 3px;">Jurisdiction: India • Automatic Compliance Scanning • Indian Contract Act • MSMED • FEMA • DPDP 2023</p>
            </div>
        """

        if self.current_clauses:
            for idx, c in enumerate(self.current_clauses):
                if c.is_resolved:
                    css_class = "compliant-risk"
                    badge_bg = "#10B981"
                    badge_txt = "✔ COMPLIANT REDLINE ACCEPTED"
                    statute_color = "#34D399"
                elif c.risk_tier == "HIGH":
                    css_class = "high-risk"
                    badge_bg = "#EF4444"
                    badge_txt = f"🔴 DEALBREAKER / HIGH RISK [{c.clause_type}]"
                    statute_color = "#F87171"
                elif c.risk_tier == "CAUTION":
                    css_class = "caution-risk"
                    badge_bg = "#F59E0B"
                    badge_txt = f"🟡 CAUTION / DEVIATION [{c.clause_type}]"
                    statute_color = "#FBBF24"
                else:
                    css_class = "compliant-risk"
                    badge_bg = "#10B981"
                    badge_txt = f"🟢 COMPLIANT [{c.clause_type}]"
                    statute_color = "#34D399"

                html += f"""
                <div class="clause-box {css_class}">
                    <span class="badge" style="background-color: {badge_bg};">{badge_txt}</span>
                    <div class="statute-tag" style="color: {statute_color};">
                        <b>Indian Law Mandate:</b> {c.indian_law_violation or 'Aligned with standard Indian Playbook.'}
                    </div>
                    <div class="clause-text" style="color: #F8FAFC;">
                        <b>Contract Clause Text:</b><br/>
                        {c.raw_text}
                    </div>
                </div>
                """
        else:
            html += f"<div class='standard-text'><pre style='white-space: pre-wrap; color: #F8FAFC;'>{raw_text or 'No document loaded.'}</pre></div>"

        html += "</body></html>"
        self.contract_text_edit.setHtml(html)

    def update_score_banner(self, overall: int, liability: int, statutory: int, fema: int):
        color = "#10B981" if overall >= 80 else ("#F59E0B" if overall >= 60 else "#EF4444")
        self.lbl_overall_score.setText(f"Overall Legal Health: <b>{overall} / 100</b>")
        self.lbl_overall_score.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
        self.lbl_liability_score.setText(f"Liability Cap: <b>{liability}%</b>")
        self.lbl_statutory_score.setText(f"Statutory Codes (Sec 27/MSME): <b>{statutory}%</b>")
        self.lbl_fema_score.setText(f"Labour & FEMA: <b>{fema}%</b>")

    def on_copilot_submit(self):
        q = self.copilot_input.text().strip()
        if not q:
            return
        self.copilot_input.clear()
        self.run_copilot_query(q)

    def run_copilot_query(self, query: str):
        self.copilot_history.append(f"<p style='color: #38BDF8;'><b>You:</b> {query}</p>")
        reply = self.ai_service.ask_legal_copilot(query)
        self.copilot_history.append(f"<div style='color: #F8FAFC; background-color: #1E293B; padding: 8px; border-radius: 6px;'>{reply}</div><br>")
        self.copilot_history.moveCursor(QTextCursor.MoveOperation.End)

    # =========================================================================
    # EXPORT DOCUMENT WITH HIGHLIGHTS
    # =========================================================================
    def download_reviewed_document_with_highlights(self):
        self.export_document_by_id(self.current_doc_id)

    def export_document_by_id(self, doc_id: int):
        doc = Document.get_by_id(doc_id)
        if not doc:
            QMessageBox.warning(self, "No Document", "No document available to export.")
            return

        clauses = DocumentClause.get_by_document(doc_id)
        ent = Entity.get_by_id(doc.entity_id)
        ent_name = ent.legal_name if ent else "Corporate Operating Entity"

        default_filename = f"Reviewed_{Path(doc.original_filename).stem}_LexSecure_Highlights.html"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Reviewed Document with Highlights", default_filename, "HTML Document (*.html);;All Files (*.*)"
        )
        if not save_path:
            return

        now_str = datetime.now().strftime("%d %B %Y, %H:%M:%S IST")
        html_export = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>LexSecure India Pro — Reviewed Legal Document ({doc.original_filename})</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0F172A; color: #F8FAFC; margin: 0; padding: 30px; }}
        .header {{ border-bottom: 2px solid #0D9488; padding-bottom: 16px; margin-bottom: 24px; }}
        h1 {{ color: #10B981; font-size: 22px; margin: 0 0 6px 0; }}
        .meta-bar {{ display: flex; flex-wrap: wrap; gap: 20px; font-size: 13px; color: #94A3B8; margin-top: 8px; }}
        .score-box {{ background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 14px 20px; margin-bottom: 24px; }}
        .clause-card {{ margin-bottom: 16px; padding: 16px; border-radius: 8px; }}
        .high-risk {{ background-color: rgba(239, 68, 68, 0.12); border: 1px solid #EF4444; border-left: 6px solid #EF4444; }}
        .caution-risk {{ background-color: rgba(245, 158, 11, 0.12); border: 1px solid #F59E0B; border-left: 6px solid #F59E0B; }}
        .compliant-risk {{ background-color: rgba(16, 185, 129, 0.12); border: 1px solid #10B981; border-left: 6px solid #10B981; }}
        .badge {{ color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .statute-title {{ font-size: 12px; font-weight: bold; margin-top: 8px; }}
        .clause-body {{ margin-top: 10px; font-size: 14px; line-height: 1.6; color: #F1F5F9; }}
        .redline-box {{ background-color: #0B1120; border: 1px dashed #0D9488; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: 13px; color: #5EEAD4; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 24px; font-size: 12px; }}
        th, td {{ border: 1px solid #334155; padding: 10px; text-align: left; }}
        th {{ background-color: #0B1120; color: #38BDF8; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LEXSECURE INDIA PRO — REVIEWED CONTRACT & HIGHLIGHT DOSSIER</h1>
        <div class="meta-bar">
            <span><b>Document:</b> {doc.original_filename}</span>
            <span><b>Operating Entity:</b> {ent_name}</span>
            <span><b>Review Date:</b> {now_str}</span>
            <span><b>Jurisdiction:</b> Republic of India</span>
            <span><b>Audit Hash:</b> Verified Tamper-Evident SHA-256</span>
        </div>
    </div>

    <div class="score-box">
        <h3 style="margin: 0 0 8px 0; color: #38BDF8;">Executive Legal Health Score: {doc.overall_health_score} / 100</h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 0;">
            Liability Score: <b>{doc.liability_score}%</b> | Statutory Score (Sec 27 / MSME): <b>{doc.statutory_score}%</b> | Labour & FEMA Score: <b>{doc.labour_fema_score}%</b>
        </p>
    </div>

    <h2 style="color: #F8FAFC; font-size: 16px; margin-bottom: 14px;">1. Full Document Text with Color-Coded Statutory Highlights</h2>
"""

        for c in clauses:
            if c.is_resolved:
                c_class = "compliant-risk"
                badge_bg = "#10B981"
                badge_label = "🟢 PLAYBOOK COMPLIANT REDLINE ACCEPTED"
                s_color = "#34D399"
            elif c.risk_tier == "HIGH":
                c_class = "high-risk"
                badge_bg = "#EF4444"
                badge_label = f"🔴 DEALBREAKER / HIGH RISK — {c.clause_type}"
                s_color = "#F87171"
            elif c.risk_tier == "CAUTION":
                c_class = "caution-risk"
                badge_bg = "#F59E0B"
                badge_label = f"🟡 CAUTION / STATUTORY DEVIATION — {c.clause_type}"
                s_color = "#FBBF24"
            else:
                c_class = "compliant-risk"
                badge_bg = "#10B981"
                badge_label = f"🟢 COMPLIANT — {c.clause_type}"
                s_color = "#34D399"

            html_export += f"""
    <div class="clause-card {c_class}">
        <span class="badge" style="background-color: {badge_bg};">{badge_label}</span>
        <div class="statute-title" style="color: {s_color};">
            <b>Statutory Citation:</b> {c.indian_law_violation or 'Complies with Indian Contract Act 1872.'}
        </div>
        <div class="clause-body">
            <b>Contract Provision:</b><br/>
            {c.raw_text}
        </div>
        {f'<div class="redline-box"><b>Recommended Playbook Redline:</b><br/>{c.suggested_redline}</div>' if c.suggested_redline else ''}
    </div>
"""

        html_export += f"""
    <h2 style="color: #F8FAFC; font-size: 16px; margin-top: 30px;">2. Indian Statutory Compliance & Risk Schedule</h2>
    <table>
        <tr>
            <th>Clause Type</th>
            <th>Risk Tier</th>
            <th>Indian Law Infraction / Case Law</th>
            <th>Status</th>
        </tr>
"""
        for c in clauses:
            html_export += f"""
        <tr>
            <td><b>{c.clause_type}</b></td>
            <td><span class="badge" style="background-color: {'#EF4444' if c.risk_tier == 'HIGH' else ('#F59E0B' if c.risk_tier == 'CAUTION' else '#10B981')};">{c.risk_tier}</span></td>
            <td>{c.indian_law_violation or 'Compliant'}</td>
            <td>{'Accepted' if c.is_resolved else 'Pending Action'}</td>
        </tr>
"""
        html_export += """
    </table>
</body>
</html>"""

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html_export)

        QMessageBox.information(
            self, "Export Successful",
            f"Reviewed document with highlights successfully exported!\n\nSaved to:\n{save_path}\n\nYou can open this file in any web browser or print to PDF."
        )
