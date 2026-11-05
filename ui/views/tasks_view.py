"""
LexSecure India Pro - Pillar 2: Department Compliance Tasks & Evidence Workspace
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFileDialog, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from ui.styles import THEME_COLORS
from database.db_engine import DatabaseEngine
from models.entities import ComplianceTask, TaskEvidence

class TasksView(QWidget):
    audit_event_logged = pyqtSignal()

    def __init__(self, current_entity_id: int = 1):
        super().__init__()
        self.current_entity_id = current_entity_id
        self.db = DatabaseEngine.get_instance()
        self.tasks_data = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Top Control Bar
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            background-color: {THEME_COLORS['bg_card']};
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 10px;
            padding: 10px 16px;
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setSpacing(12)

        icon_title = QLabel("📋 DEPARTMENT STATUTORY COMPLIANCE TASKS")
        icon_title.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        top_layout.addWidget(icon_title)

        top_layout.addStretch()

        top_layout.addWidget(QLabel("Department:"))
        self.dept_filter = QComboBox()
        self.dept_filter.addItems(["ALL", "LEGAL", "HR_LABOUR", "FINANCE_TAX", "INFOSEC_TECH", "OPERATIONS"])
        self.dept_filter.currentTextChanged.connect(self.load_tasks)
        top_layout.addWidget(self.dept_filter)

        top_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["ALL", "PENDING", "IN_PROGRESS", "COMPLETED"])
        self.status_filter.currentTextChanged.connect(self.load_tasks)
        top_layout.addWidget(self.status_filter)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setProperty("class", "btn-outline")
        refresh_btn.clicked.connect(self.load_tasks)
        top_layout.addWidget(refresh_btn)

        main_layout.addWidget(top_bar)

        # Tasks Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Task Title & Statutory Mandate", "Department", "Deadline",
            "Priority", "Status", "Compliance Evidence"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 8px;
                gridline-color: #334155;
            }}
            QTableWidget::item {{
                padding: 10px;
            }}
        """)
        main_layout.addWidget(self.table, 1)

        self.load_tasks()

    def load_tasks(self):
        dept = self.dept_filter.currentText()
        status = self.status_filter.currentText()

        all_tasks = ComplianceTask.get_all_with_details(self.current_entity_id)

        # Filter in memory
        filtered = []
        for t in all_tasks:
            if dept != "ALL" and t["dept_name"] != dept:
                continue
            if status != "ALL" and t["status"] != status:
                continue
            filtered.append(t)

        self.tasks_data = filtered
        self.table.setRowCount(len(filtered))

        for row_idx, t in enumerate(filtered):
            # ID
            id_item = QTableWidgetItem(str(t["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 0, id_item)

            # Title
            title_text = f"{t['title']}\n{t.get('description', '')}"
            title_item = QTableWidgetItem(title_text)
            self.table.setItem(row_idx, 1, title_item)

            # Dept
            dept_item = QTableWidgetItem(t["dept_name"].replace("_", " "))
            dept_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, dept_item)

            # Deadline
            dl_item = QTableWidgetItem(t["deadline"])
            dl_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, dl_item)

            # Priority
            p_color = "#EF4444" if t["priority"] == "CRITICAL" else ("#F59E0B" if t["priority"] == "HIGH" else "#10B981")
            p_item = QTableWidgetItem(t["priority"])
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            p_item.setForeground(Qt.GlobalColor.white)
            p_item.setBackground(QColor(p_color))
            self.table.setItem(row_idx, 4, p_item)

            # Status Button / Dropdown
            status_btn = QPushButton(t["status"])
            if t["status"] == "COMPLETED":
                status_btn.setStyleSheet("background-color: #10B981; color: white; border-radius: 4px; font-weight: bold; padding: 4px 8px;")
            elif t["status"] == "IN_PROGRESS":
                status_btn.setStyleSheet("background-color: #0284C7; color: white; border-radius: 4px; font-weight: bold; padding: 4px 8px;")
            else:
                status_btn.setStyleSheet("background-color: #475569; color: white; border-radius: 4px; font-weight: bold; padding: 4px 8px;")

            status_btn.clicked.connect(lambda checked, task_id=t["id"], cur_st=t["status"]: self.toggle_task_status(task_id, cur_st))
            self.table.setCellWidget(row_idx, 5, status_btn)

            # Evidence Button
            evidences = TaskEvidence.get_by_task(t["id"])
            ev_label = f"📁 Evidence ({len(evidences)})" if evidences else "➕ Attach Evidence"
            ev_btn = QPushButton(ev_label)
            ev_btn.setStyleSheet("background-color: #0B1120; color: #38BDF8; border: 1px solid #0284C7; border-radius: 4px; padding: 4px 8px;")
            ev_btn.clicked.connect(lambda checked, task_id=t["id"], title=t["title"]: self.open_evidence_dialog(task_id, title))
            self.table.setCellWidget(row_idx, 6, ev_btn)

    def toggle_task_status(self, task_id: int, current_status: str):
        next_status_map = {
            "PENDING": "IN_PROGRESS",
            "IN_PROGRESS": "COMPLETED",
            "COMPLETED": "PENDING"
        }
        next_status = next_status_map.get(current_status, "PENDING")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE compliance_tasks SET status = ? WHERE id = ?", (next_status, task_id))
            conn.commit()

        # Log cryptographic audit trail
        self.db.log_tamper_evident_event(
            organization_id=1,
            actor_id=1,
            actor_name="Compliance Officer",
            event_type="TASK_STATUS_UPDATED",
            target_model="ComplianceTask",
            target_id=task_id,
            details_dict={"old_status": current_status, "new_status": next_status}
        )
        self.audit_event_logged.emit()
        self.load_tasks()

    def open_evidence_dialog(self, task_id: int, task_title: str):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Compliance Evidence — Task #{task_id}")
        dialog.setMinimumSize(600, 420)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {THEME_COLORS['bg_main']};
                color: #F8FAFC;
            }}
        """)
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(18, 18, 18, 18)
        d_layout.setSpacing(12)

        d_layout.addWidget(QLabel(f"<b>Task:</b> {task_title}"))

        # Existing Evidences
        evidences = TaskEvidence.get_by_task(task_id)
        if evidences:
            d_layout.addWidget(QLabel("<b>Attached Audit Proofs:</b>"))
            for ev in evidences:
                box = QFrame()
                box.setStyleSheet("background-color: #0B1120; border-radius: 6px; padding: 8px; border: 1px solid #334155;")
                b_layout = QVBoxLayout(box)
                b_layout.setSpacing(4)
                file_lbl = QLabel(f"📄 <b>{ev.evidence_file or 'Proof Document'}</b> • {ev.uploaded_at}")
                file_lbl.setTextFormat(Qt.TextFormat.RichText)
                file_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
                b_layout.addWidget(file_lbl)

                notes_lbl = QLabel(ev.notes or "")
                notes_lbl.setStyleSheet("color: #CBD5E1; font-size: 12px;")
                b_layout.addWidget(notes_lbl)
                d_layout.addWidget(box)
        else:
            d_layout.addWidget(QLabel("<span style='color: #94A3B8;'>No evidence files uploaded yet.</span>"))

        d_layout.addWidget(QLabel("<b>Attach New Verification Evidence:</b>"))
        
        file_row = QHBoxLayout()
        file_path_label = QLabel("No file selected")
        file_path_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        
        selected_file = {"path": "", "name": ""}
        def pick_file():
            fp, _ = QFileDialog.getOpenFileName(dialog, "Select Evidence File", "", "All Documents (*.pdf *.png *.jpg *.docx *.xlsx)")
            if fp:
                selected_file["path"] = fp
                selected_file["name"] = Path(fp).name
                file_path_label.setText(f"Selected: {selected_file['name']}")

        browse_btn = QPushButton("Browse File...")
        browse_btn.setProperty("class", "btn-outline")
        browse_btn.clicked.connect(pick_file)
        file_row.addWidget(browse_btn)
        file_row.addWidget(file_path_label)
        file_row.addStretch()
        d_layout.addLayout(file_row)

        notes_edit = QTextEdit()
        notes_edit.setPlaceholderText("Enter compliance verification notes (e.g. Approved board resolution, signed DPA, challan reference)...")
        notes_edit.setFixedHeight(70)
        notes_edit.setStyleSheet("background-color: #0B1120; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 6px;")
        d_layout.addWidget(notes_edit)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Close")
        cancel_btn.setProperty("class", "btn-outline")
        cancel_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(cancel_btn)

        btn_box.addStretch()

        save_btn = QPushButton("✔ Save Evidence to Immutable Audit Trail")
        save_btn.setProperty("class", "btn-emerald")
        def save_evidence():
            fname = selected_file["name"] or "Compliance_Signoff_Note.pdf"
            notes = notes_edit.toPlainText().strip()
            if not notes and not selected_file["path"]:
                QMessageBox.warning(dialog, "Missing Input", "Please select an evidence file or provide compliance verification notes.")
                return

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO task_evidences (task_id, uploaded_by, evidence_file, notes)
                    VALUES (?, 1, ?, ?)
                """, (task_id, fname, notes))
                ev_id = cursor.lastrowid
                conn.commit()

            # Tamper-evident log
            self.db.log_tamper_evident_event(
                organization_id=1,
                actor_id=1,
                actor_name="Compliance Officer",
                event_type="TASK_EVIDENCE_ATTACHED",
                target_model="ComplianceTask",
                target_id=task_id,
                details_dict={"evidence_id": ev_id, "file": fname}
            )
            self.audit_event_logged.emit()
            dialog.accept()
            self.load_tasks()
            QMessageBox.information(self, "Evidence Recorded", "Compliance evidence has been successfully recorded and added to the cryptographic audit chain!")

        save_btn.clicked.connect(save_evidence)
        btn_box.addWidget(save_btn)
        d_layout.addLayout(btn_box)

        dialog.exec()
