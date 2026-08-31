"""Layer 3 workflow. Build Prompt v2 §5.4 and §10."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import CommentStatus


class ReviewComment(Base):
    """Threaded review comments (§10).

    Attaches to a field or a document, threads via `parent_id`, and keeps
    full history — a resolved comment is never deleted, only marked.
    """

    __tablename__ = "review_comment"

    comment_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    field_key: Mapped[str | None] = mapped_column(String(120), default=None)
    document: Mapped[str | None] = mapped_column(String(60), default=None)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("review_comment.comment_id"), default=None
    )

    body: Mapped[str] = mapped_column(Text)
    raised_by: Mapped[str] = mapped_column(String(200))
    raised_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    status: Mapped[CommentStatus] = mapped_column(
        Enum(CommentStatus, native_enum=False), default=CommentStatus.OPEN
    )
    resolved_by: Mapped[str] = mapped_column(String(200), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    replies: Mapped[list[ReviewComment]] = relationship(
        back_populates="parent", remote_side=lambda: [ReviewComment.parent_id]
    )
    parent: Mapped[ReviewComment | None] = relationship(
        back_populates="replies", remote_side=lambda: [ReviewComment.comment_id]
    )
