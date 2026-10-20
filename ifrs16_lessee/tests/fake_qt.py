"""Minimal PySide6 stand-in used ONLY by test_ui_smoke.py so UI logic (form building, previews, refreshes) can be exercised on machines
without Qt/a display. Widgets that carry state (line edits, combos, tables, checkboxes, date edits) behave; everything else is a no-op."""
import sys
import types


class _Meta(type):
    def __getattr__(cls, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return _Any()


class _Any(metaclass=_Meta):
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return _Any()

    def __call__(self, *a, **k):
        return _Any()

    def __or__(self, o):
        return self

    def __ror__(self, o):
        return self

    def __invert__(self):
        return self

    def __and__(self, o):
        return self

    def connect(self, fn):
        pass

    def exec(self):
        return 0

    def emit(self, *a):
        pass


class _Bound:
    def __init__(self):
        self.fns = []
    def connect(self, fn): self.fns.append(fn)
    def emit(self, *a):
        for f in self.fns: f(*a)


class Signal:
    def __init__(self, *a):
        pass

    def __set_name__(self, owner, name):
        self.name = '_sig_' + name

    def __get__(self, o, t=None):
        if o is None:
            return self
        if self.name not in o.__dict__:
            o.__dict__[self.name] = _Bound()
        return o.__dict__[self.name]


class QDate:
    def __init__(self, y=2025, m=1, d=1):
        self.y, self.m, self.d = y, m, d

    def year(self): return self.y
    def month(self): return self.m
    def day(self): return self.d

    @staticmethod
    def currentDate():
        import datetime as dt
        t = dt.date.today(); return QDate(t.year, t.month, t.day)


class QDateEdit(_Any):
    def __init__(self, d=None, *a):
        self._d = d or QDate()
    def date(self): return self._d
    def setDate(self, d): self._d = d


class QLineEdit(_Any):
    def __init__(self, t=''):
        self._t = t
    def text(self): return self._t
    def setText(self, t): self._t = str(t)
    def setPlaceholderText(self, t): pass


class QPlainTextEdit(QLineEdit):
    def toPlainText(self): return self._t
    def setPlainText(self, t): self._t = str(t)
    def clear(self): self._t = ''


class QCheckBox(_Any):
    def __init__(self, *a):
        self._c = False
    def isChecked(self): return self._c
    def setChecked(self, v): self._c = bool(v)


class QSpinBox(_Any):
    def __init__(self):
        self._v = 0
    def value(self): return self._v
    def setValue(self, v): self._v = int(v)


class QComboBox(_Any):
    def __init__(self):
        self.items, self.i = [], 0
    def addItem(self, t, d=None): self.items.append((t, d))
    def addItems(self, ts): [self.addItem(t, t) for t in ts]
    def clear(self): self.items, self.i = [], 0
    def currentData(self): return self.items[self.i][1] if self.items else None
    def currentText(self): return self.items[self.i][0] if self.items else ''
    def findData(self, d):
        for k, (_, v) in enumerate(self.items):
            if v == d: return k
        return -1
    def setCurrentIndex(self, i): self.i = i
    def setCurrentText(self, t):
        for k, (a, _) in enumerate(self.items):
            if a == t: self.i = k


class QTableWidgetItem(_Any):
    def __init__(self, t=''):
        self._t = t
    def text(self): return self._t
    def flags(self): return _Any()
    def setFlags(self, f): pass


class QTableWidget(_Any):
    def __init__(self, r=0, c=0):
        self.r, self.c, self.cells, self._cur = r, c, {}, -1
    def rowCount(self): return self.r
    def columnCount(self): return self.c
    def setRowCount(self, n):
        self.r = n; self.cells = {k: v for k, v in self.cells.items() if k[0] < n}
    def insertRow(self, i): self.r += 1
    def removeRow(self, i): self.r -= 1; self.cells = {(a - (a > i), b): v for (a, b), v in self.cells.items() if a != i}
    def setItem(self, r, c, it): self.cells[(r, c)] = it
    def item(self, r, c): return self.cells.get((r, c))
    def currentRow(self): return self._cur
    def selectedItems(self): return []


class QWidget(_Any):
    pass


class QMessageBox(_Any):
    shown = []
    @classmethod
    def information(cls, *a): cls.shown.append(('info', a[1:])); return 0
    @classmethod
    def warning(cls, *a): cls.shown.append(('warn', a[1:])); return 0
    @classmethod
    def critical(cls, *a): cls.shown.append(('crit', a[1:])); return 0
    @classmethod
    def question(cls, *a): return cls.StandardButton.Yes


class _SB:
    Yes = 1; No = 2; Close = 3
QMessageBox.StandardButton = _SB


def install():
    core, gui, wid = (types.ModuleType(n) for n in ('PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'))
    pkg = types.ModuleType('PySide6'); pkg.__path__ = []
    core.Qt = _Any; core.QDate = QDate; core.Signal = Signal
    core.QEventLoop = type('QEventLoop', (_Any,), {})
    class QThread(_Any):
        def start(self):
            self.run()
        def wait(self): pass
    core.QThread = QThread
    gui.QColor = _Any
    local = {'QDateEdit': QDateEdit, 'QLineEdit': QLineEdit, 'QPlainTextEdit': QPlainTextEdit, 'QCheckBox': QCheckBox, 'QSpinBox': QSpinBox, 'QComboBox': QComboBox,
             'QTableWidget': QTableWidget, 'QTableWidgetItem': QTableWidgetItem, 'QWidget': QWidget, 'QMessageBox': QMessageBox}
    def gattr(mod):
        def f(name):
            if name.startswith('__'):
                raise AttributeError(name)
            return local.get(name, type(name, (_Any,), {}))
        return f
    for m in (core, gui, wid):
        m.__getattr__ = gattr(m)
    for k, v in local.items():
        setattr(wid, k, v)
    pkg.QtCore, pkg.QtGui, pkg.QtWidgets = core, gui, wid
    sys.modules.update({'PySide6': pkg, 'PySide6.QtCore': core, 'PySide6.QtGui': gui, 'PySide6.QtWidgets': wid})
