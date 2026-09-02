"""queries.reviewer_query_text, query_responses.evidence_description/evidence_reference

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-24

Stage 13 (explicitly approved before implementation — see the Stage 13
schema-proposal exchange): adds three nullable columns, all additive,
no new tables, no new foreign keys:

  - queries.reviewer_query_text — the reviewer's edited version of the
    FinSight-generated query. `queries.question_text` remains the
    original, immutable, FinSight-generated wording — this migration
    never touches it. A NULL value means "not yet reviewer-edited";
    every row that exists before this migration gets NULL, which is the
    correct, honest state (no reviewer edit has happened for any of
    them).
  - query_responses.evidence_description — a description of evidence
    actually received/provided by the client, recorded by the reviewer.
  - query_responses.evidence_reference — a local file name/path/
    reference number for that evidence. Deliberately just a text field
    — Stage 13 does not build a document-management system, and no file
    is uploaded, moved, or stored anywhere by this migration or by the
    application code that uses this column.

No existing row's `question_text`, `management_response`,
`reviewer_comments`, or `resolution` value is read, copied, or modified
by this migration — purely additive.

Hand-authored, same reason as 0001/0002 (see database/migrations/
versions/README.md) — Alembic/SQLAlchemy could not be installed in the
delivery sandbox. Verified via database/seed/_sandbox_migration_harness.py
(extended in Stage 13 to run this migration after 0001/0002 against a
real, on-disk SQLite database and confirm the resulting live schema).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("queries", sa.Column("reviewer_query_text", sa.String, nullable=True))
    op.add_column("query_responses", sa.Column("evidence_description", sa.String, nullable=True))
    op.add_column("query_responses", sa.Column("evidence_reference", sa.String, nullable=True))


def downgrade() -> None:
    op.drop_column("query_responses", "evidence_reference")
    op.drop_column("query_responses", "evidence_description")
    op.drop_column("queries", "reviewer_query_text")
