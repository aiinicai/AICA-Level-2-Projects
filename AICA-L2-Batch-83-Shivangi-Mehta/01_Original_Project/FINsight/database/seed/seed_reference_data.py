"""
Reference-data bootstrap — NOT rule content (Stage 3 condition #5).

Seeds only two things, both fixed taxonomy/bootstrap metadata rather than
business-rule logic:
  1. audit_assertions — the 9 fixed assertion values (Blueprint Section
     2.2). Not user-editable; this is a closed vocabulary.
  2. One initial knowledge_base_versions row marking the schema baseline.
     is_current is left False deliberately — a KB version only becomes
     "current" once real rule content exists behind it (Stage 8+).

Accounting/audit/tax/SEBI rule ROWS are explicitly NOT seeded here. Those
tables exist (created by the migration) but stay empty until their
owning stage populates them with verified content.

Run with:  python -m database.seed.seed_reference_data
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.orm import Session

from app.extensions import init_engine
from app.models import Base, AuditAssertion, KnowledgeBaseVersion
from config import Config

ASSERTIONS = [
    ("EXISTENCE", "Existence"),
    ("OCCURRENCE", "Occurrence"),
    ("COMPLETENESS", "Completeness"),
    ("ACCURACY", "Accuracy"),
    ("CUT_OFF", "Cut-off"),
    ("CLASSIFICATION", "Classification"),
    ("VALUATION", "Valuation"),
    ("RIGHTS_OBLIGATIONS", "Rights & Obligations"),
    ("PRESENTATION_DISCLOSURE", "Presentation / Disclosure"),
]


def seed(session: Session) -> None:
    existing_codes = {a.code for a in session.query(AuditAssertion).all()}
    for code, label in ASSERTIONS:
        if code not in existing_codes:
            session.add(AuditAssertion(code=code, label=label))

    if not session.query(KnowledgeBaseVersion).filter_by(version_label="0.2-schema-baseline").first():
        session.add(
            KnowledgeBaseVersion(
                version_label="0.2-schema-baseline",
                released_at=datetime.now(timezone.utc).isoformat(),
                notes=(
                    "Stage 3 schema baseline per approved Blueprint v0.2. "
                    "No rule content yet — accounting/audit/tax/SEBI rule "
                    "tables are created but empty."
                ),
                is_current=False,
            )
        )
    session.commit()


def main() -> None:
    engine = init_engine(Config.SQLALCHEMY_DATABASE_URI)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    print("Reference data seeded (audit_assertions + KB baseline row). No rule content added.")


if __name__ == "__main__":
    main()
