import datetime
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from reconai.models.transaction import StatementTransaction, LedgerEntry, MatchRecord, AuditFlag
from reconai.config import AppConfig


class AuditTrailEvent(BaseModel):
    """Audit trail record tracking system and user actions."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    action: str = Field(..., description="e.g. INGEST_STATEMENT, AUTO_RECONCILE, MANUAL_MATCH, UNPAIR_MATCH, RUN_AUDIT")
    details: str = Field(..., description="Detailed description of the change")
    user: str = Field(default="Auditor")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReconciliationSession(BaseModel):
    """Encapsulates a full reconciliation workspace session."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: Optional[str] = Field(default=None, description="Linked Client Master ID")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    client_name: str = Field(default="SUN HEALTH CARE")
    period_label: str = Field(default="2025-26 Q3")
    auditor_remarks: str = Field(default="", description="Auditor review remarks and observations")
    partner_opinion: str = Field(default="", description="Chartered Accountant professional opinion / qualification")
    config: AppConfig = Field(default_factory=AppConfig)
    
    statements: List[StatementTransaction] = Field(default_factory=list)
    ledger_entries: List[LedgerEntry] = Field(default_factory=list)
    matches: List[MatchRecord] = Field(default_factory=list)
    audit_flags: List[AuditFlag] = Field(default_factory=list)
    audit_trail: List[AuditTrailEvent] = Field(default_factory=list)

    def log_event(self, action: str, details: str, metadata: Optional[Dict[str, Any]] = None, user: str = "Auditor"):
        event = AuditTrailEvent(
            action=action,
            details=details,
            metadata=metadata or {},
            user=user
        )
        self.audit_trail.append(event)
        self.updated_at = datetime.datetime.now()
