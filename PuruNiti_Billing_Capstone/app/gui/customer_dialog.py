import time
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QPushButton, QLabel, 
                             QFormLayout, QMessageBox, QGroupBox, QHeaderView, QWidget,
                             QFileDialog)
from PyQt5.QtCore import Qt
from app.database import get_customers, save_customers
from app.utils import validate_gstin, validate_pan, validate_pin

class CustomerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Client Directory Manager")
        self.resize(850, 500)
        self.selected_customer = None
        
        self.init_ui()
        self.refresh_table()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # --- LEFT SIDE: Search and Directory Table ---
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search contacts by name, mobile, GSTIN...")
        self.txt_search.textChanged.connect(self.refresh_table)
        search_layout.addWidget(self.txt_search)
        
        left_layout.addLayout(search_layout)
        
        # Directory Table
        self.tbl_customers = QTableWidget(0, 5)
        self.tbl_customers.setHorizontalHeaderLabels(["Name", "Mobile", "GSTIN", "PAN", "State (Place)"])
        self.tbl_customers.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_customers.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl_customers.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_customers.doubleClicked.connect(self.select_and_close)
        
        header = self.tbl_customers.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
        left_layout.addWidget(self.tbl_customers)
        
        # Actions under table
        table_actions = QHBoxLayout()
        self.btn_select = QPushButton("Select Contact")
        self.btn_select.setObjectName("btnPrimary")
        self.btn_select.clicked.connect(self.select_and_close)
        
        self.btn_delete = QPushButton("Delete Contact")
        self.btn_delete.setObjectName("btnDanger")
        self.btn_delete.clicked.connect(self.delete_customer)
        
        self.btn_import_legacy = QPushButton("Import Client Master")
        self.btn_import_legacy.setStyleSheet("background-color: #0F766E; color: white; font-weight: bold;")
        self.btn_import_legacy.clicked.connect(self.import_legacy_customers)
        
        table_actions.addWidget(self.btn_select)
        table_actions.addWidget(self.btn_delete)
        table_actions.addWidget(self.btn_import_legacy)
        table_actions.addStretch()
        
        left_layout.addLayout(table_actions)
        main_layout.addWidget(left_widget, 3)
        
        # --- RIGHT SIDE: Add / Edit Client Form ---
        self.form_group = QGroupBox("Add / Edit Client Profile")
        form_layout = QFormLayout(self.form_group)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(15, 20, 15, 15)
        
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Full Customer Name")
        
        self.txt_mobile = QLineEdit()
        self.txt_mobile.setPlaceholderText("10-digit Phone Code")
        
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Email Address (optional)")
        
        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("Full Billing Address")
        
        self.txt_gstin = QLineEdit()
        self.txt_gstin.setPlaceholderText("15-digit GSTIN (optional)")
        self.txt_gstin.textChanged.connect(self.validate_field_gstin)
        
        self.txt_pan = QLineEdit()
        self.txt_pan.setPlaceholderText("10-digit PAN (optional)")
        self.txt_pan.textChanged.connect(self.validate_field_pan)
        
        self.txt_pin = QLineEdit()
        self.txt_pin.setPlaceholderText("6-digit PIN Code (optional)")
        self.txt_pin.textChanged.connect(self.validate_field_pin)
        
        self.txt_state = QLineEdit()
        self.txt_state.setPlaceholderText("e.g. Maharashtra (27)")
        
        form_layout.addRow("Name *", self.txt_name)
        form_layout.addRow("Mobile *", self.txt_mobile)
        form_layout.addRow("Email", self.txt_email)
        form_layout.addRow("Address", self.txt_address)
        form_layout.addRow("GSTIN (15-char)", self.txt_gstin)
        form_layout.addRow("PAN (10-char)", self.txt_pan)
        form_layout.addRow("PIN Code (6-digit)", self.txt_pin)
        form_layout.addRow("State (POS) *", self.txt_state)
        
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Contact")
        self.btn_save.setObjectName("btnSuccess")
        self.btn_save.clicked.connect(self.save_customer_profile)
        
        self.btn_clear = QPushButton("Clear Fields")
        self.btn_clear.clicked.connect(self.clear_form)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_clear)
        form_layout.addRow(btn_layout)
        
        main_layout.addWidget(self.form_group, 2)
        
        # Bind table selection change to show details in form for editing
        self.tbl_customers.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        self.editing_id = None

    def validate_field_gstin(self, text):
        """Highlights GSTIN field in red if format is invalid."""
        if not text:
            self.txt_gstin.setStyleSheet("")
            return
        if validate_gstin(text):
            self.txt_gstin.setStyleSheet("border: 1.5px solid #16A34A;") # Green border
            # Extract state code
            if len(text) >= 2:
                from app.gui.main_window import STATE_CODES
                code = text[:2]
                if code in STATE_CODES:
                    self.txt_state.setText(f"{STATE_CODES[code]} ({code})")
        else:
            self.txt_gstin.setStyleSheet("border: 1.5px solid #DC2626;") # Red border

    def validate_field_pan(self, text):
        """Highlights PAN field in red if format is invalid."""
        if not text:
            self.txt_pan.setStyleSheet("")
            return
        if validate_pan(text):
            self.txt_pan.setStyleSheet("border: 1.5px solid #16A34A;")
        else:
            self.txt_pan.setStyleSheet("border: 1.5px solid #DC2626;")

    def validate_field_pin(self, text):
        """Highlights PIN field in red if format is invalid."""
        if not text:
            self.txt_pin.setStyleSheet("")
            return
        if validate_pin(text):
            self.txt_pin.setStyleSheet("border: 1.5px solid #16A34A;")
        else:
            self.txt_pin.setStyleSheet("border: 1.5px solid #DC2626;")

    def refresh_table(self):
        """Refreshes customer registry listing with filtering."""
        query = self.txt_search.text().lower().strip()
        customers = get_customers()
        
        self.tbl_customers.setRowCount(0)
        
        filtered = []
        for c in customers:
            name = c.get("name", "").lower()
            mobile = c.get("mobile", "").lower()
            gstin = c.get("gstin", "").lower()
            if not query or query in name or query in mobile or query in gstin:
                filtered.append(c)
                
        # Populate
        for r_idx, c in enumerate(filtered):
            self.tbl_customers.insertRow(r_idx)
            
            name_item = QTableWidgetItem(c.get("name", ""))
            name_item.setData(Qt.UserRole, c.get("id", ""))
            
            self.tbl_customers.setItem(r_idx, 0, name_item)
            self.tbl_customers.setItem(r_idx, 1, QTableWidgetItem(c.get("mobile", "")))
            self.tbl_customers.setItem(r_idx, 2, QTableWidgetItem(c.get("gstin", "")))
            self.tbl_customers.setItem(r_idx, 3, QTableWidgetItem(c.get("pan", "")))
            self.tbl_customers.setItem(r_idx, 4, QTableWidgetItem(c.get("place_of_supply", "")))

    def on_selection_changed(self):
        """Loads selected contact into editing form."""
        selected_indexes = self.tbl_customers.selectionModel().selectedRows()
        if not selected_indexes:
            self.clear_form()
            return
            
        row = selected_indexes[0].row()
        cust_id = self.tbl_customers.item(row, 0).data(Qt.UserRole)
        
        customers = get_customers()
        for c in customers:
            if c.get("id") == cust_id:
                self.editing_id = cust_id
                self.txt_name.setText(c.get("name", ""))
                self.txt_mobile.setText(c.get("mobile", ""))
                self.txt_email.setText(c.get("email", ""))
                self.txt_address.setText(c.get("address", ""))
                self.txt_gstin.setText(c.get("gstin", ""))
                self.txt_pan.setText(c.get("pan", ""))
                self.txt_pin.setText(c.get("pin", ""))
                self.txt_state.setText(c.get("place_of_supply", ""))
                self.form_group.setTitle("Edit Client Profile")
                break

    def clear_form(self):
        self.editing_id = None
        self.txt_name.clear()
        self.txt_mobile.clear()
        self.txt_email.clear()
        self.txt_address.clear()
        self.txt_gstin.clear()
        self.txt_pan.clear()
        self.txt_pin.clear()
        self.txt_state.clear()
        self.txt_gstin.setStyleSheet("")
        self.txt_pan.setStyleSheet("")
        self.txt_pin.setStyleSheet("")
        self.form_group.setTitle("Add Client Profile")
        self.tbl_customers.clearSelection()

    def save_customer_profile(self):
        """Validates formats and saves or updates the customer contact in database."""
        name = self.txt_name.text().strip()
        mobile = self.txt_mobile.text().strip()
        email = self.txt_email.text().strip()
        address = self.txt_address.text().strip()
        gstin = self.txt_gstin.text().strip().upper()
        pan = self.txt_pan.text().strip().upper()
        pin = self.txt_pin.text().strip()
        state = self.txt_state.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Warning", "Customer Name is required.")
            self.txt_name.setFocus()
            return
        if not state:
            QMessageBox.warning(self, "Validation Warning", "State (Place of Supply) is required.")
            self.txt_state.setFocus()
            return
            
        # Format validations
        if gstin and not validate_gstin(gstin):
            QMessageBox.critical(self, "Validation Error", "Invalid GSTIN format entered.\n(Must be 15 characters, starting with valid 2-digit state code)")
            self.txt_gstin.setFocus()
            return
        if pan and not validate_pan(pan):
            QMessageBox.critical(self, "Validation Error", "Invalid PAN format entered.\n(Must be 10 characters alphanumeric: e.g. ABCDE1234F)")
            self.txt_pan.setFocus()
            return
        if pin and not validate_pin(pin):
            QMessageBox.critical(self, "Validation Error", "Invalid PIN Code format entered.\n(Must be exactly 6 numeric digits: e.g. 400001)")
            self.txt_pin.setFocus()
            return
            
        customers = get_customers()
        
        if self.editing_id:
            # Update existing
            for c in customers:
                if c.get("id") == self.editing_id:
                    c.update({
                        "name": name,
                        "mobile": mobile,
                        "email": email,
                        "address": address,
                        "gstin": gstin,
                        "pan": pan,
                        "pin": pin,
                        "place_of_supply": state
                    })
                    break
        else:
            # Create new
            new_id = f"{int(time.time())}_{name[:10].replace(' ', '')}"
            customers.append({
                "id": new_id,
                "name": name,
                "mobile": mobile,
                "email": email,
                "address": address,
                "gstin": gstin,
                "pan": pan,
                "pin": pin,
                "place_of_supply": state
            })
            
        if save_customers(customers):
            QMessageBox.information(self, "Success", "Customer profile saved successfully!")
            self.clear_form()
            self.refresh_table()
        else:
            QMessageBox.critical(self, "Database Error", "Failed to write customer details to disk.")

    def delete_customer(self):
        """Deletes selected contact from CRM database."""
        selected_indexes = self.tbl_customers.selectionModel().selectedRows()
        if not selected_indexes:
            return
            
        row = selected_indexes[0].row()
        cust_id = self.tbl_customers.item(row, 0).data(Qt.UserRole)
        cust_name = self.tbl_customers.item(row, 0).text()
        
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete client '{cust_name}' from contacts?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            customers = get_customers()
            customers = [c for c in customers if c.get("id") != cust_id]
            if save_customers(customers):
                QMessageBox.information(self, "Contact Deleted", "Contact removed successfully.")
                self.clear_form()
                self.refresh_table()
            else:
                QMessageBox.critical(self, "Error", "Failed to remove customer record from database.")

    def select_and_close(self):
        """Passes details of double-clicked or selected customer to active MainWindow form."""
        selected_indexes = self.tbl_customers.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, "Selection Required", "Please select a client from the directory table first.")
            return
            
        row = selected_indexes[0].row()
        cust_id = self.tbl_customers.item(row, 0).data(Qt.UserRole)
        
        customers = get_customers()
        for c in customers:
            if c.get("id") == cust_id:
                self.selected_customer = c
                self.accept()
                return

    def import_legacy_customers(self):
        """Allows importing customer master details from Excel (.xlsx) or JSON files."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Client Master from Legacy System", "",
            "Legacy Files (*.xlsx *.json);;Excel Files (*.xlsx);;JSON Files (*.json)",
            options=options
        )
        if not file_path:
            return
            
        imported_count = 0
        duplicate_count = 0
        errors = []
        
        customers = get_customers()
        existing_names = {c.get("name", "").lower().strip(): c for c in customers}
        existing_mobiles = {c.get("mobile", "").strip(): c for c in customers if c.get("mobile")}
        existing_gstins = {c.get("gstin", "").upper().strip(): c for c in customers if c.get("gstin")}
        
        try:
            if file_path.endswith(".json"):
                import json
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError("JSON file must contain a list of client profiles.")
                raw_records = data
            else:
                # Excel file
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True)
                sheet = wb.active
                
                # Read rows
                rows = list(sheet.iter_rows(values_only=True))
                if len(rows) < 2:
                    raise ValueError("Excel file must contain a header row and at least one client record.")
                    
                headers = [str(cell).lower().strip() if cell else "" for cell in rows[0]]
                
                # Helper to find column index case-insensitively
                def find_col(possible_names):
                    for name in possible_names:
                        if name in headers:
                            return headers.index(name)
                    return -1
                    
                col_name = find_col(["name", "client name", "customer name", "client", "customer"])
                col_mobile = find_col(["mobile", "phone", "contact", "mobile no", "phone no", "mobile number"])
                col_email = find_col(["email", "email id", "email address", "mail"])
                col_address = find_col(["address", "billing address", "street"])
                col_gstin = find_col(["gstin", "gst", "gst number", "gstin no"])
                col_pan = find_col(["pan", "pan card", "pan number", "pan no"])
                col_pin = find_col(["pin", "pin code", "pincode", "zip", "zip code"])
                col_state = find_col(["state", "place of supply", "pos", "state name"])
                
                if col_name == -1:
                    raise ValueError("Could not find a 'Name' or 'Client Name' column in Excel headers.")
                    
                raw_records = []
                for row_data in rows[1:]:
                    if not any(row_data):
                        continue # Skip empty rows
                        
                    def get_val(col_idx):
                        if col_idx != -1 and col_idx < len(row_data):
                            val = row_data[col_idx]
                            return str(val).strip() if val is not None else ""
                        return ""
                        
                    raw_records.append({
                        "name": get_val(col_name),
                        "mobile": get_val(col_mobile),
                        "email": get_val(col_email),
                        "address": get_val(col_address),
                        "gstin": get_val(col_gstin),
                        "pan": get_val(col_pan),
                        "pin": get_val(col_pin),
                        "place_of_supply": get_val(col_state)
                    })
            
            # Process records
            for idx, rec in enumerate(raw_records, 1):
                name = rec.get("name", "").strip()
                mobile = rec.get("mobile", "").strip()
                email = rec.get("email", "").strip()
                address = rec.get("address", "").strip()
                gstin = rec.get("gstin", "").strip().upper()
                pan = rec.get("pan", "").strip().upper()
                pin = rec.get("pin", "").strip()
                state = rec.get("place_of_supply", "").strip()
                
                if not name:
                    errors.append(f"Row/Record {idx}: Missing client name (Skipped).")
                    continue
                    
                # Standardize GSTIN/PAN formats
                if gstin and not validate_gstin(gstin):
                    errors.append(f"Row/Record {idx} ({name}): Invalid GSTIN format '{gstin}' (Skipped).")
                    continue
                if pan and not validate_pan(pan):
                    errors.append(f"Row/Record {idx} ({name}): Invalid PAN format '{pan}' (Skipped).")
                    continue
                if pin and not validate_pin(pin):
                    errors.append(f"Row/Record {idx} ({name}): Invalid PIN format '{pin}' (Skipped).")
                    continue
                    
                # If state is missing but GSTIN is valid, extract state
                if not state and gstin:
                    from app.gui.main_window import STATE_CODES
                    code = gstin[:2]
                    if code in STATE_CODES:
                        state = f"{STATE_CODES[code]} ({code})"
                        
                if not state:
                    state = "Out of State" # Fallback if empty and not deducible
                    
                # Check duplicates (skip or update)
                existing = None
                if gstin and gstin in existing_gstins:
                    existing = existing_gstins[gstin]
                elif mobile and mobile in existing_mobiles:
                    existing = existing_mobiles[mobile]
                elif name.lower() in existing_names:
                    existing = existing_names[name.lower()]
                    
                if existing:
                    # Update fields in-place
                    existing["mobile"] = mobile or existing.get("mobile", "")
                    existing["email"] = email or existing.get("email", "")
                    existing["address"] = address or existing.get("address", "")
                    existing["gstin"] = gstin or existing.get("gstin", "")
                    existing["pan"] = pan or existing.get("pan", "")
                    existing["pin"] = pin or existing.get("pin", "")
                    existing["place_of_supply"] = state or existing.get("place_of_supply", "")
                    duplicate_count += 1
                else:
                    new_id = f"{int(time.time())}_{name[:10].replace(' ', '')}_{imported_count}"
                    new_cust = {
                        "id": new_id,
                        "name": name,
                        "mobile": mobile,
                        "email": email,
                        "address": address,
                        "gstin": gstin,
                        "pan": pan,
                        "pin": pin,
                        "place_of_supply": state
                    }
                    customers.append(new_cust)
                    existing_names[name.lower()] = new_cust
                    if mobile:
                        existing_mobiles[mobile] = new_cust
                    if gstin:
                        existing_gstins[gstin] = new_cust
                    imported_count += 1
                    
            if save_customers(customers):
                msg = f"Client Master Import Finished!\n\n- New clients imported: {imported_count}\n- Existing clients updated: {duplicate_count}"
                if errors:
                    msg += "\n\nWarnings/Skipped rows details:\n" + "\n".join(errors[:10])
                    if len(errors) > 10:
                        msg += f"\n...and {len(errors) - 10} more warnings."
                QMessageBox.information(self, "Client Import Success", msg)
                self.refresh_table()
            else:
                QMessageBox.critical(self, "Database Error", "Failed to write imported clients to database.")
                
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to parse clients source file:\n{e}")
