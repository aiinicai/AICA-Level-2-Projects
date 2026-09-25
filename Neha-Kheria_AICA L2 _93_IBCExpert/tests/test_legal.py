from __future__ import annotations

import json

from app.db.connection import connect
from app.db.migrate import migrate
from app.legal.service import LegalService
from app.security.audit import AuditService


def service(tmp_path):
    db = connect(tmp_path / "legal.sqlite3")
    migrate(db)
    return db, LegalService(db, AuditService(db, bytes(range(32))))


def test_legal_import_real_search_and_point_in_time_versioning(tmp_path):
    db, legal = service(tmp_path)
    statute = legal.add_statute({
        "title": "Test Insolvency Statute",
        "short_title": "TIS",
        "statute_type": "ACT",
        "verification_status": "VERIFIED",
    })
    first = legal.add_provision(statute, {
        "provision_type": "Section",
        "number_label": "10",
        "heading": "Commencement of process",
        "text_content": "The original provision requires an application by the debtor.",
        "effective_from": "2020-01-01",
        "verification_status": "VERIFIED",
    })
    first_row = db.execute("SELECT provision_uuid FROM legal_provisions WHERE id=?", (first,)).fetchone()
    second = legal.version_provision(
        first, "2024-04-01",
        "The amended provision requires an electronic application by the debtor.",
        "Test Amendment 2024", verification_status="VERIFIED",
    )
    old = legal.provision_at(first_row[0], "2024-03-15")
    new = legal.provision_at(first_row[0], "2024-04-01")
    assert "original" in old["text_content"]
    assert "amended" in new["text_content"]
    assert old["effective_to"] == "2024-04-01"
    results = legal.search("electronic application", statute_id=statute)
    assert results[0]["entity_id"] == str(second)
    assert results[0]["verification_status"] == "VERIFIED"


def test_json_package_import_defaults_to_review_required(tmp_path):
    db, legal = service(tmp_path)
    package = tmp_path / "law.json"
    package.write_text(json.dumps({
        "format": "IBC-EXPERT-LEGAL-1",
        "statutes": [{
            "title": "Imported Rules", "statute_type": "RULES",
            "provisions": [{
                "provision_type": "Rule", "number_label": "1",
                "text_content": "Imported searchable phrase quantum resolution.",
            }],
        }],
        "judgments": [{
            "title": "A v B", "court": "Test Tribunal",
            "text_content": "The tribunal considered quantum resolution issues.",
        }],
    }), encoding="utf-8")
    assert legal.import_json_package(package) == {"statutes": 1, "provisions": 1, "judgments": 1}
    results = legal.search("quantum resolution")
    assert len(results) == 2
    assert all(result["verification_status"] == "REVIEW_REQUIRED" for result in results)
