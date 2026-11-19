from datetime import date, timedelta
from html import escape
import json
from pathlib import Path
import uuid

from PySide6.QtCore import QDate, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCalendarWidget, QCheckBox, QComboBox, QCompleter,
    QDateEdit, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea,
    QSplitter, QStackedWidget, QSystemTrayIcon, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget
)

from app.database.events import EventRepository
from app.data_sources.manager import SourceManager
from app.notifications.engine import NotificationEngine
from app.notifications.windows import WindowsNotificationSink
from app.services.demo import load_demo, simulate_reminder
from app.services.ingestion import IngestionService
from app.services.gemini import get_gemini_api_key
from app.ui.dialogs import ApiKeyDialog, ImportDialog, RuleDialog, SourceDialog
from app.ui.widgets import (
    CalendarGrid, CalendarViewContainer, EventDetail, EventTableModel, LiveSecondsClock, LiveSignalBeacon,
    browser, event_table, html_page, label
)
from app.ui.workers import Worker
from app.utils.paths import resource_path
from app.utils.time import display_time, local_date, stamp, zones

NAV = [
    "Dashboard",
    "Unified Calendar",
    "Economic Events",
    "Corporate Announcements",
    "Regulatory Updates",
    "Historical Database",
    "Event Knowledge Base",
    "Watchlists",
    "Notification Settings",
    "Sources & Settings"
]

NAV_ICONS = ["📊", "📅", "📈", "🏢", "⚖️", "🏛️", "📖", "⭐", "🔔", "📡"]


def button(text, callback, primary=False):
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    widget.clicked.connect(callback)
    return widget


def read_only_table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)
    return table


class MainWindow(QMainWindow):
    def __init__(self, db, background=True):
        super().__init__()
        self.db = db
        self.repository = EventRepository(db)
        self.notifications = NotificationEngine(db)
        self.sources = SourceManager(db)
        self.worker = None
        self.offset = 0
        self.quitting = False
        self.current_theme = db.setting("theme", "Dark Navy")
        self.sink = WindowsNotificationSink(self)
        self.sink.activated.connect(self.toast_opened)
        self.sink.failed.connect(self.toast_failed)
        self.setWindowTitle("Finstock EventScope · Finstock Capital")
        self.setWindowIcon(QIcon(str(resource_path("assets/finstock.svg"))))
        self.resize(1600, 940)
        self.setMinimumSize(1100, 720)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- OpenAI / Claude-Inspired Creative Left Sidebar ---
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        left = QVBoxLayout(sidebar)
        left.setContentsMargins(0, 20, 0, 15)
        left.setSpacing(6)

        brand_box = QVBoxLayout()
        brand_box.setContentsMargins(20, 0, 20, 14)
        brand_box.setSpacing(2)
        brand = label("FINSTOCK", "brand")
        sub = label("E V E N T S C O P E", "brandSub")
        brand_box.addWidget(brand)
        brand_box.addWidget(sub)
        left.addLayout(brand_box)

        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        for index, title in enumerate(NAV):
            item = QListWidgetItem(f"  {NAV_ICONS[index]}   {title}")
            item.setData(Qt.UserRole, index)
            self.navigation.addItem(item)
        left.addWidget(self.navigation, 1)

        sidefoot = label("FINSTOCK CAPITAL\nTradingView Terminal Engine\nReal-time Event Intelligence", "subtitle")
        sidefoot.setContentsMargins(20, 10, 12, 6)
        left.addWidget(sidefoot)
        outer.addWidget(sidebar)

        # --- Main Workspace ---
        main = QVBoxLayout()
        main.setContentsMargins(20, 16, 16, 8)
        main.setSpacing(10)
        outer.addLayout(main, 1)

        # --- Top Header Bar ---
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)

        headings = QVBoxLayout()
        headings.setSpacing(1)
        headings.addWidget(label("FINANCIAL EVENT INTELLIGENCE", "eyebrow"))
        self.page_title = label("Dashboard", "pageTitle")
        headings.addWidget(self.page_title)
        self.subtitle = label("Your economic, corporate and regulatory events in one place.", "subtitle")
        headings.addWidget(self.subtitle)
        top.addLayout(headings, 1)

        # Live Signal Beacon (Red = Offline/Sample, Green = Live Streaming)
        self.beacon = LiveSignalBeacon(is_live=self.is_any_source_enabled(), theme=self.current_theme)
        self.beacon.clicked.connect(lambda: self.navigation.setCurrentRow(9))
        top.addWidget(self.beacon)

        # Real-time Monospace Seconds Clock & Countdown
        if not db.setting("timezone"):
            db.set_setting("timezone", "Asia/Kolkata")
        current_tz = db.setting("timezone", "Asia/Kolkata")
        self.clock_widget = LiveSecondsClock(zone=current_tz, theme=self.current_theme)
        top.addWidget(self.clock_widget)

        # 3-Way Theme Switcher (Dark Navy / Clean Light / Auto)
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("themeToggle")
        self.theme_btn.setToolTip("Theme: Dark Navy / Clean Light / Auto System")
        curr_theme_mode = self.db.setting("theme_mode", self.current_theme)
        self.update_theme_btn_text(curr_theme_mode)
        self.theme_btn.clicked.connect(self.toggle_theme)
        top.addWidget(self.theme_btn)

        # API Keys & AI Configuration Button
        self.api_keys_btn = QPushButton("🔑 API & AI")
        self.api_keys_btn.setToolTip("Configure free Finnhub & Google Gemini AI API keys")
        self.api_keys_btn.clicked.connect(self.configure_api_keys)
        top.addWidget(self.api_keys_btn)

        # Timezone Selector
        self.zone = QComboBox()
        self.zone.setEditable(True)
        self.zone.addItems(zones())
        self.zone.setCurrentText(current_tz)
        self.zone.setMinimumWidth(160)
        self.zone.setMaximumWidth(210)
        self.zone.setToolTip("Display timezone · IANA timezone database")
        completer = QCompleter(zones(), self.zone)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.popup().setObjectName("completerPopup")
        if self.zone.lineEdit():
            self.zone.lineEdit().setObjectName("zoneInput")
        self.zone.setCompleter(completer)
        top.addWidget(self.zone)

        top.addWidget(button("Import", self.import_file, True))
        main.addLayout(top)

        self.banner = label("● LIVE WORKSPACE  ·  Real-time institutional financial calendar and official market announcements.", "liveBanner")
        self.banner.setWordWrap(True)
        main.addWidget(self.banner)

        self.stack = QStackedWidget()
        main.addWidget(self.stack, 1)

        self.build_events()
        self.build_knowledge()
        self.build_watchlists()
        self.build_notifications()
        self.build_sources()

        self.statusBar().showMessage("Local database ready · live feeds active")
        self.navigation.currentRowChanged.connect(self.navigate)
        self.zone.currentTextChanged.connect(self.change_zone)
        self.zone.lineEdit().editingFinished.connect(lambda: self.zone.setCurrentText(self.db.setting("timezone", "Asia/Kolkata")) if self.zone.currentText() not in zones() else None)
        self.build_tray()
        self.notifications.recover()

        self.notification_timer = QTimer(self)
        self.notification_timer.setInterval(2000)
        self.notification_timer.timeout.connect(self.tick)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30000)
        self.refresh_timer.timeout.connect(self.refresh_due)

        # 1-second live heartbeat timer
        self.sync_seconds = 5
        self.seconds_to_sync = self.sync_seconds
        self.second_timer = QTimer(self)
        self.second_timer.setInterval(1000)
        self.second_timer.timeout.connect(self.on_second_tick)

        if background:
            self.notification_timer.start()
            self.refresh_timer.start()
            self.second_timer.start()

        self.navigation.setCurrentRow(0)

    def is_any_source_enabled(self):
        try:
            rows = self.db.rows("SELECT count(*) as c FROM data_sources WHERE enabled=1 AND adapter!='import'")
            return rows[0]["c"] > 0
        except Exception:
            return False

    def on_second_tick(self):
        self.seconds_to_sync -= 1
        if hasattr(self, "clock_widget"):
            self.clock_widget.set_sync_countdown(self.seconds_to_sync)
        if self.seconds_to_sync <= 0:
            self.seconds_to_sync = self.sync_seconds
            if not (self.worker and self.worker.isRunning()):
                self.refresh_due(force=False)
        if hasattr(self, "beacon"):
            self.beacon.set_live(self.is_any_source_enabled())

    def build_events(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # --- Sleek Minimal Face Control Bar ---
        face_bar = QHBoxLayout()
        face_bar.setContentsMargins(0, 0, 0, 2)
        face_bar.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search events, companies, symbols…")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(260)
        face_bar.addWidget(self.search, 1)

        self.scope = QComboBox()
        self.scope.addItems(["All records", "Live source records", "Sample records"])
        self.scope.setCurrentText(self.db.setting("data_scope", "All records"))
        self.scope.setToolTip("Workspace Scope: Filter live vs sample records")
        face_bar.addWidget(self.scope)

        self.view = QComboBox()
        self.view.addItems(["Agenda", "Day", "Week", "Month"])
        self.view.hide()

        self.view_buttons = {}
        view_pill_box = QHBoxLayout()
        view_pill_box.setSpacing(2)
        for v in ("Agenda", "Day", "Week", "Month"):
            b = QPushButton(v)
            b.setObjectName("viewPill")
            b.setCheckable(True)
            b.setChecked(v == "Agenda")
            b.clicked.connect(lambda checked, text=v: self.view.setCurrentText(text))
            self.view_buttons[v] = b
            view_pill_box.addWidget(b)
        face_bar.addLayout(view_pill_box)
        self.view.currentTextChanged.connect(self.sync_view_buttons)

        self.anchor = QDateEdit(self.today())
        self.anchor.setCalendarPopup(True)
        self.anchor.setDisplayFormat("dd MMM yyyy")
        cal = self.anchor.calendarWidget()
        if cal:
            cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
            cal.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
            cal.setGridVisible(False)
            cal.setMinimumSize(400, 270)
        face_bar.addWidget(button("‹", lambda: self.shift_date(-1)))
        face_bar.addWidget(self.anchor)
        face_bar.addWidget(button("›", lambda: self.shift_date(1)))
        face_bar.addWidget(button("Today", lambda: self.anchor.setDate(self.today())))
        face_bar.addWidget(button("Watch", self.watch_selected))
        layout.addLayout(face_bar)

        # --- Center Workspace + Right Slide-Out Drawer + Right Tool Dock ---
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)

        # Main Event Views Stack
        self.event_views = QStackedWidget()
        self.model = EventTableModel(self.zone.currentText(), self.current_theme)
        self.table = event_table(self.model)
        self.table.selectionModel().currentRowChanged.connect(self.select_row)

        self.calendar_container = CalendarViewContainer(self.current_theme)
        self.calendar = self.calendar_container.grid
        self.calendar_container.event_selected.connect(self.open_event)
        self.calendar_container.day_selected.connect(self.on_calendar_day_selected)
        self.calendar_container.prev_month_clicked.connect(self.on_prev_month)
        self.calendar_container.next_month_clicked.connect(self.on_next_month)
        self.calendar_container.today_clicked.connect(self.on_today_clicked)

        self.event_views.addWidget(self.table)
        self.event_views.addWidget(self.calendar_container)
        self.splitter.addWidget(self.event_views)

        # Right Slide-Out Drawer
        self.right_drawer = QFrame()
        self.right_drawer.setObjectName("rightDrawer")
        self.right_drawer.setMinimumWidth(380)
        self.right_drawer.setMaximumWidth(560)
        drawer_box = QVBoxLayout(self.right_drawer)
        drawer_box.setContentsMargins(10, 8, 10, 8)
        drawer_box.setSpacing(6)

        self.drawer_stack = QStackedWidget()

        # Page 0: Filters
        self.build_filter_drawer()
        self.drawer_stack.addWidget(self.filter_drawer_widget)

        # Page 1: Event Details & Revisions
        self.details = EventDetail(self.db, self.repository, self.current_theme)
        self.details.action_requested.connect(self.handle_drawer_action)
        self.drawer_stack.addWidget(self.details)

        # Page 2: Macro Metrics
        self.build_metrics_drawer()
        self.drawer_stack.addWidget(self.metrics_drawer_widget)

        drawer_box.addWidget(self.drawer_stack, 1)
        self.splitter.addWidget(self.right_drawer)

        # Initial layout: Main view gets maximum space, Details panel occupies right
        self.splitter.setSizes([1140, 440])
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)

        body_layout.addWidget(self.splitter, 1)

        # TradingView-Style Right Tool Dock
        self.right_dock = QFrame()
        self.right_dock.setObjectName("rightDock")
        dock_vbox = QVBoxLayout(self.right_dock)
        dock_vbox.setContentsMargins(0, 6, 0, 6)
        dock_vbox.setSpacing(6)

        self.dock_detail_btn = QPushButton("📑")
        self.dock_detail_btn.setObjectName("dockBtn")
        self.dock_detail_btn.setToolTip("Event Inspector & History Chart")
        self.dock_detail_btn.setCheckable(True)
        self.dock_detail_btn.setChecked(True)
        self.dock_detail_btn.clicked.connect(lambda: self.toggle_drawer(1))

        self.dock_filter_btn = QPushButton("🔍")
        self.dock_filter_btn.setObjectName("dockBtn")
        self.dock_filter_btn.setToolTip("Deep Filters (Country, Category, Authority…)")
        self.dock_filter_btn.setCheckable(True)
        self.dock_filter_btn.clicked.connect(lambda: self.toggle_drawer(0))

        self.dock_metrics_btn = QPushButton("📊")
        self.dock_metrics_btn.setObjectName("dockBtn")
        self.dock_metrics_btn.setToolTip("Macro Statistics & Metric Cards")
        self.dock_metrics_btn.setCheckable(True)
        self.dock_metrics_btn.clicked.connect(lambda: self.toggle_drawer(2))

        dock_vbox.addWidget(self.dock_detail_btn)
        dock_vbox.addWidget(self.dock_filter_btn)
        dock_vbox.addWidget(self.dock_metrics_btn)
        dock_vbox.addStretch()

        body_layout.addWidget(self.right_dock)
        layout.addLayout(body_layout, 1)

        footer = QHBoxLayout()
        self.results_label = label("", "subtitle")
        footer.addWidget(self.results_label, 1)
        self.previous_page = button("Previous", lambda: self.page(-1))
        self.next_page = button("Next", lambda: self.page(1))
        footer.addWidget(self.previous_page)
        footer.addWidget(self.next_page)
        layout.addLayout(footer)

        self.stack.addWidget(page)

        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(250)
        self.debounce.timeout.connect(self.reset_search)

        self.search.textChanged.connect(lambda: self.debounce.start())
        self.scope.currentIndexChanged.connect(self.reset_search)
        self.period.currentIndexChanged.connect(self.reset_search)
        self.view.currentIndexChanged.connect(self.reset_search)
        self.anchor.dateChanged.connect(self.reset_search)
        self.range_enabled.toggled.connect(self.reset_search)
        self.start.dateChanged.connect(self.reset_search)
        self.end.dateChanged.connect(self.reset_search)
        self.basis.currentIndexChanged.connect(self.reset_search)

    def build_filter_drawer(self):
        self.filter_drawer_widget = QWidget()
        vbox = QVBoxLayout(self.filter_drawer_widget)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(label("DEEP FILTERS & PERMUTATIONS", "eyebrow"))
        header.addStretch()
        reset_btn = QPushButton("Reset All")
        reset_btn.setObjectName("secondary")
        reset_btn.clicked.connect(self.clear_all_filters)
        header.addWidget(reset_btn)
        vbox.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        form = QVBoxLayout(container)
        form.setContentsMargins(0, 0, 4, 0)
        form.setSpacing(8)

        self.filters = {}
        filter_configs = [
            ("country", "All countries", "🌐 COUNTRY"),
            ("category", "All categories", "🏷️ CATEGORY"),
            ("authority", "All authorities", "🏛️ AUTHORITY"),
            ("exchange", "All exchanges", "🏢 EXCHANGE"),
            ("importance", "All importance", "⚡ IMPORTANCE"),
            ("status", "All statuses", "📌 EVENT STATUS")
        ]
        for key, def_text, card_title in filter_configs:
            card = QFrame()
            card.setObjectName("card")
            cbox = QVBoxLayout(card)
            cbox.setContentsMargins(10, 6, 10, 6)
            cbox.setSpacing(3)
            cbox.addWidget(label(card_title, "eyebrow"))
            combo = QComboBox()
            combo.addItem(def_text, "")
            self.filters[key] = combo
            combo.currentIndexChanged.connect(self.reset_search)
            cbox.addWidget(combo)
            form.addWidget(card)

        # Time Horizon Card
        p_card = QFrame()
        p_card.setObjectName("card")
        p_box = QVBoxLayout(p_card)
        p_box.setContentsMargins(10, 6, 10, 6)
        p_box.setSpacing(3)
        p_box.addWidget(label("📅 TIME HORIZON", "eyebrow"))
        self.period = QComboBox()
        self.period.addItems(["Any time", "Past", "Today", "Upcoming"])
        self.period.currentIndexChanged.connect(self.reset_search)
        p_box.addWidget(self.period)
        form.addWidget(p_card)

        # Milestone Basis Card
        b_card = QFrame()
        b_card.setObjectName("card")
        b_box = QVBoxLayout(b_card)
        b_box.setContentsMargins(10, 6, 10, 6)
        b_box.setSpacing(3)
        b_box.addWidget(label("🔄 MILESTONE BASIS", "eyebrow"))
        self.basis = QComboBox()
        for text, data in (
            ("Calendar date", "calendar"),
            ("All milestones", "all milestones"),
            ("Publication", "published_at"),
            ("Effective", "effective_at"),
            ("Deadline", "deadline_at"),
            ("Record date", "record_date"),
            ("Ex-date", "ex_date")
        ):
            self.basis.addItem(text, data)
        self.basis.currentIndexChanged.connect(self.reset_search)
        b_box.addWidget(self.basis)
        form.addWidget(b_card)

        # Custom Date Range Card
        r_card = QFrame()
        r_card.setObjectName("card")
        r_box = QVBoxLayout(r_card)
        r_box.setContentsMargins(10, 6, 10, 6)
        r_box.setSpacing(4)
        self.range_enabled = QCheckBox("Enable Custom Date Range")
        self.range_enabled.toggled.connect(self.reset_search)
        r_box.addWidget(self.range_enabled)
        self.start = QDateEdit(QDate.currentDate().addYears(-1))
        self.start.setCalendarPopup(True)
        self.start.setDisplayFormat("dd MMM yyyy")
        self.start.dateChanged.connect(self.reset_search)
        start_cal = self.start.calendarWidget()
        if start_cal:
            start_cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
            start_cal.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
            start_cal.setGridVisible(True)
            start_cal.setMinimumSize(320, 240)
        r_box.addWidget(self.start)
        self.end = QDateEdit(QDate.currentDate().addMonths(1))
        self.end.setCalendarPopup(True)
        self.end.setDisplayFormat("dd MMM yyyy")
        self.end.dateChanged.connect(self.reset_search)
        end_cal = self.end.calendarWidget()
        if end_cal:
            end_cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
            end_cal.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
            end_cal.setGridVisible(True)
            end_cal.setMinimumSize(320, 240)
        r_box.addWidget(self.end)
        form.addWidget(r_card)

        form.addStretch()
        scroll.setWidget(container)
        vbox.addWidget(scroll, 1)

    def build_metrics_drawer(self):
        self.metrics_drawer_widget = QWidget()
        vbox = QVBoxLayout(self.metrics_drawer_widget)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(8)

        vbox.addWidget(label("MACRO STATISTICS", "eyebrow"))

        self.metrics = QWidget()
        self.metric_values = []
        grid = QVBoxLayout(self.metrics)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        titles = [
            ("EVENTS IN THIS VIEW", "📊"),
            ("ECONOMIC RELEASES", "📈"),
            ("CORPORATE FILINGS", "🏢"),
            ("REGULATORY NOTICES", "⚖️")
        ]
        for title, icon in titles:
            card = QFrame()
            card.setObjectName("card")
            cbox = QVBoxLayout(card)
            cbox.setContentsMargins(14, 10, 14, 10)
            cbox.setSpacing(2)
            cbox.addWidget(label(f"{icon}  {title}", "eyebrow"))
            val = label("0", "metricValue")
            self.metric_values.append(val)
            cbox.addWidget(val)
            grid.addWidget(card)

        vbox.addWidget(self.metrics)
        vbox.addStretch()
        return self.metrics_drawer_widget

    def clear_all_filters(self):
        for combo in self.filters.values():
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.period.blockSignals(True)
        self.period.setCurrentIndex(0)
        self.period.blockSignals(False)
        self.range_enabled.blockSignals(True)
        self.range_enabled.setChecked(False)
        self.range_enabled.blockSignals(False)
        self.basis.blockSignals(True)
        self.basis.setCurrentIndex(0)
        self.basis.blockSignals(False)
        self.reset_search()

    def toggle_drawer(self, tab_index):
        if self.right_drawer.isVisible() and self.drawer_stack.currentIndex() == tab_index:
            self.dock_filter_btn.setChecked(False)
            self.dock_detail_btn.setChecked(False)
            self.dock_metrics_btn.setChecked(False)
            self.animate_drawer(close=True)
        else:
            self.drawer_stack.setCurrentIndex(tab_index)
            self.dock_filter_btn.setChecked(tab_index == 0)
            self.dock_detail_btn.setChecked(tab_index == 1)
            self.dock_metrics_btn.setChecked(tab_index == 2)
            if not self.right_drawer.isVisible():
                self.animate_drawer(close=False)

    def animate_drawer(self, close=False):
        from PySide6.QtCore import QVariantAnimation, QEasingCurve
        if hasattr(self, "drawer_anim") and self.drawer_anim.state() == QVariantAnimation.Running:
            self.drawer_anim.stop()

        start_w = self.right_drawer.width() if self.right_drawer.isVisible() else 0
        end_w = 0 if close else 440
        if not close:
            self.right_drawer.show()

        self.drawer_anim = QVariantAnimation(self)
        self.drawer_anim.setDuration(160)
        self.drawer_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.drawer_anim.setStartValue(start_w)
        self.drawer_anim.setEndValue(end_w)

        def on_step(val):
            total_w = self.splitter.width()
            val = int(val)
            if val <= 10 and close:
                self.right_drawer.hide()
            else:
                self.splitter.setSizes([max(200, total_w - val), val])

        self.drawer_anim.valueChanged.connect(on_step)
        if close:
            self.drawer_anim.finished.connect(lambda: self.right_drawer.hide())
        self.drawer_anim.start()

    def on_calendar_day_selected(self, day):
        self.anchor.setDate(QDate(day.year, day.month, day.day))
        self.view.setCurrentText("Agenda")
        self.refresh_events()

    def build_knowledge(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.articles = QListWidget()
        self.articles.setMaximumWidth(330)
        self.article_view = browser()
        for row in self.db.rows("SELECT * FROM knowledge_articles ORDER BY title"):
            item = QListWidgetItem(row["title"])
            item.setData(Qt.UserRole, row)
            self.articles.addItem(item)
        self.articles.currentItemChanged.connect(self.show_article)
        layout.addWidget(self.articles)
        layout.addWidget(self.article_view, 1)
        self.stack.addWidget(page)
        self.articles.setCurrentRow(0)

    def build_watchlists(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label("Follow companies by exact name, exchange symbol or ISIN. Watchlist members can be selected in notification rules.", "subtitle"))
        row = QHBoxLayout()
        self.watchlist_combo = QComboBox()
        row.addWidget(self.watchlist_combo)
        row.addWidget(button("New watchlist", self.new_watchlist))
        self.member_input = QLineEdit()
        self.member_input.setPlaceholderText("Company name, symbol or ISIN")
        row.addWidget(self.member_input, 1)
        row.addWidget(button("Add member", self.add_member, True))
        row.addWidget(button("Remove selected", self.remove_member))
        layout.addLayout(row)
        self.members = QListWidget()
        layout.addWidget(self.members, 1)
        self.watchlist_combo.currentIndexChanged.connect(self.refresh_members)
        self.stack.addWidget(page)
        self.refresh_watchlists()

    def build_notifications(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        note = label("Windows desktop notifications · background monitoring continues in the tray. Fully quitting stops monitoring.\nMissed reminders expire after the rule’s grace period; a submitted notification may be hidden by Windows Do Not Disturb.", "subtitle")
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        row.addWidget(button("Create rule", lambda: self.edit_rule(), True))
        row.addWidget(button("Edit selected", lambda: self.edit_rule(True)))
        row.addWidget(button("Enable / disable", self.toggle_rule))
        row.addStretch()
        row.addWidget(button("Simulate reminder in 10s", self.simulate))
        layout.addLayout(row)
        self.rules_table = read_only_table(["RULE", "ENABLED", "FILTERS", "ADVANCE MINUTES", "TRIGGERS", "SAMPLES"])
        self.rules_table.setMaximumHeight(240)
        layout.addWidget(self.rules_table)
        layout.addWidget(label("NOTIFICATION HISTORY", "eyebrow"))
        self.notification_table = read_only_table(["EVENT", "TRIGGER", "DUE", "STATE", "OPENED", "DETAIL"])
        self.notification_table.cellDoubleClicked.connect(self.open_notification)
        layout.addWidget(self.notification_table, 1)
        layout.addWidget(label("Double-click a history entry to open its event. Failed or uncertain deliveries are retained for inspection.", "subtitle"))
        self.stack.addWidget(page)

    def build_sources(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        note = label("Enable only sources you are entitled to access and store. Real-time updates check every 1-5 seconds.\nCredentials are encrypted locally. Imports and demonstrations remain tagged with SAMPLE badges.", "subtitle")
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        row.addWidget(button("⚡ Enable Indian Feeds (NSE/SEBI/RBI)", self.enable_official_feeds, True))
        row.addWidget(button("Configure selected", self.configure_source))
        row.addWidget(button("Refresh selected", self.refresh_selected))
        row.addWidget(button("Refresh enabled sources", lambda: self.refresh_due(True)))
        row.addWidget(button("View ingestion logs", self.show_logs))
        row.addWidget(button("Possible duplicate filings", self.show_duplicates))
        row.addStretch()
        layout.addLayout(row)
        self.source_table = read_only_table(["SOURCE", "STATUS", "AUTO", "INTERVAL", "LAST SUCCESS", "LAST RESULT"])
        self.source_table.cellDoubleClicked.connect(lambda *_: self.configure_source())
        layout.addWidget(self.source_table, 1)
        row = QHBoxLayout()
        row.addWidget(label("Terminal Theme:", "subtitle"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Navy", "Clean Light", "Auto (System)"])
        self.theme_combo.setCurrentText(self.db.setting("theme_mode", self.current_theme))
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        row.addWidget(self.theme_combo)
        self.tray_enabled = QCheckBox("Close window to system tray")
        self.tray_enabled.setChecked(self.db.setting("close_to_tray", True))
        self.tray_enabled.toggled.connect(lambda value: self.db.set_setting("close_to_tray", value))
        row.addWidget(self.tray_enabled)
        row.addStretch()
        row.addWidget(button("Back up database", self.backup))
        row.addWidget(button("Open user guide", self.user_guide))
        layout.addLayout(row)
        self.storage_label = label(f"Local storage: {self.db.path}\nNo cloud synchronization. Historical records remain available offline.", "subtitle")
        self.storage_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.storage_label.setWordWrap(True)
        layout.addWidget(self.storage_label)
        self.stack.addWidget(page)

    def build_tray(self):
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("Finstock EventScope · monitoring while running")
        menu = QMenu(self)
        show = menu.addAction("Open Finstock EventScope")
        show.triggered.connect(self.restore_window)
        quit_action = menu.addAction("Quit and stop monitoring")
        quit_action.triggered.connect(self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.restore_window() if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger) else None)
        self.tray.messageClicked.connect(lambda: self.toast_opened(self.sink.current_job["id"], self.sink.current_job["event_id"]) if getattr(self.sink, "current_job", None) else self.restore_window())
        self.tray.show()

    def navigate(self, index):
        if index < 0:
            return
        self.page_title.setText(NAV[index])
        self.subtitle.setText({
            0: "Executive terminal overview · key market events, live indicators & metrics.",
            1: "Master multi-asset visual calendar · combining Economic, Corporate & Regulatory milestones.",
            2: "Macroeconomic indicators, central bank decisions (RBI/Fed) & consensus data.",
            3: "Corporate disclosures, quarterly earnings, dividends, board meetings & IPOs.",
            4: "Regulatory orders, SEBI circulars, RBI statutory notices & exchange compliances.",
            5: "Search stored records and inspect historical revisions and archives.",
            6: "Source-referenced financial concepts and educational library.",
            7: "Customized event watchlists for tracked companies and sectors.",
            8: "Automated alert rules, sound alerts and desktop notification schedules.",
            9: "Live data sources, Finnhub & Gemini API configuration and system health."
        }.get(index, "Explore events, inspect the source and follow every update."))
        if index <= 5:
            self.stack.setCurrentIndex(0)
            if hasattr(self, "metrics"):
                self.metrics.setVisible(index == 0)
            if index == 1:
                # Unified Calendar: Force Month or Week view to display full visual calendar!
                if self.view.currentText() not in ("Month", "Week"):
                    self.view.setCurrentText("Month")
            elif index in (0, 2, 3, 4, 5):
                # Economic, Corporate, Regulatory, History, Dashboard: Open in Agenda table
                if self.view.currentText() not in ("Agenda", "Day"):
                    self.view.setCurrentText("Agenda")
            self.sync_view_buttons(self.view.currentText())
            self.period.blockSignals(True)
            self.period.setCurrentText("Past" if index == 5 else "Any time")
            self.period.blockSignals(False)
            self.reset_search()
            self.refresh_facets()
        else:
            self.stack.setCurrentIndex(index - 5)
            if index == 7:
                self.refresh_watchlists()
            if index == 8:
                self.refresh_notifications()
            if index == 9:
                self.refresh_sources()

    def refresh_facets(self):
        for key, combo in self.filters.items():
            current = combo.currentData()
            first = combo.itemText(0)
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(first, "")
            values = {"importance": ["Unknown", "Low", "Medium", "High"], "status": ["Scheduled", "Tentative", "Published", "Updated", "Postponed", "Cancelled"]}.get(key)
            for value in values if values is not None else self.repository.facets(key):
                combo.addItem(value, value)
            found = combo.findData(current)
            combo.setCurrentIndex(max(0, found))
            combo.blockSignals(False)

    def reset_search(self, *_):
        self.offset = 0
        self.refresh_events()

    def refresh_events(self):
        if self.zone.currentText() not in zones():
            return
        filters = {key: combo.currentData() for key, combo in self.filters.items()}
        mode = self.navigation.currentRow()
        if mode in (2, 3, 4):
            filters["kind"] = {2: "Economic", 3: "Corporate", 4: "Regulatory"}[mode]
        filters["sample"] = {0: None, 1: False, 2: True}.get(self.scope.currentIndex(), None)
        self.db.set_setting("data_scope", self.scope.currentText())
        if self.scope.currentIndex() == 2:
            self.banner.setText("SAMPLE WORKSPACE  ·  Displaying imported test and demonstration records.")
            self.banner.setObjectName("sampleBanner")
        else:
            self.banner.setText("● LIVE WORKSPACE  ·  Real-time institutional financial calendar and official market announcements.")
            self.banner.setObjectName("liveBanner")
        self.banner.setStyle(self.banner.style())
        start = end = None
        anchor = self.anchor.date().toPython()
        view = self.view.currentText()
        if view == "Day":
            start = end = anchor.isoformat()
        elif view == "Week":
            first = anchor - timedelta(days=anchor.weekday())
            start = first.isoformat()
            end = (first + timedelta(days=6)).isoformat()
        elif view == "Month":
            first = anchor.replace(day=1)
            first -= timedelta(days=first.weekday())
            start = first.isoformat()
            end = (first + timedelta(days=41)).isoformat()
        elif self.range_enabled.isChecked():
            start = self.start.date().toString(Qt.ISODate)
            end = self.end.date().toString(Qt.ISODate)

        if start and end and start > end:
            self.results_label.setText("Start date must not be later than end date")
            return

        limit = 500 if view in ("Agenda", "Day") else 5000
        events, total = self.repository.search(self.search.text(), filters, start, end, self.zone.currentText(), self.basis.currentData(), limit, self.offset)
        self.model.set_events(events, self.zone.currentText())
        if view in ("Week", "Month"):
            self.calendar_container.populate(events, anchor, view, self.zone.currentText(), self.basis.currentData())
            self.event_views.setCurrentIndex(1)
        else:
            self.event_views.setCurrentIndex(0)

        counts = [total] + [sum(e["kind"] == kind for e in events) for kind in ("Economic", "Corporate", "Regulatory")]
        for value, count in zip(self.metric_values, counts):
            value.setText(f"{count:,}")

        self.results_label.setText(f"{total:,} matching records · displaying {len(events):,} · {self.zone.currentText()} · date-only values retain their source date")
        self.previous_page.setEnabled(self.offset > 0)
        self.next_page.setEnabled(self.offset + limit < total)
        if events and not self.details.event_id:
            self.table.selectRow(0)

    def page(self, direction):
        self.offset = max(0, self.offset + direction * (500 if self.view.currentText() in ("Agenda", "Day") else 5000))
        self.refresh_events()

    def sync_view_buttons(self, text):
        for v, btn in getattr(self, "view_buttons", {}).items():
            btn.blockSignals(True)
            btn.setChecked(v == text)
            btn.blockSignals(False)

    def shift_date(self, direction):
        value = self.anchor.date()
        view = self.view.currentText()
        self.anchor.setDate(value.addMonths(direction) if view == "Month" else value.addDays(direction * (7 if view == "Week" else 1)))

    def today(self):
        tz = self.zone.currentText() if hasattr(self, "zone") and self.zone.currentText() in zones() else self.db.setting("timezone", "Asia/Kolkata")
        return QDate.fromString(local_date(stamp(), tz), Qt.ISODate)

    def select_row(self, current, previous):
        if current.isValid() and current.row() < len(self.model.events):
            self.open_event(self.model.events[current.row()]["id"])

    def open_event(self, event_id):
        self.details.show_event(event_id, self.zone.currentText())
        if not self.right_drawer.isVisible():
            self.toggle_drawer(1)
        else:
            self.drawer_stack.setCurrentIndex(1)
            self.dock_detail_btn.setChecked(True)
            self.dock_filter_btn.setChecked(False)
            self.dock_metrics_btn.setChecked(False)

    def change_zone(self, zone):
        if zone not in zones():
            return
        self.db.set_setting("timezone", zone)
        self.anchor.setDate(self.today())
        if hasattr(self, "clock_widget"):
            self.clock_widget.set_zone(zone)
        self.refresh_events()
        self.notifications.reconcile()
        if self.details.event_id:
            self.open_event(self.details.event_id)
        self.refresh_notifications()

    def update_theme_btn_text(self, theme_mode):
        from app.ui.theme import resolve_theme
        resolved = resolve_theme(theme_mode)
        if "auto" in str(theme_mode).lower():
            self.theme_btn.setText(f"💻 Auto ({resolved})")
        elif resolved == "Clean Light":
            self.theme_btn.setText("☀️ Clean Light")
        else:
            self.theme_btn.setText("🌙 Dark Navy")

    def toggle_theme(self):
        themes = ["Dark Navy", "Clean Light", "Auto (System)"]
        curr = self.db.setting("theme_mode", self.current_theme)
        idx = themes.index(curr) if curr in themes else 0
        next_theme = themes[(idx + 1) % len(themes)]
        self.apply_theme(next_theme)

    def apply_theme(self, theme_name):
        self.db.set_setting("theme_mode", theme_name)
        from app.ui.theme import resolve_theme
        resolved = resolve_theme(theme_name)
        self.current_theme = resolved
        self.db.set_setting("theme", resolved)
        if hasattr(self, "theme_btn"):
            self.update_theme_btn_text(theme_name)
        if hasattr(self, "theme_combo"):
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText(theme_name)
            self.theme_combo.blockSignals(False)
        from app.ui.theme import get_style
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_style(resolved))
        if hasattr(self, "model"):
            self.model.set_theme(resolved)
        if hasattr(self, "details"):
            self.details.set_theme(resolved)
        if hasattr(self, "calendar"):
            self.calendar.set_theme(resolved)
        if hasattr(self, "article_view") and hasattr(self, "articles") and self.articles.currentItem():
            self.show_article(self.articles.currentItem())
        self.refresh_events()

    def run_task(self, function, on_done=None):
        if self.worker and self.worker.isRunning():
            self.statusBar().showMessage("Another background operation is still running", 5000)
            return
        self.statusBar().showMessage("Working in background… You can continue browsing stored records.")
        self.worker = Worker(function, self)
        self.worker.completed.connect(lambda result: self.task_done(result, on_done))
        self.worker.failed.connect(lambda message: self.task_failed(message))
        self.worker.start()

    def task_done(self, result, callback):
        self.statusBar().showMessage(result.describe() if hasattr(result, "describe") else str(result or "Completed"), 15000)
        self.refresh_facets()
        self.refresh_events()
        self.refresh_sources()
        self.refresh_notifications()
        if hasattr(self, "beacon"):
            self.beacon.set_live(self.is_any_source_enabled())
        if callback:
            callback(result)

    def task_failed(self, message):
        self.statusBar().showMessage(message, 20000)
        self.refresh_sources()
        if hasattr(self, "beacon"):
            self.beacon.set_live(self.is_any_source_enabled())
        QMessageBox.warning(self, "Operation incomplete", message)

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import event data", str(resource_path("sample_data")), "Event datasets (*.xlsx *.csv *.json);;Excel files (*.xlsx);;CSV files (*.csv);;JSON files (*.json)")
        if not path:
            return
        dialog = ImportDialog(self.db, path, self)
        if dialog.exec() != QDialog.Accepted:
            return
        sample = True if dialog.samples.isChecked() else None
        source = dialog.source.currentData()
        self.run_task(lambda: IngestionService(self.db).import_file(path, source, sample))

    def load_samples(self):
        self.scope.setCurrentIndex(0)
        self.run_task(lambda: load_demo(self.db))

    def show_article(self, current, previous=None):
        if not current:
            return
        row = current.data(Qt.UserRole)
        content = f"<h2>{escape(row['title'])}</h2><p>{escape(row['definition'])}</p><h3>WHY IT MATTERS</h3><p>{escape(row['importance'])}</p><h3>FREQUENCY</h3><p>{escape(row['frequency'])}</p><h3>SOURCE REFERENCES</h3>"
        for source in json.loads(row["sources"]):
            content += f'<p><a href="{escape(source)}">{escape(source)} ↗</a></p>'
        content += f"<p class='muted'>Original educational summary · reviewed {row['reviewed_at']}<br>Country-specific methodology and original documents prevail. No market impact is promised.</p>"
        self.article_view.setHtml(html_page(content, self.current_theme))

    def refresh_watchlists(self):
        current = self.watchlist_combo.currentData()
        self.watchlist_combo.blockSignals(True)
        self.watchlist_combo.clear()
        for row in self.db.rows("SELECT * FROM watchlists ORDER BY name"):
            self.watchlist_combo.addItem(row["name"], row["id"])
        self.watchlist_combo.setCurrentIndex(max(0, self.watchlist_combo.findData(current)))
        self.watchlist_combo.blockSignals(False)
        self.refresh_members()

    def refresh_members(self, *_):
        self.members.clear()
        for row in self.db.rows("SELECT member FROM watchlist_members WHERE watchlist_id=? ORDER BY member", (self.watchlist_combo.currentData(),)):
            self.members.addItem(row["member"])

    def new_watchlist(self):
        name, ok = QInputDialog.getText(self, "Create watchlist", "Name")
        if ok and name.strip():
            try:
                self.db.execute("INSERT INTO watchlists VALUES(?,?)", (str(uuid.uuid4()), name.strip()))
                self.refresh_watchlists()
            except Exception:
                QMessageBox.warning(self, "Watchlist", "This watchlist name already exists.")

    def add_member(self):
        member = self.member_input.text().strip()
        if member:
            self.db.execute("INSERT OR IGNORE INTO watchlist_members VALUES(?,?)", (self.watchlist_combo.currentData(), member))
            self.member_input.clear()
            self.refresh_members()
            self.notifications.reconcile()

    def remove_member(self):
        item = self.members.currentItem()
        if item:
            self.db.execute("DELETE FROM watchlist_members WHERE watchlist_id=? AND member=?", (self.watchlist_combo.currentData(), item.text()))
            self.refresh_members()
            self.notifications.reconcile()

    def watch_selected(self):
        event = self.repository.get(self.details.event_id) if self.details.event_id else None
        if not event or not (event.get("isin") or event.get("symbol") or event.get("company")):
            QMessageBox.information(self, "Watch company", "Select a corporate event with a supplied issuer identity.")
            return
        member = event.get("isin") or event.get("symbol") or event["company"]
        self.db.execute("INSERT OR IGNORE INTO watchlist_members VALUES('default',?)", (member,))
        self.notifications.reconcile()
        self.statusBar().showMessage(f"Added {member} to My watchlist", 8000)

    def edit_rule(self, selected=False):
        rule = None
        if selected:
            row = self.rules_table.currentRow()
            if row < 0:
                return
            rule = self.rule_rows[row]
        if RuleDialog(self.db, self.notifications, rule, self).exec() == QDialog.Accepted:
            self.refresh_notifications()

    def toggle_rule(self):
        row = self.rules_table.currentRow()
        if row >= 0:
            rule = self.rule_rows[row]
            self.db.execute("UPDATE notification_rules SET enabled=? WHERE id=?", (int(not rule["enabled"]), rule["id"]))
            self.notifications.reconcile()
            self.refresh_notifications()

    def refresh_notifications(self):
        self.rule_rows = self.notifications.rules()
        self.rules_table.setRowCount(len(self.rule_rows))
        for i, row in enumerate(self.rule_rows):
            filters = "; ".join(k + ": " + ", ".join(v) for k, v in row["filters"].items() if v) or "Any event"
            values = [row["name"], "Yes" if row["enabled"] else "No", filters, ", ".join(str(v / 60) for v in row["offsets"]), ", ".join(row["triggers"]), "Included" if row["include_samples"] else "Excluded"]
            for j, value in enumerate(values):
                self.rules_table.setItem(i, j, QTableWidgetItem(value))
        self.notification_rows = self.notifications.history()
        self.notification_table.setRowCount(len(self.notification_rows))
        for i, row in enumerate(self.notification_rows):
            values = [row["title"], row["trigger"], display_time(row["due_at"], self.zone.currentText()), row["state"], "Yes" if row["opened_at"] else "—", row["last_error"]]
            for j, value in enumerate(values):
                self.notification_table.setItem(i, j, QTableWidgetItem(value))

    def simulate(self):
        simulate_reminder(self.db)
        self.refresh_notifications()
        self.refresh_events()
        self.statusBar().showMessage("Sample reminder scheduled for approximately 10 seconds from now. Keep the application running.", 12000)

    def tick(self):
        try:
            count = self.notifications.dispatch(self.sink)
            if count or self.navigation.currentRow() == 8:
                self.refresh_notifications()
        except Exception as exc:
            self.statusBar().showMessage(f"Notification engine error: {type(exc).__name__}", 10000)

    def toast_opened(self, job_id, event_id):
        self.notifications.opened(job_id)
        self.restore_window()
        self.navigation.setCurrentRow(1)
        self.open_event(event_id)
        self.refresh_notifications()

    def toast_failed(self, job_id, detail):
        self.db.execute("UPDATE notification_jobs SET state='Failed',last_error=? WHERE id=?", (detail, job_id))
        self.refresh_notifications()

    def open_notification(self, row, column):
        job = self.notification_rows[row]
        self.navigation.setCurrentRow(1)
        self.open_event(job["event_id"])

    def refresh_sources(self):
        self.source_rows = self.sources.sources()
        self.source_table.setRowCount(len(self.source_rows))
        for i, row in enumerate(self.source_rows):
            if row["adapter"] == "import":
                status = "Connected" if row["enabled"] else "Import only"
            elif row["status"] == "Error":
                status = "Offline (Cached)" if row["last_success"] else "Connection Pending"
            else:
                status = row["status"]
            int_sec = row["interval_seconds"]
            interval_str = f"{int_sec} sec" if int_sec < 60 else f"{int_sec // 60} min"
            last_err = row["last_error"]
            if last_err and "ConnectionError" in last_err:
                diagnostic = "Live poll awaiting connection; cached database active."
            elif last_err:
                diagnostic = last_err
            else:
                diagnostic = row["rights_note"]
            values = [row["name"], status, "On" if row["enabled"] else "Off", interval_str, display_time(row["last_success"], self.zone.currentText()), diagnostic]
            for j, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.source_table.setItem(i, j, item)

    def enable_official_feeds(self):
        official_ids = ["sebi", "rbi_press", "rbi_notifications", "nse_announcements", "nse_circulars"]
        for sid in official_ids:
            self.db.execute("UPDATE data_sources SET enabled=1, failures=0, next_attempt=NULL, last_error='' WHERE id=?", (sid,))
        self.refresh_sources()
        if hasattr(self, "beacon"):
            self.beacon.set_live(True)
        self.statusBar().showMessage("Enabled official NSE, SEBI and RBI live feeds. Refreshing live records in background...", 10000)
        self.refresh_due(force=True)

    def configure_source(self):
        row = self.source_table.currentRow()
        if row < 0:
            return
        source = self.source_rows[row]
        if SourceDialog(self.db, source, self).exec() == QDialog.Accepted:
            self.refresh_sources()
            if hasattr(self, "beacon"):
                self.beacon.set_live(self.is_any_source_enabled())
            self.run_task(lambda: self.sources.refresh(source["id"], force=True))

    def configure_api_keys(self):
        if ApiKeyDialog(self.db, self).exec() == QDialog.Accepted:
            self.statusBar().showMessage("API keys saved. Refreshing live data in background...", 8000)
            self.refresh_sources()
            if hasattr(self, "beacon"):
                self.beacon.set_live(self.is_any_source_enabled())
            self.refresh_due(force=True)
            if self.details.event_id:
                self.details.show_event(self.details.event_id, self.zone.currentText())

    def on_prev_month(self):
        self.anchor.setDate(self.anchor.date().addMonths(-1))

    def on_next_month(self):
        self.anchor.setDate(self.anchor.date().addMonths(1))

    def on_today_clicked(self):
        self.anchor.setDate(self.today())

    def handle_drawer_action(self, action, event_id):
        if action in ("gemini-generate", "gemini-refresh"):
            self.generate_ai_analysis(event_id, force=(action == "gemini-refresh"))
        elif action == "gemini-config":
            self.configure_api_keys()

    def generate_ai_analysis(self, event_id, force=False):
        key = get_gemini_api_key(self.db)
        if not key:
            if ApiKeyDialog(self.db, self).exec() == QDialog.Accepted:
                key = get_gemini_api_key(self.db)
        if not key:
            self.statusBar().showMessage("Gemini API key is required to generate AI insights.", 8000)
            return

        event = self.repository.get(event_id)
        if not event:
            return

        title_trunc = event.get("title", "")[:40]
        self.statusBar().showMessage(f"✨ Gemini AI is analyzing real-time market impact for {title_trunc}...", 20000)
        
        def run_ai():
            from app.services.gemini import analyze_event_impact
            return analyze_event_impact(event, self.db, api_key=key, force=force)

        def on_done(res):
            if res.get("success"):
                self.statusBar().showMessage("✨ Gemini AI analysis ready and cached!", 10000)
                self.details.show_event(event_id, self.zone.currentText())
            else:
                self.statusBar().showMessage(res.get("error", "AI analysis failed"), 12000)
                QMessageBox.warning(self, "Gemini AI Analysis", res.get("error", "Failed to generate AI analysis."))

        self.run_task(run_ai, on_done)

    def refresh_selected(self):
        row = self.source_table.currentRow()
        if row < 0:
            return
        source = self.source_rows[row]
        self.run_task(lambda: self.sources.refresh(source["id"], force=True))

    def refresh_due(self, force=False):
        if self.worker and self.worker.isRunning():
            return
        enabled = [s for s in self.sources.sources() if s["enabled"] and s["adapter"] != "import"]
        if not enabled:
            if force:
                self.statusBar().showMessage("No live sources enabled. Configure a permitted source first.", 8000)
            return
        if force:
            for source in enabled:
                if not source["last_error"].startswith("HTTP 429"):
                    self.db.execute("UPDATE data_sources SET next_attempt=NULL, failures=0 WHERE id=?", (source["id"],))
        self.run_task(lambda: self.sources.refresh_due(force=force))

    def text_dialog(self, title, content):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(900, 600)
        layout = QVBoxLayout(dialog)
        view = browser()
        view.setHtml(html_page(content, self.current_theme))
        layout.addWidget(view)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def show_logs(self):
        html = "<h2>Ingestion history</h2><table><tr><th>Source</th><th>Started</th><th>Mode</th><th>Result</th></tr>"
        for row in self.db.rows("SELECT * FROM ingestion_logs ORDER BY id DESC LIMIT 100"):
            html += f"<tr><td>{escape(row['source_id'])}</td><td>{row['started_at']}</td><td>{row['mode']}</td><td>{row['status']} · {row['inserted']} added / {row['updated']} revised / {row['rejected']} rejected</td></tr>"
        html += "</table><h3>REJECTED RECORDS</h3>"
        for row in self.db.rows("SELECT * FROM ingestion_errors ORDER BY id DESC LIMIT 100"):
            html += f"<p>Run {row['run_id']} / row {row['row_number']}: {escape(row['message'])}</p>"
        self.text_dialog("Ingestion diagnostics", html)

    def show_duplicates(self):
        rows = self.db.rows("SELECT d.*,a.title AS title_a,b.title AS title_b FROM duplicate_candidates d JOIN events a ON a.id=d.event_a JOIN events b ON b.id=d.event_b ORDER BY d.id DESC LIMIT 200")
        html = "<h2>Possible duplicate filings</h2><p>These records remain separate because document equivalence has not been established. Automatic grouping requires matching ISIN, category, period and supplied document SHA-256.</p>"
        for row in rows:
            html += f"<h3>{escape(row['title_a'])}</h3><p>{escape(row['title_b'])}<br>{escape(row['reason'])}<br>Event IDs: {row['event_a']} / {row['event_b']}</p>"
        if not rows:
            html += "<p>No unresolved candidates.</p>"
        self.text_dialog("Potential duplicate review", html)

    def backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Back up local database", "EventScope-backup.db", "SQLite database (*.db)")
        if path:
            self.run_task(lambda: self.db.backup(path), lambda _: self.statusBar().showMessage("Database backup completed", 10000))

    def user_guide(self):
        self.text_dialog("Finstock EventScope user guide", "<pre style='white-space:pre-wrap'>" + escape(resource_path("docs/USER_MANUAL.md").read_text(encoding="utf-8")) + "</pre>")

    def restore_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Background operation", "Wait for the current source/import operation to finish before quitting.")
            return
        self.quitting = True
        self.notification_timer.stop()
        self.refresh_timer.stop()
        if hasattr(self, "second_timer"):
            self.second_timer.stop()
        self.tray.hide()
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        if not self.quitting and self.db.setting("close_to_tray", True) and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            event.ignore()
            return
        if self.worker and self.worker.isRunning():
            event.ignore()
            return
        self.notification_timer.stop()
        self.refresh_timer.stop()
        if hasattr(self, "second_timer"):
            self.second_timer.stop()
        self.tray.hide()
        event.accept()
