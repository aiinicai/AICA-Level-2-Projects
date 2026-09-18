"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Custom Reusable UI Widgets (PyQt6)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QDateEdit,
    QPushButton,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QDoubleValidator
from utils import format_inr, parse_inr


class MetricCard(QFrame):
    """A card widget displaying a KPI metric (Title, Value in ₹, Subtext)."""

    def __init__(self, title: str, value: str = "₹0", subtext: str = "", card_type: str = "default", parent=None):
        super().__init__(parent)
        self.card_type = card_type
        self.init_ui(title, value, subtext)

    def init_ui(self, title: str, value: str, subtext: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        # Title
        self.title_label = QLabel(title.upper())
        self.title_label.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        layout.addWidget(self.title_label)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("color: #0F172A; font-size: 20px; font-weight: 800;")
        layout.addWidget(self.value_label)

        # Subtext
        self.subtext_label = QLabel(subtext)
        self.subtext_label.setStyleSheet("color: #64748B; font-size: 10.5px;")
        layout.addWidget(self.subtext_label)

        self.apply_style()

    def set_value(self, value: str, subtext: str = None):
        self.value_label.setText(value)
        if subtext is not None:
            self.subtext_label.setText(subtext)

    def apply_style(self):
        if self.card_type == "success":
            self.setStyleSheet("""
                MetricCard {
                    background-color: #ECFDF5;
                    border: 1.5px solid #10B981;
                    border-radius: 8px;
                }
            """)
            self.value_label.setStyleSheet("color: #047857; font-size: 20px; font-weight: 800;")
        elif self.card_type == "primary":
            self.setStyleSheet("""
                MetricCard {
                    background-color: #EFF6FF;
                    border: 1.5px solid #3B82F6;
                    border-radius: 8px;
                }
            """)
            self.value_label.setStyleSheet("color: #1D4ED8; font-size: 20px; font-weight: 800;")
        elif self.card_type == "warning":
            self.setStyleSheet("""
                MetricCard {
                    background-color: #FFFBEB;
                    border: 1.5px solid #F59E0B;
                    border-radius: 8px;
                }
            """)
            self.value_label.setStyleSheet("color: #B45309; font-size: 20px; font-weight: 800;")
        else:
            self.setStyleSheet("""
                MetricCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
            """)


class RecommendationBanner(QFrame):
    """Prominent dashboard result banner showcasing the winning method and tax saving."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        self.header_label = QLabel("⭐ MOST BENEFICIAL METHOD FOR ASSESSEE")
        self.header_label.setStyleSheet("color: #065F46; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")
        layout.addWidget(self.header_label)

        self.method_label = QLabel("CALCULATION PENDING")
        self.method_label.setStyleSheet("color: #064E3B; font-size: 22px; font-weight: 900;")
        layout.addWidget(self.method_label)

        self.details_label = QLabel("Fill in transaction details and click 'Calculate & Compare'.")
        self.details_label.setStyleSheet("color: #047857; font-size: 12px;")
        layout.addWidget(self.details_label)

        self.saving_label = QLabel("")
        self.saving_label.setStyleSheet("color: #059669; font-size: 16px; font-weight: 800; margin-top: 4px;")
        layout.addWidget(self.saving_label)

        self.setStyleSheet("""
            RecommendationBanner {
                background-color: #ECFDF5;
                border: 2px solid #059669;
                border-radius: 10px;
            }
        """)

    def update_result(
        self,
        recommended_method: str,
        tax_saving: float,
        tax_12_5: float,
        tax_20: Optional[float],
        is_20_applicable: bool,
        reason: str = "",
    ):
        if not is_20_applicable:
            self.header_label.setText("⚠ STATUTORY DETERMINATION")
            self.header_label.setStyleSheet("color: #92400E; font-size: 13px; font-weight: 800;")
            self.method_label.setText(recommended_method)
            self.method_label.setStyleSheet("color: #78350F; font-size: 20px; font-weight: 900;")
            self.details_label.setText(f"20% Indexed Method Not Applicable: {reason}\nTax payable at 12.5%: {format_inr(tax_12_5)}")
            self.details_label.setStyleSheet("color: #92400E; font-size: 11.5px;")
            self.saving_label.setText("")
            self.setStyleSheet("""
                RecommendationBanner {
                    background-color: #FFFBEB;
                    border: 2px solid #D97706;
                    border-radius: 10px;
                }
            """)
        else:
            self.header_label.setText("⭐ MOST BENEFICIAL METHOD FOR ASSESSEE")
            self.header_label.setStyleSheet("color: #065F46; font-size: 13px; font-weight: 800;")
            self.method_label.setText(recommended_method)
            self.method_label.setStyleSheet("color: #064E3B; font-size: 22px; font-weight: 900;")

            tax_20_val = tax_20 if tax_20 is not None else 0.0
            self.details_label.setText(
                f"Tax under 12.5% Method: {format_inr(tax_12_5)}   |   Tax under 20% Indexed Method: {format_inr(tax_20_val)}"
            )
            self.details_label.setStyleSheet("color: #047857; font-size: 12.5px; font-weight: 500;")

            if tax_saving > 0:
                self.saving_label.setText(f"ESTIMATED TAX SAVING: {format_inr(tax_saving, show_paise=True)}")
            else:
                self.saving_label.setText("Tax liability is identical under both statutory options.")

            self.setStyleSheet("""
                RecommendationBanner {
                    background-color: #ECFDF5;
                    border: 2px solid #059669;
                    border-radius: 10px;
                }
            """)


class IndianCurrencyInput(QWidget):
    """An input field formatted with Indian currency notation and optional auto-updating preview."""

    valueChanged = pyqtSignal(float)

    def __init__(self, default_val: float = 0.0, show_preview: bool = True, parent=None):
        super().__init__(parent)
        self._value = float(default_val)
        self.show_preview = show_preview

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2 if show_preview else 0)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("0.00")
        if default_val > 0:
            show_paise = not float(default_val).is_integer()
            self.line_edit.setText(format_inr(default_val, show_symbol=False, show_paise=show_paise))
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.editingFinished.connect(self._on_editing_finished)
        layout.addWidget(self.line_edit)

        if self.show_preview:
            self.preview_label = QLabel(format_inr(default_val, show_paise=True))
            self.preview_label.setStyleSheet("color: #2563EB; font-size: 11px; font-weight: 600;")
            layout.addWidget(self.preview_label)
        else:
            self.preview_label = None

    def _on_text_changed(self, text: str):
        val = parse_inr(text)
        self._value = val
        if self.preview_label:
            self.preview_label.setText(format_inr(val, show_paise=True))
        self.valueChanged.emit(val)

    def _on_editing_finished(self):
        if self._value > 0:
            show_paise = not float(self._value).is_integer()
            formatted = format_inr(self._value, show_symbol=False, show_paise=show_paise)
            if self.line_edit.text() != formatted:
                self.line_edit.setText(formatted)

    def value(self) -> float:
        return self._value

    def setValue(self, val: float):
        self._value = float(val)
        if val != 0:
            show_paise = not float(val).is_integer()
            self.line_edit.setText(format_inr(val, show_symbol=False, show_paise=show_paise))
        else:
            self.line_edit.setText("")
        if self.preview_label:
            self.preview_label.setText(format_inr(val, show_paise=True))


def create_date_picker(default_date: QDate = None) -> QDateEdit:
    """Creates a standardized Date Picker with calendar popup in DD/MM/YYYY format."""
    de = QDateEdit()
    de.setCalendarPopup(True)
    de.setDisplayFormat("dd/MM/yyyy")
    de.setDate(default_date or QDate.currentDate())
    return de
