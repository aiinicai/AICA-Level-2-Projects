from datetime import date, timedelta
from html import escape
import json

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPointF, Qt, Signal, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QTabWidget, QTableView, QTableWidget, QTextBrowser, QVBoxLayout, QWidget
)

from app.knowledge.explanations import get_event_deep_explanation
from app.knowledge.library import article_for
from app.services.gemini import format_ai_analysis_html, get_cached_analysis, get_gemini_api_key
from app.services.validation import safe_url
from app.utils.time import display_time, local_date, stamp


def label(text, name=None):
    item = QLabel(text)
    if name:
        item.setObjectName(name)
    return item


def html_page(content, theme="Dark Navy"):
    is_dark = str(theme).lower() not in ("clean light", "light", "white")
    if is_dark:
        style = """
        body {
            color: #E2E8F0;
            background-color: transparent;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            font-size: 12px;
            line-height: 1.5;
            margin: 0;
            padding: 4px;
        }
        h1, h2, h4 {
            color: #FFFFFF;
            font-weight: 700;
            margin-top: 18px;
            margin-bottom: 8px;
        }
        h2 {
            font-size: 18px;
            letter-spacing: 0.2px;
        }
        h3 {
            font-size: 11px;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 700;
            margin-top: 20px;
            margin-bottom: 8px;
            border-bottom: 1px solid #1E2E48;
            padding-bottom: 4px;
        }
        p {
            margin: 6px 0;
        }
        a {
            color: #38BDF8;
            text-decoration: none;
            font-weight: 500;
        }
        a:hover {
            color: #7DD3FC;
            text-decoration: underline;
        }
        .card {
            background: #0D1C33;
            border: 1px solid #1E3558;
            border-radius: 8px;
            padding: 12px 14px;
            margin: 10px 0;
            color: #E2E8F0;
        }
        .stat-grid {
            display: table;
            width: 100%;
            margin: 10px 0;
        }
        .stat-col {
            display: table-cell;
            width: 33.33%;
            background: #091528;
            border: 1px solid #172D4D;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
            vertical-align: middle;
        }
        .stat-label {
            font-size: 10px;
            color: #94A3B8;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .stat-value {
            font-size: 20px;
            font-weight: 800;
            color: #FFFFFF;
        }
        .stat-value-beat {
            font-size: 20px;
            font-weight: 800;
            color: #34D399;
        }
        .stat-value-miss {
            font-size: 20px;
            font-weight: 800;
            color: #F87171;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-right: 4px;
        }
        .badge-sample {
            background: #3B2D14;
            color: #FBBF24;
            border: 1px solid #78350F;
        }
        .badge-source {
            background: #064E3B;
            color: #34D399;
            border: 1px solid #047857;
        }
        .badge-high {
            background: #450A0A;
            color: #F87171;
            border: 1px solid #991B1B;
        }
        .badge-med {
            background: #451A03;
            color: #FBBF24;
            border: 1px solid #B45309;
        }
        .badge-low {
            background: #172554;
            color: #60A5FA;
            border: 1px solid #1E40AF;
        }
        .badge-status {
            background: #1E293B;
            color: #94A3B8;
            border: 1px solid #334155;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 8px 0;
        }
        .data-table th {
            background: #0A162B;
            color: #94A3B8;
            font-size: 10px;
            text-transform: uppercase;
            font-weight: 700;
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #1C3355;
        }
        .data-table td {
            padding: 8px;
            border-bottom: 1px solid #13243B;
            color: #E2E8F0;
        }
        .data-table td.label {
            color: #94A3B8;
            width: 140px;
            font-weight: 500;
        }
        .muted {
            color: #94A3B8;
            font-size: 11px;
        }
        .btn-link {
            display: inline-block;
            background: #102647;
            color: #38BDF8;
            border: 1px solid #1E3A63;
            padding: 5px 10px;
            border-radius: 4px;
            margin-top: 4px;
            font-size: 11px;
        }
        .concept-card {
            background: #09192F;
            border-left: 3px solid #38BDF8;
            border-radius: 4px;
            padding: 10px 14px;
            margin: 8px 0;
            color: #E2E8F0;
        }
        .impact-grid {
            display: table;
            width: 100%;
            margin: 8px 0;
            border-collapse: separate;
            border-spacing: 6px;
        }
        .impact-row {
            display: table-row;
        }
        .impact-cell {
            display: table-cell;
            width: 50%;
            background: #0B1728;
            border: 1px solid #1E3558;
            border-radius: 6px;
            padding: 10px 12px;
            vertical-align: top;
        }
        .impact-title {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
            color: #38BDF8;
        }
        .impact-desc {
            font-size: 11px;
            line-height: 1.45;
            color: #CBD5E1;
        }
        .playbook-card {
            background: #111D33;
            border: 1px dashed #2A4365;
            border-radius: 6px;
            padding: 10px 12px;
            margin: 8px 0;
            color: #F1F5F9;
        }
        """
    else:
        style = """
        body {
            color: #0A192F;
            background-color: transparent;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            font-size: 12px;
            line-height: 1.5;
            margin: 0;
            padding: 4px;
        }
        h1, h2, h4 {
            color: #0A192F;
            font-weight: 700;
            margin-top: 18px;
            margin-bottom: 8px;
        }
        h2 {
            font-size: 18px;
            letter-spacing: 0.2px;
        }
        h3 {
            font-size: 11px;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 700;
            margin-top: 20px;
            margin-bottom: 8px;
            border-bottom: 1px solid #CBD5E1;
            padding-bottom: 4px;
        }
        p {
            margin: 6px 0;
        }
        a {
            color: #1D4ED8;
            text-decoration: none;
            font-weight: 600;
        }
        a:hover {
            color: #2563EB;
            text-decoration: underline;
        }
        .card {
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            padding: 12px 14px;
            margin: 10px 0;
            color: #0A192F;
        }
        .stat-grid {
            display: table;
            width: 100%;
            margin: 10px 0;
        }
        .stat-col {
            display: table-cell;
            width: 33.33%;
            background: #F8FAFC;
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
            vertical-align: middle;
        }
        .stat-label {
            font-size: 10px;
            color: #64748B;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .stat-value {
            font-size: 20px;
            font-weight: 800;
            color: #0A192F;
        }
        .stat-value-beat {
            font-size: 20px;
            font-weight: 800;
            color: #059669;
        }
        .stat-value-miss {
            font-size: 20px;
            font-weight: 800;
            color: #DC2626;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-right: 4px;
        }
        .badge-sample {
            background: #FEF3C7;
            color: #B45309;
            border: 1px solid #FCD34D;
        }
        .badge-source {
            background: #DCFCE7;
            color: #15803D;
            border: 1px solid #86EFAC;
        }
        .badge-high {
            background: #FEE2E2;
            color: #DC2626;
            border: 1px solid #FCA5A5;
        }
        .badge-med {
            background: #FEF3C7;
            color: #D97706;
            border: 1px solid #FCD34D;
        }
        .badge-low {
            background: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
        }
        .badge-status {
            background: #F1F5F9;
            color: #475569;
            border: 1px solid #CBD5E1;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 8px 0;
        }
        .data-table th {
            background: #F1F5F9;
            color: #0A192F;
            font-size: 10px;
            text-transform: uppercase;
            font-weight: 700;
            padding: 8px;
            text-align: left;
            border-bottom: 2px solid #CBD5E1;
        }
        .data-table td {
            padding: 8px;
            border-bottom: 1px solid #E2E8F0;
            color: #0A192F;
        }
        .data-table td.label {
            color: #64748B;
            width: 140px;
            font-weight: 600;
        }
        .muted {
            color: #64748B;
            font-size: 11px;
        }
        .btn-link {
            display: inline-block;
            background: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
            padding: 5px 10px;
            border-radius: 4px;
            margin-top: 4px;
            font-size: 11px;
            font-weight: 600;
        }
        .concept-card {
            background: #F0F9FF;
            border-left: 3px solid #0284C7;
            border-radius: 4px;
            padding: 10px 14px;
            margin: 8px 0;
            color: #0A192F;
        }
        .impact-grid {
            display: table;
            width: 100%;
            margin: 8px 0;
            border-collapse: separate;
            border-spacing: 6px;
        }
        .impact-row {
            display: table-row;
        }
        .impact-cell {
            display: table-cell;
            width: 50%;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 10px 12px;
            vertical-align: top;
        }
        .impact-title {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
            color: #1D4ED8;
        }
        .impact-desc {
            font-size: 11px;
            line-height: 1.45;
            color: #334155;
        }
        .playbook-card {
            background: #F8FAFC;
            border: 1px dashed #CBD5E1;
            border-radius: 6px;
            padding: 10px 12px;
            margin: 8px 0;
            color: #0F172A;
        }
        """

    return f"""<!DOCTYPE html>
<html>
<head>
<style>
{style}
</style>
</head>
<body>
{content}
</body>
</html>"""


def browser(action_handler=None):
    view = QTextBrowser()
    view.setOpenExternalLinks(False)
    def open_url(url):
        url_str = url.toString()
        if url_str.startswith("action:") and action_handler:
            action_handler(url_str.replace("action:", ""))
            return
        try:
            QDesktopServices.openUrl(QUrl(safe_url(url_str)))
        except ValueError:
            pass
    view.anchorClicked.connect(open_url)
    return view


class EventTableModel(QAbstractTableModel):
    HEADERS = ["TIME / DATE", "EVENT", "REGION / ISSUER", "TYPE", "PRIOR", "CONSENSUS", "ACTUAL", "IMPORTANCE", "STATUS", "DATA"]

    def __init__(self, zone="Asia/Kolkata", theme="Dark Navy"):
        super().__init__()
        self.events = []
        self.zone = zone
        self.theme = theme

    def set_theme(self, theme):
        self.theme = theme
        self.layoutChanged.emit()

    def set_events(self, events, zone):
        self.beginResetModel()
        self.events, self.zone = events, zone
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.events)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        e = self.events[index.row()]
        primary_time = e.get("scheduled_at") or e.get("published_at") or e.get("effective_at") or e.get("deadline_at") or e.get("record_date") or e.get("ex_date")
        values = [
            display_time(primary_time, self.zone),
            e["title"],
            e.get("company") or e.get("country") or e.get("authority"),
            e["kind"],
            e.get("previous"),
            e.get("forecast"),
            e.get("actual"),
            e["importance"],
            e["status"],
            "SAMPLE" if e["sample"] else "SOURCE"
        ]
        if role == Qt.DisplayRole:
            value = values[index.column()]
            if index.column() == 1 and e["sample"]:
                return "SAMPLE · " + str(value)
            return "—" if value is None else str(value)
        if role == Qt.ToolTipRole:
            return ("SYNTHETIC SAMPLE · not live data\n" if e["sample"] else "") + str(values[index.column()] if values[index.column()] is not None else "Unavailable: not supplied by source")
        
        is_dark = str(self.theme).lower() not in ("clean light", "light", "white")
        if role == Qt.ForegroundRole:
            if index.column() == 1:
                return QColor("#FFFFFF") if is_dark else QColor("#0A192F")
            if index.column() == 9:
                return QColor("#FBBF24" if e["sample"] else ("#34D399" if is_dark else "#059669"))
            if index.column() == 7:
                if is_dark:
                    return QColor({"High": "#F87171", "Medium": "#FBBF24", "Low": "#60A5FA", "Unknown": "#94A3B8"}[e["importance"]])
                else:
                    return QColor({"High": "#DC2626", "Medium": "#D97706", "Low": "#1D4ED8", "Unknown": "#64748B"}[e["importance"]])
            if index.column() == 8:
                if is_dark:
                    return QColor("#34D399" if e["status"] == "Published" else "#FBBF24")
                else:
                    return QColor("#059669" if e["status"] == "Published" else "#D97706")
            if index.column() == 6 and e.get("actual") is not None and e.get("forecast") is not None:
                try:
                    act, fct = float(e["actual"]), float(e["forecast"])
                    if is_dark:
                        return QColor("#34D399" if act >= fct else "#F87171")
                    else:
                        return QColor("#059669" if act >= fct else "#DC2626")
                except ValueError:
                    pass
            if index.column() in (0, 2, 3, 4, 5):
                return QColor("#CBD5E1") if is_dark else QColor("#334155")
        if role == Qt.TextAlignmentRole and index.column() in (4, 5, 6):
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def sort(self, column, order=Qt.AscendingOrder):
        keys = ["scheduled_at", "title", "company", "kind", "previous", "forecast", "actual", "importance", "status", "sample"]
        def key(event):
            if column == 0:
                return event.get("scheduled_at") or event.get("published_at") or event.get("effective_at") or event.get("deadline_at") or event.get("record_date") or event.get("ex_date") or ""
            value = event.get(keys[column])
            if column in (4, 5, 6):
                try:
                    return (0, float(value)) if value is not None else (2, 0)
                except ValueError:
                    return (1, str(value))
            return str(value or "").casefold()
        self.layoutAboutToBeChanged.emit()
        self.events.sort(key=key, reverse=order == Qt.DescendingOrder)
        self.layoutChanged.emit()


def event_table(model):
    table = QTableView()
    table.setModel(model)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(40)
    table.setSortingEnabled(True)
    for col, width in enumerate((185, 300, 150, 95, 75, 95, 75, 95, 100, 80)):
        table.setColumnWidth(col, width)
    table.horizontalHeader().setStretchLastSection(False)
    return table


class LiveSignalBeacon(QWidget):
    clicked = Signal()

    def __init__(self, is_live=False, theme="Dark Navy", parent=None):
        super().__init__(parent)
        self.is_live = is_live
        self.theme = theme
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 8, 2)
        layout.setSpacing(6)

        self.dot = QLabel("●")
        self.text = QLabel("LIVE STREAMING" if is_live else "OFFLINE / SAMPLE")
        self.text.setObjectName("beaconLive" if is_live else "beaconOffline")
        layout.addWidget(self.dot)
        layout.addWidget(self.text)
        self.update_state(is_live)

    def set_live(self, is_live: bool):
        self.is_live = is_live
        self.update_state(is_live)

    def update_state(self, is_live: bool):
        if is_live:
            self.dot.setStyleSheet("font-size: 15px; color: #10B981;")
            self.text.setText("LIVE STREAMING")
            self.text.setObjectName("beaconLive")
            self.setToolTip("● Live Data Connected\nOfficial Feeds (NSE/SEBI/RBI) & Finnhub Active\n1-second background sync heartbeat\nClick to view source status.")
        else:
            self.dot.setStyleSheet("font-size: 15px; color: #EF4444;")
            self.text.setText("OFFLINE / SAMPLE")
            self.text.setObjectName("beaconOffline")
            self.setToolTip("● Offline / Sample Workspace\nClick to configure or enable live data feeds.")
        self.text.style().unpolish(self.text)
        self.text.style().polish(self.text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class LiveSecondsClock(QWidget):
    def __init__(self, zone="Asia/Kolkata", theme="Dark Navy", parent=None):
        super().__init__(parent)
        self.zone = zone
        self.theme = theme
        self.seconds_left = 5

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.clock_label = QLabel()
        self.clock_label.setObjectName("realtimeClock")
        self.sync_badge = QLabel("Sync: 5s")
        self.sync_badge.setObjectName("syncCountdown")
        layout.addWidget(self.clock_label)
        layout.addWidget(self.sync_badge)

        from PySide6.QtCore import QTimer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.tick()

    def set_zone(self, zone):
        self.zone = zone
        self.tick()

    def set_sync_countdown(self, seconds_left):
        self.seconds_left = max(0, seconds_left)
        if self.seconds_left == 0:
            self.sync_badge.setText("⚡ Syncing…")
            self.sync_badge.setStyleSheet("color: #10B981; font-weight: 700; background: #064E3B; border: 1px solid #059669; border-radius: 6px; padding: 4px 8px;")
        else:
            self.sync_badge.setText(f"Sync: {self.seconds_left}s")
            self.sync_badge.setStyleSheet("")

    def tick(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        try:
            now = datetime.now(ZoneInfo(self.zone))
        except Exception:
            now = datetime.now(ZoneInfo("Asia/Kolkata"))
        tz_short = self.zone.split("/")[-1].replace("_", " ")
        self.clock_label.setText(now.strftime("%I:%M:%S %p") + f"  {tz_short}")


class CalendarGrid(QTableWidget):
    event_selected = Signal(str)
    day_selected = Signal(object)

    def __init__(self, theme="Dark Navy"):
        super().__init__()
        self.theme = theme
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.horizontalHeader().setDefaultSectionSize(120)
        self.verticalHeader().hide()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(True)

    def set_theme(self, theme):
        self.theme = theme

    def populate(self, events, anchor, mode, zone, basis="calendar"):
        first = anchor.replace(day=1) if mode == "Month" else anchor
        first -= timedelta(days=first.weekday())
        rows = 6 if mode == "Month" else 1
        self.clearContents()
        self.setRowCount(rows)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        today = date.fromisoformat(local_date(stamp(), zone))
        anchor_month = anchor.month if mode == "Month" else None
        
        by_day = {}
        for e in events:
            if basis == "all milestones":
                fields = ["scheduled_at", "published_at", "effective_at", "deadline_at", "record_date", "ex_date"]
            elif basis != "calendar":
                fields = [basis]
            else:
                fields = [next((k for k in ("scheduled_at", "published_at", "effective_at", "deadline_at", "record_date", "ex_date") if e.get(k)), "scheduled_at")]
            for field in fields:
                day_str = local_date(e.get(field), zone)
                if day_str:
                    by_day.setdefault(day_str, []).append((e, field))
        
        is_dark = str(self.theme).lower() not in ("clean light", "light", "white")

        for index in range(rows * 7):
            day = first + timedelta(days=index)
            day_events = sorted(by_day.get(day.isoformat(), []), key=lambda pair: pair[0].get(pair[1]) or "")
            
            cell = QFrame()
            cell.setObjectName("dayCell")
            cell.setCursor(Qt.PointingHandCursor)
            layout = QVBoxLayout(cell)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(2)
            
            # --- Header Row: Date & Event Count Pill ---
            header_row = QHBoxLayout()
            header_row.setContentsMargins(0, 0, 0, 0)
            header_row.setSpacing(4)
            
            day_text = day.strftime("%d %b") if day.day == 1 else day.strftime("%d")
            day_num_lbl = QLabel(day_text)
            
            is_in_active_month = (anchor_month is None) or (day.month == anchor_month)
            
            if day == today:
                day_num_lbl.setStyleSheet("background: #2563EB; color: #FFFFFF; font-weight: 800; font-size: 11px; border-radius: 9px; padding: 1px 6px;")
            elif is_in_active_month:
                day_num_lbl.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 12px;" if is_dark else "color: #0A192F; font-weight: 700; font-size: 12px;")
            else:
                day_num_lbl.setStyleSheet("color: #475569; font-weight: 500; font-size: 11px;" if is_dark else "color: #94A3B8; font-weight: 500; font-size: 11px;")
                    
            header_row.addWidget(day_num_lbl)
            header_row.addStretch()
            
            if day_events:
                cnt_lbl = QLabel(f"● {len(day_events):,}")
                cnt_lbl.setStyleSheet(
                    "color: #38BDF8; font-size: 10px; font-weight: 700; background: #0E223D; border-radius: 5px; padding: 1px 5px;"
                    if is_dark else
                    "color: #1D4ED8; font-size: 10px; font-weight: 700; background: #DBEAFE; border-radius: 5px; padding: 1px 5px;"
                )
                header_row.addWidget(cnt_lbl)
                
            layout.addLayout(header_row)

            # --- Sleek Single-Line Event Chips (No Text Wrap, Clean 2026 Layout) ---
            for event, field in day_events[:2]:
                pill = QPushButton()
                pill.setCursor(Qt.PointingHandCursor)
                kind = event.get("kind", "Economic")
                dot_color = {"Economic": "#38BDF8", "Corporate": "#34D399", "Regulatory": "#FBBF24"}.get(kind, "#60A5FA")
                
                title = event.get("title", "")
                if len(title) > 22:
                    title = title[:20] + "…"
                pill.setText(f" {title}")
                pill.setToolTip(f"{event.get('title')}\nType: {kind}\nAuthority: {event.get('authority', 'N/A')}\nTime: {display_time(event.get(field), zone)}")
                
                pill_bg = "#0B1A2F" if is_dark else "#F1F5F9"
                pill_border = "#162D4A" if is_dark else "#CBD5E1"
                pill_text = "#E2E8F0" if is_dark else "#0A192F"
                pill.setStyleSheet(f"""
                    QPushButton {{
                        background: {pill_bg};
                        border: 1px solid {pill_border};
                        border-left: 3px solid {dot_color};
                        border-radius: 3px;
                        color: {pill_text};
                        font-size: 10px;
                        font-weight: 600;
                        text-align: left;
                        padding: 1px 4px;
                        max-height: 18px;
                    }}
                    QPushButton:hover {{
                        background: #1E3A8A;
                        border-color: #3B82F6;
                        color: #FFFFFF;
                    }}
                """)
                ev_id = event["id"]
                pill.clicked.connect(lambda checked=False, eid=ev_id: self.event_selected.emit(eid))
                layout.addWidget(pill)

            if len(day_events) > 2:
                more_btn = QPushButton(f"+{len(day_events) - 2} more…")
                more_btn.setCursor(Qt.PointingHandCursor)
                more_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: 0;
                        color: {"#38BDF8" if is_dark else "#2563EB"};
                        font-size: 10px;
                        font-weight: 700;
                        text-align: left;
                        padding: 0 4px;
                        max-height: 16px;
                    }}
                    QPushButton:hover {{
                        color: #60A5FA;
                        text-decoration: underline;
                    }}
                """)
                cur_day = day
                more_btn.clicked.connect(lambda checked=False, d=cur_day: self.day_selected.emit(d))
                layout.addWidget(more_btn)

            layout.addStretch()

            def make_cell_click(d):
                return lambda ev: self.day_selected.emit(d)

            cell.mousePressEvent = make_cell_click(day)
            self.setCellWidget(index // 7, index % 7, cell)


class CalendarViewContainer(QWidget):
    event_selected = Signal(str)
    day_selected = Signal(object)
    prev_month_clicked = Signal()
    next_month_clicked = Signal()
    today_clicked = Signal()

    def __init__(self, theme="Dark Navy"):
        super().__init__()
        self.theme = theme
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Dedicated Month Navigation Bar
        self.header_bar = QFrame()
        self.header_bar.setObjectName("card")
        bar_layout = QHBoxLayout(self.header_bar)
        bar_layout.setContentsMargins(10, 6, 10, 6)
        bar_layout.setSpacing(8)

        self.btn_prev = QPushButton("◀ Prev Month")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(self.prev_month_clicked)
        bar_layout.addWidget(self.btn_prev)

        self.btn_today = QPushButton("Today")
        self.btn_today.setCursor(Qt.PointingHandCursor)
        self.btn_today.clicked.connect(self.today_clicked)
        bar_layout.addWidget(self.btn_today)

        self.btn_next = QPushButton("Next Month ▶")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self.next_month_clicked)
        bar_layout.addWidget(self.btn_next)

        bar_layout.addStretch()

        self.month_title = QLabel("📅  NOVEMBER 2026")
        self.month_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #38BDF8; letter-spacing: 0.5px;")
        bar_layout.addWidget(self.month_title)

        bar_layout.addStretch()

        self.badge = QLabel("● 0 Events")
        self.badge.setStyleSheet("font-size: 11px; font-weight: 700; color: #93C5FD; background: #1E3A8A; padding: 3px 8px; border-radius: 6px;")
        bar_layout.addWidget(self.badge)

        layout.addWidget(self.header_bar)

        self.grid = CalendarGrid(theme)
        self.grid.event_selected.connect(self.event_selected)
        self.grid.day_selected.connect(self.day_selected)
        layout.addWidget(self.grid, 1)

    def set_theme(self, theme):
        self.theme = theme
        self.grid.set_theme(theme)

    def update_header(self, anchor_date, count: int = 0):
        if hasattr(anchor_date, "strftime"):
            month_str = anchor_date.strftime("%B %Y").upper()
            self.month_title.setText(f"📅  {month_str}")
        self.badge.setText(f"● {count:,} Events")

    def populate(self, events, anchor, mode, zone, basis="calendar"):
        self.update_header(anchor, len(events))
        self.grid.populate(events, anchor, mode, zone, basis)


class HistoryChart(QWidget):
    def __init__(self, theme="Dark Navy"):
        super().__init__()
        self.rows = []
        self.unit = ""
        self.sample = False
        self.theme = theme
        self.setMinimumHeight(190)
        self.setMouseTracking(True)
        self.points = []

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def set_history(self, rows, unit, sample):
        self.rows = [r for r in rows if r["value_decimal"] is not None]
        self.unit, self.sample = unit, sample
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        is_dark = str(self.theme).lower() not in ("clean light", "light", "white")

        if is_dark:
            bg_color = QColor("#081426")
            text_color = QColor("#94A3B8")
            grid_color = QColor("#152845")
            line_color = QColor("#38BDF8")
            point_brush = QColor("#081426")
            grad_top = QColor(56, 189, 248, 70)
            grad_bot = QColor(56, 189, 248, 5)
        else:
            bg_color = QColor("#FFFFFF")
            text_color = QColor("#0A192F")
            grid_color = QColor("#E2E8F0")
            line_color = QColor("#1D4ED8")
            point_brush = QColor("#FFFFFF")
            grad_top = QColor(29, 78, 216, 60)
            grad_bot = QColor(29, 78, 216, 5)

        painter.fillRect(self.rect(), bg_color)
        painter.setPen(text_color)
        painter.drawText(16, 22, ("SAMPLE · " if self.sample else "") + "Actual Readings Trend · " + (self.unit or "unit unavailable"))
        if not self.rows:
            painter.setPen(QColor("#64748B"))
            painter.drawText(16, 80, "No numeric history available for this series.")
            return

        values = [float(r["value_decimal"]) for r in self.rows]
        min_v, max_v = min(values), max(values)
        span = max_v - min_v if max_v != min_v else 1.0

        top = 40
        bottom = self.height() - 30
        left = 50
        right = self.width() - 20
        chart_w = right - left
        chart_h = bottom - top

        # Subtle horizontal gridlines
        painter.setPen(QPen(grid_color, 1, Qt.DashLine))
        for step in (0, 0.5, 1.0):
            y = int(bottom - step * chart_h)
            painter.drawLine(left, y, right, y)
            v = min_v + step * span
            painter.setPen(QColor("#64748B"))
            painter.drawText(8, y + 4, f"{v:.1f}")
            painter.setPen(QPen(grid_color, 1, Qt.DashLine))

        if len(self.rows) < 2:
            return

        self.points = []
        for i, val in enumerate(values):
            x = left + (i / (len(values) - 1)) * chart_w
            y = bottom - ((val - min_v) / span) * chart_h
            self.points.append(QPointF(x, y))

        # Fill under curve
        poly = QPolygonF(self.points)
        poly.append(QPointF(right, bottom))
        poly.append(QPointF(left, bottom))
        gradient = QLinearGradient(0, top, 0, bottom)
        gradient.setColorAt(0.0, grad_top)
        gradient.setColorAt(1.0, grad_bot)
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(poly)

        # Draw smooth line
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(line_color, 2))
        for i in range(len(self.points) - 1):
            painter.drawLine(self.points[i], self.points[i + 1])

        # Glowing points
        for point in self.points:
            painter.setBrush(point_brush)
            painter.setPen(QPen(line_color, 2))
            painter.drawEllipse(point, 4, 4)

        painter.setPen(text_color)
        painter.drawText(left, self.height() - 8, str(self.rows[0]["reporting_period"]))
        painter.drawText(max(left, self.width() - 110), self.height() - 8, str(self.rows[-1]["reporting_period"]))

    def mouseMoveEvent(self, event):
        if not self.points:
            return
        index = min(range(len(self.points)), key=lambda i: abs(self.points[i].x() - event.position().x()))
        row = self.rows[index]
        self.setToolTip(f"{'SAMPLE · ' if self.sample else ''}{row['reporting_period']}: {row['value_text']} {self.unit}\nRecorded: {row['recorded_at']}")


def resolve_source_url(event: dict) -> str:
    url = event.get("source_url") or event.get("document_url")
    if url and str(url).startswith("http"):
        return str(url)
    auth = str(event.get("authority", "")).lower()
    title = str(event.get("title", "")).lower()
    if any(k in auth or k in title for k in ("rbi", "reserve bank", "mpc", "repo")):
        return "https://www.rbi.org.in"
    if any(k in auth or k in title for k in ("sebi", "lodr")):
        return "https://www.sebi.gov.in"
    if any(k in auth or k in title for k in ("nse", "nifty")):
        return "https://www.nseindia.com"
    if any(k in auth or k in title for k in ("bse", "sensex")):
        return "https://www.bseindia.com"
    if any(k in auth or k in title for k in ("mospi", "cpi", "iip", "gdp")):
        return "https://www.mospi.gov.in"
    if any(k in auth or k in title for k in ("dpiit", "wpi", "commerce")):
        return "https://eaindustry.nic.in"
    if any(k in auth for k in ("finnhub",)):
        return "https://finnhub.io"
    if any(k in auth or k in title for k in ("fed", "fomc")):
        return "https://www.federalreserve.gov"
    if any(k in auth or k in title for k in ("bls", "payrolls", "nfp")):
        return "https://www.bls.gov"
    return "https://www.nseindia.com"


class EventDetail(QTabWidget):
    action_requested = Signal(str, str)  # action, event_id

    def __init__(self, db, repository, theme="Dark Navy"):
        super().__init__()
        self.db, self.repository = db, repository
        self.theme = theme
        self.event_id = None
        self.zone = "Asia/Kolkata"
        self.overview = browser(lambda act: self.action_requested.emit(act, str(self.event_id or "")))
        self.analysis_view = browser(lambda act: self.action_requested.emit(act, str(self.event_id or "")))
        self.history_text = browser()
        self.revision_text = browser()
        self.source_text = browser()
        history = QWidget()
        layout = QVBoxLayout(history)
        layout.setContentsMargins(8, 8, 8, 8)
        self.chart = HistoryChart(self.theme)
        layout.addWidget(self.chart)
        layout.addWidget(self.history_text, 1)
        self.addTab(self.overview, "Overview")
        self.addTab(self.analysis_view, "Analysis")
        self.addTab(history, "History")
        self.addTab(self.revision_text, "Changes")
        self.addTab(self.source_text, "Sources")
        self.clear()

    def set_theme(self, theme):
        self.theme = theme
        self.chart.set_theme(theme)
        if self.event_id:
            self.show_event(self.event_id, self.zone)
        else:
            self.clear()

    def clear(self):
        is_dark = str(self.theme).lower() not in ("clean light", "light", "white")
        h2_color = "#FFFFFF" if is_dark else "#0A192F"
        p_color = "#94A3B8" if is_dark else "#64748B"
        empty = f"""
            <div style='text-align:center; padding:50px 20px;'>
                <div style='font-size:28px; margin-bottom:12px;'>📊</div>
                <h2 style='color:{h2_color}; margin-bottom:6px;'>Trading Event Inspector</h2>
                <p style='color:{p_color};'>Select an event from the calendar or table to inspect readings, consensus comparison, milestones, and original filing provenance.</p>
            </div>
        """
        self.overview.setHtml(html_page(empty, self.theme))
        self.analysis_view.setHtml(html_page("<p class='muted'>Select an event to view institutional financial analysis, asset class impacts, and market relevance.</p>", self.theme))
        self.chart.set_history([], "", False)
        self.history_text.setHtml(html_page("<p class='muted'>No historical readings selected.</p>", self.theme))
        self.revision_text.setHtml(html_page("<p class='muted'>No revision audit trail selected.</p>", self.theme))
        self.source_text.setHtml(html_page("<p class='muted'>No source records selected.</p>", self.theme))

    def show_event(self, event_id, zone):
        event = self.repository.get(event_id)
        if not event:
            return
        self.event_id = event_id
        self.zone = zone
        esc = lambda value: escape(str(value))
        article = article_for(self.db, event)
        is_dark = str(self.theme).lower() not in ("clean light", "light", "white")

        # Build TradingView-inspired overview card
        tag_sample = f'<span class="badge badge-sample">SYNTHETIC SAMPLE</span>' if event["sample"] else '<span class="badge badge-source">SOURCE RECORD</span>'
        imp = event["importance"]
        imp_class = "badge-high" if imp == "High" else "badge-med" if imp == "Medium" else "badge-low"
        tag_importance = f'<span class="badge {imp_class}">{imp.upper()}</span>'
        tag_status = f'<span class="badge badge-status">{event["status"].upper()}</span>'

        title_color = "#FFFFFF" if is_dark else "#0A192F"
        sub_color = "#94A3B8" if is_dark else "#475569"

        html = f"""
        <div style='margin-bottom:12px;'>
            {tag_sample} {tag_importance} {tag_status}
            <h2 style='margin-top:8px; margin-bottom:4px; color:{title_color};'>{esc(event['title'])}</h2>
            <div style='color:{sub_color}; font-size:11px;'>
                <b>{esc(event['kind'])}</b> · {esc(event['category'])} &nbsp;|&nbsp; 
                {esc(event.get('company') or event.get('country'))} · {esc(event.get('authority'))}
            </div>
        </div>
        """

        # 3-stat comparison for economic releases
        if event["kind"] == "Economic":
            prev = esc(event.get('previous') or '—')
            fct = esc(event.get('forecast') or '—')
            act = event.get('actual')
            act_class = "stat-value"
            if act is not None and event.get('forecast') is not None:
                try:
                    if float(act) >= float(event['forecast']):
                        act_class = "stat-value-beat"
                    else:
                        act_class = "stat-value-miss"
                except ValueError:
                    pass
            act_display = esc(act if act is not None else '—')
            html += f"""
            <h3>READINGS BREAKDOWN</h3>
            <div class='stat-grid'>
                <div class='stat-col'>
                    <div class='stat-label'>Previous</div>
                    <div class='stat-value'>{prev}</div>
                </div>
                <div class='stat-col' style='border-left:0; border-right:0;'>
                    <div class='stat-label'>Consensus</div>
                    <div class='stat-value'>{fct}</div>
                </div>
                <div class='stat-col'>
                    <div class='stat-label'>Actual</div>
                    <div class='{act_class}'>{act_display}</div>
                </div>
            </div>
            <div style='color:{sub_color}; font-size:11px; margin-bottom:12px;'>
                Unit: <b>{esc(event.get('unit') or 'Unavailable')}</b> &nbsp;·&nbsp; 
                Reporting Period: <b>{esc(event.get('reporting_period') or 'Unavailable')}</b>
            </div>
            """

        # Key milestone dates
        html += "<h3>EVENT MILESTONES</h3><table class='data-table'>"
        for field, name in (
            ("scheduled_at", "Scheduled Release"),
            ("published_at", "Publication Time"),
            ("effective_at", "Effective Date"),
            ("deadline_at", "Filing Deadline"),
            ("record_date", "Record Date"),
            ("ex_date", "Ex-Date"),
        ):
            if event.get(field):
                val_color = "#FFFFFF" if is_dark else "#0A192F"
                html += f"<tr><td class='label'>{name}</td><td><b style='color:{val_color};'>{esc(display_time(event[field], zone))}</b></td></tr>"
        html += "</table>"

        # Disclosure summary
        summary_color = "#F1F5F9" if is_dark else "#0A192F"
        html += f"""
        <h3>DISCLOSURE SUMMARY</h3>
        <div class='card'>
            <p style='margin:0; color:{summary_color}; font-weight:500;'>{esc(event.get('summary') or 'No summary supplied. Consult original documentation.')}</p>
        </div>
        """

        # Deep Financial Intelligence
        deep = get_event_deep_explanation(event)
        concept = deep.get("concept", "")
        what_it_means = deep.get("what_it_means", "")
        effects = deep.get("what_it_effects", {})
        relevance = deep.get("relevance", "")
        playbook = deep.get("interpretation", "")

        html += f"""
        <h3>💡 THE FINANCIAL CONCEPT</h3>
        <div class='concept-card'>
            <p style='margin:0; font-size:12px; line-height:1.5;'>{esc(concept)}</p>
        </div>

        <h3>💥 ASSET CLASS IMPACT SNAPSHOT</h3>
        <div class='impact-grid'>
            <div class='impact-row'>
                <div class='impact-cell'>
                    <div class='impact-title'>📈 EQUITIES & STOCKS</div>
                    <div class='impact-desc'>{esc(effects.get('equities', 'N/A'))}</div>
                </div>
                <div class='impact-cell'>
                    <div class='impact-title'>🏛️ BONDS & YIELDS</div>
                    <div class='impact-desc'>{esc(effects.get('bonds', 'N/A'))}</div>
                </div>
            </div>
            <div class='impact-row'>
                <div class='impact-cell'>
                    <div class='impact-title'>💱 CURRENCY (USD/INR)</div>
                    <div class='impact-desc'>{esc(effects.get('currency', 'N/A'))}</div>
                </div>
                <div class='impact-cell'>
                    <div class='impact-title'>💳 BORROWING COSTS</div>
                    <div class='impact-desc'>{esc(effects.get('borrowers', 'N/A'))}</div>
                </div>
            </div>
        </div>
        """

        # Educational insight
        if article:
            art_title = "#FFFFFF" if is_dark else "#0A192F"
            art_why = "#94A3B8" if is_dark else "#475569"
            html += f"""
            <h3>MARKET KNOWLEDGE · {esc(article['title']).upper()}</h3>
            <div class='card'>
                <p style='color:{art_title}; font-weight:600;'>{esc(article['definition'])}</p>
                <p style='color:{art_why}; font-size:11px; margin-top:8px;'><b>WHY IT MATTERS:</b> {esc(article['importance'])}</p>
                <p class='muted'>Release Frequency: {esc(article['frequency'])}</p>
            </div>
            """

        source_url = resolve_source_url(event)
        authority = event.get("authority") or "Official Regulatory & Market Authority"

        # Official Source & Updates Reference Card
        html += f"""
        <h3>OFFICIAL SOURCE & DATA UPDATES</h3>
        <div class='card'>
            <div style='color:{sub_color}; font-size:11px;'>Issuing Authority / Portal: <b style='color:{title_color};'>{esc(authority)}</b></div>
            <p style='margin-top:6px; margin-bottom:2px;'>
                <a href='{esc(source_url)}' class='btn-link'>🔗 Open Official Source Portal ({esc(source_url)}) ↗</a>
            </p>
        </div>
        """

        self.overview.setHtml(html_page(html, self.theme))

        # Check Gemini AI Analysis cache
        cached_ai = get_cached_analysis(self.db, event_id)
        has_gemini = bool(get_gemini_api_key(self.db))
        
        if cached_ai:
            ai_card = format_ai_analysis_html({"success": True, "text": cached_ai["text"], "model": cached_ai["model"], "created_at": cached_ai["created_at"], "cached": True}, self.theme)
            ai_card += f"""
            <div style='text-align:right; margin-top:4px; margin-bottom:12px;'>
                <a href='action:gemini-refresh' style='color:#38BDF8; font-size:11px; text-decoration:none; font-weight:600;'>🔄 Regenerate with Gemini AI</a>
            </div>
            """
        elif has_gemini:
            ai_card = f"""
            <div style='background:{"#0B192E" if is_dark else "#F8FAFC"}; border:1px solid #1E3A8A; border-radius:8px; padding:16px; margin:12px 0; text-align:center;'>
                <div style='font-size:22px; margin-bottom:4px;'>✨</div>
                <div style='font-size:13px; font-weight:700; color:{title_color}; margin-bottom:4px;'>Google Gemini AI Market Intelligence</div>
                <div style='font-size:11px; color:{sub_color}; max-width:480px; margin:0 auto 12px auto; line-height:1.5;'>
                    Evaluate transmission channels for Nifty 50, Bank Nifty, and key Indian sectors using Google Gemini 1.5 Flash.
                </div>
                <a href='action:gemini-generate' style='display:inline-block; background:#2563EB; color:#FFFFFF; text-decoration:none; padding:7px 16px; border-radius:6px; font-weight:700; font-size:11px;'>
                    ✨ Generate Live Gemini AI Analysis ↗
                </a>
            </div>
            """
        else:
            ai_card = f"""
            <div style='background:{"#0B192E" if is_dark else "#F8FAFC"}; border:1px solid #1E3A8A; border-radius:8px; padding:16px; margin:12px 0; text-align:center;'>
                <div style='font-size:22px; margin-bottom:4px;'>✨</div>
                <div style='font-size:13px; font-weight:700; color:{title_color}; margin-bottom:4px;'>Google Gemini AI Integration Ready</div>
                <div style='font-size:11px; color:{sub_color}; max-width:480px; margin:0 auto 12px auto; line-height:1.5;'>
                    Connect your free Gemini API key to unlock instant institutional impact research and sector sensitivity models.
                </div>
                <a href='action:gemini-config' style='display:inline-block; background:#1E40AF; color:#FFFFFF; text-decoration:none; padding:7px 14px; border-radius:6px; font-weight:600; font-size:11px;'>
                    🔑 Connect Free Gemini API Key ↗
                </a>
            </div>
            """

        # Deep Analysis Tab
        analysis_html = f"""
        <div style='margin-bottom:12px;'>
            {tag_sample} {tag_importance} {tag_status}
            <h2 style='margin-top:8px; margin-bottom:4px; color:{title_color};'>{esc(event['title'])}</h2>
            <div style='color:{sub_color}; font-size:11px;'>
                <b>INSTITUTIONAL INTELLIGENCE & MARKET IMPACT REPORT</b> &nbsp;|&nbsp; 
                {esc(event.get('authority', 'Official Source'))} · {esc(event.get('category', 'General'))}
            </div>
        </div>

        {ai_card}

        <h3>💡 1. THE FINANCIAL CONCEPT & FOUNDATION</h3>
        <div class='concept-card'>
            <p style='margin:0; font-size:12px; line-height:1.6;'>{esc(concept)}</p>
        </div>

        <h3>📖 2. WHAT THIS ANNOUNCEMENT MEANS</h3>
        <div class='card'>
            <p style='margin:0; font-size:12px; line-height:1.6;'>{esc(what_it_means)}</p>
        </div>

        <h3>💥 3. WHAT IT EFFECTS (CROSS-ASSET IMPACT MATRIX)</h3>
        <div class='impact-grid'>
            <div class='impact-row'>
                <div class='impact-cell'>
                    <div class='impact-title'>📈 EQUITIES & INDIAN STOCK MARKET</div>
                    <div class='impact-desc'>{esc(effects.get('equities', 'N/A'))}</div>
                </div>
                <div class='impact-cell'>
                    <div class='impact-title'>🏛️ FIXED INCOME & SOVEREIGN G-SEC YIELDS</div>
                    <div class='impact-desc'>{esc(effects.get('bonds', 'N/A'))}</div>
                </div>
            </div>
            <div class='impact-row'>
                <div class='impact-cell'>
                    <div class='impact-title'>💱 CURRENCY & FOREX (USD/INR PAIR)</div>
                    <div class='impact-desc'>{esc(effects.get('currency', 'N/A'))}</div>
                </div>
                <div class='impact-cell'>
                    <div class='impact-title'>💳 BORROWING COSTS, EMIS & REAL ECONOMY</div>
                    <div class='impact-desc'>{esc(effects.get('borrowers', 'N/A'))}</div>
                </div>
            </div>
        </div>

        <h3>🎯 4. STRATEGIC RELEVANCE & WHY INSTITUTIONS TRACK IT</h3>
        <div class='card'>
            <p style='margin:0; font-size:12px; line-height:1.6;'>{esc(relevance)}</p>
        </div>

        <h3>🔍 5. TRADING & FORECAST PLAYBOOK (BEAT VS MISS)</h3>
        <div class='playbook-card'>
            <p style='margin:0; font-size:12px; line-height:1.6;'><b>Interpretation Guide:</b> {esc(playbook)}</p>
        </div>
        """
        self.analysis_view.setHtml(html_page(analysis_html, self.theme))

        # History tab
        history = self.repository.history(event)
        self.chart.set_history(history, event.get("unit", ""), event["sample"])
        val_color = "#FFFFFF" if is_dark else "#0A192F"
        h = f"""
        <h3>STORED HISTORICAL OBSERVATIONS</h3>
        <p class='muted'>Auditable historical readings from verified releases. Original source snapshots remain immutable.</p>
        <table class='data-table'>
            <tr><th>Reporting Period</th><th style='text-align:right;'>Actual Reading</th><th style='text-align:right;'>Unit</th></tr>
        """
        for row in history:
            val = esc(row['value_text'] if row['value_text'] is not None else '—')
            h += f"<tr><td>{esc(row['reporting_period'])}</td><td style='text-align:right;'><b style='color:{val_color};'>{val}</b></td><td style='text-align:right;'>{esc(row['unit'])}</td></tr>"
        self.history_text.setHtml(html_page(h + "</table>", self.theme))

        # Revisions tab
        r = "<h3>REVISION & AUDIT TRAIL</h3>"
        for revision in self.repository.revisions(event_id):
            snapshot = json.loads(revision["payload"])
            rev_title_color = "#38BDF8" if is_dark else "#1D4ED8"
            r += f"""
            <div class='card'>
                <div style='color:{rev_title_color}; font-weight:700;'>Revision Version {revision['revision']} · {esc(display_time(revision['recorded_at'], zone))}</div>
                <div class='muted'>Source: {esc(revision['source_id'])} | Modified: {esc(', '.join(json.loads(revision['changed_fields'])))}</div>
                <table class='data-table' style='margin-top:6px;'>
            """
            for key in ("status", "scheduled_at", "published_at", "effective_at", "previous", "forecast", "actual", "revised", "summary"):
                if snapshot.get(key) is not None:
                    val_c = "#FFFFFF" if is_dark else "#0A192F"
                    r += f"<tr><td class='label'>{esc(key)}</td><td style='color:{val_c};'>{esc(snapshot[key])}</td></tr>"
            r += "</table></div>"
        self.revision_text.setHtml(html_page(r, self.theme))

        # Sources tab
        s = f"""
        <h3>DATA PROVENANCE & AUTHENTICITY</h3>
        <div class='card'>
            <p><b>Verification Status:</b> {esc(event['verification'])}</p>
            <p class='muted'>
                Retrieved: {esc(display_time(event['retrieved_at'], zone))}<br>
                Database Revision: #{event['revision']}<br>
                Source Timestamp: {esc(display_time(event.get('source_updated_at'), zone))}<br>
                Primary Issuing Authority: <b>{esc(authority)}</b>
            </p>
        </div>
        <h3>OFFICIAL SOURCE HYPERLINK & PUBLIC RELEASE PORTAL</h3>
        <div class='card'>
            <b>Primary Source: {esc(authority)}</b><br>
            <span class='muted'>Direct official public release documentation & verified live feed updates</span>
            <p style='margin-top:8px;'>
                <a href='{esc(source_url)}' class='btn-link'>🔗 Open Official Source Portal ({esc(source_url)}) ↗</a>
            </p>
        </div>
        <h3>OFFICIAL AUDIT & FILING LINKS</h3>
        """
        for source in self.repository.sources(event_id):
            s += f"""
            <div class='card'>
                <b>{esc(source['name'])}</b> &nbsp;·&nbsp; <span class='muted'>External ID: {esc(source['external_id'])}</span>
            """
            if source.get("source_url"):
                source_payload = json.loads(source.get("payload", "{}"))
                link_label = "Open Official RSS Feed ↗" if source_payload.get("source_reference_kind") == "feed" else "Open Official Filing ↗"
                s += f"<p><a href='{esc(source['source_url'])}' class='btn-link'>{link_label}</a></p>"
            s += "</div>"
        if event.get("document_url"):
            s += f"""
            <div class='card'>
                <b>Supporting Document / Regulatory Filing</b>
                <p><a href='{esc(event['document_url'])}' class='btn-link'>📄 Open Supporting Document ↗</a></p>
            </div>
            """

        s += f"<p class='muted' style='margin-top:20px;'>Internal Event ID: {esc(event_id)}</p>"
        self.source_text.setHtml(html_page(s, self.theme))
