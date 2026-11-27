"""Small helpers shared by the pages."""
from PyQt5.QtWidgets import QDoubleSpinBox, QSpinBox, QPushButton, QHBoxLayout


def money(maximum=1e12):
    s = QDoubleSpinBox()
    s.setRange(0, maximum)
    s.setDecimals(0)
    s.setGroupSeparatorShown(True)
    s.setSingleStep(100000)
    s.setMinimumWidth(150)
    return s


def pct(maximum=100.0, step=0.25, special=None):
    s = QDoubleSpinBox()
    s.setRange(-1 if special else 0, maximum)
    s.setDecimals(2)
    s.setSuffix(" %")
    s.setSingleStep(step)
    if special:
        s.setSpecialValueText(special)
    return s


def times(maximum=20.0, special=None):
    s = QDoubleSpinBox()
    s.setRange(-1 if special else 0, maximum)
    s.setDecimals(2)
    s.setSingleStep(0.05)
    if special:
        s.setSpecialValueText(special)
    return s


def buttons(page, specs):
    bar = QHBoxLayout()
    for text, fn, style in specs:
        b = QPushButton(text)
        if style:
            b.setObjectName(style)
        b.clicked.connect(lambda *_, f=fn: f())
        bar.addWidget(b)
    bar.addStretch()
    return bar


def opt_get(spin, scale=1.0):
    """Spin box with special value 'default' (minimum) -> None."""
    return None if spin.value() == spin.minimum() and spin.specialValueText() else spin.value() / scale


def opt_set(spin, value, scale=1.0):
    if value is None:
        spin.setValue(spin.minimum())
    else:
        spin.setValue(value * scale)


def rs(v):
    return "{:,.0f}".format(v or 0)


def lakh(v):
    return "{:,.2f}".format((v or 0) / 1e5)
