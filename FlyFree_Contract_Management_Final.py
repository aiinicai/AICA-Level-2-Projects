"""FlyFree Contract Management System v7 Offline — Python 3, PyQt6, Faker.
Run in IDLE with F5. Install packages: py -m pip install PyQt6 Faker
Six password-protected local profiles. Notifications remain inside FlyFree.
Data saves locally in the user's application-data directory. CSV exports use UTF-8 BOM.
"""
import sys
import os
import csv
import json
import random
import copy
import hashlib
import hmac
import secrets
import time
import shutil
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation

try:
    from faker import Faker
    from PyQt6.QtCore import Qt, QDate, QLockFile, QTimer, QUrl
    from PyQt6.QtGui import QColor, QDesktopServices
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QComboBox, QStackedWidget, QTableWidget, QTableWidgetItem,
        QHeaderView, QAbstractItemView, QDialog, QFormLayout, QLineEdit,
        QDoubleSpinBox, QDialogButtonBox, QMessageBox, QFrame, QFileDialog,
        QSplitter, QTabWidget, QTextEdit, QScrollArea, QDateEdit, QCheckBox,
    )
except ImportError as exc:
    raise SystemExit(f'{exc}\n\nOpen Windows Command Prompt and run:\n'
                     'py -m pip install PyQt6 Faker\n\nThen open this file in IDLE and press F5.') from exc

STAGES = ['Originator', 'Department Manager', 'Procurement', 'Legal', 'CFO', 'CEO']
PROFILES = [f'User {i + 1:02d} | {role}' for i, role in enumerate(STAGES)]
COLORS = {'Pending Review': '#efc66d', 'Approved': '#73e0b4', 'Rejected': '#ff929c',
          'Escalated': '#c1adff', 'Available': '#73e0b4', 'Maintenance': '#efc66d',
          'In Flight': '#8bc5ff', 'Unread': '#efc66d', 'Read': '#9fafc6'}
STYLE = '''
QWidget { background:#101827; color:#e6edf7; font-family:"Segoe UI"; font-size:13px; }
QFrame#sidebar { background:#162235; border-right:1px solid #30415a; }
QLabel#brand { color:#88c6ff; font-size:29px; font-weight:800; }
QLabel#title { font-size:24px; font-weight:700; }
QLabel#section { font-size:17px; font-weight:700; color:#c7def9; }
QLabel#muted { color:#a6b6cc; }
QLabel#notice { background:#183c3b; color:#a3f0d4; padding:12px; border-radius:8px; }
QPushButton { background:#263c58; border:1px solid #496181; border-radius:7px;
 padding:10px 14px; font-weight:600; }
QPushButton:hover { background:#365a82; border-color:#8ac6ff; }
QPushButton:checked { background:#235c9e; border:2px solid #86c5ff; }
QPushButton:disabled { background:#1d293c; color:#6f819b; border-color:#30415a; }
QPushButton#metric { text-align:left; padding:14px; font-size:15px; }
QPushButton#primary { background:#2562ac; }
QPushButton#approve { background:#17634c; }
QPushButton#reject { background:#823848; }
QLineEdit,QComboBox,QDoubleSpinBox,QTextEdit { background:#1b2a40; border:1px solid #405776;
 border-radius:6px; padding:8px; selection-background-color:#2b6199; }
QComboBox QAbstractItemView { background:#1b2a40; selection-background-color:#2b6199; }
QTableWidget { background:#152236; alternate-background-color:#1c2c43; border:1px solid #344c69;
 gridline-color:#2c405b; selection-background-color:#2c527b; selection-color:white; }
QTableWidget::item { padding:7px; }
QHeaderView::section { background:#243852; color:#ccddf3; padding:10px; border:0;
 border-bottom:1px solid #47617e; font-weight:600; }
QTabWidget::pane { border:1px solid #344c69; }
QTabBar::tab { background:#1c2c43; padding:11px 17px; margin-right:3px; }
QTabBar::tab:selected { background:#2b527e; color:white; }
QSplitter::handle { background:#344c69; width:7px; height:7px; }
QScrollBar:vertical { background:#152236; width:14px; }
QScrollBar::handle:vertical { background:#527294; min-height:28px; border-radius:5px; }
QToolTip { background:#294564; color:white; border:1px solid #7fb5ed; }
'''


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def csv_cell(value):
    # Prevent names/comments beginning with formula operators from executing in Excel.
    text = str(value)
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


def write_csv(path, headers, rows):
    with open(path, 'w', newline='', encoding='utf-8-sig') as output:
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows([[csv_cell(value) for value in row] for row in rows])


class Engine:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        if self.path and self.path.exists():
            with self.path.open(encoding='utf-8') as handle:
                self.data = json.load(handle)
            self.validate()
            self.upgrade_contract_fields()
        else:
            self.data = {'version': 2, 'sequence': 1, 'fleet': [], 'contracts': [],
                         'history': [], 'notifications': []}
            self.seed()
            self.save()

    def upgrade_contract_fields(self):
        """Backfill identifiable demo rows; never invent dates for user-created rows."""
        changed = False
        backup = copy.deepcopy(self.data)
        descriptions = [
            'Executive charter services within the GCC.',
            'Aircraft management and operational support services.',
            'Corporate shuttle flights between GCC business hubs.',
            'Ad hoc VIP charter flights and ground coordination.',
            'Dedicated aircraft charter capacity for regional operations.',
        ]
        demo_ids = {h['contract'] for h in self.data['history']
                    if h.get('stage') == 'Originator'
                    and h.get('comment') == 'Demo charter contract submitted.'}
        for i, c in enumerate(self.data['contracts']):
            if all(key in c for key in ('start_date', 'end_date', 'description')):
                continue
            changed = True
            if c['id'] in demo_ids:
                start = date.fromisoformat(c['created'][:10]) + timedelta(days=(i % 10) * 7)
                c.setdefault('start_date', start.isoformat())
                c.setdefault('end_date', (start + timedelta(days=[90, 180, 365][i % 3])).isoformat())
                c.setdefault('description', descriptions[i % len(descriptions)])
            else:
                c.setdefault('start_date', '')
                c.setdefault('end_date', '')
                c.setdefault('description', '')
        if changed:
            if self.path:
                backup_path = self.path.with_name('flyfree_data_before_dates.json')
                if not backup_path.exists():
                    with backup_path.open('x', encoding='utf-8') as handle:
                        json.dump(backup, handle, indent=2, ensure_ascii=False)
            self.save()

    def validate(self):
        d = self.data
        if not isinstance(d, dict) or d.get('version') != 2:
            raise ValueError('Unsupported data-file format.')
        for key in ('fleet', 'contracts', 'history', 'notifications'):
            if not isinstance(d.get(key), list):
                raise ValueError(f'Invalid saved {key}.')
        if not isinstance(d.get('sequence'), int):
            raise ValueError('Invalid saved contract sequence.')
        for c in d['contracts']:
            if c['status'] not in ('Pending Review', 'Escalated', 'Approved', 'Rejected'):
                raise ValueError('Invalid saved contract status.')
            if c['stage'] not in range(1, 6):
                raise ValueError('Invalid saved workflow stage.')
            if not Decimal(c['value']).is_finite() or Decimal(c['value']) <= 0:
                raise ValueError('Invalid saved contract value.')

    def save(self):
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as handle:
            json.dump(self.data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    def transaction(self, function, *args):
        before = copy.deepcopy(self.data)
        try:
            result = function(*args)
            self.save()
            return result
        except Exception:
            self.data = before
            raise

    def log(self, c, stage, status, actor, comment):
        self.data['history'].append({'time': now(), 'contract': c['id'], 'stage': stage,
            'status': status, 'actor': actor, 'comment': comment})

    def notify(self, c, recipient, message):
        self.data['notifications'].append({'id': len(self.data['notifications']) + 1,
            'time': now(), 'contract': c['id'], 'recipient': recipient,
            'message': message, 'read': False})

    def get(self, contract_id):
        for c in self.data['contracts']:
            if c['id'] == contract_id:
                return c
        raise ValueError('Contract not found.')

    def create(self, role, client, tail, value, comment, start_date, end_date, description):
        if role != 'Originator':
            raise ValueError('Only the Originator profile can submit new contracts.')
        if not client.strip() or not comment.strip():
            raise ValueError('Client name and submission comments are required.')
        if tail not in {a['tail'] for a in self.data['fleet']}:
            raise ValueError('Select an aircraft from the fleet.')
        if not description.strip():
            raise ValueError('Enter a brief contract description.')
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except (ValueError, TypeError) as exc:
            raise ValueError('Enter valid start and end dates (YYYY-MM-DD).') from exc
        if end < start:
            raise ValueError('Contract end date cannot be before its start date.')
        try:
            amount = Decimal(str(value))
            if not amount.is_finite() or amount <= 0 or amount > Decimal('999999999.99'):
                raise ValueError('Enter a valid positive contract value.')
            amount = amount.quantize(Decimal('0.01'))
        except InvalidOperation as exc:
            raise ValueError('Invalid contract value.') from exc
        c = {'id': f"FF-{self.data['sequence']:04d}", 'client': client.strip(), 'tail': tail,
             'value': str(amount), 'status': 'Pending Review', 'stage': 1,
             'originator': PROFILES[0], 'created': now(), 'custodian': 'Legal', 'finalized': '',
             'start_date': start.isoformat(), 'end_date': end.isoformat(),
             'description': description.strip()}
        self.data['sequence'] += 1
        self.data['contracts'].append(c)
        self.log(c, 'Originator', 'Pending Review', PROFILES[0], comment.strip())
        self.notify(c, 'Department Manager', 'New contract submitted for your review.')
        return c['id']

    def decide(self, role, contract_id, action, comment):
        c = self.get(contract_id)
        if c['status'] not in ('Pending Review', 'Escalated'):
            raise ValueError('This contract has a final decision and cannot be processed again.')
        if role != STAGES[c['stage']]:
            raise ValueError(f"Only {STAGES[c['stage']]} can act on this contract.")
        if action not in ('Approve', 'Reject', 'Escalate'):
            raise ValueError('Unknown action.')
        if not comment.strip():
            raise ValueError('Enter your comments before taking an action.')
        actor = PROFILES[STAGES.index(role)]
        if action == 'Approve':
            self.log(c, role, 'Approved', actor, comment.strip())
            if role == 'CEO':
                c['status'] = 'Approved'
                c['finalized'] = now()
                self.notify(c, 'Legal', 'CEO FINAL APPROVAL: retain this approved contract '
                            'in Legal custody and acknowledge receipt.')
            else:
                c['stage'] += 1
                c['status'] = 'Pending Review'
                next_role = STAGES[c['stage']]
                self.notify(c, next_role, f'{role} approved. Contract awaits your review.')
        elif action == 'Reject':
            c['status'] = 'Rejected'
            self.log(c, role, 'Rejected', actor, comment.strip())
            self.notify(c, 'Originator', f'Contract rejected by {role}. See approval history.')
        else:
            if c['status'] == 'Escalated':
                raise ValueError('Already escalated. Approve or reject after resolving the issue.')
            c['status'] = 'Escalated'
            self.log(c, role, 'Escalated', actor, comment.strip())
            self.notify(c, 'Originator', f'{role} escalated this contract. See comments in history.')

    def acknowledge(self, role, notification_id):
        for notification in self.data['notifications']:
            if notification['id'] == notification_id:
                if notification['recipient'] != role:
                    raise ValueError('This notification belongs to another profile.')
                notification['read'] = True
                return
        raise ValueError('Notification not found.')

    def seed(self):
        fake = Faker('en_GB')
        models = ['Gulfstream G650', 'Challenger 650', 'Falcon 8X', 'Praetor 600', 'Citation XLS+']
        for i in range(15):
            self.data['fleet'].append({'tail': ('A6-' if i < 10 else 'T7-') + 'FF' + chr(65 + i),
                'model': random.choice(models),
                'status': random.choice(['Available', 'Maintenance', 'In Flight']),
                'inspected': str(fake.date_between(start_date='-180d', end_date='today'))})
        descriptions = ['Executive charter services within the GCC.',
            'Aircraft management and operational support services.',
            'Corporate shuttle flights between GCC business hubs.',
            'Ad hoc VIP charter flights and ground coordination.',
            'Dedicated aircraft charter capacity for regional operations.']
        for i in range(30):
            start = fake.date_between(start_date='-90d', end_date='+90d')
            end = start + timedelta(days=random.choice([30, 90, 180, 365, 730]))
            cid = self.create('Originator', fake.company(), self.data['fleet'][i % 15]['tail'],
                             random.randrange(50000, 2000001, 5000), 'Demo charter contract submitted.',
                             start.isoformat(), end.isoformat(), descriptions[i % len(descriptions)])
            # First twenty contracts cover all five approval inboxes.
            if i < 20:
                count, outcome = i % 5, 'Pending Review'
            elif i < 25:
                count, outcome = 5, 'Approved'
            else:
                count, outcome = (i - 25) % 5, ('Rejected' if i % 2 else 'Escalated')
            for _ in range(count):
                self.decide(STAGES[self.get(cid)['stage']], cid, 'Approve',
                            'Demo review completed; requirements verified.')
            if outcome in ('Rejected', 'Escalated'):
                self.decide(STAGES[self.get(cid)['stage']], cid,
                            'Reject' if outcome == 'Rejected' else 'Escalate',
                            'Demo commercial clarification required.')
        # Seed assignment notices are historical; final Legal custody notices remain unread.
        for n in self.data['notifications']:
            n['read'] = not n['message'].startswith('CEO FINAL APPROVAL')


def table(headers):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setAlternatingRowColors(True)
    widget.setWordWrap(False)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    widget.verticalHeader().setVisible(False)
    widget.verticalHeader().setDefaultSectionSize(44)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    widget.horizontalHeader().setStretchLastSection(True)
    for i in range(len(headers)):
        widget.setColumnWidth(i, 150)
    return widget


def fill(widget, rows):
    widget.blockSignals(True)
    widget.clearSelection()
    widget.setCurrentCell(-1, -1)
    widget.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for col, value in enumerate(row):
            item = QTableWidgetItem(str(value))
            item.setToolTip(str(value))
            if str(value) in COLORS:
                item.setForeground(QColor(COLORS[str(value)]))
            widget.setItem(r, col, item)
    widget.blockSignals(False)


def button(text, callback, style=''):
    result = QPushButton(text)
    result.setObjectName(style)
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    result.clicked.connect(lambda checked=False: callback())
    return result


def selected_text(widget, column=0):
    row = widget.currentRow()
    item = widget.item(row, column) if row >= 0 else None
    return item.text() if item else None


class CreateDialog(QDialog):
    def __init__(self, fleet, parent):
        super().__init__(parent)
        self.setWindowTitle('FlyFree | Originator submission')
        self.resize(650, 640)
        layout = QVBoxLayout(self)
        title = QLabel('Create & Submit Contract')
        title.setObjectName('section')
        layout.addWidget(title)
        form = QFormLayout()
        self.client = QLineEdit()
        self.client.setMaxLength(150)
        self.client.setPlaceholderText('Client / company name')
        self.tail = QComboBox()
        for a in fleet:
            self.tail.addItem(f"{a['tail']} | {a['model']} | {a['status']}", a['tail'])
        self.value = QDoubleSpinBox()
        self.value.setRange(0.01, 999999999.99)
        self.value.setDecimals(2)
        self.value.setPrefix('AED ')
        self.value.setGroupSeparatorShown(True)
        self.value.setValue(100000)
        self.start_date = QDateEdit(QDate.currentDate())
        self.end_date = QDateEdit(QDate.currentDate().addYears(1))
        for field in (self.start_date, self.end_date):
            field.setCalendarPopup(True)
            field.setDisplayFormat('yyyy-MM-dd')
        self.end_date.setMinimumDate(self.start_date.date())
        self.start_date.dateChanged.connect(self.end_date.setMinimumDate)
        self.description = QLineEdit()
        self.description.setMaxLength(500)
        self.description.setPlaceholderText('Brief scope / purpose of the contract')
        self.comment = QTextEdit()
        self.comment.setPlaceholderText('Required: contract purpose and submission comments')
        self.comment.setMinimumHeight(110)
        form.addRow('Client', self.client)
        form.addRow('Aircraft reference', self.tail)
        form.addRow('Financial value', self.value)
        form.addRow('Start date', self.start_date)
        form.addRow('End date', self.end_date)
        form.addRow('Brief description', self.description)
        form.addRow('Originator comments', self.comment)
        layout.addLayout(form)
        note = QLabel('Routes to Department Manager. Legal is the custodian.\n'
                      'Aircraft reference does not reserve a flight or confirm availability.')
        note.setObjectName('muted')
        note.setWordWrap(True)
        layout.addWidget(note)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        controls.button(QDialogButtonBox.StandardButton.Save).setText('Submit Contract')
        controls.accepted.connect(self.validate)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)

    def validate(self):
        if not self.client.text().strip() or not self.comment.toPlainText().strip():
            QMessageBox.warning(self, 'Required information', 'Enter a client name and submission comments.')
            return
        if not self.description.text().strip():
            QMessageBox.warning(self, 'Description required', 'Enter a brief contract description.')
            return
        if self.end_date.date() < self.start_date.date():
            QMessageBox.warning(self, 'Invalid dates', 'End date cannot be before start date.')
            return
        self.accept()


class Window(QMainWindow):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.current_contract = None
        self.drafts = {}
        self.last_role = 'Originator'
        self.setWindowTitle('FlyFree | Contract Management System v7 Offline')
        self.resize(1500, 940)
        self.setMinimumSize(1000, 700)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(210)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(18, 26, 18, 20)
        brand = QLabel('FlyFree')
        brand.setObjectName('brand')
        nav.addWidget(brand)
        nav.addWidget(QLabel('CONTRACT MANAGEMENT'))
        nav.addSpacing(25)
        self.nav = []
        for i, title in enumerate(['Fleet', 'Contracts', 'Approval Workflow', 'Notifications']):
            b = button(title, lambda index=i: self.navigate(index))
            b.setCheckable(True)
            nav.addWidget(b)
            self.nav.append(b)
        nav.addStretch()
        note = QLabel('CAPSTONE DEMO\n\nSix authenticated role profiles\nLocal data saving\nIn-app notifications\n\nPassword-protected accounts\nLocal in-app notifications')
        note.setWordWrap(True)
        note.setObjectName('muted')
        nav.addWidget(note)
        outer.addWidget(sidebar)
        content = QVBoxLayout()
        content.setContentsMargins(22, 20, 22, 16)
        content.setSpacing(12)
        outer.addLayout(content, 1)
        header = QHBoxLayout()
        self.title = QLabel('Fleet Overview')
        self.title.setObjectName('title')
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(QLabel('Active profile'))
        self.profile = QComboBox()
        self.profile.addItems(PROFILES)
        self.profile.setMinimumWidth(240)
        header.addWidget(self.profile)
        content.addLayout(header)
        self.role_hint = QLabel()
        self.role_hint.setObjectName('muted')
        self.role_hint.setWordWrap(True)
        content.addWidget(self.role_hint)
        metric_layout = QHBoxLayout()
        self.metrics = []
        for i in range(4):
            b = button('', lambda index=i: self.metric_clicked(index), 'metric')
            b.setCheckable(True)
            metric_layout.addWidget(b, 1)
            self.metrics.append(b)
        content.addLayout(metric_layout)
        self.legal_notice = QPushButton()
        self.legal_notice.setObjectName('approve')
        self.legal_notice.clicked.connect(lambda: self.navigate(3))
        content.addWidget(self.legal_notice)
        self.pages = QStackedWidget()
        content.addWidget(self.pages, 1)
        self.build_fleet()
        self.build_contracts()
        self.build_workflow()
        self.build_notifications()
        self.profile.currentIndexChanged.connect(self.profile_changed)
        self.refresh()
        self.navigate(0)

    def role(self):
        return STAGES[self.profile.currentIndex()]

    def new_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.pages.addWidget(page)
        return layout

    def build_fleet(self):
        layout = self.new_page()
        bar = QHBoxLayout()
        bar.addWidget(QLabel('15 aircraft • 10 A6- and 5 T7- registrations'))
        bar.addStretch()
        bar.addWidget(button('Export Fleet CSV', lambda: self.export_table(self.fleet_table, 'FlyFree_Fleet')))
        layout.addLayout(bar)
        self.fleet_table = table(['Tail Number', 'Aircraft Model', 'Status', 'Last Inspected'])
        self.fleet_table.setColumnWidth(1, 280)
        layout.addWidget(self.fleet_table)

    def build_contracts(self):
        layout = self.new_page()
        bar = QHBoxLayout()
        self.contract_search = QLineEdit()
        self.contract_search.setPlaceholderText('Search contract, client, aircraft or description…')
        self.contract_search.textChanged.connect(self.refresh_contracts)
        bar.addWidget(self.contract_search, 1)
        self.contract_filter = QComboBox()
        self.contract_filter.addItems(['All Contracts', 'Pending Review', 'Approved', 'Rejected', 'Escalated'])
        self.contract_filter.currentTextChanged.connect(self.refresh_contracts)
        bar.addWidget(self.contract_filter)
        bar.addWidget(button('Export Visible CSV', lambda: self.export_table(self.contract_table, 'FlyFree_Contracts')))
        self.create_button = button('+ Create Contract', self.create_contract, 'primary')
        bar.addWidget(self.create_button)
        layout.addLayout(bar)
        self.contract_count = QLabel()
        layout.addWidget(self.contract_count)
        self.contract_table = table(['Contract ID', 'Client', 'Aircraft', 'Value (AED)', 'Status',
                                     'Current / Final Stage', 'Custodian', 'CEO Approval Date',
                                     'Start Date', 'End Date', 'Brief Description'])
        self.contract_table.setColumnWidth(1, 230)
        self.contract_table.setColumnWidth(5, 190)
        self.contract_table.setColumnWidth(8, 130)
        self.contract_table.setColumnWidth(9, 130)
        self.contract_table.setColumnWidth(10, 370)
        self.contract_table.itemDoubleClicked.connect(lambda item: self.open_contract(selected_text(self.contract_table)))
        layout.addWidget(self.contract_table)
        hint = QLabel('Legal is custodian of all contracts. Double-click a contract to read its review details and history.')
        hint.setObjectName('muted')
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def build_workflow(self):
        layout = self.new_page()
        route = QLabel('Originator → Department Manager → Procurement → Legal → CFO → CEO → Legal custody notification')
        route.setWordWrap(True)
        layout.addWidget(route)
        toolbar = QHBoxLayout()
        self.workflow_scope = QComboBox()
        self.workflow_scope.addItems(['My Actionable Inbox', 'All Contracts (view / history)'])
        self.workflow_scope.currentIndexChanged.connect(self.refresh_inbox)
        toolbar.addWidget(self.workflow_scope)
        self.workflow_search = QLineEdit()
        self.workflow_search.setPlaceholderText('Search contract, client, aircraft or description…')
        self.workflow_search.textChanged.connect(self.refresh_inbox)
        toolbar.addWidget(self.workflow_search, 1)
        toolbar.addWidget(button('Export Inbox CSV', lambda: self.export_table(self.inbox, 'FlyFree_Approval_Inbox')))
        layout.addLayout(toolbar)
        self.inbox_count = QLabel()
        layout.addWidget(self.inbox_count)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.inbox = table(['Contract ID', 'Client', 'Status', 'Stage'])
        self.inbox.setMinimumWidth(300)
        self.inbox.horizontalHeader().setStretchLastSection(False)
        self.inbox.setColumnWidth(0, 100)
        self.inbox.setColumnWidth(2, 125)
        self.inbox.setColumnWidth(3, 150)
        self.inbox.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.inbox.itemSelectionChanged.connect(self.selection_changed)
        splitter.addWidget(self.inbox)
        right = QWidget()
        right.setMinimumWidth(380)
        panel = QVBoxLayout(right)
        panel.setContentsMargins(10, 0, 0, 0)
        self.detail_tabs = QTabWidget()
        review = QWidget()
        review_layout = QVBoxLayout(review)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.details = QLabel('Select a contract on the left.')
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setWordWrap(True)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.details.setMargin(12)
        scroll.setWidget(self.details)
        review_layout.addWidget(scroll, 1)
        self.review_hint = QLabel()
        self.review_hint.setWordWrap(True)
        self.review_hint.setObjectName('muted')
        review_layout.addWidget(self.review_hint)
        review_layout.addWidget(QLabel('Your comments — required before taking an action'))
        self.comments = QTextEdit()
        self.comments.setPlaceholderText('Record your review, conditions or reasons here…')
        self.comments.setMinimumHeight(105)
        self.comments.setMaximumHeight(170)
        review_layout.addWidget(self.comments)
        actions = QHBoxLayout()
        self.approve = button('Approve', lambda: self.take_action('Approve'), 'approve')
        self.reject = button('Reject', lambda: self.take_action('Reject'), 'reject')
        self.escalate = button('Escalate', lambda: self.take_action('Escalate'))
        for b in (self.approve, self.reject, self.escalate):
            actions.addWidget(b)
        review_layout.addLayout(actions)
        self.detail_tabs.addTab(review, 'Review & Comments')
        history_page = QWidget()
        history_layout = QVBoxLayout(history_page)
        history_bar = QHBoxLayout()
        history_bar.addWidget(button('Export Selected History', self.export_history))
        history_bar.addWidget(button('Export All History', lambda: self.export_history(True)))
        history_bar.addStretch()
        history_layout.addLayout(history_bar)
        self.history = table(['Timestamp', 'Stage', 'Decision', 'Approver', 'Comments'])
        self.history.setColumnWidth(0, 190)
        self.history.setColumnWidth(1, 170)
        self.history.setColumnWidth(3, 220)
        self.history.setColumnWidth(4, 360)
        history_layout.addWidget(self.history, 1)
        self.history_comment = QTextEdit()
        self.history_comment.setReadOnly(True)
        self.history_comment.setPlaceholderText('Select a history row to read its complete comment here.')
        self.history_comment.setMaximumHeight(170)
        history_layout.addWidget(self.history_comment)
        self.history.itemSelectionChanged.connect(self.show_history_comment)
        self.detail_tabs.addTab(history_page, 'Approval History')
        panel.addWidget(self.detail_tabs)
        splitter.addWidget(right)
        splitter.setSizes([570, 650])
        layout.addWidget(splitter, 1)

    def build_notifications(self):
        layout = self.new_page()
        bar = QHBoxLayout()
        self.notification_count = QLabel()
        bar.addWidget(self.notification_count)
        bar.addStretch()
        bar.addWidget(button('Export Notifications CSV', lambda: self.export_table(self.notification_table, 'FlyFree_Notifications')))
        self.ack_button = button('Acknowledge Selected', self.acknowledge, 'primary')
        bar.addWidget(self.ack_button)
        layout.addLayout(bar)
        self.notification_table = table(['ID', 'Timestamp', 'Contract', 'Recipient', 'Status', 'Message'])
        self.notification_table.setColumnWidth(0, 60)
        self.notification_table.setColumnWidth(1, 190)
        self.notification_table.setColumnWidth(5, 450)
        self.notification_table.itemSelectionChanged.connect(self.notification_selected)
        self.notification_table.itemDoubleClicked.connect(lambda item: self.open_contract(selected_text(self.notification_table, 2)))
        layout.addWidget(self.notification_table, 2)
        self.notification_message = QTextEdit()
        self.notification_message.setReadOnly(True)
        self.notification_message.setPlaceholderText('Select a notification to read the complete message. Double-click to open the contract.')
        layout.addWidget(self.notification_message, 1)

    def save_draft(self):
        if self.current_contract:
            self.drafts[(self.last_role, self.current_contract)] = self.comments.toPlainText()

    def profile_changed(self, *_):
        self.save_draft()
        self.last_role = self.role()
        self.current_contract = None
        self.refresh()
        self.statusBar().showMessage(f'Active profile: {self.profile.currentText()}', 5000)

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        for i, b in enumerate(self.nav):
            b.setChecked(i == index)
        self.title.setText(['Fleet Overview', 'Contract Register', 'Approval Workspace', 'Profile Notifications'][index])
        self.highlight_metrics()

    def metric_clicked(self, index):
        if index == 0:
            self.navigate(0)
            return
        self.contract_search.clear()
        self.contract_filter.setCurrentText({1: 'All Contracts', 2: 'Pending Review', 3: 'Approved'}[index])
        self.navigate(1)

    def highlight_metrics(self):
        active = None
        if self.pages.currentIndex() == 0:
            active = 0
        elif self.pages.currentIndex() == 1:
            active = {'All Contracts': 1, 'Pending Review': 2, 'Approved': 3}.get(self.contract_filter.currentText())
        for i, b in enumerate(self.metrics):
            b.setChecked(i == active)

    def refresh(self):
        contracts = self.engine.data['contracts']
        values = [len(self.engine.data['fleet']), len(contracts),
                  sum(c['status'] == 'Pending Review' for c in contracts),
                  sum(c['status'] == 'Approved' for c in contracts)]
        for b, label, value in zip(self.metrics, ['Aircraft', 'Contracts', 'Pending Review', 'Final Approved'], values):
            b.setText(f'{label}\n{value}')
        self.create_button.setEnabled(self.role() == 'Originator')
        self.role_hint.setText(f'{self.profile.currentText()} • ' +
            ('Submit contracts and track progress.' if self.role() == 'Originator' else
             'Legal custodian of all contracts. Approve only at the Legal stage; receive final CEO approvals.' if self.role() == 'Legal' else
             f'Approve, reject or escalate only contracts awaiting {self.role()}.'))
        fill(self.fleet_table, [(a['tail'], a['model'], a['status'], a['inspected']) for a in self.engine.data['fleet']])
        self.refresh_contracts()
        self.refresh_inbox()
        self.refresh_notifications()

    def refresh_contracts(self, *_):
        query = self.contract_search.text().strip().casefold()
        status = self.contract_filter.currentText()
        contracts = [c for c in self.engine.data['contracts'] if
            (status == 'All Contracts' or c['status'] == status) and
            query in f"{c['id']} {c['client']} {c['tail']} {c['description']}".casefold()]
        fill(self.contract_table, [(c['id'], c['client'], c['tail'], f"{Decimal(c['value']):,.2f}",
             c['status'], STAGES[c['stage']], 'Legal', c['finalized'],
             c['start_date'], c['end_date'], c['description']) for c in contracts])
        self.contract_count.setText(f'{len(contracts)} contracts shown • All values in AED • Custodian: Legal')
        self.highlight_metrics()

    def refresh_inbox(self, *_):
        self.save_draft()
        selected = self.current_contract
        query = self.workflow_search.text().strip().casefold()
        all_contracts = self.workflow_scope.currentIndex() == 1
        contracts = [c for c in self.engine.data['contracts'] if
            (all_contracts or (c['status'] in ('Pending Review', 'Escalated') and STAGES[c['stage']] == self.role()))
            and query in f"{c['id']} {c['client']} {c['tail']} {c['description']}".casefold()]
        fill(self.inbox, [(c['id'], c['client'], c['status'], STAGES[c['stage']]) for c in contracts])
        self.inbox_count.setText(f'{len(contracts)} contracts • ' + ('All contracts; actions restricted to your stage.' if all_contracts else f'Awaiting {self.role()}.'))
        target = next((i for i, c in enumerate(contracts) if c['id'] == selected), 0 if contracts else -1)
        self.current_contract = None
        if target >= 0:
            self.inbox.selectRow(target)
        else:
            self.selection_changed()

    def selection_changed(self):
        self.save_draft()
        self.current_contract = selected_text(self.inbox)
        self.comments.clear()
        self.history_comment.clear()
        if not self.current_contract:
            self.details.setText('No contract selected.\n\nChoose a contract, or use All Contracts to review past decisions.')
            fill(self.history, [])
            self.review_hint.setText('Originator creates contracts from the Contracts tab.')
            allowed = False
            escalated = False
        else:
            c = self.engine.get(self.current_contract)
            self.details.setText(f"{c['id']}\n\nClient: {c['client']}\nAircraft: {c['tail']}\n"
                f"Value: AED {Decimal(c['value']):,.2f}\nStatus: {c['status']}\n"
                f"Start date: {c['start_date'] or 'Not provided (legacy record)'}\n"
                f"End date: {c['end_date'] or 'Not provided (legacy record)'}\n"
                f"Description: {c['description'] or 'Not provided (legacy record)'}\n\n"
                f"Current / final stage: {STAGES[c['stage']]}\nCustodian: Legal\n"
                f"Originator: {c['originator']}\nSubmitted: {c['created']}\n"
                f"CEO final approval: {c['finalized'] or 'Not yet approved'}")
            allowed = c['status'] in ('Pending Review', 'Escalated') and STAGES[c['stage']] == self.role()
            escalated = c['status'] == 'Escalated'
            self.comments.setPlainText(self.drafts.get((self.role(), self.current_contract), ''))
            self.review_hint.setText(('Your stage: comments are required for every decision.' if allowed else
                'View only: this contract is finalized or belongs to another approval stage.'))
            entries = [h for h in self.engine.data['history'] if h['contract'] == c['id']]
            fill(self.history, [(h['time'], h['stage'], h['status'], h['actor'], h['comment']) for h in reversed(entries)])
        self.comments.setEnabled(allowed)
        self.approve.setEnabled(allowed)
        self.reject.setEnabled(allowed)
        self.escalate.setEnabled(allowed and not escalated)
        self.approve.setText('CEO Final Approval' if self.role() == 'CEO' else 'Approve Stage')

    def show_history_comment(self):
        self.history_comment.setPlainText(selected_text(self.history, 4) or '')

    def refresh_notifications(self):
        notices = [n for n in self.engine.data['notifications'] if n['recipient'] == self.role()]
        fill(self.notification_table, [(n['id'], n['time'], n['contract'], n['recipient'],
             'Read' if n['read'] else 'Unread', n['message']) for n in reversed(notices)])
        unread = sum(not n['read'] for n in notices)
        self.notification_count.setText(f'{self.role()}: {len(notices)} notifications • {unread} unread')
        self.nav[3].setText(f'Notifications ({unread})')
        finals = sum(not n['read'] and n['message'].startswith('CEO FINAL APPROVAL') for n in notices)
        self.legal_notice.setVisible(self.role() == 'Legal' and finals > 0)
        self.legal_notice.setText(f'LEGAL CUSTODY: {finals} final CEO approval notification(s) — click to review and acknowledge')
        self.notification_selected()

    def notification_selected(self):
        self.notification_message.setPlainText(selected_text(self.notification_table, 5) or '')
        self.ack_button.setEnabled(bool(selected_text(self.notification_table)) and
                                  selected_text(self.notification_table, 4) == 'Unread')

    def acknowledge(self):
        nid = selected_text(self.notification_table)
        if not nid:
            return
        try:
            self.engine.transaction(self.engine.acknowledge, self.role(), int(nid))
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Could not acknowledge', str(exc))
            return
        self.refresh_notifications()
        self.statusBar().showMessage('Notification acknowledged and saved.', 5000)

    def create_contract(self):
        if self.role() != 'Originator':
            return
        dialog = CreateDialog(self.engine.data['fleet'], self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            cid = self.engine.transaction(self.engine.create, self.role(), dialog.client.text(),
                dialog.tail.currentData(), dialog.value.value(), dialog.comment.toPlainText(),
                dialog.start_date.date().toString('yyyy-MM-dd'),
                dialog.end_date.date().toString('yyyy-MM-dd'), dialog.description.text())
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Contract not created', str(exc))
            return
        self.contract_search.clear()
        self.contract_filter.setCurrentText('All Contracts')
        self.refresh()
        self.navigate(1)
        self.statusBar().showMessage(f'{cid} submitted to Department Manager and saved.', 7000)

    def take_action(self, action):
        cid = self.current_contract
        if not cid:
            return
        comment = self.comments.toPlainText().strip()
        if not comment:
            QMessageBox.warning(self, 'Comments required', 'Enter your review comments before taking an action.')
            self.comments.setFocus()
            return
        if action == 'Reject' or (action == 'Approve' and self.role() == 'CEO'):
            message = (f'Reject {cid} and close the workflow?' if action == 'Reject' else
                       f'Give final CEO approval to {cid} and notify Legal as custodian?')
            if QMessageBox.question(self, 'Confirm decision', message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        try:
            self.engine.transaction(self.engine.decide, self.role(), cid, action, comment)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Decision not recorded', str(exc))
            return
        self.drafts.pop((self.role(), cid), None)
        self.comments.clear()
        self.refresh()
        message = f'{cid}: {action} recorded with your comments.'
        if action == 'Approve' and self.role() == 'CEO':
            message += ' Final notification delivered to the Legal profile.'
            QMessageBox.information(self, 'Final approval completed', message)
        self.statusBar().showMessage(message, 9000)

    def open_contract(self, cid):
        if not cid:
            return
        self.save_draft()
        self.workflow_scope.blockSignals(True)
        self.workflow_scope.setCurrentIndex(1)
        self.workflow_scope.blockSignals(False)
        self.workflow_search.blockSignals(True)
        self.workflow_search.clear()
        self.workflow_search.blockSignals(False)
        self.refresh_inbox()
        for row in range(self.inbox.rowCount()):
            if self.inbox.item(row, 0).text() == cid:
                self.inbox.selectRow(row)
                break
        self.detail_tabs.setCurrentIndex(0)
        self.navigate(2)

    def export_rows(self, headers, rows, name):
        path, _ = QFileDialog.getSaveFileName(self, 'Save CSV', name + '.csv', 'CSV files (*.csv)')
        if not path:
            return
        if not path.lower().endswith('.csv'):
            path += '.csv'
        try:
            write_csv(path, headers, rows)
        except (OSError, csv.Error, UnicodeError) as exc:
            QMessageBox.warning(self, 'Export failed', f'Could not write the CSV file.\n\n{exc}')
            return
        self.statusBar().showMessage(f'Exported {len(rows)} row(s) to {path}', 9000)

    def export_table(self, widget, name):
        headers = [widget.horizontalHeaderItem(col).text() for col in range(widget.columnCount())]
        rows = [[widget.item(r, col).text() if widget.item(r, col) else ''
                 for col in range(widget.columnCount())] for r in range(widget.rowCount()) if not widget.isRowHidden(r)]
        self.export_rows(headers, rows, name)

    def export_history(self, all_contracts=False):
        # Include the contract ID so a standalone history export remains identifiable.
        entries = [h for h in self.engine.data['history'] if all_contracts or h['contract'] == self.current_contract]
        rows = [(h['contract'], h['time'], h['stage'], h['status'], h['actor'], h['comment']) for h in reversed(entries)]
        self.export_rows(['Contract ID', 'Timestamp', 'Stage', 'Status', 'Approver', 'Comments'],
                         rows, 'FlyFree_All_History' if all_contracts else f'FlyFree_History_{self.current_contract or "No_Selection"}')

    def closeEvent(self, event):
        self.save_draft()
        if any(text.strip() for text in self.drafts.values()):
            result = QMessageBox.question(self, 'Unsubmitted comments',
                'Some review comments have not been submitted. Close and discard these drafts?\n'
                'Recorded decisions and submitted comments are already saved.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if result != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()



USERNAMES = ['originator', 'manager', 'procurement', 'legal', 'cfo', 'ceo']

def password_record(password):
    salt = secrets.token_bytes(16)
    return {'salt': salt.hex(), 'iterations': 600000,
            'hash': hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 600000).hex()}

def password_matches(password, record):
    candidate = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
        bytes.fromhex(record['salt']), record['iterations']).hex()
    return hmac.compare_digest(candidate, record['hash'])

def password_policy(password):
    if len(password) < 8:
        raise ValueError('Use at least 8 characters. A memorable passphrase is suitable.')
    if len(password) > 256:
        raise ValueError('Use no more than 256 characters.')

class LocalEngine(Engine):
    def __init__(self, path=None):
        self.initializing = True
        self.session_role = None
        super().__init__(path)
        self.data.setdefault('users', {})
        self.data.setdefault('recovery', None)
        self.initializing = False
        self.save()

    def require_role(self, role):
        if not self.initializing and self.session_role != role:
            raise ValueError('Please authenticate as the correct user first.')

    def create(self, role, *args):
        self.require_role(role)
        return super().create(role, *args)

    def acknowledge(self, role, notification_id):
        self.require_role(role)
        return super().acknowledge(role, notification_id)

    def setup_accounts(self, passwords):
        if self.data['users']:
            raise ValueError('Accounts have already been configured.')
        if len(passwords) != 6:
            raise ValueError('Set a password for each of the six profiles.')
        for password in passwords:
            password_policy(password)
        self.data['users'] = {username: dict(password_record(password), failed=0, locked_until=0)
                             for username, password in zip(USERNAMES, passwords)}
        recovery_code = secrets.token_urlsafe(24)
        self.data['recovery'] = password_record(recovery_code)
        return recovery_code

    def verify(self, index, password):
        record = self.data['users'][USERNAMES[index]]
        if time.time() < record.get('locked_until', 0):
            return False, 'Too many attempts. Wait one minute before trying again.'
        if not password_matches(password, record):
            record['failed'] = record.get('failed', 0) + 1
            if record['failed'] >= 5:
                record['locked_until'] = time.time() + 60
                record['failed'] = 0
            return False, 'Incorrect password. After five failures this account pauses for one minute.'
        record['failed'] = 0
        record['locked_until'] = 0
        return True, ''

    def change_password(self, index, old, new):
        self.require_role(STAGES[index])
        password_policy(new)
        username = USERNAMES[index]
        if not password_matches(old, self.data['users'][username]):
            raise ValueError('The current password is incorrect.')
        self.data['users'][username] = dict(password_record(new), failed=0, locked_until=0)

    def recover_password(self, index, code, new):
        password_policy(new)
        if not self.data['recovery'] or not password_matches(code, self.data['recovery']):
            raise ValueError('Recovery code is incorrect.')
        self.data['users'][USERNAMES[index]] = dict(password_record(new), failed=0, locked_until=0)

    def decide(self, role, contract_id, action, comment):
        self.require_role(role)
        super().decide(role, contract_id, action, comment)


class SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('FlyFree | First-time password setup')
        self.resize(650, 650)
        layout = QVBoxLayout(self)
        heading = QLabel('Set six local user passwords')
        heading.setObjectName('section')
        layout.addWidget(heading)
        info = QLabel('Choose at least 8 characters for each password. These protect your local accounts. '
                      'There are no default passwords.\n\n'
                      'A recovery code will be shown once after setup. Store it safely: it can reset any profile.')
        info.setWordWrap(True)
        layout.addWidget(info)
        self.fields = []
        form = QFormLayout()
        for role, username in zip(STAGES, USERNAMES):
            field = QLineEdit()
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setMaxLength(256)
            field.setPlaceholderText('At least 8 characters')
            self.fields.append(field)
            form.addRow(f'{role}\nUsername: {username}', field)
        show = QCheckBox('Show passwords while setting up')
        show.toggled.connect(lambda checked: [f.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password) for f in self.fields])
        layout.addLayout(form)
        layout.addWidget(show)
        layout.addWidget(button('Create Accounts', self.validate, 'primary'))
        layout.addWidget(button('Cancel', self.reject))

    def validate(self):
        try:
            for field in self.fields:
                password_policy(field.text())
        except ValueError as exc:
            QMessageBox.warning(self, 'Password requirements', str(exc))
            return
        self.accept()

class LoginDialog(QDialog):
    def __init__(self, engine, index=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle('FlyFree | Sign in')
        self.resize(470, 260)
        layout = QVBoxLayout(self)
        self.user = QComboBox()
        self.user.addItems([f'{username} | {role}' for username, role in zip(USERNAMES, STAGES)])
        if index is not None:
            self.user.setCurrentIndex(index)
            self.user.setEnabled(False)
        layout.addWidget(QLabel('Select your account and enter its FlyFree password.'))
        layout.addWidget(self.user)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMaxLength(256)
        self.password.setPlaceholderText('FlyFree password')
        self.password.returnPressed.connect(self.authenticate)
        layout.addWidget(self.password)
        layout.addWidget(button('Sign In', self.authenticate, 'primary'))
        layout.addWidget(button('Reset with Recovery Code', self.recover))
        layout.addWidget(button('Cancel', self.reject))

    def authenticate(self):
        try:
            ok, message = self.engine.transaction(self.engine.verify, self.user.currentIndex(), self.password.text())
        except OSError as exc:
            QMessageBox.warning(self, 'Cannot save login state', str(exc))
            return
        self.password.clear()
        if not ok:
            QMessageBox.warning(self, 'Sign-in unsuccessful', message)
            return
        self.accept()

    def recover(self):
        dialog = PasswordDialog(self.engine, self.user.currentIndex(), recovery=True, parent=self)
        dialog.exec()

class PasswordDialog(QDialog):
    def __init__(self, engine, index, recovery=False, parent=None):
        super().__init__(parent)
        self.engine, self.index, self.recovery = engine, index, recovery
        self.setWindowTitle('FlyFree | Reset password' if recovery else 'FlyFree | Change password')
        self.resize(500, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f'Account: {USERNAMES[index]} | {STAGES[index]}'))
        form = QFormLayout()
        self.old, self.new, self.confirm = QLineEdit(), QLineEdit(), QLineEdit()
        for field in (self.old, self.new, self.confirm):
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setMaxLength(256)
        form.addRow('Recovery code' if recovery else 'Current password', self.old)
        form.addRow('New password (8+ characters)', self.new)
        form.addRow('Confirm new password', self.confirm)
        layout.addLayout(form)
        layout.addWidget(button('Save Password', self.save_password, 'primary'))
        layout.addWidget(button('Cancel', self.reject))

    def save_password(self):
        if self.new.text() != self.confirm.text():
            QMessageBox.warning(self, 'Passwords differ', 'The new passwords do not match.')
            return
        try:
            fn = self.engine.recover_password if self.recovery else self.engine.change_password
            self.engine.transaction(fn, self.index, self.old.text(), self.new.text())
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Password not changed', str(exc))
            return
        QMessageBox.information(self, 'Password saved', 'The new password is ready to use.')
        self.accept()

class LocalWindow(Window):
    def __init__(self, engine, index):
        self.authenticated_index = index
        super().__init__(engine)
        self.profile.blockSignals(True)
        self.profile.setCurrentIndex(index)
        self.profile.blockSignals(False)
        self.last_role = self.role()
        self.current_contract = None
        sidebar_layout = self.nav[0].parentWidget().layout()
        sidebar_layout.insertWidget(7, button('Change Password', self.change_my_password))
        sidebar_layout.insertWidget(8, button('Lock / Sign Out', self.lock_session))
        self.refresh()

    def role(self):
        return STAGES[self.authenticated_index]

    def profile_changed(self, *_):
        requested = self.profile.currentIndex()
        previous = self.authenticated_index
        if requested == previous:
            return
        # Restore the selector until the target user authenticates successfully.
        self.profile.blockSignals(True)
        self.profile.setCurrentIndex(previous)
        self.profile.blockSignals(False)
        dialog = LoginDialog(self.engine, requested, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.save_draft()
        self.authenticated_index = requested
        self.engine.session_role = STAGES[requested]
        self.profile.blockSignals(True)
        self.profile.setCurrentIndex(requested)
        self.profile.blockSignals(False)
        self.last_role = self.role()
        self.current_contract = None
        self.refresh()
        self.statusBar().showMessage(f'Authenticated as {USERNAMES[requested]} | {self.role()}', 6000)

    def change_my_password(self):
        PasswordDialog(self.engine, self.authenticated_index, parent=self).exec()

    def lock_session(self):
        self.save_draft()
        self.engine.session_role = None
        self.hide()
        while True:
            dialog = LoginDialog(self.engine)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                index = dialog.user.currentIndex()
                self.authenticated_index = index
                self.engine.session_role = STAGES[index]
                self.profile.blockSignals(True)
                self.profile.setCurrentIndex(index)
                self.profile.blockSignals(False)
                self.last_role = self.role()
                self.current_contract = None
                self.refresh()
                self.show()
                return
            if QMessageBox.question(None, 'Exit FlyFree', 'Exit the application? Unsubmitted comment drafts will be discarded.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.drafts.clear()
                self.comments.clear()
                self.close()
                QApplication.instance().quit()
                return



DOCUMENT_TYPES = {'.pdf', '.docx', '.doc', '.txt', '.rtf', '.png', '.jpg', '.jpeg'}
DOCUMENT_FILTER = 'Documents (*.pdf *.docx *.doc *.txt *.rtf *.png *.jpg *.jpeg)'


def expiry_state(contract, today=None):
    """Only final-approved contracts generate operational expiry alerts."""
    if contract['status'] != 'Approved' or not contract.get('end_date'):
        return None
    try:
        days = (date.fromisoformat(contract['end_date']) - (today or date.today())).days
    except (ValueError, TypeError):
        return None
    if days < 0:
        return days, 'Expired'
    if days == 0:
        return days, 'Expires Today'
    for threshold in (7, 30, 60, 90):
        if days <= threshold:
            return days, f'{threshold}-day alert'
    return days, 'Beyond 90 days'


class DocumentEngine(LocalEngine):
    def __init__(self, path=None):
        super().__init__(path)
        self.data.setdefault('attachments', [])
        self.data.setdefault('expiry_alert_keys', [])
        self.save()

    @property
    def attachment_root(self):
        if not self.path:
            raise ValueError('A saved application data folder is required for document uploads.')
        return self.path.parent / 'contract_documents'

    def scan_expiry(self, today=None):
        today = today or date.today()
        recorded = set(self.data['expiry_alert_keys'])
        created = 0
        for c in self.data['contracts']:
            state = expiry_state(c, today)
            if not state or state[1] == 'Beyond 90 days':
                continue
            days, band = state
            key = f"{c['id']}|{c['end_date']}|{band}"
            if key in recorded:
                continue
            if days < 0:
                timing = f'expired {-days} day(s) ago'
            elif days == 0:
                timing = 'expires today'
            else:
                timing = f'expires in {days} day(s) — {band}'
            self.notify(c, 'Legal', f"CONTRACT EXPIRY: {c['id']} ({c['client']}) {timing}. "
                f"End date: {c['end_date']}. Legal: review renewal or closure requirements.")
            self.data['expiry_alert_keys'].append(key)
            recorded.add(key)
            created += 1
        return created

    def add_document(self, role, contract_id, source):
        self.require_role(role)
        self.get(contract_id)
        original = Path(source).expanduser().resolve(strict=True)
        if not original.is_file():
            raise ValueError('Choose a regular document file.')
        suffix = original.suffix.lower()
        if suffix not in DOCUMENT_TYPES:
            raise ValueError('Supported types: PDF, Word (.docx/.doc), text, RTF, PNG and JPEG.')
        size = original.stat().st_size
        if size == 0:
            raise ValueError('The selected file is empty.')
        if size > 100 * 1024 * 1024:
            raise ValueError('Each attachment must be 100 MB or smaller.')
        identifier = secrets.token_hex(16)
        self.attachment_root.mkdir(parents=True, exist_ok=True)
        destination = self.attachment_root / (identifier + suffix)
        try:
            with original.open('rb') as incoming, destination.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            metadata = {'id': identifier, 'contract': contract_id, 'filename': original.name,
                'stored_name': destination.name, 'size': destination.stat().st_size,
                'type': suffix.lstrip('.').upper(), 'uploaded': now(),
                'uploader': PROFILES[STAGES.index(role)]}
            def register():
                self.data['attachments'].append(metadata)
            self.transaction(register)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return identifier

    def document(self, document_id):
        for doc in self.data['attachments']:
            if doc['id'] == document_id:
                return doc
        raise ValueError('Document attachment not found.')

    def document_path(self, document_id):
        if not self.session_role:
            raise ValueError('Sign in before opening documents.')
        doc = self.document(document_id)
        name = doc['stored_name']
        if Path(name).name != name or Path(name).suffix.lower() not in DOCUMENT_TYPES:
            raise ValueError('Invalid attachment storage reference.')
        root = self.attachment_root.resolve()
        path = (root / name).resolve()
        if path.parent != root or not path.is_file():
            raise ValueError('The stored document is missing. Restore it from your document-folder backup.')
        return path


class DocumentWindow(LocalWindow):
    def __init__(self, engine, index):
        self.features_ready = False
        self.alert_popup_days = set()
        super().__init__(engine, index)
        self.build_alert_page()
        self.build_document_page()
        sidebar = self.nav[0].parentWidget().layout()
        for index, title in ((4, 'Expiry Alerts'), (5, 'Documents')):
            entry = button(title, lambda page=index: self.navigate(page))
            entry.setCheckable(True)
            self.nav.append(entry)
            sidebar.insertWidget(7 + index - 4, entry)
        # Provide a shortcut beside the existing contract register controls.
        self.contract_table.parentWidget().layout().insertWidget(1,
            button('Documents for Selected Contract', self.documents_from_register))
        self.detail_tabs.widget(0).layout().insertWidget(1,
            button('View Contract Documents', lambda: self.show_documents(self.current_contract)))
        self.features_ready = True
        self.refresh()
        self.expiry_timer = QTimer(self)
        self.expiry_timer.timeout.connect(self.check_alerts)
        self.expiry_timer.start(15 * 60 * 1000)
        QTimer.singleShot(0, self.startup_alerts)

    def build_alert_page(self):
        layout = self.new_page()
        info = QLabel('Approved contracts only • Legal receives in-app alerts at 90, 60, 30 and 7 days before expiry. '
            'Expiry today and expired contracts are also highlighted. Checks run at startup, after changes and every '
            '15 minutes while FlyFree is open. If a threshold was missed while closed, the current urgency is reported.')
        info.setObjectName('muted')
        info.setWordWrap(True)
        layout.addWidget(info)
        tools = QHBoxLayout()
        self.expiry_filter = QComboBox()
        self.expiry_filter.addItems(['All Alerts', 'Expired Contracts', 'Expires Today',
            'Within 7 Days', 'Within 30 Days', 'Within 60 Days', 'Within 90 Days', 'All Approved Contracts'])
        self.expiry_filter.currentTextChanged.connect(self.refresh_expiry_list)
        tools.addWidget(self.expiry_filter)
        self.expiry_search = QLineEdit()
        self.expiry_search.setPlaceholderText('Search client, contract or description…')
        self.expiry_search.textChanged.connect(self.refresh_expiry_list)
        tools.addWidget(self.expiry_search, 1)
        tools.addWidget(button('Check Alerts Now', self.check_alerts))
        tools.addWidget(button('Export Visible CSV', lambda: self.export_table(self.expiry_table, 'FlyFree_Expiry_Alerts')))
        layout.addLayout(tools)
        self.expiry_count = QLabel()
        self.expiry_count.setWordWrap(True)
        layout.addWidget(self.expiry_count)
        self.expiry_table = table(['Contract ID', 'Client', 'End Date', 'Days Remaining', 'Expiry Status', 'Description'])
        self.expiry_table.setColumnWidth(1, 230)
        self.expiry_table.setColumnWidth(5, 320)
        self.expiry_table.itemDoubleClicked.connect(lambda item: self.open_contract(selected_text(self.expiry_table)))
        layout.addWidget(self.expiry_table, 1)
        controls = QHBoxLayout()
        controls.addWidget(button('Review Selected Contract', lambda: self.open_contract(selected_text(self.expiry_table))))
        controls.addWidget(button('Documents for Selected Contract',
            lambda: self.show_documents(selected_text(self.expiry_table))))
        layout.addLayout(controls)
        foot = QLabel('Expiry status does not change approval history. Acknowledging an alert in Notifications '
            'does not remove the contract from this list. Dates use the computer’s local calendar date. '
            'Legacy contracts without an end date cannot generate expiry alerts.')
        foot.setObjectName('muted')
        foot.setWordWrap(True)
        layout.addWidget(foot)

    def build_document_page(self):
        layout = self.new_page()
        note = QLabel('Attach documents to a contract, then open them in the computer’s PDF, Word, image or text viewer. '
            'Each upload is copied into FlyFree’s local document folder. The original can be moved afterwards. '
            'All six signed-in users can upload and read attachments.')
        note.setWordWrap(True)
        note.setObjectName('muted')
        layout.addWidget(note)
        bar = QHBoxLayout()
        self.document_contract = QComboBox()
        self.document_contract.setMinimumWidth(280)
        self.document_contract.currentIndexChanged.connect(self.refresh_documents)
        bar.addWidget(self.document_contract, 1)
        self.upload_document_button = button('+ Add Documents', self.upload_documents, 'primary')
        bar.addWidget(self.upload_document_button)
        layout.addLayout(bar)
        self.document_count = QLabel()
        layout.addWidget(self.document_count)
        self.document_table = table(['Document ID', 'Contract', 'Filename', 'Type', 'Size (KB)', 'Uploaded', 'Uploaded By'])
        self.document_table.setColumnHidden(0, True)
        self.document_table.setColumnWidth(2, 300)
        self.document_table.setColumnWidth(5, 210)
        self.document_table.setColumnWidth(6, 220)
        self.document_table.itemSelectionChanged.connect(self.document_selection_changed)
        self.document_table.itemDoubleClicked.connect(lambda item: self.open_document())
        layout.addWidget(self.document_table, 1)
        actions = QHBoxLayout()
        self.open_document_button = button('Open & Read Document', self.open_document, 'primary')
        self.save_document_button = button('Save a Copy', self.save_document_copy)
        actions.addWidget(self.open_document_button)
        actions.addWidget(self.save_document_button)
        actions.addWidget(button('Export Attachment List CSV', lambda: self.export_table(self.document_table, 'FlyFree_Attachments')))
        layout.addLayout(actions)
        self.document_info = QLabel()
        self.document_info.setWordWrap(True)
        self.document_info.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.document_info)
        footer = QLabel('Supported: PDF, DOCX, DOC, TXT, RTF, PNG and JPEG • Maximum 100 MB per file. '
            'Opening requires a suitable installed viewer. This feature does not perform OCR or analyse contract clauses. '
            'Back up the application data folder together with its contract_documents subfolder.')
        footer.setObjectName('muted')
        footer.setWordWrap(True)
        layout.addWidget(footer)

    def navigate(self, index):
        if index < 4:
            super().navigate(index)
        else:
            self.pages.setCurrentIndex(index)
            self.title.setText('Expiry Alerts & Expired Contracts' if index == 4 else 'Contract Documents')
            for i, entry in enumerate(self.nav):
                entry.setChecked(i == index)
            self.highlight_metrics()
            if index == 4:
                self.refresh_expiry_list()
            else:
                self.refresh_documents()

    def refresh(self):
        super().refresh()
        if not self.features_ready:
            return
        self.refresh_expiry_list()
        selected = self.document_contract.currentData()
        self.document_contract.blockSignals(True)
        self.document_contract.clear()
        self.document_contract.addItem('All Contracts — choose one to upload', None)
        for c in self.engine.data['contracts']:
            self.document_contract.addItem(f"{c['id']} | {c['client']}", c['id'])
        index = self.document_contract.findData(selected)
        self.document_contract.setCurrentIndex(max(index, 0))
        self.document_contract.blockSignals(False)
        self.refresh_documents()
        self.check_alerts()

    def startup_alerts(self):
        self.check_alerts()
        key = (self.role(), date.today().isoformat())
        if self.role() != 'Legal' or key in self.alert_popup_days:
            return
        states = [expiry_state(c) for c in self.engine.data['contracts']]
        urgent = sum(s is not None and s[0] <= 90 for s in states)
        expired = sum(s is not None and s[0] < 0 for s in states)
        self.alert_popup_days.add(key)
        if urgent:
            QMessageBox.information(self, 'Legal | Contract expiry review',
                f'{urgent} approved contract(s) require expiry review, including {expired} expired contract(s).\n\n'
                'Open Expiry Alerts for the current list. Individual alerts are recorded in Legal Notifications.')

    def profile_changed(self, *_):
        super().profile_changed()
        if self.features_ready:
            QTimer.singleShot(0, self.startup_alerts)

    def check_alerts(self):
        if not self.features_ready:
            return
        try:
            # Avoid rewriting the data file when no threshold has changed.
            snapshot = copy.deepcopy(self.engine.data)
            changed = self.engine.scan_expiry()
            if changed:
                try:
                    self.engine.save()
                except OSError:
                    self.engine.data = snapshot
                    raise
                self.refresh_notifications()
        except (ValueError, OSError) as exc:
            self.statusBar().showMessage(f'Expiry alerts could not be saved: {exc}', 12000)
        self.refresh_expiry_list()

    def refresh_expiry_list(self, *_):
        if not self.features_ready:
            return
        mode = self.expiry_filter.currentText()
        query = self.expiry_search.text().strip().casefold()
        entries = []
        missing = 0
        for c in self.engine.data['contracts']:
            state = expiry_state(c)
            if c['status'] == 'Approved' and state is None:
                missing += 1
            if not state:
                continue
            days, band = state
            if query not in f"{c['id']} {c['client']} {c['description']}".casefold():
                continue
            include = (mode == 'All Approved Contracts' or
                (mode == 'All Alerts' and days <= 90) or
                (mode == 'Expired Contracts' and days < 0) or
                (mode == 'Expires Today' and days == 0))
            for threshold in (7, 30, 60, 90):
                if mode == f'Within {threshold} Days':
                    include = 0 <= days <= threshold
            if include:
                entries.append((days, c, band))
        entries.sort(key=lambda entry: (entry[0], entry[1]['id']))
        fill(self.expiry_table, [(c['id'], c['client'], c['end_date'], days, band, c['description'])
                                for days, c, band in entries])
        for row, (days, _, _) in enumerate(entries):
            color = '#ff929c' if days < 0 else '#efc66d' if days <= 30 else '#8bc5ff'
            for col in (3, 4):
                self.expiry_table.item(row, col).setForeground(QColor(color))
        self.expiry_count.setText(f'As of {date.today().isoformat()} • {len(entries)} contract(s) shown • '
                                 f'{missing} approved contract(s) have no valid end date')
        count = sum(expiry_state(c) is not None and expiry_state(c)[0] <= 90 for c in self.engine.data['contracts'])
        if len(self.nav) > 4:
            self.nav[4].setText(f'Expiry Alerts ({count})')

    def documents_from_register(self):
        cid = selected_text(self.contract_table)
        if not cid:
            QMessageBox.information(self, 'Select a contract', 'Select a contract row first.')
            return
        self.show_documents(cid)

    def show_documents(self, cid):
        if cid:
            index = self.document_contract.findData(cid)
            if index >= 0:
                self.document_contract.setCurrentIndex(index)
        self.navigate(5)

    def refresh_documents(self, *_):
        if not self.features_ready:
            return
        cid = self.document_contract.currentData()
        docs = [d for d in self.engine.data['attachments'] if not cid or d['contract'] == cid]
        fill(self.document_table, [(d['id'], d['contract'], d['filename'], d['type'],
             f"{d['size'] / 1024:,.1f}", d['uploaded'], d['uploader']) for d in reversed(docs)])
        self.upload_document_button.setEnabled(bool(cid))
        self.document_count.setText(f'{len(docs)} attachment(s) • ' + (cid or 'All contracts'))
        self.document_selection_changed()

    def document_selection_changed(self):
        identifier = selected_text(self.document_table)
        self.open_document_button.setEnabled(bool(identifier))
        self.save_document_button.setEnabled(bool(identifier))
        if identifier:
            doc = self.engine.document(identifier)
            self.document_info.setText(f"{doc['filename']}\nLinked to {doc['contract']} • Uploaded by {doc['uploader']}")
        else:
            self.document_info.setText('Choose a contract above to add documents. Select an attachment to open it.')

    def upload_documents(self):
        cid = self.document_contract.currentData()
        if not cid:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, f'Add documents to {cid}', '', DOCUMENT_FILTER)
        if not paths:
            return
        success, errors = 0, []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for path in paths:
                try:
                    self.engine.add_document(self.role(), cid, path)
                    success += 1
                except (ValueError, OSError) as exc:
                    errors.append(Path(path).name + ': ' + str(exc))
        finally:
            QApplication.restoreOverrideCursor()
        self.refresh_documents()
        self.statusBar().showMessage(f'{success} document(s) attached to {cid} and saved.', 8000)
        if errors:
            QMessageBox.warning(self, 'Some documents were not attached', '\n'.join(errors))

    def open_document(self):
        identifier = selected_text(self.document_table)
        if not identifier:
            return
        try:
            path = self.engine.document_path(identifier)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Cannot open attachment', str(exc))
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, 'No document viewer available',
                'Windows could not open the document. Install or select a suitable PDF/Word/image viewer, '
                'or use Save a Copy and open it manually.')

    def save_document_copy(self):
        identifier = selected_text(self.document_table)
        if not identifier:
            return
        try:
            source = self.engine.document_path(identifier)
            doc = self.engine.document(identifier)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Cannot read attachment', str(exc))
            return
        destination, _ = QFileDialog.getSaveFileName(self, 'Save Document Copy', doc['filename'], 'All files (*)')
        if not destination:
            return
        try:
            target = Path(destination).resolve()
            if target.parent == self.engine.attachment_root.resolve():
                raise ValueError('Choose a location outside the managed document folder for your copy.')
            shutil.copyfile(source, target)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Copy not saved', str(exc))
            return
        self.statusBar().showMessage(f'Document copy saved to {target}', 8000)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / '.local' / 'share'))
    path = base / 'FlyFree_Capstone_v2' / 'flyfree_data.json'
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        QMessageBox.critical(None, 'Data folder unavailable', str(exc))
        return
    instance_lock = QLockFile(str(path.with_suffix('.lock')))
    if not instance_lock.tryLock(0):
        QMessageBox.warning(None, 'FlyFree is already running',
            'Close the other FlyFree window before opening another instance.')
        return
    try:
        engine = DocumentEngine(path)
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
        QMessageBox.critical(None, 'Unable to open saved data', f'{path}\n\n{exc}\n\nExisting data has not been replaced.')
        return
    if not engine.data['users']:
        setup = SetupDialog()
        if setup.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            code = engine.transaction(engine.setup_accounts, [f.text() for f in setup.fields])
        except (ValueError, OSError) as exc:
            QMessageBox.critical(None, 'Setup unsuccessful', str(exc))
            return
        for field in setup.fields:
            field.clear()
        notice = QMessageBox()
        notice.setWindowTitle('Save your FlyFree recovery code')
        notice.setText('Store this recovery code safely. It can reset any of the six accounts.\n\n' + code +
                       '\n\nThis code is shown only once. Keep it safely for account recovery.')
        notice.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        notice.exec()
    login = LoginDialog(engine)
    if login.exec() != QDialog.DialogCode.Accepted:
        return
    index = login.user.currentIndex()
    engine.session_role = STAGES[index]
    window = DocumentWindow(engine, index)
    window.show()
    app.exec()

if __name__ == '__main__':
    main()
