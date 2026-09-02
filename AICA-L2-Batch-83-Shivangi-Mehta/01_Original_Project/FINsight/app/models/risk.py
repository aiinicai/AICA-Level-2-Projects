"""
RiskScore — Blueprint Section 2 (D.13) / Section H. Schema only; the
actual weighted-factor scoring algorithm is Stage 12.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    risk_score_id: Mapped[int] = mapped_column(primary_key=True)
    exception_id: Mapped[int] = mapped_column(ForeignKey("exceptions.exception_id"))
    total_score: Mapped[int] = mapped_column()  # 0-100
    # e.g. {"amount": 22, "movement": 12, ..., "total": 82} — the
    # "why did this receive 82/100?" transparency requirement.
    factor_breakdown_json: Mapped[str | None] = mapped_column(default=None)
    calculated_at: Mapped[str] = mapped_column()
