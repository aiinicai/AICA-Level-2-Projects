import os
import shutil
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QTextEdit, QPushButton, QMessageBox, QLabel, QFileDialog, QComboBox)
from PyQt5.QtCore import Qt
from app.database import get_settings, save_settings, get_database_dir

class SellerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Supplier Profiles Manager")
        self.resize(550, 650)
        self.setModal(True)
        
        # Track logo state
        self.selected_logo_path = None
        self.remove_existing_logo = False
        
        self.init_ui()
        self.load_profiles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("Supplier / Business Profiles Manager")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Profile Selector Row
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Select Profile:"))
        
        self.cmb_profile = QComboBox()
        self.cmb_profile.currentTextChanged.connect(self.on_profile_selection_changed)
        profile_layout.addWidget(self.cmb_profile, 3)
        
        self.btn_new_profile = QPushButton("New Profile")
        self.btn_new_profile.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_new_profile.clicked.connect(self.create_new_profile)
        profile_layout.addWidget(self.btn_new_profile, 1)
        
        self.btn_delete_profile = QPushButton("Delete Profile")
        self.btn_delete_profile.setObjectName("btnDanger")
        self.btn_delete_profile.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_delete_profile.clicked.connect(self.delete_current_profile)
        profile_layout.addWidget(self.btn_delete_profile, 1)
        
        layout.addLayout(profile_layout)
        
        # Form Layout for fields
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(10, 10, 10, 10)
        
        self.txt_trade_name = QLineEdit()
        self.txt_trade_name.setPlaceholderText("e.g. Smart Solutions Ltd")
        
        self.txt_address = QTextEdit()
        self.txt_address.setPlaceholderText("Full Business Address")
        self.txt_address.setMaximumHeight(80)
        
        self.txt_mobile = QLineEdit()
        self.txt_mobile.setPlaceholderText("e.g. +91 9876543210")
        
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("e.g. contact@domain.com")
        
        self.txt_gstin = QLineEdit()
        self.txt_gstin.setPlaceholderText("15-digit GSTIN (optional)")
        
        # Business Logo Section
        logo_layout = QHBoxLayout()
        self.lbl_logo_status = QLabel("No Logo Configured")
        self.lbl_logo_status.setStyleSheet("font-style: italic; color: #64748B;")
        
        self.btn_browse_logo = QPushButton("Browse")
        self.btn_browse_logo.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_browse_logo.clicked.connect(self.browse_logo)
        
        self.btn_remove_logo = QPushButton("Remove")
        self.btn_remove_logo.setStyleSheet("font-size: 11px; padding: 4px 8px; color: #B91C1C;")
        self.btn_remove_logo.clicked.connect(self.remove_logo)
        
        logo_layout.addWidget(self.lbl_logo_status, 3)
        logo_layout.addWidget(self.btn_browse_logo, 1)
        logo_layout.addWidget(self.btn_remove_logo, 1)
        
        # Bank Details Section
        bank_section_title = QLabel("Bank details for payments:")
        bank_section_title.setStyleSheet("font-weight: bold; margin-top: 10px; color: #1A365D;")
        
        self.txt_bank_name = QLineEdit()
        self.txt_bank_name.setPlaceholderText("e.g. State Bank of India")
        
        self.txt_acc_no = QLineEdit()
        self.txt_acc_no.setPlaceholderText("Bank Account Number")
        
        self.txt_ifsc = QLineEdit()
        self.txt_ifsc.setPlaceholderText("IFSC Code")
        
        self.txt_branch = QLineEdit()
        self.txt_branch.setPlaceholderText("Bank Branch Location")
        
        self.txt_declaration = QTextEdit()
        self.txt_declaration.setPlaceholderText("Declaration on invoice footer")
        self.txt_declaration.setMaximumHeight(60)
        
        # Add to form
        form_layout.addRow("Trade/Business Name *", self.txt_trade_name)
        form_layout.addRow("Address *", self.txt_address)
        form_layout.addRow("Mobile No. *", self.txt_mobile)
        form_layout.addRow("Email *", self.txt_email)
        form_layout.addRow("GSTIN (Optional)", self.txt_gstin)
        form_layout.addRow("Business Logo", logo_layout)
        
        # Inserting separator widget for Bank Details
        form_layout.addRow("", bank_section_title)
        form_layout.addRow("Bank Name", self.txt_bank_name)
        form_layout.addRow("Account Number", self.txt_acc_no)
        form_layout.addRow("IFSC Code", self.txt_ifsc)
        form_layout.addRow("Branch Name", self.txt_branch)
        form_layout.addRow("Declaration", self.txt_declaration)
        
        layout.addLayout(form_layout)
        
        # Buttons Row
        buttons_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setObjectName("btnPrimary")
        self.btn_save.setProperty("primary", True)
        self.btn_save.clicked.connect(self.save_data)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_save)
        
        layout.addLayout(buttons_layout)

    def load_profiles(self):
        """Loads profiles from settings and populates the selector combo box."""
        settings = get_settings()
        sellers = settings.get("sellers", {})
        active = settings.get("active_seller_id", "")
        
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.clear()
        for key in sellers.keys():
            self.cmb_profile.addItem(key)
        if active in sellers:
            self.cmb_profile.setCurrentText(active)
        self.cmb_profile.blockSignals(False)
        
        self.on_profile_selection_changed(self.cmb_profile.currentText())

    def on_profile_selection_changed(self, profile_name):
        """Fills form inputs with the selected profile's data."""
        if not profile_name:
            self.clear_form_fields()
            return
            
        settings = get_settings()
        seller = settings.get("sellers", {}).get(profile_name, {})
        
        self.txt_trade_name.setText(seller.get("trade_name", profile_name))
        self.txt_address.setPlainText(seller.get("address", ""))
        self.txt_mobile.setText(seller.get("mobile", ""))
        self.txt_email.setText(seller.get("email", ""))
        self.txt_gstin.setText(seller.get("gstin", ""))
        
        self.txt_bank_name.setText(seller.get("bank_name", ""))
        self.txt_acc_no.setText(seller.get("account_number", ""))
        self.txt_ifsc.setText(seller.get("ifsc", ""))
        self.txt_branch.setText(seller.get("branch", ""))
        self.txt_declaration.setPlainText(seller.get("declaration", ""))
        
        # Load unique profile logo status
        safe_profile = "".join([c if c.isalnum() else "_" for c in profile_name])
        logo_file = os.path.join(get_database_dir(), f"{safe_profile}_logo.png")
        
        self.selected_logo_path = None
        self.remove_existing_logo = False
        
        if os.path.exists(logo_file):
            self.lbl_logo_status.setText(f"Logo Configured ({safe_profile}_logo.png)")
            self.btn_remove_logo.setEnabled(True)
        else:
            self.lbl_logo_status.setText("No Logo Configured")
            self.btn_remove_logo.setEnabled(False)

    def clear_form_fields(self):
        self.txt_trade_name.clear()
        self.txt_address.clear()
        self.txt_mobile.clear()
        self.txt_email.clear()
        self.txt_gstin.clear()
        self.txt_bank_name.clear()
        self.txt_acc_no.clear()
        self.txt_ifsc.clear()
        self.txt_branch.clear()
        self.txt_declaration.clear()
        self.lbl_logo_status.setText("No Logo Configured")
        self.btn_remove_logo.setEnabled(False)

    def create_new_profile(self):
        """Creates a fresh Supplier Profile metadata block."""
        name, ok = QInputDialog.getText(self, "New Profile", "Enter Trade/Business Name:")
        if ok and name.strip():
            name = name.strip()
            settings = get_settings()
            if name in settings.get("sellers", {}):
                QMessageBox.warning(self, "Duplicate Name", f"Profile '{name}' already exists.")
                self.cmb_profile.setCurrentText(name)
                return
                
            self.cmb_profile.blockSignals(True)
            self.cmb_profile.addItem(name)
            self.cmb_profile.setCurrentText(name)
            self.cmb_profile.blockSignals(False)
            
            self.clear_form_fields()
            self.txt_trade_name.setText(name)
            self.txt_trade_name.setFocus()

    def delete_current_profile(self):
        """Removes the selected supplier profile from database."""
        current_profile = self.cmb_profile.currentText()
        if not current_profile:
            return
            
        if self.cmb_profile.count() <= 1:
            QMessageBox.warning(self, "Action Denied", "At least one Supplier Profile is required.")
            return
            
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete profile '{current_profile}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            settings = get_settings()
            if current_profile in settings.get("sellers", {}):
                del settings["sellers"][current_profile]
                
                # Cleanup specific logo file
                safe_profile = "".join([c if c.isalnum() else "_" for c in current_profile])
                logo_file = os.path.join(get_database_dir(), f"{safe_profile}_logo.png")
                if os.path.exists(logo_file):
                    try:
                        os.remove(logo_file)
                    except Exception:
                        pass
                
                # If deleted active profile, select a new active profile
                if settings.get("active_seller_id") == current_profile:
                    settings["active_seller_id"] = list(settings["sellers"].keys())[0]
                    
                save_settings(settings)
                QMessageBox.information(self, "Profile Deleted", "Supplier profile removed successfully.")
                self.load_profiles()

    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.selected_logo_path = file_path
            self.remove_existing_logo = False
            self.lbl_logo_status.setText(f"Selected: {os.path.basename(file_path)}")
            self.btn_remove_logo.setEnabled(True)

    def remove_logo(self):
        self.selected_logo_path = None
        self.remove_existing_logo = True
        self.lbl_logo_status.setText("Logo will be removed on Save")
        self.btn_remove_logo.setEnabled(False)

    def save_data(self):
        """Saves current supplier fields to settings under its profile key."""
        current_profile = self.cmb_profile.currentText()
        trade_name = self.txt_trade_name.text().strip()
        address = self.txt_address.toPlainText().strip()
        mobile = self.txt_mobile.text().strip()
        email = self.txt_email.text().strip()
        
        if not trade_name:
            QMessageBox.warning(self, "Validation Error", "Trade/Business Name is required.")
            self.txt_trade_name.setFocus()
            return
        if not address:
            QMessageBox.warning(self, "Validation Error", "Business Address is required.")
            self.txt_address.setFocus()
            return
        if not mobile:
            QMessageBox.warning(self, "Validation Error", "Mobile Number is required.")
            self.txt_mobile.setFocus()
            return
        if not email:
            QMessageBox.warning(self, "Validation Error", "Email is required.")
            self.txt_email.setFocus()
            return
            
        settings = get_settings()
        sellers = settings.get("sellers", {})
        
        # If the user edited the trade name, delete the old key and create new key
        if current_profile and current_profile != trade_name:
            if current_profile in sellers:
                del sellers[current_profile]
                
            # Rename unique logo file if exists
            old_safe = "".join([c if c.isalnum() else "_" for c in current_profile])
            new_safe = "".join([c if c.isalnum() else "_" for c in trade_name])
            old_logo = os.path.join(get_database_dir(), f"{old_safe}_logo.png")
            new_logo = os.path.join(get_database_dir(), f"{new_safe}_logo.png")
            if os.path.exists(old_logo):
                try:
                    shutil.move(old_logo, new_logo)
                except Exception:
                    pass
                    
        sellers[trade_name] = {
            "trade_name": trade_name,
            "address": address,
            "mobile": mobile,
            "email": email,
            "gstin": self.txt_gstin.text().strip().upper(),
            "bank_name": self.txt_bank_name.text().strip(),
            "account_number": self.txt_acc_no.text().strip(),
            "ifsc": self.txt_ifsc.text().strip().upper(),
            "branch": self.txt_branch.text().strip(),
            "declaration": self.txt_declaration.toPlainText().strip()
        }
        
        settings["sellers"] = sellers
        settings["active_seller_id"] = trade_name
        
        # For legacy backward-compatibility so we don't break other accesses
        settings["seller"] = sellers[trade_name]
        
        if save_settings(settings):
            # Process profile-specific logo file operations
            safe_profile = "".join([c if c.isalnum() else "_" for c in trade_name])
            logo_target = os.path.join(get_database_dir(), f"{safe_profile}_logo.png")
            
            if self.selected_logo_path:
                try:
                    shutil.copy2(self.selected_logo_path, logo_target)
                except Exception as e:
                    QMessageBox.warning(self, "Logo Error", f"Failed to save logo file: {e}")
            elif self.remove_existing_logo:
                try:
                    if os.path.exists(logo_target):
                        os.remove(logo_target)
                except Exception as e:
                    print(f"Failed to remove logo file: {e}")
                    
            # Also copy this profile logo to standard logo.png for ReportLab PDF compiler
            std_logo_path = os.path.join(get_database_dir(), "logo.png")
            if os.path.exists(logo_target):
                try:
                    shutil.copy2(logo_target, std_logo_path)
                except Exception:
                    pass
            else:
                try:
                    if os.path.exists(std_logo_path):
                        os.remove(std_logo_path)
                except Exception:
                    pass
            
            QMessageBox.information(self, "Success", "Supplier Business Profile saved successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Database Error", "Failed to save settings to JSON file.")

# Import QInputDialog at top/runtime
from PyQt5.QtWidgets import QInputDialog
