"""
LexSecure India Pro - Pillar 2: Regulatory Feed, AI Impact Assessment & Dispatch Engine
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QScrollArea, QDialog, QTextEdit,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from datetime import datetime, timedelta
from ui.styles import THEME_COLORS
from services.legal_ai_service import LegalAIService
from database.db_engine import DatabaseEngine
from models.entities import RegulatoryUpdate, ImpactAssessment, ComplianceTask

class RegulatoryView(QWidget):
    task_dispatched = pyqtSignal()
    audit_event_logged = pyqtSignal()

    def __init__(self, current_entity_id: int = 1):
        super().__init__()
        self.current_entity_id = current_entity_id
        self.ai_service = LegalAIService()
        self.db = DatabaseEngine.get_instance()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. Top Controls Bar
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            background-color: {THEME_COLORS['bg_card']};
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 10px;
            padding: 10px 16px;
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setSpacing(12)

        icon_title = QLabel("📡 INDIAN STATUTORY GAZETTE & REGULATORY TRACKER")
        icon_title.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        top_layout.addWidget(icon_title)

        top_layout.addStretch()

        # Filter by Statutory Body
        top_layout.addWidget(QLabel("Statutory Body:"))
        self.body_filter = QComboBox()
        self.body_filter.addItems(["ALL", "MCA", "RBI_FEMA", "LABOUR_MINISTRY", "DPDPB", "CERT_IN", "GSTN"])
        self.body_filter.currentTextChanged.connect(self.load_circulars)
        top_layout.addWidget(self.body_filter)

        refresh_btn = QPushButton("🔄 Ingest Latest Feeds")
        refresh_btn.setProperty("class", "btn-outline")
        refresh_btn.clicked.connect(self.load_circulars)
        top_layout.addWidget(refresh_btn)

        main_layout.addWidget(top_bar)

        # 2. Scrollable Circulars Container
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background-color: transparent;")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(14)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)

        self.scroll.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll, 1)

        self.load_circulars()

    def load_circulars(self):
        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        selected_body = self.body_filter.currentText()
        circulars = RegulatoryUpdate.get_all(selected_body)

        if not circulars:
            empty_lbl = QLabel(f"No circulars found for {selected_body}.")
            empty_lbl.setStyleSheet("color: #94A3B8; font-size: 13px; padding: 20px;")
            self.cards_layout.addWidget(empty_lbl)
            return

        for circ in circulars:
            card = self.create_circular_card(circ)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def create_circular_card(self, circ: RegulatoryUpdate) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        # Header Row
        header = QHBoxLayout()
        sev_color = THEME_COLORS["risk_high"] if circ.severity == "CRITICAL" else THEME_COLORS["risk_caution"]
        sev_badge = QLabel(f" {circ.severity} ")
        sev_badge.setStyleSheet(f"background-color: {sev_color}; color: white; font-size: 10px; font-weight: bold; border-radius: 3px; padding: 2px 6px;")
        header.addWidget(sev_badge)

        body_lbl = QLabel(f"<b>{circ.statutory_body}</b> • Circular: <span style='color: #38BDF8;'>{circ.circular_number}</span> • Issued: {circ.official_date}")
        body_lbl.setTextFormat(Qt.TextFormat.RichText)
        body_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        header.addWidget(body_lbl)

        header.addStretch()

        # Check if already has an impact assessment
        existing_assessment = ImpactAssessment.get_by_circular(circ.id)
        if existing_assessment:
            status_color = "#10B981" if existing_assessment.status == "DISPATCHED" else "#F59E0B"
            tag = QLabel(f" STATUS: {existing_assessment.status} ")
            tag.setStyleSheet(f"background-color: {status_color}; color: white; font-size: 10px; font-weight: bold; border-radius: 3px; padding: 2px 6px;")
            header.addWidget(tag)

        layout.addLayout(header)

        # Title
        title_lbl = QLabel(circ.title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        layout.addWidget(title_lbl)

        # Raw Text Preview
        text_box = QLabel(circ.raw_text)
        text_box.setWordWrap(True)
        text_box.setStyleSheet("color: #CBD5E1; font-size: 12px; background-color: #0B1120; border-radius: 6px; padding: 10px; border: 1px solid #1E293B;")
        layout.addWidget(text_box)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        run_ia_btn = QPushButton("⚡ Run AI Impact Assessment & Tasks")
        run_ia_btn.setProperty("class", "btn-primary")
        run_ia_btn.clicked.connect(lambda checked, c=circ: self.open_impact_assessment_dialog(c))
        btn_layout.addWidget(run_ia_btn)

        layout.addLayout(btn_layout)
        return card

    def open_impact_assessment_dialog(self, circ: RegulatoryUpdate):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"LexSecure AI Impact Assessment — {circ.statutory_body}")
        dialog.setMinimumSize(750, 560)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {THEME_COLORS['bg_main']};
                color: #F8FAFC;
            }}
        """)
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 20, 20, 20)
        d_layout.setSpacing(14)

        # Top Info
        d_head = QLabel(f"<b>Statutory Circular:</b> {circ.title}")
        d_head.setTextFormat(Qt.TextFormat.RichText)
        d_head.setWordWrap(True)
        d_head.setStyleSheet("color: #F8FAFC; font-size: 13px;")
        d_layout.addWidget(d_head)

        # Generate AI Assessment
        assessment_data = self.ai_service.generate_impact_assessment(circ.raw_text, circ.statutory_body)

        # Summary box
        d_layout.addWidget(QLabel("<b>Executive Summary & Regulatory Scope:</b>"))
        summary_edit = QTextEdit()
        summary_edit.setPlainText(assessment_data["executive_summary"])
        summary_edit.setFixedHeight(90)
        summary_edit.setStyleSheet("background-color: #0B1120; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 8px;")
        d_layout.addWidget(summary_edit)

        # Affected Depts & Deadline
        meta_row = QHBoxLayout()
        depts_lbl = QLabel(f"Affected Departments: <b style='color: #38BDF8;'>{assessment_data['affected_departments']}</b>")
        depts_lbl.setTextFormat(Qt.TextFormat.RichText)
        meta_row.addWidget(depts_lbl)

        meta_row.addStretch()

        deadline_lbl = QLabel(f"Statutory Deadline: <b style='color: #EF4444;'>{assessment_data['statutory_deadline']}</b>")
        deadline_lbl.setTextFormat(Qt.TextFormat.RichText)
        meta_row.addWidget(deadline_lbl)
        d_layout.addLayout(meta_row)

        # Actionable Tasks Table
        d_layout.addWidget(QLabel("<b>Mandatory Action Checklist to Dispatch:</b>"))
        task_table = QTableWidget()
        tasks = assessment_data.get("tasks", [])
        task_table.setRowCount(len(tasks))
        task_table.setColumnCount(3)
        task_table.setHorizontalHeaderLabels(["Action Item Title", "Responsible Dept", "Priority"])
        task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        task_table.setFixedHeight(160)

        for row_idx, t in enumerate(tasks):
            task_table.setItem(row_idx, 0, QTableWidgetItem(t["title"]))
            task_table.setItem(row_idx, 1, QTableWidgetItem(t["dept"]))
            task_table.setItem(row_idx, 2, QTableWidgetItem(t["priority"]))
        d_layout.addWidget(task_table)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "btn-outline")
        cancel_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(cancel_btn)

        btn_box.addStretch()

        dispatch_btn = QPushButton("✔ Approve & Dispatch Tasks to Dept Leads")
        dispatch_btn.setProperty("class", "btn-emerald")
        dispatch_btn.clicked.connect(lambda: self.dispatch_impact_assessment(circ, assessment_data, dialog))
        btn_box.addWidget(dispatch_btn)

        d_layout.addLayout(btn_box)
        dialog.exec()

    def dispatch_impact_assessment(self, circ: RegulatoryUpdate, data: Dict[str, Any], dialog: QDialog):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Save or Update Impact Assessment
            cursor.execute("""
                INSERT INTO impact_assessments (
                    regulatory_update_id, approved_by, status, executive_summary,
                    affected_departments, statutory_deadline
                ) VALUES (?, ?, 'DISPATCHED', ?, ?, ?)
            """, (circ.id, 1, data["executive_summary"], data["affected_departments"], data["statutory_deadline"]))
            ia_id = cursor.lastrowid

            # 2. Map & Insert Department Tasks
            now = datetime.now()
            # Map dept name to department_id
            cursor.execute("SELECT id, name FROM departments WHERE entity_id = ?", (self.current_entity_id,))
            dept_map = {row["name"]: row["id"] for row in cursor.fetchall()}

            for t in data.get("tasks", []):
                dept_id = dept_map.get(t["dept"], 1)
                task_deadline = (now + timedelta(days=t.get("deadline_days", 14))).strftime("%Y-%m-%d")
                cursor.execute("""
                    INSERT INTO compliance_tasks (
                        impact_assessment_id, department_id, assigned_to,
                        title, description, deadline, priority, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
                """, (ia_id, dept_id, 1, t["title"], f"Statutory task generated from {circ.statutory_body} circular: {circ.circular_number}", task_deadline, t["priority"]))

            conn.commit()

        # Log cryptographic audit trail
        self.db.log_tamper_evident_event(
            organization_id=1,
            actor_id=1,
            actor_name="Adv. Vikramaditya Sen",
            event_type="IMPACT_ASSESSMENT_DISPATCHED",
            target_model="ImpactAssessment",
            target_id=ia_id,
            details_dict={"circular_id": circ.id, "tasks_created": len(data.get("tasks", []))}
        )

        self.audit_event_logged.emit()
        self.task_dispatched.emit()
        dialog.accept()
        self.load_circulars()
        QMessageBox.information(self, "Dispatched", f"Successfully dispatched {len(data.get('tasks', []))} statutory compliance tasks to department queues!")
