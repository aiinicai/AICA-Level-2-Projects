"""Workings drilldown dialog showing numerator and denominator component sources (§6)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from src.config import COLORS
from src.core.calculator import SingleRatioResult


class WorkingsDialog(QDialog):
    def __init__(self, ratio: SingleRatioResult, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Workings & Line Items — {ratio.name}")
        self.setMinimumSize(700, 480)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        title = QLabel(f"<b>{ratio.name}</b> ({ratio.clause})")
        title.setStyleSheet(f"font-size: 15px; color: {COLORS['deep_navy']};")
        layout.addWidget(title)
        
        formula_box = QLabel(
            f"<b>Formula:</b> {ratio.numerator_desc} ÷ {ratio.denominator_desc}<br>"
            f"<b>Current Year Value:</b> {ratio.value_cy_formatted} &nbsp;|&nbsp; <b>Previous Year Value:</b> {ratio.value_py_formatted} &nbsp;|&nbsp; <b>Variance:</b> {ratio.variance_pct_formatted}"
        )
        formula_box.setStyleSheet("background-color: #F1F5F9; padding: 10px; border-radius: 6px;")
        layout.addWidget(formula_box)
        
        # Table of Numerator & Denominator Breakdown
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Component", "Description / Basis", "Current Year Amount", "Previous Year Amount"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        items = [
            ("Numerator", ratio.numerator_desc, f"{ratio.numerator_cy:.2f}" if ratio.numerator_cy is not None else "—", f"{ratio.numerator_py:.2f}" if ratio.numerator_py is not None else "—"),
            ("Denominator", ratio.denominator_desc, f"{ratio.denominator_cy:.2f}" if ratio.denominator_cy is not None else "—", f"{ratio.denominator_py:.2f}" if ratio.denominator_py is not None else "—"),
            ("Ratio Result", f"Computed in accordance with Schedule III ({ratio.unit})", ratio.value_cy_formatted, ratio.value_py_formatted),
        ]
        
        table.setRowCount(len(items))
        for row_idx, (comp, desc, cy_val, py_val) in enumerate(items):
            item_comp = QTableWidgetItem(comp)
            item_comp.setFlags(item_comp.flags() ^ Qt.ItemIsEditable)
            table.setItem(row_idx, 0, item_comp)
            
            item_desc = QTableWidgetItem(desc)
            item_desc.setFlags(item_desc.flags() ^ Qt.ItemIsEditable)
            table.setItem(row_idx, 1, item_desc)
            
            item_cy = QTableWidgetItem(cy_val)
            item_cy.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_cy.setFlags(item_cy.flags() ^ Qt.ItemIsEditable)
            table.setItem(row_idx, 2, item_cy)
            
            item_py = QTableWidgetItem(py_val)
            item_py.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_py.setFlags(item_py.flags() ^ Qt.ItemIsEditable)
            table.setItem(row_idx, 3, item_py)
            
        layout.addWidget(table)
        
        # Reason details
        if ratio.reason_final:
            reason_lbl = QLabel(f"<b>Variance Driver Analysis:</b><br>{ratio.reason_final}")
            reason_lbl.setWordWrap(True)
            reason_lbl.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 8px; border-radius: 4px;")
            layout.addWidget(reason_lbl)
            
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
