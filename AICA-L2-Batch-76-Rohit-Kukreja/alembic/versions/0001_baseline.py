"""Baseline — establishes the migration chain.

Phase 0 delivers the scaffold, config, database wiring and Alembic. The
business tables arrive in Phase 4 (§16), each as its own revision on top of
this one. This revision is deliberately empty rather than speculative: a
table invented here would have to be migrated again when Phase 4 designs it
properly.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-15

"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
