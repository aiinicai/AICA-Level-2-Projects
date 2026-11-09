"""Tests for client emails only for verified entries; version / recipient mix-up checks."""

from judgment_analyzer.audience_check import client_markers_in_team, recipient_warnings, team_markers_in_client
from judgment_analyzer.email_composer import DEFAULT_INTERNAL_INTRO, DEFAULT_INTRO
from judgment_analyzer.exporter import build_final_document
from judgment_analyzer.recipients import Recipient
from judgment_analyzer.repository import JudgmentRecord, Repository
from judgment_analyzer.response_parser import parse_report


def test_team_material_in_client_version_is_found():
    assert team_markers_in_client("Judgment update: A v. B", DEFAULT_INTRO, "## Summary\n\nText") == []
    found = team_markers_in_client("[Precedent register] Judgment update: A v. B", DEFAULT_INTERNAL_INTRO,
                                   "**Precedent register reference:** JIA-2026-0006\n\n## Summary")
    assert len(found) == 3
    assert team_markers_in_client("S", "Dear all", "See JIA-2026-0001") != []


def test_client_material_in_team_version_is_found():
    assert client_markers_in_team("[Precedent register] X", DEFAULT_INTRO, "") != []
    assert client_markers_in_team("[Precedent register] X", DEFAULT_INTERNAL_INTRO, "") == []


def test_people_in_the_wrong_list():
    clients = [Recipient("Client", "c@acme.com"), Recipient("Colleague", "x@firm-example.in")]
    team = [Recipient("Me", "y@firm-example.in"), Recipient("Outsider", "z@other.com")]
    warns = recipient_warnings(clients, team, "partner@firm-example.in")
    assert len(warns) == 2 and "CLIENT list" in warns[0] and "EMPLOYEE list" in warns[1]
    assert recipient_warnings(clients, team, "someone@gmail.com") == []      # firm domain unknown


def test_unverified_outputs_are_marked_draft(tmp_path):
    report = parse_report("## 1. Case Details\n- **Case title:** A v. B\n\n## 2. Executive Summary\nText.")
    doc = build_final_document(report, {"case_title": "A v. B"}, status_note="DRAFT - for internal review")
    assert doc.metadata[0] == ("Status", "DRAFT - for internal review")
    assert all(k != "Status" for k, _ in build_final_document(report, {"case_title": "A v. B"}).metadata)
    repo = Repository(tmp_path / "r.db")
    rec = repo.add(JudgmentRecord(case_title="A v. B"))
    assert repo.get_by_ref(rec.ref).status == "Draft" and repo.get_by_ref("JIA-1999-0001") is None
