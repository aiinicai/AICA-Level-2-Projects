"""entity_profiles.ind_as_mandated

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-26

Stage 18 (explicitly approved before implementation — see the Stage 18
UX/workflow redesign exchange): adds one nullable column,
`ind_as_mandated`, to `entity_profiles` only. No other table is
touched, and `accounting_framework` (the column every rule/service
already reads) is NOT dropped, renamed, or made nullable — it keeps its
existing NOT NULL constraint and meaning unchanged.

`ind_as_mandated` (Boolean, nullable) records the user's own plain
Yes/No answer to "Is this company required to follow Ind AS?" — NULL
means "not yet answered" (the honest state for every row that existed
before this migration). The application layer
(app/engagement/validation.py::validate_entity_profile_form()) uses
this to auto-set `accounting_framework` (True -> "IND_AS", False ->
"AS") ONLY when the professional has not also explicitly chosen a
framework directly on the form — an explicit manual choice always
takes precedence. This migration itself makes no decision about any
existing row's `accounting_framework` value and does not touch it.

Hand-authored, same reason as 0001/0002/0003 (see database/migrations/
versions/README.md) — Alembic/SQLAlchemy could not be installed in the
delivery sandbox, so this migration's `upgrade()`/`downgrade()` could
NOT be executed against a real Alembic/SQLite run here, unlike
0001-0003 which were verified via
database/seed/_sandbox_migration_harness.py in earlier stages when
that harness was available. This is disclosed, not silently claimed as
tested — see the Stage 18 report for the honest verification status of
this specific migration file. The SQLAlchemy model change itself
(app/models/engagement.py) WAS exercised, indirectly, by every test in
this stage that calls `Base.metadata.create_all()` against a fresh
test database, which does pick up the new column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("entity_profiles", sa.Column("ind_as_mandated", sa.Boolean, nullable=True))


def downgrade() -> None:
    op.drop_column("entity_profiles", "ind_as_mandated")
