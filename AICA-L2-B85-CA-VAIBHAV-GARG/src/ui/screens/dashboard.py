"""Screen 1: Client Portfolio Dashboard presenting clients in a sleek, executive List View."""
from typing import Dict, List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from src.database.repository import Repository
from src.ui.dialogs.client_dialogs import RenameClientDialog, DuplicateClientDialog, DeleteClientDialog


class DashboardScreen(QWidget):
    create_new_client = Signal()
    open_client = Signal(int, str)

    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self.repo = repo
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(32, 28, 32, 28)
        self.main_layout.setSpacing(20)
        
        # 1. Header banner
        header_layout = QHBoxLayout()
        
        title_box = QVBoxLayout()
        title = QLabel("Client Portfolio")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0A2540;")
        subtitle = QLabel("Select a client to view statutory analytical ratios or initialize a new engagement.")
        subtitle.setStyleSheet("font-size: 13px; color: #64748B;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        
        header_layout.addStretch()
        
        new_btn = QPushButton("➕ New Client Engagement")
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066CC;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0052A3;
            }
        """)
        new_btn.clicked.connect(self.create_new_client.emit)
        header_layout.addWidget(new_btn)
        
        self.main_layout.addLayout(header_layout)
        
        # 2. Search & Count bar
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search clients by name or CIN...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #0066CC;
            }
        """)
        self.search_input.textChanged.connect(self.refresh_clients)
        filter_layout.addWidget(self.search_input, stretch=1)
        
        self.count_label = QLabel("0 Clients")
        self.count_label.setStyleSheet("font-size: 13px; color: #64748B; font-weight: 500;")
        filter_layout.addWidget(self.count_label)
        
        self.main_layout.addLayout(filter_layout)
        
        # 3. Modern Client List Table
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(6)
        self.client_table.setHorizontalHeaderLabels([
            "Client Name", "CIN / Registration", "Reporting Unit", "Last Financial Year", "Last Analysis Date", "Actions"
        ])
        
        hdr = self.client_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.client_table.verticalHeader().setVisible(False)
        self.client_table.setAlternatingRowColors(True)
        self.client_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                alternate-background-color: #F8FAFC;
            }
        """)
        self.main_layout.addWidget(self.client_table, stretch=1)
        
        # 4. Empty State Widget
        self.empty_state = QFrame()
        self.empty_state.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 2px dashed #CBD5E1;
                border-radius: 12px;
                padding: 40px;
            }
        """)
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(12)
        
        empty_icon = QLabel("📊")
        empty_icon.setStyleSheet("font-size: 42px;")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_icon)
        
        empty_title = QLabel("No Client Engagements Found")
        empty_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0A2540;")
        empty_title.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_title)
        
        empty_sub = QLabel("Create your first client to start automated Schedule III ratio analysis.")
        empty_sub.setStyleSheet("font-size: 13px; color: #64748B;")
        empty_sub.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_sub)
        
        empty_btn = QPushButton("➕ Create Client")
        empty_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066CC;
                color: white;
                font-weight: bold;
                padding: 9px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
        """)
        empty_btn.clicked.connect(self.create_new_client.emit)
        empty_layout.addWidget(empty_btn, alignment=Qt.AlignCenter)
        
        self.main_layout.addWidget(self.empty_state)
        
        self.refresh_clients()

    def refresh_clients(self):
        query = self.search_input.text().strip() if hasattr(self, "search_input") else ""
        clients = self.repo.list_clients(query)
        
        self.count_label.setText(f"{len(clients)} Client{'s' if len(clients) != 1 else ''}")
        
        if not clients:
            self.client_table.hide()
            self.empty_state.show()
            return
            
        self.empty_state.hide()
        self.client_table.show()
        
        self.client_table.setRowCount(len(clients))
        for row_idx, client in enumerate(clients):
            self.client_table.setRowHeight(row_idx, 48)
            cid = client["id"]
            cname = client["name"]
            
            # 0. Client Name
            name_item = QTableWidgetItem(f"🏢  {cname}")
            name_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_item.setForeground(QColor("#0A2540"))
            self.client_table.setItem(row_idx, 0, name_item)
            
            # 1. CIN
            cin_val = client.get("cin") or "—"
            cin_item = QTableWidgetItem(cin_val)
            cin_item.setTextAlignment(Qt.AlignCenter)
            cin_item.setForeground(QColor("#64748B"))
            self.client_table.setItem(row_idx, 1, cin_item)
            
            # 2. Reporting Unit Badge
            unit_val = f"₹ {client.get('units', 'Lacs')}"
            unit_item = QTableWidgetItem(unit_val)
            unit_item.setTextAlignment(Qt.AlignCenter)
            unit_item.setForeground(QColor("#0066CC"))
            unit_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.client_table.setItem(row_idx, 2, unit_item)
            
            # 3. Last Financial Year
            last_fy = client.get("last_fy") or "Ready"
            fy_item = QTableWidgetItem(last_fy)
            fy_item.setTextAlignment(Qt.AlignCenter)
            if last_fy != "Ready":
                fy_item.setForeground(QColor("#0F766E"))
                fy_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            else:
                fy_item.setForeground(QColor("#94A3B8"))
            self.client_table.setItem(row_idx, 3, fy_item)
            
            # 4. Last Analysis Date
            last_date = client.get("last_analysis_date")
            date_str = last_date[:10] if last_date else "—"
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignCenter)
            date_item.setForeground(QColor("#64748B"))
            self.client_table.setItem(row_idx, 4, date_item)
            
            # 5. Actions Toolbar
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(6, 4, 6, 4)
            act_layout.setSpacing(6)
            
            open_btn = QPushButton("📂 Open")
            open_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0066CC;
                    color: white;
                    border-radius: 4px;
                    padding: 5px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0052A3;
                }
            """)
            open_btn.clicked.connect(lambda checked=False, id=cid, name=cname: self.on_open(id, name))
            act_layout.addWidget(open_btn)
            
            rename_btn = QPushButton("✏️ Rename")
            rename_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F8FAFC;
                    color: #1E293B;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                }
            """)
            rename_btn.clicked.connect(lambda checked=False, id=cid, name=cname: self.on_rename(id, name))
            act_layout.addWidget(rename_btn)
            
            dup_btn = QPushButton("📑 Duplicate")
            dup_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F8FAFC;
                    color: #1E293B;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                }
            """)
            dup_btn.clicked.connect(lambda checked=False, id=cid, name=cname: self.on_duplicate(id, name))
            act_layout.addWidget(dup_btn)
            
            del_btn = QPushButton("🗑️ Delete")
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEF2F2;
                    color: #DC2626;
                    border: 1px solid #FECACA;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #FEE2E2;
                }
            """)
            del_btn.clicked.connect(lambda checked=False, id=cid, name=cname: self.on_delete(id, name))
            act_layout.addWidget(del_btn)
            
            self.client_table.setCellWidget(row_idx, 5, act_widget)

    def on_open(self, client_id: int, client_name: str):
        self.open_client.emit(client_id, client_name)

    def on_rename(self, client_id: int, current_name: str):
        dlg = RenameClientDialog(current_name, self)
        if dlg.exec():
            new_name = dlg.get_new_name()
            if new_name and new_name != current_name:
                self.repo.update_client_name(client_id, new_name)
                self.refresh_clients()

    def on_duplicate(self, client_id: int, current_name: str):
        dlg = DuplicateClientDialog(current_name, self)
        if dlg.exec():
            new_name = dlg.get_new_name()
            if new_name:
                self.repo.duplicate_client(client_id, new_name)
                self.refresh_clients()

    def on_delete(self, client_id: int, current_name: str):
        dlg = DeleteClientDialog(current_name, self)
        if dlg.exec():
            self.repo.delete_client(client_id)
            self.refresh_clients()
