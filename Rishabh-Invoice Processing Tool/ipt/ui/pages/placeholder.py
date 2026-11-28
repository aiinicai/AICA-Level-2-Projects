"""Shown for modules that are scheduled in a later phase. No buttons, so
there are no non-functional controls."""
from __future__ import annotations

from PySide6.QtCore import Qt

from ipt.ui.helpers import muted, title
from ipt.ui.pages.base import BasePage


class PlaceholderPage(BasePage):
    def __init__(self, services, name: str, phase: int, description: str, parent=None):
        super().__init__(services, parent)
        self.title_text = name
        self.layout_.addWidget(title(name))
        self.layout_.addWidget(muted(description))
        note = muted(f"This module is built in Phase {phase}. See docs/BUILD_PLAN.md.")
        self.layout_.addWidget(note)
        self.layout_.addStretch(1)
        self.layout_.setAlignment(Qt.AlignTop)
