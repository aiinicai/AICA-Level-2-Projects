"""Declarative base, shared mixins and enums."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


def str_enum(e: type[enum.Enum], length: int = 24):
    """Store enums as readable strings with a CHECK constraint (not native ENUM)."""
    return Enum(e, native_enum=False, length=length, validate_strings=True,
                values_callable=lambda x: [m.value for m in x])


class Role(str, enum.Enum):
    ADMIN = "admin"
    PREPARER = "preparer"
    VIEWER = "viewer"
    APPROVER = "approver"  # in the model; active only when setting approver_enabled = true


class Direction(str, enum.Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"


class Treatment(str, enum.Enum):
    FIXED = "fixed"
    DEFERRABLE = "deferrable"


class SourceType(str, enum.Enum):
    COLLECTIONS = "collections"              # ERP customer collections
    ADDITIONAL_COLLECTIONS = "additional"    # template
    VENDOR_PDC = "vendor_pdc"                # ERP PDC register
    PAYMENT_ALLOCATION = "allocation"        # ERP vendor payment plan
    BILL_DISCOUNT = "bill_discount"          # bank file: discount proceeds + LC / discount maturities
    OTHER = "other"                          # other & recurring template
    CATEGORY_LIST = "category_list"          # category master upload
    PAYMENT_HISTORY = "payment_history"      # optional, for collection-delay model
    BANK_BALANCES = "bank_balances"          # optional bulk entry (normally typed on screen)
    BANK_FACILITY = "bank_facility"          # optional bulk entry (normally typed on screen)


class BatchStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    EXCEPTIONS = "exceptions"     # waiting for header/category mapping
    ACCEPTED = "accepted"         # current data for its source type
    SUPERSEDED = "superseded"     # replaced by a later upload of the same source type
    REJECTED = "rejected"


class OverrideAction(str, enum.Enum):
    # HOLD: cheque stopped by us. Leaves its original lot and comes back in the lot of the
    # next honouring date (new_date). new_date NULL = open-ended (out of every later lot).
    # new_amount = part held (NULL = full cheque). Shown as a separate hold adjustment block,
    # so funding is visible both before and after holds.
    HOLD = "hold"
    DEFER = "defer"                     # move to a chosen later lot
    REDATE = "redate"                   # new planned date
    REDUCE = "reduce"                   # new (lower) amount
    EXCLUDE = "exclude"                 # out of the forecast, not a hold
    BILL_DISCOUNTED = "bill_discounted" # collection already financed -> not counted again
    RISK_ADJUSTED = "risk_adjusted"     # collection flagged; scenario toggle may exclude it
    RECATEGORISE = "recategorise"       # move to another category


class ApprovalStatus(str, enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExceptionStatus(str, enum.Enum):
    OPEN = "open"
    MAPPED = "mapped"            # mapped to an existing category
    NEW_CATEGORY = "new_category"
    IGNORED = "ignored"


class ExportCheck(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"            # export blocked
    NOT_RUN = "not_run"
