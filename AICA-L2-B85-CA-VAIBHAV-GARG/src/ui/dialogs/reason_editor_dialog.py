"""Dialog to view and edit multi-line driver variance reasons with full formatting."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame
)
from PySide6.QtCore import Qt


class ReasonEditorDialog(QDialog):
    def __init__(self, ratio_name: str, current_reason: str, variance_pct: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Variance Explanation — {ratio_name}")
        self.setMinimumSize(600, 380)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        # Header banner
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-left: 4px solid #0066CC;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(12, 8, 12, 8)
        
        title = QLabel(f"<b>Ratio:</b> {ratio_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Variance:</b> <span style='color: #DC2626; font-weight: bold;'>{variance_pct}</span>")
        title.setStyleSheet("font-size: 13px; color: #0F172A;")
        h_layout.addWidget(title)
        
        sub = QLabel("Edit or customize the statutory explanation for the audit report:")
        sub.setStyleSheet("font-size: 11px; color: #64748B;")
        h_layout.addWidget(sub)
        
        layout.addWidget(header_frame)
        
        # Reason Text Edit
        self.editor = QTextEdit()
        self.editor.setPlainText(current_reason)
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.5;
                color: #0F172A;
            }
            QTextEdit:focus {
                border: 2px solid #0066CC;
            }
        """)
        layout.addWidget(self.editor)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Apply Reason")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066CC;
                color: white;
                border-radius: 6px;
                padding: 8px 22px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052A3;
            }
        """)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)

    def get_reason(self) -> str:
        return self.editor.toPlainText().strip()
