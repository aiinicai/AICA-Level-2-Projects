"""
ui_main.py
----------
PyQt5 GUI for Lochan Billing Manager.

Layout:
  * Toolbar: New | Save | Preview | Print | Export PDF | Search | Delete | Clear
  * Invoice details group (Invoice No., Invoice Date)
  * Customer details group (Name, Address, Mobile, GSTIN, PAN, State, Place of Supply)
  * Items table (Particulars, SAC, Amount, GST %, GST Amt, Total, [Remove])
  * Totals panel (Subtotal, CGST, SGST, IGST, Round Off, Grand Total, Amount in words)

The GUI is intentionally kept in one module for a small/medium desktop tool;
all business logic (GST calc, invoice numbering, number-to-words, GSTIN/PAN
validation) lives in utils.py, and all persistence lives in database.py /
pdf_generator.py, so this file focuses on layout and event wiring only.
"""

import os
import sys
import tempfile
import subprocess
from datetime import date, datetime

from PyQt5.QtCore import Qt, QDate, QUrl
from PyQt5.QtGui import QDesktopServices, QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QDateEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QScrollArea, QMessageBox,
    QDialog, QListWidget, QAbstractItemView, QListWidgetItem, QSizePolicy,
    QToolBar, QAction, QStyle, QHeaderView, QFrame, QStatusBar, QFormLayout,
)

from app import config, database, pdf_generator, utils, auth, tally_sync

ITEM_COLS = ["Particulars", "Service Accounting Code", "Amount (Rs.)",
             "GST %", "GST Amt (Rs.)", "Total (Rs.)", ""]
COL_PARTICULARS, COL_SAC, COL_AMOUNT, COL_GST_PCT, COL_GST_AMT, COL_TOTAL, COL_REMOVE = range(7)

STATE_ITEMS = [f"{code} - {name}" for code, name in utils.GST_STATE_CODES]


STYLESHEET = f"""
QMainWindow {{ background: {config.COLOR_WHITE}; }}
QWidget {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: {config.COLOR_TEXT_DARK}; }}
QGroupBox {{
    border: 1px solid {config.COLOR_BORDER_GREY};
    border-radius: 6px;
    margin-top: 14px;
    background: {config.COLOR_WHITE};
    font-weight: 600;
    color: {config.COLOR_PRIMARY_BLUE};
    padding-top: 6px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}}
QLineEdit, QTextEdit, QDateEdit, QComboBox {{
    border: 1px solid {config.COLOR_BORDER_GREY};
    border-radius: 4px;
    padding: 4px 6px;
    background: {config.COLOR_WHITE};
    selection-background-color: {config.COLOR_PRIMARY_BLUE};
}}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QComboBox:focus {{
    border: 1px solid {config.COLOR_PRIMARY_BLUE};
}}
QTableWidget {{
    border: 1px solid {config.COLOR_BORDER_GREY};
    gridline-color: {config.COLOR_BORDER_GREY};
    background: {config.COLOR_WHITE};
    selection-background-color: {config.COLOR_LIGHT_GREY};
    selection-color: {config.COLOR_TEXT_DARK};
}}
QHeaderView::section {{
    background-color: {config.COLOR_PRIMARY_BLUE};
    color: white;
    padding: 6px;
    border: none;
    font-weight: 600;
}}
QPushButton {{
    background-color: {config.COLOR_PRIMARY_BLUE};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: #0a327a; }}
QPushButton:pressed {{ background-color: #082860; }}
QPushButton#dangerButton {{ background-color: {config.COLOR_ACCENT_RED}; }}
QPushButton#dangerButton:hover {{ background-color: #9e1f24; }}
QPushButton#secondaryButton {{ background-color: #6b7280; }}
QPushButton#secondaryButton:hover {{ background-color: #565d68; }}
QToolBar {{
    background: {config.COLOR_LIGHT_GREY};
    border-bottom: 2px solid {config.COLOR_PRIMARY_BLUE};
    spacing: 6px;
    padding: 6px;
}}
QLabel#totalsLabel {{ font-weight: 600; }}
QLabel#grandTotalValue {{
    font-weight: 700; font-size: 13pt; color: {config.COLOR_ACCENT_RED};
}}
QLabel#headerTitle {{
    font-size: 16pt; font-weight: 700; color: {config.COLOR_PRIMARY_BLUE};
}}
QLabel#headerSubtitle {{ color: {config.COLOR_ACCENT_RED}; font-style: italic; }}
QStatusBar {{ background: {config.COLOR_LIGHT_GREY}; }}
"""


def _safe_float(text, default=0.0):
    try:
        return float(str(text).strip() or 0)
    except ValueError:
        return default


def _invoice_filename(invoice_number: str) -> str:
    safe = invoice_number.replace("/", "_").replace("\\", "_")
    return f"{safe}.pdf"


# ---------------------------------------------------------------------------
# Authentication dialogs
# ---------------------------------------------------------------------------
class CreateFirstUserDialog(QDialog):
    """Mandatory first-run bootstrap: create the very first authorised
    account. Shown before the main window if no users exist yet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Up the First Authorised User")
        self.setModal(True)
        self.resize(420, 220)

        layout = QVBoxLayout(self)
        info = QLabel(
            "No authorised user accounts exist yet.\n\n"
            "Create the first account below. This person will be able to "
            "search invoice history, edit saved invoices, and add further "
            "authorised users."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)
        form.addRow("Confirm Password:", self.confirm_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        create_btn = QPushButton("Create Account")
        create_btn.clicked.connect(self._on_create)
        btn_row.addStretch(1)
        btn_row.addWidget(create_btn)
        layout.addLayout(btn_row)

    def _on_create(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()
        if password != confirm:
            QMessageBox.warning(self, "Passwords Do Not Match", "Please re-enter matching passwords.")
            return
        try:
            auth.create_user(username, password)
        except ValueError as e:
            QMessageBox.warning(self, "Could Not Create Account", str(e))
            return
        self.accept()

    def closeEvent(self, event):
        # This step is mandatory -- without at least one account, Search and
        # Edit could never be unlocked by anyone.
        if not auth.users_exist():
            event.ignore()
        else:
            event.accept()


class LoginDialog(QDialog):
    """Prompted the first time (per session) an authorised-only action is
    attempted. Also usable as a general "sign in" dialog."""

    def __init__(self, parent=None, reason=""):
        super().__init__(parent)
        self.setWindowTitle("Authorised Login Required")
        self.setModal(True)
        self.resize(360, 160)
        self.authenticated_username = None

        layout = QVBoxLayout(self)
        if reason:
            reason_label = QLabel(reason)
            reason_label.setWordWrap(True)
            layout.addWidget(reason_label)

        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.returnPressed.connect(self._on_login)
        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self._on_login)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch(1)
        btn_row.addWidget(login_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _on_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if auth.verify_user(username, password):
            self.authenticated_username = username
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")
            self.password_edit.clear()
            self.password_edit.setFocus()


class ManageUsersDialog(QDialog):
    """Lets a logged-in authorised user add, remove, or reset the password
    of other authorised accounts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Authorised Users")
        self.resize(420, 380)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Authorised users who can search history and edit saved invoices:"))

        self.user_list = QListWidget()
        layout.addWidget(self.user_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add User")
        add_btn.clicked.connect(self._on_add)
        reset_btn = QPushButton("Reset Password")
        reset_btn.clicked.connect(self._on_reset_password)
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self._on_remove)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(remove_btn)
        layout.addLayout(btn_row)

        close_row = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(self.accept)
        close_row.addStretch(1)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        self._refresh()

    def _refresh(self):
        self.user_list.clear()
        for username in auth.list_usernames():
            self.user_list.addItem(username)

    def _on_add(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Authorised User")
        form = QFormLayout(dlg)
        username_edit = QLineEdit()
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        confirm_edit = QLineEdit()
        confirm_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", username_edit)
        form.addRow("Password:", password_edit)
        form.addRow("Confirm Password:", confirm_edit)
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Add")
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)

        if dlg.exec_() == QDialog.Accepted:
            if password_edit.text() != confirm_edit.text():
                QMessageBox.warning(self, "Passwords Do Not Match", "Please re-enter matching passwords.")
                return
            try:
                auth.create_user(username_edit.text().strip(), password_edit.text())
            except ValueError as e:
                QMessageBox.warning(self, "Could Not Add User", str(e))
                return
            self._refresh()

    def _on_reset_password(self):
        item = self.user_list.currentItem()
        if not item:
            QMessageBox.information(self, "Reset Password", "Select a user first.")
            return
        username = item.text()
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Reset Password -- {username}")
        form = QFormLayout(dlg)
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        confirm_edit = QLineEdit()
        confirm_edit.setEchoMode(QLineEdit.Password)
        form.addRow("New Password:", password_edit)
        form.addRow("Confirm Password:", confirm_edit)
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Reset")
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)

        if dlg.exec_() == QDialog.Accepted:
            if password_edit.text() != confirm_edit.text():
                QMessageBox.warning(self, "Passwords Do Not Match", "Please re-enter matching passwords.")
                return
            try:
                auth.change_password(username, password_edit.text())
                QMessageBox.information(self, "Password Reset", f"Password for '{username}' has been updated.")
            except ValueError as e:
                QMessageBox.warning(self, "Could Not Reset Password", str(e))

    def _on_remove(self):
        item = self.user_list.currentItem()
        if not item:
            QMessageBox.information(self, "Remove User", "Select a user first.")
            return
        username = item.text()
        reply = QMessageBox.question(
            self, "Remove User", f"Remove authorised user '{username}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            auth.delete_user(username)
            self._refresh()
        except ValueError as e:
            QMessageBox.warning(self, "Could Not Remove User", str(e))


# ---------------------------------------------------------------------------
# Search / Open dialog
# ---------------------------------------------------------------------------
class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Invoices")
        self.resize(640, 440)
        self.selected_invoice_number = None

        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by invoice number, customer name, GSTIN or mobile...")
        self.search_box.textChanged.connect(self.refresh_results)
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.results_list)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open Selected")
        open_btn.clicked.connect(self.accept_selection)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch(1)
        btn_row.addWidget(open_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.refresh_results()

    def refresh_results(self):
        query = self.search_box.text()
        records = database.search_invoices(query)
        self.results_list.clear()
        for rec in records:
            cust = rec.get("customer", {}).get("name", "")
            grand_total = rec.get("computed", {}).get("grand_total", 0)
            label = f"{rec.get('invoice_number')}   |   {cust}   |   {rec.get('invoice_date', '')}   |   Rs. {utils.format_currency(grand_total)}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, rec.get("invoice_number"))
            self.results_list.addItem(item)
        if not records:
            self.results_list.addItem("No invoices found.")

    def accept_selection(self):
        item = self.results_list.currentItem()
        if item is None or item.data(Qt.UserRole) is None:
            return
        self.selected_invoice_number = item.data(Qt.UserRole)
        self.accept()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lochan Billing Manager")
        self.resize(1180, 860)

        self.current_invoice_number = None  # None => unsaved / new
        self.is_dirty = False
        self._loading = False  # True while fields are being set programmatically

        # Authorised-user session state. Anyone can create/save a NEW
        # invoice; only an authenticated session can Search history, edit
        # + re-save an EXISTING invoice, delete an invoice, or manage users.
        self.authenticated = False
        self.authenticated_username = None

        self._build_ui()
        self._connect_dirty_signals()
        self.on_new(confirm=False)

    def _mark_dirty(self, *_args):
        if not self._loading:
            self.is_dirty = True

    def _connect_dirty_signals(self):
        self.customer_name_edit.textChanged.connect(self._mark_dirty)
        self.customer_address_edit.textChanged.connect(self._mark_dirty)
        self.customer_mobile_edit.textChanged.connect(self._mark_dirty)
        self.customer_gstin_edit.textChanged.connect(self._mark_dirty)
        self.customer_pan_edit.textChanged.connect(self._mark_dirty)
        self.customer_state_combo.currentIndexChanged.connect(self._mark_dirty)
        self.place_of_supply_edit.textChanged.connect(self._mark_dirty)
        self.invoice_number_edit.textChanged.connect(self._mark_dirty)
        self.invoice_date_edit.dateChanged.connect(self._mark_dirty)
        self.items_table.itemChanged.connect(self._mark_dirty)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def _require_auth(self, reason: str) -> bool:
        """Ensure an authorised user is logged in for this session before
        allowing a protected action (Search, edit-save, Delete, Manage
        Users). Returns True if authorised (already, or after a successful
        login just now), False otherwise."""
        if self.authenticated:
            return True
        dlg = LoginDialog(self, reason=reason)
        if dlg.exec_() == QDialog.Accepted:
            self.authenticated = True
            self.authenticated_username = dlg.authenticated_username
            self._update_login_status()
            self.status_bar.showMessage(f"Logged in as {self.authenticated_username}.", 4000)
            return True
        return False

    def _update_login_status(self):
        if self.authenticated:
            self.login_status_btn.setText(f"Logout ({self.authenticated_username})")
        else:
            self.login_status_btn.setText("Login")

    def on_login_logout(self):
        if self.authenticated:
            reply = QMessageBox.question(
                self, "Logout",
                f"Log out '{self.authenticated_username}'? "
                "Search, editing saved invoices, and Delete will be locked again.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            self.authenticated = False
            self.authenticated_username = None
            self._update_login_status()
            self.status_bar.showMessage("Logged out.", 4000)
        else:
            self._require_auth("Sign in as an authorised user.")

    def on_manage_users(self):
        if not self._require_auth("Sign in to manage authorised users."):
            return
        dlg = ManageUsersDialog(self)
        dlg.exec_()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._build_toolbar()
        self._build_brand_banner(outer_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 16)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._build_invoice_group())
        content_layout.addWidget(self._build_customer_group())
        content_layout.addWidget(self._build_items_group())
        content_layout.addWidget(self._build_totals_group())

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.")

    def _build_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        self.addToolBar(toolbar)

        def add_action(text, handler, danger=False):
            btn = QPushButton(text)
            if danger:
                btn.setObjectName("dangerButton")
            btn.clicked.connect(handler)
            toolbar.addWidget(btn)
            return btn

        add_action("New", self.on_new)
        add_action("Save", self.on_save)
        add_action("Preview", self.on_preview)
        add_action("Print", self.on_print)
        add_action("Export PDF", self.on_export_pdf)
        add_action("Search", self.on_search)
        add_action("Delete", self.on_delete, danger=True)
        add_action("Clear", self.on_clear)
        toolbar.addSeparator()
        add_action("Manage Users", self.on_manage_users)
        self.login_status_btn = add_action("Login", self.on_login_logout)
        toolbar.addSeparator()
        add_action("Test Tally Connection", self.on_test_tally_connection)
        add_action("Preview Tally XML", self.on_preview_tally_xml)
        add_action("Sync to Tally", self.on_sync_to_tally)

    def _build_brand_banner(self, outer_layout):
        banner = QFrame()
        banner.setStyleSheet(f"background:{config.COLOR_LIGHT_GREY}; border-bottom: 2px solid {config.COLOR_PRIMARY_BLUE};")
        layout = QVBoxLayout(banner)
        layout.setContentsMargins(16, 8, 16, 8)
        title = QLabel(config.FIRM_NAME)
        title.setObjectName("headerTitle")
        subtitle = QLabel(f"{config.FIRM_TAGLINE}  •  Lochan Billing Manager")
        subtitle.setObjectName("headerSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        outer_layout.addWidget(banner)

    def _build_invoice_group(self):
        box = QGroupBox("Invoice Details")
        grid = QGridLayout(box)

        grid.addWidget(QLabel("Invoice Number:"), 0, 0)
        self.invoice_number_edit = QLineEdit()
        self.invoice_number_edit.setToolTip(
            "Auto-generated as LC/<Financial Year>/<Month>/<Sequence>. "
            "You may edit this field freely."
        )
        grid.addWidget(self.invoice_number_edit, 0, 1)

        grid.addWidget(QLabel("Invoice Date:"), 0, 2)
        self.invoice_date_edit = QDateEdit()
        self.invoice_date_edit.setCalendarPopup(True)
        self.invoice_date_edit.setDisplayFormat("dd-MM-yyyy")
        self.invoice_date_edit.setDate(QDate.currentDate())
        self.invoice_date_edit.dateChanged.connect(self._on_date_changed)
        grid.addWidget(self.invoice_date_edit, 0, 3)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return box

    def _build_customer_group(self):
        box = QGroupBox("Customer Details")
        grid = QGridLayout(box)

        grid.addWidget(QLabel("Customer Name *:"), 0, 0)
        self.customer_name_edit = QLineEdit()
        grid.addWidget(self.customer_name_edit, 0, 1, 1, 3)

        grid.addWidget(QLabel("Address:"), 1, 0)
        self.customer_address_edit = QTextEdit()
        self.customer_address_edit.setMaximumHeight(60)
        grid.addWidget(self.customer_address_edit, 1, 1, 1, 3)

        grid.addWidget(QLabel("Mobile:"), 2, 0)
        self.customer_mobile_edit = QLineEdit()
        self.customer_mobile_edit.setPlaceholderText("10-digit mobile number")
        grid.addWidget(self.customer_mobile_edit, 2, 1)

        grid.addWidget(QLabel("GSTIN:"), 2, 2)
        self.customer_gstin_edit = QLineEdit()
        self.customer_gstin_edit.setPlaceholderText("e.g. 09ABLFA5191L1ZW")
        self.customer_gstin_edit.editingFinished.connect(self._on_gstin_edited)
        grid.addWidget(self.customer_gstin_edit, 2, 3)

        grid.addWidget(QLabel("PAN (optional):"), 3, 0)
        self.customer_pan_edit = QLineEdit()
        self.customer_pan_edit.setPlaceholderText("e.g. AACFL4183D")
        grid.addWidget(self.customer_pan_edit, 3, 1)

        grid.addWidget(QLabel("State:"), 3, 2)
        self.customer_state_combo = QComboBox()
        self.customer_state_combo.addItems(STATE_ITEMS)
        self.customer_state_combo.currentIndexChanged.connect(self._recompute_totals)
        grid.addWidget(self.customer_state_combo, 3, 3)

        grid.addWidget(QLabel("Place of Supply:"), 4, 0)
        self.place_of_supply_edit = QLineEdit()
        self.place_of_supply_edit.setText("Same as above")
        grid.addWidget(self.place_of_supply_edit, 4, 1, 1, 3)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return box

    def _build_items_group(self):
        box = QGroupBox("Items")
        layout = QVBoxLayout(box)

        self.items_table = QTableWidget(0, len(ITEM_COLS))
        self.items_table.setHorizontalHeaderLabels(ITEM_COLS)
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(COL_PARTICULARS, QHeaderView.Stretch)
        for c in (COL_SAC, COL_AMOUNT, COL_GST_PCT, COL_GST_AMT, COL_TOTAL, COL_REMOVE):
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.items_table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.items_table)

        btn_row = QHBoxLayout()
        add_item_btn = QPushButton("+ Add Item")
        add_item_btn.clicked.connect(lambda: self.add_item_row())
        btn_row.addWidget(add_item_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        return box

    def _build_totals_group(self):
        box = QGroupBox("Tax Summary")
        grid = QGridLayout(box)

        def value_label():
            lbl = QLabel("0.00")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            return lbl

        labels = [
            ("Sub Total (Rs.):", "subtotal_value"),
            ("CGST (Rs.):", "cgst_value"),
            ("SGST (Rs.):", "sgst_value"),
            ("IGST (Rs.):", "igst_value"),
            ("Round Off (Rs.):", "round_off_value"),
        ]
        row = 0
        for text, attr in labels:
            lbl = QLabel(text)
            lbl.setObjectName("totalsLabel")
            grid.addWidget(lbl, row, 0)
            val = value_label()
            setattr(self, attr, val)
            grid.addWidget(val, row, 1)
            row += 1

        grand_label = QLabel("Grand Total (Rs.):")
        grand_label.setObjectName("totalsLabel")
        grid.addWidget(grand_label, row, 0)
        self.grand_total_value = QLabel("0.00")
        self.grand_total_value.setObjectName("grandTotalValue")
        self.grand_total_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.grand_total_value, row, 1)
        row += 1

        grid.addWidget(QLabel("Amount in Words:"), row, 0)
        self.amount_in_words_label = QLabel("")
        self.amount_in_words_label.setWordWrap(True)
        self.amount_in_words_label.setStyleSheet("font-style: italic;")
        grid.addWidget(self.amount_in_words_label, row, 1, 1, 3)

        grid.setColumnStretch(1, 1)
        return box

    # ------------------------------------------------------------------
    # Items table helpers
    # ------------------------------------------------------------------
    def add_item_row(self, item=None):
        item = item or {}
        row = self.items_table.rowCount()
        self.items_table.blockSignals(True)
        self.items_table.insertRow(row)

        self.items_table.setItem(row, COL_PARTICULARS, QTableWidgetItem(item.get("particulars", "")))
        self.items_table.setItem(row, COL_SAC, QTableWidgetItem(item.get("sac", "")))
        self.items_table.setItem(row, COL_AMOUNT, QTableWidgetItem(str(item.get("amount", "")) if item.get("amount") is not None else ""))
        self.items_table.setItem(row, COL_GST_PCT, QTableWidgetItem(str(item.get("gst_percent", 18))))

        gst_amt_item = QTableWidgetItem("0.00")
        gst_amt_item.setFlags(gst_amt_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, COL_GST_AMT, gst_amt_item)

        total_item = QTableWidgetItem("0.00")
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, COL_TOTAL, total_item)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(lambda _, r=row: self._remove_row_by_widget(remove_btn))
        self.items_table.setCellWidget(row, COL_REMOVE, remove_btn)

        self.items_table.blockSignals(False)
        self._recompute_row(row)
        self._recompute_totals()
        self._mark_dirty()

    def _remove_row_by_widget(self, widget):
        for r in range(self.items_table.rowCount()):
            if self.items_table.cellWidget(r, COL_REMOVE) is widget:
                self.items_table.removeRow(r)
                break
        self._recompute_totals()
        self._mark_dirty()

    def _on_item_changed(self, table_item):
        if table_item.column() in (COL_PARTICULARS, COL_SAC, COL_AMOUNT, COL_GST_PCT):
            self._recompute_row(table_item.row())
            self._recompute_totals()

    def _recompute_row(self, row):
        if row < 0 or row >= self.items_table.rowCount():
            return
        amount_item = self.items_table.item(row, COL_AMOUNT)
        gst_item = self.items_table.item(row, COL_GST_PCT)
        amount = _safe_float(amount_item.text() if amount_item else 0)
        gst_pct = _safe_float(gst_item.text() if gst_item else 0)
        gst_amt = round(amount * gst_pct / 100, 2)
        total = round(amount + gst_amt, 2)

        self.items_table.blockSignals(True)
        self.items_table.item(row, COL_GST_AMT).setText(utils.format_currency(gst_amt))
        self.items_table.item(row, COL_TOTAL).setText(utils.format_currency(total))
        self.items_table.blockSignals(False)

    def _collect_items(self):
        items = []
        for row in range(self.items_table.rowCount()):
            particulars_item = self.items_table.item(row, COL_PARTICULARS)
            particulars = particulars_item.text().strip() if particulars_item else ""
            sac_item = self.items_table.item(row, COL_SAC)
            sac = sac_item.text().strip() if sac_item else ""
            amount_item = self.items_table.item(row, COL_AMOUNT)
            amount = _safe_float(amount_item.text() if amount_item else 0)
            gst_item = self.items_table.item(row, COL_GST_PCT)
            gst_pct = _safe_float(gst_item.text() if gst_item else 0)
            if not particulars and amount == 0:
                continue  # skip fully blank rows
            items.append({
                "particulars": particulars,
                "sac": sac,
                "amount": amount,
                "gst_percent": gst_pct,
            })
        return items

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------
    def _selected_state_code(self):
        text = self.customer_state_combo.currentText()
        return text.split(" - ")[0] if " - " in text else config.FIRM_STATE_CODE

    def _recompute_totals(self):
        items = self._collect_items()
        computed = utils.compute_invoice_totals(items, self._selected_state_code())
        self.subtotal_value.setText(utils.format_currency(computed["subtotal"]))
        self.cgst_value.setText(utils.format_currency(computed["cgst"]))
        self.sgst_value.setText(utils.format_currency(computed["sgst"]))
        self.igst_value.setText(utils.format_currency(computed["igst"]))
        self.round_off_value.setText(utils.format_currency(computed["round_off"]))
        self.grand_total_value.setText(utils.format_currency(computed["grand_total"]))
        self.amount_in_words_label.setText(utils.amount_in_words_rupees(computed["grand_total"]))
        return computed

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_date_changed(self, _qdate):
        # Only auto-refresh the invoice number for brand-new (unsaved) invoices
        if self.current_invoice_number is None:
            self._auto_fill_invoice_number()

    def _on_gstin_edited(self):
        gstin = self.customer_gstin_edit.text().strip().upper()
        self.customer_gstin_edit.setText(gstin)
        if not gstin:
            return
        if not utils.is_valid_gstin(gstin):
            self.status_bar.showMessage(
                "Warning: GSTIN format looks invalid. Please double-check it.", 6000
            )
        code = utils.state_code_from_gstin(gstin)
        if code:
            for i, item_text in enumerate(STATE_ITEMS):
                if item_text.startswith(code + " -"):
                    self.customer_state_combo.setCurrentIndex(i)
                    break

    def _auto_fill_invoice_number(self):
        qdate = self.invoice_date_edit.date()
        py_date = date(qdate.year(), qdate.month(), qdate.day())
        existing = database.get_all_invoice_numbers()
        new_number = utils.generate_invoice_number(py_date, existing)
        self.invoice_number_edit.setText(new_number)

    def on_new(self, confirm=True):
        if confirm and self.is_dirty:
            reply = QMessageBox.question(
                self, "Start New Invoice",
                "Discard unsaved changes and start a new invoice?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self._loading = True
        try:
            self.current_invoice_number = None
            self.invoice_date_edit.setDate(QDate.currentDate())
            self._auto_fill_invoice_number()

            self.customer_name_edit.clear()
            self.customer_address_edit.clear()
            self.customer_mobile_edit.clear()
            self.customer_gstin_edit.clear()
            self.customer_pan_edit.clear()
            default_idx = next((i for i, t in enumerate(STATE_ITEMS) if t.startswith(config.FIRM_STATE_CODE + " -")), 0)
            self.customer_state_combo.setCurrentIndex(default_idx)
            self.place_of_supply_edit.setText("Same as above")

            self.items_table.setRowCount(0)
            self.add_item_row({"gst_percent": 18})

            self._recompute_totals()
        finally:
            self._loading = False

        self.is_dirty = False
        self.status_bar.showMessage("New invoice ready.", 4000)

    def on_clear(self):
        self.on_new(confirm=True)

    def _validate(self, items, computed):
        errors = []
        if not self.customer_name_edit.text().strip():
            errors.append("Customer Name is required.")
        if not self.invoice_number_edit.text().strip():
            errors.append("Invoice Number is required.")
        if not items:
            errors.append("At least one item with Particulars and Amount is required.")
        for i, item in enumerate(items, start=1):
            if not item["particulars"]:
                errors.append(f"Item {i}: Particulars is required.")
            if item["amount"] <= 0:
                errors.append(f"Item {i}: Amount must be greater than zero.")

        mobile = self.customer_mobile_edit.text().strip()
        if mobile and not utils.is_valid_mobile(mobile):
            errors.append("Mobile number format looks invalid (expected 10-digit Indian mobile number(s)).")
        gstin = self.customer_gstin_edit.text().strip()
        if gstin and not utils.is_valid_gstin(gstin):
            errors.append("GSTIN format looks invalid.")
        pan = self.customer_pan_edit.text().strip()
        if pan and not utils.is_valid_pan(pan):
            errors.append("PAN format looks invalid.")

        return errors

    def _build_invoice_dict(self):
        qdate = self.invoice_date_edit.date()
        py_date = date(qdate.year(), qdate.month(), qdate.day())
        items = self._collect_items()
        state_text = self.customer_state_combo.currentText()
        state_code, state_name = state_text.split(" - ", 1) if " - " in state_text else (config.FIRM_STATE_CODE, config.FIRM_STATE_NAME)
        computed = utils.compute_invoice_totals(items, state_code)

        customer = {
            "name": self.customer_name_edit.text().strip(),
            "address": self.customer_address_edit.toPlainText().strip(),
            "mobile": self.customer_mobile_edit.text().strip(),
            "gstin": self.customer_gstin_edit.text().strip().upper(),
            "pan": self.customer_pan_edit.text().strip().upper(),
            "state_code": state_code,
            "state_name": state_name,
            "place_of_supply": self.place_of_supply_edit.text().strip() or "Same as above",
        }

        invoice = {
            "invoice_number": self.invoice_number_edit.text().strip(),
            "invoice_date": py_date.isoformat(),
            "invoice_date_display": utils.format_date_display(py_date),
            "customer": customer,
            "items": items,
            "computed": computed,
        }
        return invoice, items, computed

    def on_save(self):
        invoice, items, computed = self._build_invoice_dict()
        errors = self._validate(items, computed)
        if errors:
            QMessageBox.warning(self, "Please fix the following", "\n".join(f"• {e}" for e in errors))
            return

        number = invoice["invoice_number"]

        # Editing/overwriting an already-saved invoice requires an
        # authorised login; creating a brand-new invoice does not.
        is_overwrite = self.current_invoice_number is not None or database.invoice_number_exists(number)
        if is_overwrite and not self._require_auth(
            "This invoice number already exists in the database.\n"
            "Sign in as an authorised user to save changes to it."
        ):
            self.status_bar.showMessage("Save cancelled -- authorised login required to edit a saved invoice.", 5000)
            return

        # Warn if creating a NEW invoice under a number that already exists
        if self.current_invoice_number is None and database.invoice_number_exists(number):
            reply = QMessageBox.question(
                self, "Invoice Number Exists",
                f"Invoice number '{number}' already exists in the database.\n"
                "Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        elif self.current_invoice_number is not None and self.current_invoice_number != number and database.invoice_number_exists(number):
            reply = QMessageBox.question(
                self, "Invoice Number Exists",
                f"Invoice number '{number}' already exists in the database.\n"
                "Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # If the invoice number was changed while editing an existing record,
        # remove the old record so we don't leave a stale duplicate behind.
        if self.current_invoice_number and self.current_invoice_number != number:
            database.delete_invoice(self.current_invoice_number)

        database.save_invoice(invoice)
        self.current_invoice_number = number
        self.is_dirty = False
        self.status_bar.showMessage(f"Invoice {number} saved successfully.", 5000)

        self._sync_to_tally_if_enabled(invoice, is_edit=is_overwrite)

    def _sync_to_tally_if_enabled(self, invoice: dict, is_edit: bool):
        if not config.TALLY_SYNC_ENABLED:
            return
        result = tally_sync.sync_invoice(invoice, is_edit=is_edit)
        # Record the sync outcome against the saved invoice so it's visible
        # later (e.g. via Search) whether it made it into Tally.
        invoice["tally_sync"] = {
            "attempted_at": datetime.now().isoformat(timespec="seconds"),
            "ok": result["ok"],
            "message": result["message"],
        }
        database.save_invoice(invoice)

        if result["ok"]:
            self.status_bar.showMessage(f"Also synced to Tally: {result['message']}", 6000)
        else:
            QMessageBox.warning(
                self, "Tally Sync Failed",
                f"The invoice was saved locally, but syncing to Tally failed:\n\n{result['message']}\n\n"
                "You can retry with 'Sync to Tally' on the toolbar once the issue is resolved."
            )

    def on_delete(self):
        if not self.current_invoice_number:
            QMessageBox.information(self, "Delete Invoice", "No saved invoice is currently open.")
            return
        if not self._require_auth("Sign in as an authorised user to delete a saved invoice."):
            return
        reply = QMessageBox.question(
            self, "Delete Invoice",
            f"Are you sure you want to permanently delete invoice '{self.current_invoice_number}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        database.delete_invoice(self.current_invoice_number)
        self.status_bar.showMessage(f"Invoice {self.current_invoice_number} deleted.", 5000)
        self.on_new(confirm=False)

    def on_search(self):
        if not self._require_auth("Sign in as an authorised user to search invoice history."):
            return
        dlg = SearchDialog(self)
        if dlg.exec_() == QDialog.Accepted and dlg.selected_invoice_number:
            record = database.get_invoice(dlg.selected_invoice_number)
            if record:
                self._load_invoice(record)

    def _load_invoice(self, record):
        self._loading = True
        try:
            self.current_invoice_number = record.get("invoice_number")
            self.invoice_number_edit.setText(record.get("invoice_number", ""))
            try:
                y, m, d = [int(x) for x in record.get("invoice_date", "").split("-")]
                self.invoice_date_edit.setDate(QDate(y, m, d))
            except (ValueError, TypeError):
                self.invoice_date_edit.setDate(QDate.currentDate())

            customer = record.get("customer", {})
            self.customer_name_edit.setText(customer.get("name", ""))
            self.customer_address_edit.setPlainText(customer.get("address", ""))
            self.customer_mobile_edit.setText(customer.get("mobile", ""))
            self.customer_gstin_edit.setText(customer.get("gstin", ""))
            self.customer_pan_edit.setText(customer.get("pan", ""))
            state_code = customer.get("state_code", config.FIRM_STATE_CODE)
            idx = next((i for i, t in enumerate(STATE_ITEMS) if t.startswith(state_code + " -")), 0)
            self.customer_state_combo.setCurrentIndex(idx)
            self.place_of_supply_edit.setText(customer.get("place_of_supply", "Same as above"))

            self.items_table.setRowCount(0)
            for item in record.get("items", []):
                self.add_item_row(item)
            if self.items_table.rowCount() == 0:
                self.add_item_row({"gst_percent": 18})

            self._recompute_totals()
        finally:
            self._loading = False

        self.is_dirty = False
        self.status_bar.showMessage(f"Loaded invoice {self.current_invoice_number}.", 4000)

    def _generate_pdf_to(self, path):
        invoice, items, computed = self._build_invoice_dict()
        errors = self._validate(items, computed)
        if errors:
            QMessageBox.warning(self, "Please fix the following", "\n".join(f"• {e}" for e in errors))
            return None
        pdf_generator.generate_invoice_pdf(invoice, path)
        return path

    def on_preview(self):
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"lochan_preview_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
        result = self._generate_pdf_to(tmp_path)
        if result:
            QDesktopServices.openUrl(QUrl.fromLocalFile(result))
            self.status_bar.showMessage("Preview opened in your default PDF viewer.", 4000)

    def on_export_pdf(self):
        database.ensure_folders()
        invoice, items, computed = self._build_invoice_dict()
        errors = self._validate(items, computed)
        if errors:
            QMessageBox.warning(self, "Please fix the following", "\n".join(f"• {e}" for e in errors))
            return
        filename = _invoice_filename(invoice["invoice_number"])
        out_path = os.path.join(config.INVOICES_PDF_DIR, filename)
        pdf_generator.generate_invoice_pdf(invoice, out_path)
        QMessageBox.information(self, "Exported", f"Invoice PDF exported to:\n{out_path}")
        self.status_bar.showMessage(f"Exported PDF: {out_path}", 5000)

    def on_print(self):
        database.ensure_folders()
        invoice, items, computed = self._build_invoice_dict()
        errors = self._validate(items, computed)
        if errors:
            QMessageBox.warning(self, "Please fix the following", "\n".join(f"• {e}" for e in errors))
            return
        filename = _invoice_filename(invoice["invoice_number"])
        out_path = os.path.join(config.INVOICES_PDF_DIR, filename)
        pdf_generator.generate_invoice_pdf(invoice, out_path)

        try:
            if sys.platform.startswith("win"):
                os.startfile(out_path, "print")  # noqa: S606 (Windows-only API)
            elif sys.platform == "darwin":
                subprocess.run(["lp", out_path], check=True)
            else:
                subprocess.run(["lp", out_path], check=True)
            self.status_bar.showMessage("Sent to printer.", 4000)
        except Exception:
            QDesktopServices.openUrl(QUrl.fromLocalFile(out_path))
            QMessageBox.information(
                self, "Print",
                "Could not send directly to a printer. The PDF has been opened "
                "instead -- please print it from there (Ctrl+P)."
            )

    # ------------------------------------------------------------------
    # Tally Prime sync
    # ------------------------------------------------------------------
    def on_test_tally_connection(self):
        if not config.TALLY_SYNC_ENABLED:
            QMessageBox.information(
                self, "Tally Sync Disabled",
                "Tally sync is currently disabled (TALLY_SYNC_ENABLED = False in app/config.py).\n\n"
                "Enable it there once Tally's HTTP gateway is set up and the ledger names in "
                "config.py have been verified against your Tally company -- see README section 8."
            )
            return
        ok, message = tally_sync.test_connection()
        if ok:
            QMessageBox.information(self, "Tally Connection", message)
        else:
            QMessageBox.warning(self, "Tally Connection Failed", message)

    def on_preview_tally_xml(self):
        invoice, items, computed = self._build_invoice_dict()
        errors = self._validate(items, computed)
        if errors:
            QMessageBox.warning(self, "Please fix the following", "\n".join(f"• {e}" for e in errors))
            return
        is_edit = self.current_invoice_number is not None
        xml_str = tally_sync.build_import_xml(invoice, action="Alter" if is_edit else "Create")

        dlg = QDialog(self)
        dlg.setWindowTitle("Tally XML Preview (not sent)")
        dlg.resize(700, 560)
        layout = QVBoxLayout(dlg)
        note = QLabel(
            "This is exactly what would be sent to Tally for this invoice. "
            "Nothing has been sent -- use this to review with your Tally setup "
            "before relying on auto-sync."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFontFamily("Courier")
        text.setPlainText(xml_str)
        layout.addWidget(text)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec_()

    def on_sync_to_tally(self):
        if not self.current_invoice_number:
            QMessageBox.information(
                self, "Sync to Tally",
                "Save the invoice first, then use this to (re)send it to Tally."
            )
            return
        if not config.TALLY_SYNC_ENABLED:
            QMessageBox.information(
                self, "Tally Sync Disabled",
                "Tally sync is currently disabled (TALLY_SYNC_ENABLED = False in app/config.py)."
            )
            return
        record = database.get_invoice(self.current_invoice_number)
        if not record:
            QMessageBox.warning(self, "Sync to Tally", "Could not find the saved invoice record to sync.")
            return
        self.status_bar.showMessage("Syncing to Tally...", 2000)
        self._sync_to_tally_if_enabled(record, is_edit=True)


def run_app():
    database.ensure_folders()
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    # First-run bootstrap: at least one authorised user account must exist
    # before Search / Edit / Delete can ever be unlocked by anyone.
    if not auth.users_exist():
        bootstrap = CreateFirstUserDialog()
        bootstrap.exec_()  # blocks; closeEvent prevents closing without a user

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
