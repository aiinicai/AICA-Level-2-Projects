import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QComboBox,
                             QTableWidget, QTableWidgetItem, QAbstractItemView)
from PyQt5.QtCore import Qt
from app.database import (authenticate_user, get_user, reset_password_with_recovery,
                          change_password, add_user, get_all_users, delete_user)

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logged_in_user = None
        self.logged_in_role = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("PuruNiti Smart Billing - User Login")
        self.resize(380, 260)
        self.setMinimumSize(360, 240)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        title_label = QLabel("PuruNiti Login")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e3a8a;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Fields
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.password_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("""
            background-color: #1e3a8a; 
            color: white; 
            font-weight: bold; 
            padding: 8px; 
            border: none; 
            border-radius: 4px;
        """)
        login_btn.clicked.connect(self.handle_login)
        btn_layout.addWidget(login_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Forgot Password link
        forgot_btn = QPushButton("Forgot Password?")
        forgot_btn.setFlat(True)
        forgot_btn.setStyleSheet("color: #0f766e; text-decoration: underline; font-size: 11px;")
        forgot_btn.clicked.connect(self.handle_forgot_password)
        layout.addWidget(forgot_btn, alignment=Qt.AlignCenter)
        
        self.setLayout(layout)
        
        self.setStyleSheet("""
            QDialog { background-color: #f8fafc; }
            QLineEdit:focus { border: 1px solid #3b82f6; }
        """)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please enter both username and password.")
            return
            
        user = authenticate_user(username, password)
        if user:
            self.logged_in_user = user["username"]
            self.logged_in_role = user["role"]
            self.accept()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid username or password.")
            
    def get_logged_in_user(self):
        return self.logged_in_user
        
    def get_logged_in_role(self):
        return self.logged_in_role

    def handle_forgot_password(self):
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.information(self, "Recovery", "Please enter your username in the field first.")
            return
            
        user = get_user(username)
        if not user or not user.get("security_question"):
            QMessageBox.critical(self, "Error", f"No recovery security question set for user '{username}'. Please contact admin.")
            return
            
        dialog = ForgotPassDialog(user, self)
        dialog.exec_()


class ForgotPassDialog(QDialog):
    def __init__(self, user_info, parent=None):
        super().__init__(parent)
        self.user_info = user_info
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Password Recovery")
        self.resize(380, 280)
        self.setMinimumSize(360, 260)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Reset Password")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f766e;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        q_label = QLabel(f"Question: {self.user_info['security_question']}")
        q_label.setWordWrap(True)
        q_label.setStyleSheet("font-weight: bold; color: #475569;")
        layout.addWidget(q_label)
        
        self.answer_input = QLineEdit()
        self.answer_input.setPlaceholderText("Your Answer")
        self.answer_input.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.answer_input)
        
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setPlaceholderText("New Password")
        self.new_pass_input.setEchoMode(QLineEdit.Password)
        self.new_pass_input.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.new_pass_input)
        
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset Password")
        reset_btn.setStyleSheet("""
            background-color: #0f766e; 
            color: white; 
            font-weight: bold; 
            padding: 8px; 
            border: none; 
            border-radius: 4px;
        """)
        reset_btn.clicked.connect(self.handle_reset)
        btn_layout.addWidget(reset_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def handle_reset(self):
        answer = self.answer_input.text().strip()
        new_pass = self.new_pass_input.text()
        
        if not answer or not new_pass:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return
            
        username = self.user_info["username"]
        success = reset_password_with_recovery(username, answer, new_pass)
        
        if success:
            QMessageBox.information(self, "Success", "Password reset successfully! You can now log in.")
            self.accept()
        else:
            QMessageBox.critical(self, "Failed", "Incorrect answer. Verification failed.")


class ChangePassDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Change Password")
        self.resize(360, 240)
        self.setMinimumSize(340, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Change Password")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e3a8a;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.old_pass = QLineEdit()
        self.old_pass.setPlaceholderText("Current Password")
        self.old_pass.setEchoMode(QLineEdit.Password)
        self.old_pass.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.old_pass)
        
        self.new_pass = QLineEdit()
        self.new_pass.setPlaceholderText("New Password")
        self.new_pass.setEchoMode(QLineEdit.Password)
        self.new_pass.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.new_pass)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            background-color: #1e3a8a; 
            color: white; 
            font-weight: bold; 
            padding: 8px; 
            border: none; 
            border-radius: 4px;
        """)
        save_btn.clicked.connect(self.handle_save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def handle_save(self):
        old_p = self.old_pass.text()
        new_p = self.new_pass.text()
        
        if not old_p or not new_p:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return
            
        user = authenticate_user(self.username, old_p)
        if not user:
            QMessageBox.critical(self, "Error", "Incorrect current password.")
            return
            
        success = change_password(self.username, new_p)
        if success:
            QMessageBox.information(self, "Success", "Password changed successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to update password.")


class UserSettingsDialog(QDialog):
    def __init__(self, active_user, parent=None):
        super().__init__(parent)
        self.active_user = active_user
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("User Accounts Settings")
        self.resize(650, 520)
        self.setMinimumSize(500, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        create_group = QVBoxLayout()
        title_a = QLabel("Create New User")
        title_a.setStyleSheet("font-weight: bold; color: #1e3a8a;")
        create_group.addWidget(title_a)
        
        f_layout = QHBoxLayout()
        self.new_username = QLineEdit()
        self.new_username.setPlaceholderText("Username")
        self.new_username.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 4px;")
        f_layout.addWidget(self.new_username)
        
        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("Password")
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 4px;")
        f_layout.addWidget(self.new_password)
        
        self.new_role = QComboBox()
        self.new_role.addItems(["staff", "admin"])
        self.new_role.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 4px;")
        f_layout.addWidget(self.new_role)
        
        create_group.addLayout(f_layout)
        
        rec_layout = QHBoxLayout()
        self.new_question = QLineEdit()
        self.new_question.setPlaceholderText("Security Question (e.g. First school name?)")
        self.new_question.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 4px;")
        rec_layout.addWidget(self.new_question)
        
        self.new_answer = QLineEdit()
        self.new_answer.setPlaceholderText("Security Answer")
        self.new_answer.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 4px;")
        rec_layout.addWidget(self.new_answer)
        
        create_group.addLayout(rec_layout)
        
        add_btn = QPushButton("Create Account")
        add_btn.setStyleSheet("""
            background-color: #1e3a8a; 
            color: white; 
            font-weight: bold; 
            padding: 6px; 
            border: none; 
            border-radius: 4px;
        """)
        add_btn.clicked.connect(self.handle_create_user)
        create_group.addWidget(add_btn)
        
        layout.addLayout(create_group)
        
        sep = QLabel()
        sep.setStyleSheet("border-top: 1px solid #cbd5e1; margin: 10px 0;")
        layout.addWidget(sep)
        
        title_b = QLabel("Existing Accounts")
        title_b.setStyleSheet("font-weight: bold; color: #1e3a8a;")
        layout.addWidget(title_b)
        
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(3)
        self.user_table.setHorizontalHeaderLabels(["Username", "Role", "Recovery Q"])
        self.user_table.horizontalHeader().setStretchLastSection(True)
        self.user_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.user_table)
        
        btn_layout = QHBoxLayout()
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("""
            background-color: #be123c; 
            color: white; 
            font-weight: bold; 
            padding: 8px; 
            border: none; 
            border-radius: 4px;
        """)
        delete_btn.clicked.connect(self.handle_delete_user)
        btn_layout.addWidget(delete_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.refresh_users()
        
    def refresh_users(self):
        users = get_all_users()
        self.user_table.setRowCount(len(users))
        for row, u in enumerate(users):
            self.user_table.setItem(row, 0, QTableWidgetItem(u["username"]))
            self.user_table.setItem(row, 1, QTableWidgetItem(u["role"]))
            self.user_table.setItem(row, 2, QTableWidgetItem(u.get("security_question") or "Not Set"))
            
    def handle_create_user(self):
        name = self.new_username.text().strip()
        pwd = self.new_password.text().strip()
        role = self.new_role.currentText()
        quest = self.new_question.text().strip()
        ans = self.new_answer.text().strip()
        
        if not name or not pwd:
            QMessageBox.warning(self, "Error", "Username and Password are required fields.")
            return
            
        if not quest or not ans:
            QMessageBox.warning(self, "Error", "Security Question and Answer are required for recovery.")
            return
            
        success = add_user(name, pwd, role, quest, ans)
        if success:
            QMessageBox.information(self, "Success", f"User '{name}' registered successfully.")
            self.new_username.clear()
            self.new_password.clear()
            self.new_question.clear()
            self.new_answer.clear()
            self.refresh_users()
        else:
            QMessageBox.critical(self, "Error", "Username already exists or database save failed.")
            
    def handle_delete_user(self):
        selected = self.user_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Please select a user to delete.")
            return
            
        username = self.user_table.item(selected, 0).text()
        if username == self.active_user:
            QMessageBox.warning(self, "Error", "You cannot delete your own active account.")
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete user '{username}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success = delete_user(username)
            if success:
                QMessageBox.information(self, "Deleted", f"User '{username}' deleted successfully.")
                self.refresh_users()
            else:
                QMessageBox.critical(self, "Failed", "Cannot delete user. Ensure there is at least one active Admin.")


from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QDateEdit

class RecordPaymentDialog(QDialog):
    def __init__(self, invoice_number, outstanding_amt, parent=None):
        super().__init__(parent)
        self.invoice_number = invoice_number
        self.outstanding_amt = outstanding_amt
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Record Invoice Payment Receipt")
        self.resize(480, 550)
        self.setMinimumSize(450, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel(f"Record Payment for {self.invoice_number}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e3a8a;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Outstanding Info
        out_lbl = QLabel(f"Remaining Outstanding: ₹ {self.outstanding_amt:,.2f}")
        out_lbl.setStyleSheet("font-weight: bold; color: #b91c1c; font-size: 12px;")
        layout.addWidget(out_lbl)
        
        # Fields
        layout.addWidget(QLabel("Payment Date:"))
        self.dt_payment = QDateEdit()
        self.dt_payment.setDate(QDate.currentDate())
        self.dt_payment.setCalendarPopup(True)
        self.dt_payment.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.dt_payment)
        
        layout.addWidget(QLabel("Amount Received (₹):"))
        self.txt_amount = QLineEdit(f"{self.outstanding_amt:.2f}")
        self.txt_amount.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.txt_amount)
        
        layout.addWidget(QLabel("Payment Mode:"))
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["Bank Transfer", "UPI / QR", "Cash", "Cheque"])
        self.cmb_mode.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.cmb_mode)
        
        layout.addWidget(QLabel("Reference / UTR / Cheque Number:"))
        self.txt_ref = QLineEdit()
        self.txt_ref.setPlaceholderText("Optional TXN / UTR #")
        self.txt_ref.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.txt_ref)
        
        layout.addWidget(QLabel("Internal Notes:"))
        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Optional notes")
        self.txt_notes.setStyleSheet("padding: 5px; border: 1px solid #cbd5e1; border-radius: 4px;")
        layout.addWidget(self.txt_notes)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Log Receipt")
        save_btn.setStyleSheet("""
            background-color: #1e3a8a; 
            color: white; 
            font-weight: bold; 
            padding: 8px; 
            border: none; 
            border-radius: 4px;
        """)
        save_btn.clicked.connect(self.handle_save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def handle_save(self):
        try:
            amt = float(self.txt_amount.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a valid numeric payment amount.")
            return
            
        if amt <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Payment amount must be greater than zero.")
            return
            
        if amt > self.outstanding_amt + 0.01:
            reply = QMessageBox.question(self, "Overpayment Warn",
                                         f"The input amount ₹ {amt:,.2f} exceeds the outstanding balance ₹ {self.outstanding_amt:,.2f}. Do you want to proceed with logging an overpayment?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
                
        date_str = self.dt_payment.date().toString("yyyy-MM-dd")
        mode = self.cmb_mode.currentText()
        ref = self.txt_ref.text().strip()
        notes = self.txt_notes.text().strip()
        
        from app.database import add_payment
        if add_payment(self.invoice_number, amt, date_str, mode, ref, notes):
            QMessageBox.information(self, "Payment Logged", f"Successfully recorded payment of ₹ {amt:,.2f} against invoice {self.invoice_number}.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to log payment transaction to SQLite database.")
