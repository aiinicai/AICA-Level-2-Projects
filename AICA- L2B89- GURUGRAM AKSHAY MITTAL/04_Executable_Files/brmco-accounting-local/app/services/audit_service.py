"""Audit trail of significant user actions (CA-office traceability)."""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from app.database.repositories import AuditRepository

logger = logging.getLogger("brmco.audit")


class AuditAction(str, Enum):
    TEMPLATE_DOWNLOADED = "TEMPLATE_DOWNLOADED"
    EXCEL_UPLOADED = "EXCEL_UPLOADED"
    VALIDATION_PERFORMED = "VALIDATION_PERFORMED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    XML_GENERATED = "XML_GENERATED"
    XML_DOWNLOADED = "XML_DOWNLOADED"
    TALLY_POST_ATTEMPTED = "TALLY_POST_ATTEMPTED"
    TALLY_POST_SUCCESS = "TALLY_POST_SUCCESS"
    TALLY_POST_FAILED = "TALLY_POST_FAILED"
    TALLY_CONNECTION_TESTED = "TALLY_CONNECTION_TESTED"
    MASTER_SYNC = "MASTER_SYNC"
    LEDGER_CREATE_ATTEMPTED = "LEDGER_CREATE_ATTEMPTED"
    LEDGER_CREATED = "LEDGER_CREATED"
    LEDGER_CREATE_FAILED = "LEDGER_CREATE_FAILED"
    SETTINGS_UPDATED = "SETTINGS_UPDATED"


class AuditService:
    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    def record(self, action: AuditAction, *, company: str = "", kind: str = "", batch_id: str = "",
               details: dict[str, Any] | str | None = None) -> None:
        try:
            self.repo.add(action.value, company_name=company, voucher_kind=kind, batch_id=batch_id, details=details)
        except Exception:
            # Auditing must never break the user's workflow, but the failure must be visible in logs.
            logger.exception("Could not write audit entry %s", action.value)
