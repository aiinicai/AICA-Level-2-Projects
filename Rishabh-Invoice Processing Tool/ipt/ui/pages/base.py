"""Base class for every page in the main window."""
from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ipt.ui.services import Services


class BasePage(QWidget):
    title_text = "Page"

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.s = services
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(20, 16, 20, 16)
        self.layout_.setSpacing(10)

    def refresh(self) -> None:
        """Reload data. Called when shown and when company/FY changes."""
