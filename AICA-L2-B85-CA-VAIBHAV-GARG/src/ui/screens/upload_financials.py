"""Screen 3 — Upload Financials with side-by-side drag & drop and auto-advancing analysis (§Screen 3)."""
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from src.config import COLORS
from src.ui.workers import AnalysisWorker


class FileDropZone(QFrame):
    """Drag-and-drop file upload zone widget (§Screen 3)."""
    file_selected = Signal(str)

    def __init__(self, title: str, subtitle: str, required: bool = True, parent=None):
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self.required = required
        self.selected_file_path: Optional[str] = None
        
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(240)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)
        
        self.icon_lbl = QLabel("📊")
        self.icon_lbl.setStyleSheet("font-size: 36px;")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_lbl)
        
        self.title_lbl = QLabel(f"<b>{self.title}</b>" + (" *" if self.required else " (Optional)"))
        self.title_lbl.setStyleSheet(f"font-size: 15px; color: {COLORS['deep_navy']};")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_lbl)
        
        self.sub_lbl = QLabel(self.subtitle)
        self.sub_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sub_lbl)
        
        self.browse_btn = QPushButton("Browse File (.xlsx / .xlsm)")
        self.browse_btn.setObjectName("SecondaryButton")
        self.browse_btn.clicked.connect(self.on_browse)
        layout.addWidget(self.browse_btn, alignment=Qt.AlignCenter)
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"font-weight: bold; color: {COLORS['success']}; font-size: 12px;")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_lbl)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            ext = Path(file_path).suffix.lower()
            if ext in (".xlsx", ".xlsm"):
                self.set_file(file_path)
            else:
                QMessageBox.warning(self, "Invalid File", "Please upload a valid Excel workbook (.xlsx or .xlsm).")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_browse()

    def on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {self.title}", "", "Excel Workbooks (*.xlsx *.xlsm)"
        )
        if file_path:
            self.set_file(file_path)

    def set_file(self, file_path: str):
        self.selected_file_path = file_path
        file_name = Path(file_path).name
        self.setObjectName("DropZoneUploaded")
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon_lbl.setText("✅")
        self.status_lbl.setText(f"Loaded: {file_name}")
        self.file_selected.emit(file_path)

    def reset_zone(self):
        self.selected_file_path = None
        self.setObjectName("DropZone")
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon_lbl.setText("📊")
        self.status_lbl.setText("")


class UploadFinancialsScreen(QWidget):
    """Screen 3: Upload CY and PY financials and run automatic analysis."""
    analysis_completed = Signal(object)  # payload dict
    back_to_dashboard = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.client_id: Optional[int] = None
        self.client_name: str = ""
        self.cy_path: Optional[str] = None
        self.py_path: Optional[str] = None
        self.worker: Optional[AnalysisWorker] = None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        self.client_header = QLabel("Upload Financial Statements")
        self.client_header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['deep_navy']};")
        header_layout.addWidget(self.client_header)
        
        header_layout.addStretch()
        
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("SecondaryButton")
        back_btn.clicked.connect(self.back_to_dashboard.emit)
        header_layout.addWidget(back_btn)
        
        main_layout.addLayout(header_layout)
        
        instructions = QLabel(
            "Upload both current year and previous year financial statement workbooks. "
            "The analysis will execute automatically once both files are uploaded."
        )
        instructions.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        main_layout.addWidget(instructions)
        
        # Drop Zones Side by Side
        zones_layout = QHBoxLayout()
        zones_layout.setSpacing(20)
        
        self.cy_zone = FileDropZone(
            title="Current Year Financials",
            subtitle="Drag & drop CY Excel file (.xlsx / .xlsm)",
            required=True
        )
        self.cy_zone.file_selected.connect(self.on_cy_selected)
        zones_layout.addWidget(self.cy_zone)
        
        self.py_zone = FileDropZone(
            title="Previous Year Financials",
            subtitle="Drag & drop PY Excel file (.xlsx / .xlsm)",
            required=False
        )
        self.py_zone.file_selected.connect(self.on_py_selected)
        zones_layout.addWidget(self.py_zone)
        
        main_layout.addLayout(zones_layout)
        
        # Progress and Status bar
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        prog_layout = QVBoxLayout(self.progress_frame)
        prog_layout.setSpacing(6)
        
        self.status_lbl = QLabel("Processing financial workbooks...")
        self.status_lbl.setStyleSheet(f"font-weight: bold; color: {COLORS['primary_blue']};")
        prog_layout.addWidget(self.status_lbl)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLORS['border_grey']};
                border-radius: 4px;
                height: 12px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent_blue']};
            }}
        """)
        prog_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(self.progress_frame)
        
        # Single Year Continue Button (If only CY uploaded)
        self.continue_single_btn = QPushButton("Continue with Current Year Only (Single Year Analysis) →")
        self.continue_single_btn.setObjectName("SecondaryButton")
        self.continue_single_btn.setVisible(False)
        self.continue_single_btn.clicked.connect(self.start_analysis)
        main_layout.addWidget(self.continue_single_btn, alignment=Qt.AlignCenter)
        
        main_layout.addStretch()

    def set_client(self, client_id: int, client_name: str):
        self.client_id = client_id
        self.client_name = client_name
        self.client_header.setText(f"Upload Financial Statements — {client_name}")
        self.cy_path = None
        self.py_path = None
        self.cy_zone.reset_zone()
        self.py_zone.reset_zone()
        self.progress_frame.setVisible(False)
        self.continue_single_btn.setVisible(False)

    def on_cy_selected(self, path: str):
        self.cy_path = path
        self.check_auto_start()

    def on_py_selected(self, path: str):
        self.py_path = path
        self.check_auto_start()

    def check_auto_start(self):
        if self.cy_path and self.py_path:
            # Both files present: execute analysis immediately (Zero-intervention!)
            self.start_analysis()
        elif self.cy_path:
            # Only CY present: show optional single-year continue button
            self.continue_single_btn.setVisible(True)

    def start_analysis(self):
        if not self.cy_path:
            return
            
        self.progress_frame.setVisible(True)
        self.continue_single_btn.setVisible(False)
        self.cy_zone.setEnabled(False)
        self.py_zone.setEnabled(False)
        
        self.worker = AnalysisWorker(
            cy_file_path=self.cy_path,
            py_file_path=self.py_path
        )
        self.worker.progress.connect(self.status_lbl.setText)
        self.worker.finished_success.connect(self.on_analysis_success)
        self.worker.finished_error.connect(self.on_analysis_error)
        self.worker.start()

    def on_analysis_success(self, payload: Dict[str, Any]):
        payload["client_id"] = self.client_id
        payload["client_name"] = self.client_name
        self.progress_frame.setVisible(False)
        self.cy_zone.setEnabled(True)
        self.py_zone.setEnabled(True)
        self.analysis_completed.emit(payload)

    def on_analysis_error(self, err_msg: str):
        self.progress_frame.setVisible(False)
        self.cy_zone.setEnabled(True)
        self.py_zone.setEnabled(True)
        QMessageBox.critical(self, "Analysis Failed", f"Failed to parse and calculate ratios:\n\n{err_msg}")
