from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QComboBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QHeaderView,
    QTextEdit,
    QLabel,
    QMessageBox,
    QSplitter,
    QWidget,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt

from reconai.models.client import ClientProfile, BankAccountProfile, ClientBookProfile
from reconai.db.database import DatabaseManager


class ClientMasterDialog(QDialog):
    """Client Master Data Management Dialog for saving & loading client profiles."""

    def __init__(self, db_manager: DatabaseManager, current_client_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_client: ClientProfile = None
        self.setWindowTitle("ReconAI — Client Master Management")
        self.resize(960, 720)
        self.setMinimumSize(880, 600)
        self._init_ui()
        self._load_clients_list(select_id=current_client_id)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Splitter between list of clients and client editor
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel: Client List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        left_layout.addWidget(QLabel("<b>Saved Client Master Records</b>"))
        self.client_list_widget = QListWidget()
        self.client_list_widget.currentRowChanged.connect(self._on_client_selected)
        left_layout.addWidget(self.client_list_widget)

        btn_row = QHBoxLayout()
        self.add_client_btn = QPushButton("+ New Client")
        self.add_client_btn.clicked.connect(self._new_client)
        self.del_client_btn = QPushButton("Delete")
        self.del_client_btn.clicked.connect(self._delete_client)
        btn_row.addWidget(self.add_client_btn)
        btn_row.addWidget(self.del_client_btn)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left_widget)

        # Right Panel: Client Details Editor wrapped in a smooth QScrollArea
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 0, 8, 0)
        right_layout.setSpacing(12)

        # 1. Basic Info
        info_group = QGroupBox("Client Legal && Tax Master Information")
        info_form = QFormLayout(info_group)
        info_form.setSpacing(8)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. SUN HEALTH CARE HOSPITAL")
        info_form.addRow("Client / Entity Name *:", self.name_edit)

        self.entity_combo = QComboBox()
        self.entity_combo.addItems(["PROPRIETORSHIP", "PARTNERSHIP", "PVT_LTD", "LIMITED_COMPANY", "LLP", "TRUST / NGO", "INDIVIDUAL"])
        info_form.addRow("Entity Constitution:", self.entity_combo)

        pan_gstin_row = QHBoxLayout()
        self.pan_edit = QLineEdit()
        self.pan_edit.setPlaceholderText("10-character PAN (e.g. ABCDE1234F)")
        self.gstin_edit = QLineEdit()
        self.gstin_edit.setPlaceholderText("15-digit GSTIN (e.g. 21ABCDE1234F1Z5)")
        pan_gstin_row.addWidget(QLabel("PAN:"))
        pan_gstin_row.addWidget(self.pan_edit)
        pan_gstin_row.addWidget(QLabel("GSTIN:"))
        pan_gstin_row.addWidget(self.gstin_edit)
        info_form.addRow("Statutory Identifiers:", pan_gstin_row)

        contact_row = QHBoxLayout()
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("Contact Phone")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Finance / Accounts Email")
        contact_row.addWidget(QLabel("Phone:"))
        contact_row.addWidget(self.phone_edit)
        contact_row.addWidget(QLabel("Email:"))
        contact_row.addWidget(self.email_edit)
        info_form.addRow("Contact Details:", contact_row)

        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("Registered office / hospital / company address")
        info_form.addRow("Registered Address:", self.address_edit)

        right_layout.addWidget(info_group)

        # 2. Bank Accounts & Accounting Books Tabs
        self.accounts_books_tabs = QTabWidget()
        self.accounts_books_tabs.setMinimumHeight(220)

        # Tab 1: Bank Accounts
        bank_tab = QWidget()
        bank_layout = QVBoxLayout(bank_tab)
        bank_layout.setContentsMargins(8, 8, 8, 8)
        bank_layout.setSpacing(8)

        self.bank_table = QTableWidget(0, 4)
        self.bank_table.setHorizontalHeaderLabels(["Bank Name", "Account Number", "IFSC Code", "Account Type"])
        self.bank_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bank_table.verticalHeader().setVisible(False)
        self.bank_table.verticalHeader().setDefaultSectionSize(34)
        self.bank_table.setAlternatingRowColors(True)
        self.bank_table.setMinimumHeight(140)
        bank_layout.addWidget(self.bank_table)

        bank_btn_row = QHBoxLayout()
        self.add_bank_btn = QPushButton("+ Add Bank Account")
        self.add_bank_btn.clicked.connect(self._add_bank_row)
        self.del_bank_btn = QPushButton("- Remove Selected Account")
        self.del_bank_btn.clicked.connect(self._del_bank_row)
        bank_btn_row.addWidget(self.add_bank_btn)
        bank_btn_row.addWidget(self.del_bank_btn)
        bank_btn_row.addStretch()
        bank_layout.addLayout(bank_btn_row)

        self.accounts_books_tabs.addTab(bank_tab, "🏦 Associated Bank Accounts (0)")

        # Tab 2: Client Books / Ledgers
        book_tab = QWidget()
        book_layout = QVBoxLayout(book_tab)
        book_layout.setContentsMargins(8, 8, 8, 8)
        book_layout.setSpacing(8)

        self.book_table = QTableWidget(0, 5)
        self.book_table.setHorizontalHeaderLabels(["Book / Ledger Name *", "Software", "Account Head / Group", "Linked Bank Account", "Opening Bal (₹)"])
        self.book_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.book_table.verticalHeader().setVisible(False)
        self.book_table.verticalHeader().setDefaultSectionSize(34)
        self.book_table.setAlternatingRowColors(True)
        self.book_table.setMinimumHeight(140)
        book_layout.addWidget(self.book_table)

        book_btn_row = QHBoxLayout()
        self.add_book_btn = QPushButton("+ Add Client Book / Ledger")
        self.add_book_btn.clicked.connect(self._add_book_row)
        self.del_book_btn = QPushButton("- Remove Selected Book")
        self.del_book_btn.clicked.connect(self._del_book_row)
        book_btn_row.addWidget(self.add_book_btn)
        book_btn_row.addWidget(self.del_book_btn)
        book_btn_row.addStretch()
        book_layout.addLayout(book_btn_row)

        self.accounts_books_tabs.addTab(book_tab, "📚 Client Books && Ledgers (Tally/ERP) (0)")

        right_layout.addWidget(self.accounts_books_tabs, 1)

        # 3. Approved Vendors & Standing Audit Notes
        notes_group = QGroupBox("Master Approved Vendors && Standing Audit Instructions")
        notes_form = QFormLayout(notes_group)

        self.vendors_edit = QLineEdit()
        self.vendors_edit.setPlaceholderText("Comma-separated list of pre-approved suppliers/vendors")
        notes_form.addRow("Approved Vendors List:", self.vendors_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(65)
        self.notes_edit.setPlaceholderText("Default auditor instructions, standing compliance notes, or materiality thresholds...")
        notes_form.addRow("Standing Audit Notes:", self.notes_edit)

        right_layout.addWidget(notes_group)

        right_scroll.setWidget(right_widget)
        splitter.addWidget(right_scroll)
        splitter.setSizes([260, 680])
        main_layout.addWidget(splitter)

        # Bottom Action Buttons
        bottom_row = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save Client Details")
        self.save_btn.clicked.connect(self._save_current_client)
        self.use_client_btn = QPushButton("✓ Select & Load Client into Workspace")
        self.use_client_btn.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px;")
        self.use_client_btn.clicked.connect(self._select_and_accept)
        self.cancel_btn = QPushButton("Close")
        self.cancel_btn.clicked.connect(self.reject)

        bottom_row.addWidget(self.save_btn)
        bottom_row.addStretch()
        bottom_row.addWidget(self.use_client_btn)
        bottom_row.addWidget(self.cancel_btn)
        main_layout.addLayout(bottom_row)

        self.clients_cache: list[ClientProfile] = []
        self.current_editing_id = None

    def _load_clients_list(self, select_id=None):
        self.client_list_widget.clear()
        self.clients_cache = self.db_manager.list_clients()

        if not self.clients_cache:
            # Seed default SUN HEALTH CARE profile if empty
            default_client = ClientProfile(
                name="SUN HEALTH CARE HOSPITAL",
                entity_type="PROPRIETORSHIP",
                pan="AAAPS1234F",
                gstin="21AAAPS1234F1Z5",
                address="GOILUNDI SQUARE, KAMAPALLI ROAD BERHAMPUR, ODISHA 760001",
                bank_accounts=[
                    BankAccountProfile(
                        bank_name="Bank of Maharashtra",
                        account_no="60396048669",
                        ifsc="MAHB0002179",
                        branch="KHODASINGI",
                        account_type="CURRENT",
                    )
                ],
                approved_vendors=["CHOKADOLA ASSOCIATES", "KPS Agencies", "T S R Pharmaceuticals", "MS P P Pharmaceuticals"],
                default_auditor_notes="Regular monthly reconciliation for Sun Health Care Hospital current account.",
            )
            self.db_manager.save_client(default_client)
            self.clients_cache = self.db_manager.list_clients()

        selected_row = 0
        for idx, client in enumerate(self.clients_cache):
            item = QListWidgetItem(f"🏢 {client.name}")
            item.setData(Qt.ItemDataRole.UserRole, client.id)
            self.client_list_widget.addItem(item)
            if select_id and client.id == select_id:
                selected_row = idx

        if self.client_list_widget.count() > 0:
            self.client_list_widget.setCurrentRow(selected_row)

    def _on_client_selected(self, row: int):
        if row < 0 or row >= len(self.clients_cache):
            return
        client = self.clients_cache[row]
        self.current_editing_id = client.id

        self.name_edit.setText(client.name)
        idx = self.entity_combo.findText(client.entity_type)
        if idx >= 0:
            self.entity_combo.setCurrentIndex(idx)
        self.pan_edit.setText(client.pan or "")
        self.gstin_edit.setText(client.gstin or "")
        self.phone_edit.setText(client.phone or "")
        self.email_edit.setText(client.email or "")
        self.address_edit.setText(client.address or "")
        self.vendors_edit.setText(", ".join(client.approved_vendors))
        self.notes_edit.setPlainText(client.default_auditor_notes or "")

        # Populate bank accounts
        self.bank_table.setRowCount(0)
        for ba in client.bank_accounts:
            r = self.bank_table.rowCount()
            self.bank_table.insertRow(r)
            self.bank_table.setRowHeight(r, 34)
            self.bank_table.setItem(r, 0, QTableWidgetItem(ba.bank_name))
            self.bank_table.setItem(r, 1, QTableWidgetItem(ba.account_no))
            self.bank_table.setItem(r, 2, QTableWidgetItem(ba.ifsc or ""))
            self.bank_table.setItem(r, 3, QTableWidgetItem(ba.account_type))
        self.accounts_books_tabs.setTabText(0, f"🏦 Associated Bank Accounts ({len(client.bank_accounts)})")

        # Populate client books / ledgers
        self.book_table.setRowCount(0)
        for cb in getattr(client, "books", []):
            r = self.book_table.rowCount()
            self.book_table.insertRow(r)
            self.book_table.setRowHeight(r, 34)
            self.book_table.setItem(r, 0, QTableWidgetItem(cb.book_name))
            self.book_table.setItem(r, 1, QTableWidgetItem(cb.software))
            self.book_table.setItem(r, 2, QTableWidgetItem(cb.account_head or "Bank Accounts"))
            self.book_table.setItem(r, 3, QTableWidgetItem(cb.linked_bank_account or ""))
            self.book_table.setItem(r, 4, QTableWidgetItem(f"{cb.opening_balance:,.2f}"))
        self.accounts_books_tabs.setTabText(1, f"📚 Client Books && Ledgers (Tally/ERP) ({len(getattr(client, 'books', []))})")

    def _new_client(self):
        new_client = ClientProfile(name="New Client Entity")
        self.db_manager.save_client(new_client)
        self._load_clients_list(select_id=new_client.id)

    def _delete_client(self):
        row = self.client_list_widget.currentRow()
        if row < 0:
            return
        client = self.clients_cache[row]
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete client '{client.name}' from Master Data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_client(client.id)
            self._load_clients_list()

    def _add_bank_row(self):
        r = self.bank_table.rowCount()
        self.bank_table.insertRow(r)
        self.bank_table.setRowHeight(r, 34)
        self.bank_table.setItem(r, 0, QTableWidgetItem("Bank of Maharashtra"))
        self.bank_table.setItem(r, 1, QTableWidgetItem(""))
        self.bank_table.setItem(r, 2, QTableWidgetItem(""))
        self.bank_table.setItem(r, 3, QTableWidgetItem("CURRENT"))
        self.bank_table.setCurrentCell(r, 1)
        self.accounts_books_tabs.setTabText(0, f"🏦 Associated Bank Accounts ({self.bank_table.rowCount()})")

    def _del_bank_row(self):
        r = self.bank_table.currentRow()
        if r >= 0:
            self.bank_table.removeRow(r)
            self.accounts_books_tabs.setTabText(0, f"🏦 Associated Bank Accounts ({self.bank_table.rowCount()})")

    def _add_book_row(self):
        r = self.book_table.rowCount()
        self.book_table.insertRow(r)
        self.book_table.setRowHeight(r, 34)
        self.book_table.setItem(r, 0, QTableWidgetItem("Tally Bank Book"))
        self.book_table.setItem(r, 1, QTableWidgetItem("Tally Prime"))
        self.book_table.setItem(r, 2, QTableWidgetItem("Bank Accounts"))
        self.book_table.setItem(r, 3, QTableWidgetItem(""))
        self.book_table.setItem(r, 4, QTableWidgetItem("0.00"))
        self.book_table.setCurrentCell(r, 0)
        self.accounts_books_tabs.setTabText(1, f"📚 Client Books && Ledgers (Tally/ERP) ({self.book_table.rowCount()})")

    def _del_book_row(self):
        r = self.book_table.currentRow()
        if r >= 0:
            self.book_table.removeRow(r)
            self.accounts_books_tabs.setTabText(1, f"📚 Client Books && Ledgers (Tally/ERP) ({self.book_table.rowCount()})")

    def _save_current_client(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Client Name cannot be empty.")
            return

        # Collect bank accounts
        bank_accounts = []
        for r in range(self.bank_table.rowCount()):
            b_name = self.bank_table.item(r, 0).text().strip() if self.bank_table.item(r, 0) else ""
            b_acc = self.bank_table.item(r, 1).text().strip() if self.bank_table.item(r, 1) else ""
            b_ifsc = self.bank_table.item(r, 2).text().strip() if self.bank_table.item(r, 2) else ""
            b_type = self.bank_table.item(r, 3).text().strip() if self.bank_table.item(r, 3) else "CURRENT"
            if b_name and b_acc:
                bank_accounts.append(
                    BankAccountProfile(
                        bank_name=b_name,
                        account_no=b_acc,
                        ifsc=b_ifsc or None,
                        account_type=b_type,
                    )
                )

        # Collect client books
        books = []
        for r in range(self.book_table.rowCount()):
            bk_name = self.book_table.item(r, 0).text().strip() if self.book_table.item(r, 0) else ""
            bk_soft = self.book_table.item(r, 1).text().strip() if self.book_table.item(r, 1) else "Tally Prime"
            bk_head = self.book_table.item(r, 2).text().strip() if self.book_table.item(r, 2) else "Bank Accounts"
            bk_link = self.book_table.item(r, 3).text().strip() if self.book_table.item(r, 3) else ""
            bk_bal_str = self.book_table.item(r, 4).text().strip() if self.book_table.item(r, 4) else "0.0"
            try:
                bk_bal = float(bk_bal_str.replace(",", ""))
            except ValueError:
                bk_bal = 0.0

            if bk_name:
                books.append(
                    ClientBookProfile(
                        book_name=bk_name,
                        software=bk_soft,
                        account_head=bk_head,
                        linked_bank_account=bk_link or None,
                        opening_balance=bk_bal,
                    )
                )

        # Collect vendors
        v_raw = self.vendors_edit.text().strip()
        vendors = [v.strip() for v in v_raw.split(",") if v.strip()]

        client = ClientProfile(
            id=self.current_editing_id or ClientProfile(name=name).id,
            name=name,
            entity_type=self.entity_combo.currentText(),
            pan=self.pan_edit.text().strip() or None,
            gstin=self.gstin_edit.text().strip() or None,
            phone=self.phone_edit.text().strip() or None,
            email=self.email_edit.text().strip() or None,
            address=self.address_edit.text().strip() or None,
            bank_accounts=bank_accounts,
            books=books,
            approved_vendors=vendors,
            default_auditor_notes=self.notes_edit.toPlainText().strip() or None,
        )

        self.db_manager.save_client(client)
        self.selected_client = client
        QMessageBox.information(self, "Saved", f"Client Master '{name}' saved successfully.")
        self._load_clients_list(select_id=client.id)

    def _select_and_accept(self):
        self._save_current_client()
        self.accept()
