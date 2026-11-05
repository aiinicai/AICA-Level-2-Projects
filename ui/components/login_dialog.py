"""
LexSecure India Pro - User Authentication & Session Login Dialog
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt
from ui.styles import THEME_COLORS
from models.entities import User
from database.db_engine import DatabaseEngine

class LoginDialog(QDialog):
    def __init__(self, parent=None, current_user_id: int = 1):
        super().__init__(parent)
        self.setWindowTitle("LexSecure India Pro — Secure User Authentication")
        self.setFixedSize(480, 420)
        self.setModal(True)
        self.authenticated_user = None
        self.db = DatabaseEngine.get_instance()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {THEME_COLORS['bg_main']};
                color: #F8FAFC;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
        """)
        self.init_ui(current_user_id)

    def init_ui(self, current_user_id: int):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Header Banner
        header = QFrame()
        header.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B1120, stop:1 #1E293B);
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 12px;
        """)
        h_layout = QVBoxLayout(header)
        h_layout.setSpacing(3)

        title = QLabel("⚖️ LEXSECURE INDIA PRO")
        title.setStyleSheet("color: #10B981; font-size: 16px; font-weight: 900; letter-spacing: 0.5px;")
        h_layout.addWidget(title)

        subtitle = QLabel("Statutory Access Gateway & Immutable Sign-Off Session")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 11px;")
        h_layout.addWidget(subtitle)
        layout.addWidget(header)

        # User Select dropdown
        layout.addWidget(QLabel("Select Active Identity / Role:"))
        self.user_combo = QComboBox()
        self.user_combo.setFixedHeight(38)
        self.user_combo.setStyleSheet("""
            background-color: #0B1120;
            color: #F8FAFC;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 13px;
        """)

        self.users = User.get_all(1)
        cur_idx = 0
        for idx, u in enumerate(self.users):
            role_fmt = u.role.replace("_", " ")
            self.user_combo.addItem(f"{u.full_name}  [{role_fmt}]", u.id)
            if u.id == current_user_id:
                cur_idx = idx

        self.user_combo.setCurrentIndex(cur_idx)
        self.user_combo.currentIndexChanged.connect(self.on_user_selected)
        layout.addWidget(self.user_combo)

        # Email display / input
        layout.addWidget(QLabel("Corporate Email:"))
        self.email_input = QLineEdit()
        self.email_input.setFixedHeight(38)
        self.email_input.setPlaceholderText("name@company.com")
        self.email_input.setStyleSheet("""
            background-color: #0B1120;
            color: #38BDF8;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 13px;
        """)
        layout.addWidget(self.email_input)

        # Password / PIN
        layout.addWidget(QLabel("Access PIN / Security Password:"))
        self.pwd_input = QLineEdit()
        self.pwd_input.setFixedHeight(38)
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("Enter PIN or Password (Default: 1234)")
        self.pwd_input.setText("1234")  # Pre-fill default PIN for seamless testing
        self.pwd_input.setStyleSheet("""
            background-color: #0B1120;
            color: #F8FAFC;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 13px;
        """)
        self.pwd_input.returnPressed.connect(self.authenticate_user)
        layout.addWidget(self.pwd_input)

        hint = QLabel("💡 Quick Access: Default PIN is <b>1234</b> for all seeded enterprise profiles.")
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setStyleSheet("color: #0D9488; font-size: 11px;")
        layout.addWidget(hint)

        # Buttons
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "btn-outline")
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        self.login_btn = QPushButton("🔒 Sign In & Authenticate")
        self.login_btn.setProperty("class", "btn-emerald")
        self.login_btn.setFixedHeight(36)
        self.login_btn.clicked.connect(self.authenticate_user)
        btn_box.addWidget(self.login_btn)

        layout.addLayout(btn_box)

        # Trigger initial user selection
        self.on_user_selected(cur_idx)

    def on_user_selected(self, index: int):
        if 0 <= index < len(self.users):
            user = self.users[index]
            self.email_input.setText(user.email)

    def authenticate_user(self):
        email = self.email_input.text().strip()
        pwd = self.pwd_input.text().strip()

        if not email:
            QMessageBox.warning(self, "Required", "Please provide a valid user corporate email.")
            return

        user = User.authenticate(email, pwd)
        if user:
            self.authenticated_user = user
            # Log session into tamper-evident audit trail
            self.db.log_tamper_evident_event(
                organization_id=1,
                actor_id=user.id,
                actor_name=user.full_name,
                event_type="USER_SESSION_AUTHENTICATED",
                target_model="User",
                target_id=user.id,
                details_dict={"email": user.email, "role": user.role}
            )
            self.accept()
        else:
            QMessageBox.critical(
                self, "Authentication Failed",
                "Invalid credentials. Please enter the correct PIN/password or use default PIN '1234'."
            )
