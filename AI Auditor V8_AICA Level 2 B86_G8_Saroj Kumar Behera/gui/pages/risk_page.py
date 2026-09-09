"""
AI Auditor V8 - Risk Areas & Red Flag Detection Page
Displays potential risk and attention areas with severity badges, descriptions, and audit implications.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt
from core.models import FinancialModel

class RiskPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: FinancialModel = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        lbl_title = QLabel("Potential Risk & Attention Areas")
        lbl_title.setProperty("class", "page-title")
        lbl_sub = QLabel("Automated screening for financial distress indicators, solvency risks, and operational anomalies.")
        lbl_sub.setProperty("class", "page-subtitle")
        main_layout.addWidget(lbl_title)
        main_layout.addWidget(lbl_sub)

        # Scroll Area for Risk Cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_layout.setSpacing(12)
        self.scroll.setWidget(self.container)

        main_layout.addWidget(self.scroll)

    def load_model(self, model: FinancialModel):
        self.model = model
        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not model.risks:
            lbl_empty = QLabel("No critical financial risks or red flags detected for the analyzed period.")
            lbl_empty.setStyleSheet("color: #64748B; font-size: 13px; font-style: italic;")
            self.cards_layout.addWidget(lbl_empty)
            return

        for r in model.risks:
            card = self._build_risk_card(r)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _build_risk_card(self, r: dict) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        
        # Border color based on severity
        border_color = "#EF4444" if r["severity"] == "High" else "#F59E0B"
        card.setStyleSheet(f"QFrame.card {{ border-left: 4px solid {border_color}; }}")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Top line: Title + Severity Tag
        top_row = QHBoxLayout()
        lbl_title = QLabel(f"{r['title']}")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F172A;")
        top_row.addWidget(lbl_title)
        top_row.addStretch()

        lbl_sev = QLabel(f" {r['severity'].upper()} RISK ")
        if r["severity"] == "High":
            lbl_sev.setStyleSheet("background-color: #FEE2E2; color: #991B1B; font-size: 11px; font-weight: bold; border-radius: 4px; padding: 2px 8px;")
        else:
            lbl_sev.setStyleSheet("background-color: #FEF08A; color: #854D0E; font-size: 11px; font-weight: bold; border-radius: 4px; padding: 2px 8px;")
        top_row.addWidget(lbl_sev)
        layout.addLayout(top_row)

        # Category
        lbl_cat = QLabel(f"Category: {r['category']}")
        lbl_cat.setStyleSheet("color: #64748B; font-size: 11.5px;")
        layout.addWidget(lbl_cat)

        # Description
        lbl_desc = QLabel(f"<b>Finding:</b> {r['description']}")
        lbl_desc.setStyleSheet("color: #334155; font-size: 12.5px;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        # Audit Implication
        lbl_imp = QLabel(f"<b>Audit & Practical Implication:</b> {r['audit_implication']}")
        lbl_imp.setStyleSheet("color: #1E293B; font-size: 12px; background-color: #F8FAFC; border-radius: 4px; padding: 6px 10px;")
        lbl_imp.setWordWrap(True)
        layout.addWidget(lbl_imp)

        return card
