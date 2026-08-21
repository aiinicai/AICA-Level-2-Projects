"""Firm-level default answers (decision 28)

The master configuration behind Admin -> Default Answers. One row per firm per
clause question; the answers themselves are still written to
`engagement_response` when an engagement is created, so nothing about how a
document renders reads this table.

`value` is deliberately NOT constrained to the option set here. The option set
lives in the clause YAML and changes with it, so a database constraint would
either go stale or block a legitimate repository change. It is validated on the
way in, against `field_catalog`, in `app.services.defaults.set_defaults` --
which is also where a default whose option was withdrawn gets reported rather
than silently kept.

Revision ID: 4f2b8e1c9a37
Revises: c91a4e7b2f08
Create Date: 2026-08-17 16:20:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4f2b8e1c9a37"
down_revision: str | None = "c91a4e7b2f08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "field_default",
        sa.Column("firm_id", sa.Integer(), nullable=False),
        sa.Column("field_key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.String(length=120), nullable=False),
        # server_default on both, because an existing row must get a value
        # when the column is added on a database that already has firms.
        sa.Column("updated_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()
        ),
        sa.ForeignKeyConstraint(["firm_id"], ["firm.firm_id"]),
        sa.PrimaryKeyConstraint("firm_id", "field_key"),
    )


def downgrade() -> None:
    op.drop_table("field_default")
