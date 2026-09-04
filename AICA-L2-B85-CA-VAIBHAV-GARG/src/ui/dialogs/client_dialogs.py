"""Client action dialogs: Rename, Duplicate, and Delete (with typed confirmation)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from src.config import COLORS


class RenameClientDialog(QDialog):
    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename Client")
        self.setMinimumWidth(380)
        self.setModal(True)
        self.new_name = current_name
        
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        
        lbl = QLabel("Enter new client name:")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)
        
        self.input_field = QLineEdit(current_name)
        self.input_field.setPlaceholderText("Enter client name")
        self.input_field.selectAll()
        layout.addWidget(self.input_field)
        
        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color: {COLORS['danger']}; font-size: 11px;")
        layout.addWidget(self.err_lbl)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
        
        self.input_field.textChanged.connect(self.validate)
        
    def validate(self):
        txt = self.input_field.text().strip()
        if len(txt) < 2:
            self.err_lbl.setText("Client name must be at least 2 characters.")
            self.save_btn.setEnabled(False)
        elif len(txt) > 150:
            self.err_lbl.setText("Client name cannot exceed 150 characters.")
            self.save_btn.setEnabled(False)
        else:
            self.err_lbl.setText("")
            self.save_btn.setEnabled(True)
            
    def on_save(self):
        txt = self.input_field.text().strip()
        if 2 <= len(txt) <= 150:
            self.new_name = txt
            self.accept()


class DuplicateClientDialog(QDialog):
    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Duplicate Client")
        self.setMinimumWidth(380)
        self.setModal(True)
        self.duplicate_name = f"{current_name} (Copy)"
        
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        
        lbl = QLabel(f"Create a duplicate copy of '{current_name}':")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)
        
        self.input_field = QLineEdit(self.duplicate_name)
        self.input_field.setPlaceholderText("Enter client name")
        self.input_field.selectAll()
        layout.addWidget(self.input_field)
        
        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color: {COLORS['danger']}; font-size: 11px;")
        layout.addWidget(self.err_lbl)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.save_btn = QPushButton("Duplicate")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
        self.input_field.textChanged.connect(self.validate)
        
    def validate(self):
        txt = self.input_field.text().strip()
        if len(txt) < 2:
            self.err_lbl.setText("Client name must be at least 2 characters.")
            self.save_btn.setEnabled(False)
        else:
            self.err_lbl.setText("")
            self.save_btn.setEnabled(True)
            
    def on_save(self):
        txt = self.input_field.text().strip()
        if len(txt) >= 2:
            self.duplicate_name = txt
            self.accept()


class DeleteClientDialog(QDialog):
    """Delete client modal requiring typing the exact client name to confirm (§Screen 1)."""
    def __init__(self, client_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Client Deletion")
        self.setMinimumWidth(420)
        self.setModal(True)
        self.client_name = client_name
        
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        
        warning_lbl = QLabel(
            f"Are you sure you want to permanently delete <b>{client_name}</b> and all its analysis history?"
        )
        warning_lbl.setWordWrap(True)
        layout.addWidget(warning_lbl)
        
        inst_lbl = QLabel(f"To confirm, please type <b>{client_name}</b> in the box below:")
        inst_lbl.setWordWrap(True)
        layout.addWidget(inst_lbl)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Type client name to confirm")
        layout.addWidget(self.confirm_input)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.delete_btn = QPushButton("Delete Permanently")
        self.delete_btn.setObjectName("DestructiveButton")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(btn_layout)
        
        self.confirm_input.textChanged.connect(self.on_text_changed)
        
    def on_text_changed(self, text: str):
        # Exact match (or case-insensitive exact)
        self.delete_btn.setEnabled(text.strip().lower() == self.client_name.strip().lower())
