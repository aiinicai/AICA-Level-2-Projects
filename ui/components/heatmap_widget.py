"""
LexSecure India Pro - Department Accountability Heatmap Component
Visualizes department-level compliance velocity, task completion, and audit readiness
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from ui.styles import THEME_COLORS

class DepartmentHeatmapWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel("DEPARTMENT ACCOUNTABILITY & STATUTORY VELOCITY HEATMAP")
        title.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: bold; letter-spacing: 0.6px;")
        header_layout.addWidget(title)

        live_tag = QLabel("REAL-TIME STATUTORY TRACKING")
        live_tag.setStyleSheet("background-color: #0F766E; color: #5EEAD4; font-size: 10px; font-weight: bold; padding: 3px 8px; border-radius: 4px;")
        header_layout.addWidget(live_tag, 0, Qt.AlignmentFlag.AlignRight)
        self.layout.addLayout(header_layout)

        # Department metrics
        self.dept_bars = {}
        departments = [
            ("LEGAL", "Statutory Filings, MSME Review & Playbooks", 88, "#10B981"),
            ("HR_LABOUR", "Code on Wages Harmonization, PoSH & EPF/ESI", 76, "#0D9488"),
            ("FINANCE_TAX", "Section 43B(h) MSMED & FEMA Form 15CA/15CB", 64, "#F59E0B"),
            ("INFOSEC_TECH", "DPDP Act Rules & 6-Hour CERT-In Telemetry", 82, "#06B6D4"),
            ("OPERATIONS", "Vendor SOW Audits & OSH Code Compliance", 91, "#10B981")
        ]

        for dept_key, subtitle, percentage, color in departments:
            row_layout = QVBoxLayout()
            row_layout.setSpacing(4)

            top_row = QHBoxLayout()
            name_lbl = QLabel(f"<b>{dept_key.replace('_', ' / ')}</b> — <span style='color: #94A3B8; font-size: 11px;'>{subtitle}</span>")
            name_lbl.setTextFormat(Qt.TextFormat.RichText)
            name_lbl.setWordWrap(True)
            name_lbl.setStyleSheet("color: #F8FAFC; font-size: 12px;")
            top_row.addWidget(name_lbl, 1)

            pct_lbl = QLabel(f"<b>{percentage}%</b> Compliant")
            pct_lbl.setTextFormat(Qt.TextFormat.RichText)
            pct_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            top_row.addWidget(pct_lbl, 0, Qt.AlignmentFlag.AlignRight)
            row_layout.addLayout(top_row)

            pbar = QProgressBar()
            pbar.setFixedHeight(8)
            pbar.setTextVisible(False)
            pbar.setValue(percentage)
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #0B1120;
                    border: none;
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 4px;
                }}
            """)
            row_layout.addWidget(pbar)
            self.dept_bars[dept_key] = (pbar, pct_lbl)

            self.layout.addLayout(row_layout)
