from datetime import datetime, timezone

import pytest

from app.core.errors import ValidationError
from app.core.time import FixedClock
from app.db.connection import connect
from app.db.migrate import migrate
from app.legal.service import LegalService
from app.security.audit import AuditService
from app.services.clients import ClientService
from app.workflow.engine import WorkflowService
from app.workflow.recommendations import RecommendationEngine


def setup(tmp_path):
    db = connect(tmp_path / "workflow.sqlite3")
    migrate(db)
    clock = FixedClock(datetime(2026, 9, 22, 10, tzinfo=timezone.utc))
    audit = AuditService(db, bytes(range(32)), clock=clock)
    clients = ClientService(db, bytes(reversed(range(32))), audit, clock=clock)
    client = clients.create({"name": "Workflow Client"})
    matter = clients.create_matter(client, {"title": "Test CIRP", "matter_type": "CIRP", "insolvency_commencement_date": "2026-09-01"})
    legal = LegalService(db, audit, clock=clock)
    statute = legal.add_statute({"title": "Verified Test Rules", "statute_type": "REGULATIONS", "verification_status": "VERIFIED"})
    provision = legal.add_provision(statute, {"provision_type": "Regulation", "number_label": "X", "text_content": "Verified test timeline source.", "verification_status": "VERIFIED"})
    citation = legal.add_citation("Verified Test Rules, Regulation X", provision_id=provision, verification_status="VERIFIED")
    workflow = WorkflowService(db, audit, clock=clock)
    return db, clock, audit, matter, citation, workflow


def test_data_driven_deadline_recalculation_completion_and_history(tmp_path):
    db, clock, audit, matter, citation, workflow = setup(tmp_path)
    definition = workflow.create_definition("Test CIRP workflow", "CIRP", 1, [{
        "stage_key": "public-announcement", "stage_name": "Public announcement",
        "citation_id": citation, "statutory_basis": "Verified Test Rules, Regulation X",
        "trigger_field": "insolvency_commencement_date", "due_offset_days": 3,
        "checklist": ["Prepare draft", "Retain proof"],
        "required_documents": ["announcement"], "verification_status": "VERIFIED",
    }], verification_status="VERIFIED")
    instance = workflow.instantiate(matter, definition)
    stage = workflow.stages(instance)[0]
    assert stage["computed_due_date"] == "2026-09-04"
    assert stage["status"] == "OVERDUE"
    workflow.update_matter_dates(matter, {"insolvency_commencement_date": "2026-09-20"})
    stage = workflow.stages(instance)[0]
    assert stage["computed_due_date"] == "2026-09-23"
    assert stage["status"] == "NOT_STARTED"
    assert db.execute("SELECT COUNT(*) FROM deadline_recalculation_history WHERE process_stage_id=?", (stage["id"],)).fetchone()[0] >= 2
    workflow.set_stage_status(stage["id"], "DONE")
    assert workflow.stages(instance)[0]["status"] == "DONE"
    assert db.execute("SELECT status FROM deadlines WHERE process_stage_id=?", (stage["id"],)).fetchone()[0] == "COMPLETED"


def test_legal_due_stage_without_citation_rejected(tmp_path):
    db, clock, audit, matter, citation, workflow = setup(tmp_path)
    with pytest.raises(ValidationError):
        workflow.create_definition("Unsafe", "CIRP", 1, [{
            "stage_key": "uncited", "stage_name": "Uncited legal deadline",
            "trigger_field": "admission_date", "due_offset_days": 10,
        }])


def test_recommendation_engine_rejects_uncited_and_labels_verification(tmp_path):
    db, clock, audit, matter, citation, workflow = setup(tmp_path)
    engine = RecommendationEngine(db, audit, clock=clock)
    with pytest.raises(ValidationError, match="without an associated citation"):
        engine.persist(matter_id=matter, rule_key="bad", priority="HIGH", title="Bad", action="Act", reason="Because", citation_id=None)

    definition = workflow.create_definition("Recommendation workflow", "CIRP", 1, [{
        "stage_key": "filing", "stage_name": "Required filing", "citation_id": citation,
        "trigger_field": "insolvency_commencement_date", "due_offset_days": 3,
        "required_documents": ["filing proof"], "verification_status": "VERIFIED",
    }], verification_status="VERIFIED")
    workflow.instantiate(matter, definition)
    recommendations = engine.generate_for_matter(matter)
    assert recommendations
    assert all(item["citation_id"] for item in recommendations)
    assert all(item["citation_text"] == "Verified Test Rules, Regulation X" for item in recommendations)
    assert all(item["verification_status"] == "VERIFIED" for item in recommendations)
