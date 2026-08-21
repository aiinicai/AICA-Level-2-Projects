"""Columns for the three applicability flags that had none

`FLAGS` declares ten applicability flags and §7 promises every one of them can
be overridden with a reason. Only seven had columns. `OVERRIDE_COLUMNS` is
built with `hasattr`, so the other three — secretarial_audit,
abridged_board_report and cfs_required — dropped silently out of the override
map and could not be reached from the applicability screen at all.

Every column is NOT NULL with a server default. Without the default this
migration succeeds on an empty development database and fails on every
populated one, which is the worst possible place to find out.

Revision ID: b3f27c04a1de
Revises: e8a1d854e695
Create Date: 2026-08-16 21:40:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3f27c04a1de"
down_revision: str | None = "e8a1d854e695"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "secretarial_audit",
    "secretarial_audit_override",
    "abridged_board_report",
    "abridged_board_report_override",
    "cfs_required",
    "cfs_required_override",
)


def upgrade() -> None:
    with op.batch_alter_table("client_profile", schema=None) as batch_op:
        for name in _COLUMNS:
            batch_op.add_column(
                sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false())
            )


def downgrade() -> None:
    with op.batch_alter_table("client_profile", schema=None) as batch_op:
        for name in reversed(_COLUMNS):
            batch_op.drop_column(name)
