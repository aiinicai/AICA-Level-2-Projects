"""Drop the unused bdr_director_change table

`bdr.directors.kmp` wrote here until §18.8 was honoured properly. It now uses
the computed entity `director_changes_in_year`, which has no table and derives
its rows from the client's director register on every render, so the Board's
Report can no longer name a director the register does not have.

Nothing has written to this table since. **Confirmed empty (0 rows) before
this migration was written** — a table that might hold a firm's data is not
something to drop on the assumption that it is unused.

Separated from the change that made it redundant, on purpose: making a table
redundant and destroying it are different decisions and deserve different
commits.

`downgrade()` recreates the table but cannot restore rows. There are none to
restore, which is why this is safe here and would not be in general.

Revision ID: c91a4e7b2f08
Revises: 5508cf94f5ff
Create Date: 2026-08-17 13:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c91a4e7b2f08"
down_revision: str | None = "5508cf94f5ff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("bdr_director_change")


def downgrade() -> None:
    op.create_table(
        "bdr_director_change",
        sa.Column("row_id", sa.Integer(), nullable=False),
        sa.Column("engagement_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("din", sa.String(length=30), nullable=False),
        sa.Column("designation", sa.String(length=120), nullable=False),
        sa.Column("change", sa.String(length=40), nullable=False),
        sa.Column("change_date", sa.Date(), nullable=True),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "user", "carried_forward", "computed", name="responsesource", native_enum=False
            ),
            nullable=False,
        ),
        sa.Column("reviewed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["engagement_id"], ["engagement.engagement_id"]),
        sa.PrimaryKeyConstraint("row_id"),
    )
