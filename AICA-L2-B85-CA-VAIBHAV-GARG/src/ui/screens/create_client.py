"""Screen 2 — Create Client with single mandatory field and inline validation (§Screen 2)."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from src.config import COLORS
from src.database.repository import Repository


class CreateClientScreen(QWidget):
    """Screen 2: Single Client Name input with inline validation."""
    client_created = Signal(int, str)  # (client_id, client_name)
    back_to_dashboard = Signal()

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        
        card = QFrame()
        card.setMinimumWidth(480)
        card.setMaximumWidth(520)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLORS['border_grey']};
                border-radius: 8px;
                padding: 30px;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        
        title_lbl = QLabel("Create New Client")
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['deep_navy']};")
        card_layout.addWidget(title_lbl)
        
        desc_lbl = QLabel(
            "Enter the name of the client to begin ratio analysis. Financial years, reporting units, "
            "and Schedule III division will be detected automatically from uploaded workbooks."
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        card_layout.addWidget(desc_lbl)
        
        field_lbl = QLabel("Client Name *")
        field_lbl.setStyleSheet("font-weight: 600;")
        card_layout.addWidget(field_lbl)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter client name")
        self.name_input.setStyleSheet("font-size: 14px; padding: 8px 12px;")
        self.name_input.textChanged.connect(self.validate_input)
        self.name_input.returnPressed.connect(self.on_submit)
        card_layout.addWidget(self.name_input)
        
        self.validation_lbl = QLabel("")
        self.validation_lbl.setWordWrap(True)
        self.validation_lbl.setStyleSheet(f"color: {COLORS['danger']}; font-size: 11.5px;")
        card_layout.addWidget(self.validation_lbl)
        
        btn_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("Back to Dashboard")
        self.back_btn.setObjectName("SecondaryButton")
        self.back_btn.clicked.connect(self.back_to_dashboard.emit)
        btn_layout.addWidget(self.back_btn)
        
        btn_layout.addStretch()
        
        self.next_btn = QPushButton("Next →")
        self.next_btn.setObjectName("PrimaryButton")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.on_submit)
        btn_layout.addWidget(self.next_btn)
        
        card_layout.addLayout(btn_layout)
        main_layout.addWidget(card)

    def reset_form(self):
        """Reset input and validation on entering screen."""
        self.name_input.clear()
        self.validation_lbl.setText("")
        self.next_btn.setEnabled(False)
        self.name_input.setFocus()

    def validate_input(self):
        name = self.name_input.text().strip()
        if not name:
            self.validation_lbl.setText("")
            self.next_btn.setEnabled(False)
            return
            
        if len(name) < 2:
            self.validation_lbl.setText("Client name must be at least 2 characters.")
            self.next_btn.setEnabled(False)
            return
            
        if len(name) > 150:
            self.validation_lbl.setText("Client name cannot exceed 150 characters.")
            self.next_btn.setEnabled(False)
            return
            
        existing = self.repo.get_client_by_name(name)
        if existing:
            self.validation_lbl.setText("A client with this name already exists (names are case-insensitive).")
            self.next_btn.setEnabled(False)
            return
            
        self.validation_lbl.setText("")
        self.next_btn.setEnabled(True)

    def on_submit(self):
        if not self.next_btn.isEnabled():
            return
        name = self.name_input.text().strip()
        client_id = self.repo.create_client(name)
        self.client_created.emit(client_id, name)
