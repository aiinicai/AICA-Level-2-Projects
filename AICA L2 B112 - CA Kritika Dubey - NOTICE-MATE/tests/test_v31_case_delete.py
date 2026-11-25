"""Permanent case deletion removes one case completely and leaves every other case untouched."""
import pathlib

import pytest

from noticemate.core import audit
from noticemate.core.config import get_settings
from noticemate.core.db import ro
from noticemate.core.errors import NotFound, PermissionDenied, ValidationError
from noticemate.services import cases, documents, drafting, intake, issues, mapping, review

PACK = pathlib.Path(__file__).parent / "fixtures" / "complex_pack"


def _make(ca, ref):
    nf = next(PACK.glob("00_*.docx"))
    r = intake.start_from_notice(ca, nf.name, nf.read_bytes())
    cid = r["case"]["id"]
    intake.confirm_case(ca, cid, assessee_name=f"Fictional {ref}", assessee_category="INDIVIDUAL", pan=None,
                        assessment_year="2025-26", case_ref=ref)
    for f in sorted(PACK.glob("0[1-3]_*.docx")):
        documents.upload(ca, cid, f.name, f.read_bytes())
    issues.generate_from_notice(ca, r["notice"]["id"])
    d = drafting.build(ca, cid, r["notice"]["id"])
    review.add_comment(ca, d["id"], "Q1", "Check the loan ledger.")
    return cid


def _rows(cid):
    with ro() as conn:
        tabs = [n for (n,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                if any(c[1] == "case_id" for c in conn.execute(f"PRAGMA table_info({n})"))]
        out = {t: conn.execute(f"SELECT COUNT(*) FROM {t} WHERE case_id=?", (cid,)).fetchone()[0] for t in tabs}
        out["doc_text"] = conn.execute("SELECT COUNT(*) FROM doc_text WHERE document_id IN "
                                       "(SELECT id FROM documents WHERE case_id=?)", (cid,)).fetchone()[0]
    return out


def _files(cid):
    d = get_settings().docs_dir / f"case_{cid}"
    return sorted(p.name for p in d.iterdir()) if d.exists() else []


def test_delete_one_case_leaves_the_other_untouched(users):
    ca, staff = users["ca"], users["staff"]
    keep, gone = _make(ca, "DEL-KEEP"), _make(ca, "DEL-GONE")
    keep_rows, keep_files = _rows(keep), _files(keep)
    keep_draft = drafting.latest_draft(ca, keep)["content_hash"]
    keep_links = mapping.summary(ca, keep)
    assert _files(gone) and _rows(gone)["documents"] > 0 and _rows(gone)["doc_links"] > 0

    with pytest.raises(PermissionDenied):
        cases.delete_case(staff, gone, "DEL-GONE")
    with pytest.raises(ValidationError):  # a confirmation for another case never deletes this one
        cases.delete_case(ca, gone, "DEL-KEEP")
    assert cases.get_case(ca, gone)

    cases.set_status(ca, keep, "CLOSED")  # CLOSED keeps everything
    assert cases.get_case(ca, keep)["status"] == "CLOSED" and _files(keep) == keep_files

    res = cases.delete_case(ca, gone, "DEL-GONE")
    assert res["deleted"] and not res["files_not_removed"]
    with pytest.raises(NotFound):
        cases.get_case(ca, gone)
    assert all(v == 0 for v in _rows(gone).values()), _rows(gone)
    assert not (get_settings().docs_dir / f"case_{gone}").exists()
    assert gone not in [c["id"] for c in cases.list_cases(ca)]
    with ro() as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE case_id=?", (gone,)).fetchone()[0] == 0
        ev = conn.execute("SELECT meta_json FROM audit_log WHERE event='CASE_DELETED' ORDER BY id DESC LIMIT 1").fetchone()
    assert '"deleted_case_id": %d' % gone in ev["meta_json"] and "DEL-GONE" not in ev["meta_json"]
    assert audit.verify_chain()["valid"]

    # the other case is exactly as before (apart from its CLOSED status change)
    after = _rows(keep)
    assert {k: v for k, v in after.items() if k != "audit_log"} == {k: v for k, v in keep_rows.items() if k != "audit_log"}
    assert _files(keep) == keep_files
    assert drafting.latest_draft(ca, keep)["content_hash"] == keep_draft
    assert mapping.summary(ca, keep)["issues"] == keep_links["issues"]
    with pytest.raises(NotFound):
        cases.delete_case(ca, gone, "DEL-GONE")
    # append-only protection is back in force after the purge
    with pytest.raises(Exception):
        with __import__("noticemate.core.db", fromlist=["tx"]).tx() as conn:
            conn.execute("DELETE FROM audit_log WHERE id=(SELECT MIN(id) FROM audit_log)")
