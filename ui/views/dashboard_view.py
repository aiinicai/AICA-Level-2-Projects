"""
LexSecure India Pro - Executive Command Center (Dashboard)
Clean, compact layout optimized to fit screen width without horizontal scrolling
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from datetime import datetime
from ui.styles import THEME_COLORS
from ui.components.stat_card import StatCard
from ui.components.heatmap_widget import DepartmentHeatmapWidget
from models.entities import RegulatoryUpdate, StatutoryCalendarEvent

class DashboardView(QWidget):
    # Navigation signals
    navigate_to_review = pyqtSignal()
    navigate_to_regulatory = pyqtSignal()
    navigate_to_calendar = pyqtSignal()

    def __init__(self, current_entity_id: int = 1):
        super().__init__()
        self.current_entity_id = current_entity_id
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Scroll area with strictly NO horizontal scrolling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(container)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 8, 0)

        # 1. Clean Executive Header Banner
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0F172A, stop:1 #1E293B);
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 12px 16px;
        """)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setSpacing(12)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        h_title = QLabel("EXECUTIVE COMMAND CENTER — STATUTORY SURVEILLANCE")
        h_title.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 800; letter-spacing: 0.5px;")
        title_box.addWidget(h_title)

        h_sub = QLabel("Pan-India Compliance Surveillance • FEMA 1999 • DPDP Act 2023 • 4 Labour Codes • Section 43B(h)")
        h_sub.setWordWrap(True)
        h_sub.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 500;")
        title_box.addWidget(h_sub)
        h_layout.addLayout(title_box, 1)

        # Quick Actions
        actions_box = QHBoxLayout()
        actions_box.setSpacing(8)
        quick_review_btn = QPushButton("📄 Review Documents")
        quick_review_btn.setProperty("class", "btn-primary")
        quick_review_btn.clicked.connect(self.navigate_to_review.emit)
        actions_box.addWidget(quick_review_btn)

        quick_reg_btn = QPushButton("📡 Regulatory Circulars")
        quick_reg_btn.setProperty("class", "btn-outline")
        quick_reg_btn.clicked.connect(self.navigate_to_regulatory.emit)
        actions_box.addWidget(quick_reg_btn)

        h_layout.addLayout(actions_box)
        layout.addWidget(header_frame)

        # 2. 4 Executive KPI Cards in a neat responsive grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)

        self.card_health = StatCard(
            title="Legal Health Score",
            value="84%",
            subtext="Calculated across active contracts",
            badge_text="SAFE TIER",
            badge_color=THEME_COLORS["emerald"]
        )
        self.card_liability = StatCard(
            title="Liability Exposure",
            value="4 Flags",
            subtext="Non-competes (Sec 27) & indemnities",
            badge_text="ACTION REQUIRED",
            badge_color=THEME_COLORS["risk_high"]
        )
        self.card_deadlines = StatCard(
            title="Statutory Deadlines",
            value="2 Due Soon",
            subtext="MCA AOC-4 & PoSH Annual Filing",
            badge_text="12 DAYS LEFT",
            badge_color=THEME_COLORS["risk_caution"]
        )
        self.card_fema = StatCard(
            title="Labour & FEMA Index",
            value="92%",
            subtext="4 Labour Codes • ECB limits aligned",
            badge_text="OPTIMAL",
            badge_color=THEME_COLORS["teal_primary"]
        )

        for card in [self.card_health, self.card_liability, self.card_deadlines, self.card_fema]:
            card.setMinimumWidth(0)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        kpi_grid.addWidget(self.card_health, 0, 0)
        kpi_grid.addWidget(self.card_liability, 0, 1)
        kpi_grid.addWidget(self.card_deadlines, 0, 2)
        kpi_grid.addWidget(self.card_fema, 0, 3)
        layout.addLayout(kpi_grid)

        # 3. Department Accountability Heatmap
        self.heatmap = DepartmentHeatmapWidget()
        self.heatmap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.heatmap)

        # 4. Bottom Grid: Live Indian Regulatory Watchlist + Upcoming Deadlines
        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(12)

        # Left Card: Live Indian Regulatory Watchlist
        reg_card = QFrame()
        reg_card.setStyleSheet(f"""
            background-color: {THEME_COLORS['bg_card']};
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 10px;
            padding: 14px;
        """)
        reg_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        reg_layout = QVBoxLayout(reg_card)
        reg_layout.setSpacing(8)

        reg_header = QHBoxLayout()
        reg_title = QLabel("LIVE STATUTORY REGULATORY WATCHLIST")
        reg_title.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: bold;")
        reg_header.addWidget(reg_title)

        see_all_btn = QPushButton("View Feed →")
        see_all_btn.setStyleSheet("color: #38BDF8; background: transparent; border: none; font-size: 11px; font-weight: bold;")
        see_all_btn.clicked.connect(self.navigate_to_regulatory.emit)
        reg_header.addWidget(see_all_btn, 0, Qt.AlignmentFlag.AlignRight)
        reg_layout.addLayout(reg_header)

        # Ingested circulars (Compact presentation)
        circulars = RegulatoryUpdate.get_all()[:3]
        for c in circulars:
            item_box = QFrame()
            item_box.setStyleSheet("background-color: #0B1120; border-radius: 6px; padding: 8px 10px; border: 1px solid #1E293B;")
            item_layout = QVBoxLayout(item_box)
            item_layout.setSpacing(3)

            top_item = QHBoxLayout()
            sev_color = THEME_COLORS["risk_high"] if c.severity == "CRITICAL" else THEME_COLORS["risk_caution"]
            sev_badge = QLabel(f" {c.severity} ")
            sev_badge.setStyleSheet(f"background-color: {sev_color}; color: white; font-size: 9px; font-weight: bold; border-radius: 3px;")
            top_item.addWidget(sev_badge)

            body_lbl = QLabel(f"<b>{c.statutory_body}</b> • {c.official_date}")
            body_lbl.setTextFormat(Qt.TextFormat.RichText)
            body_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
            top_item.addWidget(body_lbl)
            top_item.addStretch()
            item_layout.addLayout(top_item)

            c_title = QLabel(c.title)
            c_title.setWordWrap(True)
            c_title.setStyleSheet("color: #F8FAFC; font-size: 11.5px; font-weight: 600;")
            item_layout.addWidget(c_title)

            reg_layout.addWidget(item_box)

        bottom_grid.addWidget(reg_card, 0, 0)

        # Right Card: Upcoming Statutory Deadlines
        cal_card = QFrame()
        cal_card.setStyleSheet(f"""
            background-color: {THEME_COLORS['bg_card']};
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 10px;
            padding: 14px;
        """)
        cal_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        cal_layout = QVBoxLayout(cal_card)
        cal_layout.setSpacing(8)

        cal_header = QHBoxLayout()
        cal_title = QLabel("UPCOMING STATUTORY DEADLINES")
        cal_title.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: bold;")
        cal_header.addWidget(cal_title)

        cal_all_btn = QPushButton("Open Calendar →")
        cal_all_btn.setStyleSheet("color: #10B981; background: transparent; border: none; font-size: 11px; font-weight: bold;")
        cal_all_btn.clicked.connect(self.navigate_to_calendar.emit)
        cal_header.addWidget(cal_all_btn, 0, Qt.AlignmentFlag.AlignRight)
        cal_layout.addLayout(cal_header)

        events = StatutoryCalendarEvent.get_by_entity(self.current_entity_id)[:3]
        now = datetime.now().date()
        for ev in events:
            ev_box = QFrame()
            ev_box.setStyleSheet("background-color: #0B1120; border-radius: 6px; padding: 8px 10px; border: 1px solid #1E293B;")
            ev_layout = QVBoxLayout(ev_box)
            ev_layout.setSpacing(3)

            ev_top = QHBoxLayout()
            ev_name = QLabel(f"<b>{ev.compliance_name}</b>")
            ev_name.setTextFormat(Qt.TextFormat.RichText)
            ev_name.setWordWrap(True)
            ev_name.setStyleSheet("color: #F8FAFC; font-size: 11.5px;")
            ev_top.addWidget(ev_name, 1)

            try:
                due = datetime.strptime(ev.due_date, "%Y-%m-%d").date()
                days_left = (due - now).days
                if days_left < 0:
                    badge_style = "background-color: #EF4444; color: white;"
                    countdown_text = "OVERDUE"
                elif days_left <= 15:
                    badge_style = "background-color: #F59E0B; color: black;"
                    countdown_text = f"{days_left}d LEFT"
                else:
                    badge_style = "background-color: #10B981; color: white;"
                    countdown_text = f"{days_left}d LEFT"
            except Exception:
                badge_style = "background-color: #0D9488; color: white;"
                countdown_text = ev.due_date

            c_tag = QLabel(f" {countdown_text} ")
            c_tag.setStyleSheet(f"{badge_style} font-size: 9px; font-weight: bold; border-radius: 3px; padding: 2px 5px;")
            ev_top.addWidget(c_tag, 0, Qt.AlignmentFlag.AlignRight)
            ev_layout.addLayout(ev_top)

            ev_penalty = QLabel(f"<span style='color: #EF4444;'>Penalty:</span> {ev.penalty_clause}")
            ev_penalty.setTextFormat(Qt.TextFormat.RichText)
            ev_penalty.setWordWrap(True)
            ev_penalty.setStyleSheet("color: #94A3B8; font-size: 10.5px;")
            ev_layout.addWidget(ev_penalty)

            cal_layout.addWidget(ev_box)

        bottom_grid.addWidget(cal_card, 0, 1)
        layout.addLayout(bottom_grid)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def set_active_entity(self, entity_id: int):
        self.current_entity_id = entity_id
