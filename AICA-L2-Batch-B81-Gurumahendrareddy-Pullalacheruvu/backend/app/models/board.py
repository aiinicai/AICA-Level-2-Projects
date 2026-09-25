"""TAB 10 — Board Pack. A pack is a frozen snapshot, not a re-query.

'When someone asks in March what I told the board in December, I open it
rather than reconstruct it.' — so the full computed payload is stored as JSON
at generation time and never recomputed.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import utcnow


class BoardPackSection:
    CASH_RUNWAY = "Cash & Runway Summary"
    BURN = "Burn Analysis"
    COLLECTIONS = "Collections & Concentration"
    PLAN_VS_ACTUAL = "Plan vs Actual with Drivers"
    FORECAST = "13-Week Forecast"
    SCENARIOS = "Scenario Summary"
    FUNDING = "Funding Position"
    RISKS = "Key Risks"
    ALL = [CASH_RUNWAY, BURN, COLLECTIONS, PLAN_VS_ACTUAL,
           FORECAST, SCENARIOS, FUNDING, RISKS]


class BoardPack(Base):
    __tablename__ = "board_packs"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    as_on: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    generated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    generated_on: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)

    sections: Mapped[str] = mapped_column(Text, default="[]", nullable=False)      # JSON list of section names
    scenario_ids: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list
    snapshot: Mapped[str] = mapped_column(Text, default="{}", nullable=False)      # JSON — the frozen numbers
    commentary: Mapped[str] = mapped_column(Text, default="{}", nullable=False)    # JSON — section -> narrative

    # Denormalised headline figures so the library table needs no JSON parsing
    runway_stated: Mapped[float | None] = mapped_column(Float, nullable=True)
    cashout_stated: Mapped[date | None] = mapped_column(Date, nullable=True)
    cash_available_stated: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_burn_stated: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[str] = mapped_column(String(12), default="High", nullable=False)
