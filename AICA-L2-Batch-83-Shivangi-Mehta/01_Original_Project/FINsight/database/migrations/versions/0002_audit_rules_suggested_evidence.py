"""audit_rules.suggested_evidence

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-23

Stage 9, Decision A (explicitly approved before implementation — see the
Stage 9 catalogue-review exchange): adds one nullable column,
`suggested_evidence`, to `audit_rules` only. No other table is touched.

The v0.2 blueprint's own Section 4 (pre-approved, pre-code planning
table) already anticipated a "Suggested Evidence" column per audit
rule, but the schema in Section 2.4 never actually added it — this
migration closes that gap rather than the application silently working
around it by overloading an unrelated existing field.

Hand-authored, same reason as 0001 (see database/migrations/versions/
README.md) — Alembic/SQLAlchemy could not be installed in the delivery
sandbox. Verified via database/seed/_sandbox_migration_harness.py
(extended in Stage 9 to run this migration after 0001 against a real,
on-disk SQLite database and confirm the resulting live schema).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_rules", sa.Column("suggested_evidence", sa.String, nullable=True))


def downgrade() -> None:
    op.drop_column("audit_rules", "suggested_evidence")
