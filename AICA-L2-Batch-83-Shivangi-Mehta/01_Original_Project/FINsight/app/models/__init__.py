"""
Model package entrypoint.

Imports every model module so `Base.metadata` is fully populated (needed
by Alembic's env.py for autogenerate, and by Base.metadata.create_all()
for tests/local bootstrapping). This is the one place all 24 approved
tables come together — if a future stage adds a table without importing
it here, Alembic autogenerate will not see it, which is a deliberate
safety net against silently-forgotten tables.
"""
from app.models.base import Base

from app.models.engagement import Engagement, EntityProfile, Applicability
from app.models.uploads import UploadedFile, DataMapping
from app.models.rules import (
    Standard,
    AccountingRule,
    AuditRule,
    TaxRule,
    SebiRule,
    AuditAssertion,
    AuditRuleAssertion,
)
from app.models.transactions import Transaction
from app.models.structured_datasets import FixedAsset, GstLineItem, TdsLineItem
from app.models.exceptions import ExceptionRecord
from app.models.risk import RiskScore
from app.models.queries import QueryRecord, QueryResponse
from app.models.documents import Document
from app.models.system import AuditLog, ApplicationSetting, KnowledgeBaseVersion

__all__ = [
    "Base",
    "Engagement", "EntityProfile", "Applicability",
    "UploadedFile", "DataMapping",
    "Standard", "AccountingRule", "AuditRule", "TaxRule", "SebiRule",
    "AuditAssertion", "AuditRuleAssertion",
    "Transaction",
    "FixedAsset", "GstLineItem", "TdsLineItem",
    "ExceptionRecord",
    "RiskScore",
    "QueryRecord", "QueryResponse",
    "Document",
    "AuditLog", "ApplicationSetting", "KnowledgeBaseVersion",
]
