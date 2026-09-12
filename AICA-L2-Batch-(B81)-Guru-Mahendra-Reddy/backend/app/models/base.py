"""Shared column mixins.

`Provenance` exists because of SPEC design principle 4 — no number appears
without its basis. Every row that can reach a screen records where it came
from and who put it there, which is also what makes the Setup > Manual
Entries Register (12A) a query rather than a separate table.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DataSource(str, enum.Enum):
    TALLY = "tally"        # pulled from the accounting system
    MANUAL = "manual"      # typed into an in-app register
    UPLOAD = "upload"      # bulk Excel/CSV upload
    SEED = "seed"          # demonstration dataset
    DERIVED = "derived"    # computed by the app, not entered


class Provenance:
    source: Mapped[str] = mapped_column(String(16), default=DataSource.MANUAL.value, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
