"""Read-only audit trail viewer."""
from __future__ import annotations

from ipt.core.timefmt import fmt

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton

from ipt.core.permissions import has_permission
from ipt.ui.helpers import fill_table, make_table, muted, title
from ipt.ui.pages.base import BasePage


class AuditPage(BasePage):
    title_text = "Audit Trail"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Audit Trail"))
        self.layout_.addWidget(muted("Every change is recorded here and cannot be edited or deleted. "
                                     "Passwords are never stored in this log."))
        bar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Filter by user, action, entity or remark")
        self.btn = QPushButton("Refresh")
        bar.addWidget(self.search, 1); bar.addWidget(self.btn)
        self.layout_.addLayout(bar)
        self.table = make_table(["When", "User", "Action", "Entity", "ID", "Before", "After", "Remark"])
        self.layout_.addWidget(self.table, 1)
        self.btn.clicked.connect(self.refresh)
        self.search.returnPressed.connect(self.refresh)

    def refresh(self):
        role = self.s.ctx.user.role if self.s.ctx.user else None
        rows = self.s.audit.recent(500, self.search.text()) if has_permission(role, "audit.view") else []
        fill_table(self.table, [[fmt(r.at, seconds=True), r.username, r.action,
                                 r.entity, r.entity_id, r.before_json, r.after_json, r.remark] for r in rows])
