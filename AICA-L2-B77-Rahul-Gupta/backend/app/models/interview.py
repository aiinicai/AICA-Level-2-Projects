"""Rule triggers and the adaptive AI interview."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .core import now, uid


class RuleTrigger(Base):
    __tablename__ = "rule_triggers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    rule_code: Mapped[str] = mapped_column(String(60))
    metric: Mapped[str] = mapped_column(String(60), default="")
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    action: Mapped[str] = mapped_column(String(120), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    period_label: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | addressed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | completed
    total_planned: Mapped[int] = mapped_column(Integer, default=0)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey("interview_sessions.id"))
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    question_code: Mapped[str] = mapped_column(String(40))  # e.g. GROWTH_004
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, default="")
    trigger_rule: Mapped[str] = mapped_column(String(60), default="")
    question: Mapped[str] = mapped_column(Text)
    qtype: Mapped[str] = mapped_column(String(30), default="single_choice")
    options: Mapped[list] = mapped_column(JSON, default=list)
    valuation_impact: Mapped[list] = mapped_column(JSON, default=list)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | asked | answered | skipped
    ai_generated: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    question_id: Mapped[str] = mapped_column(ForeignKey("interview_questions.id"))
    session_id: Mapped[str] = mapped_column(ForeignKey("interview_sessions.id"))
    case_id: Mapped[str] = mapped_column(ForeignKey("valuation_cases.id"))
    answer_value: Mapped[dict] = mapped_column(JSON, default=dict)
    elaboration: Mapped[str] = mapped_column(Text, default="")
    ai_interpretation: Mapped[str] = mapped_column(Text, default="")
    signal: Mapped[str] = mapped_column(String(20), default="neutral")  # positive | neutral | negative
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
