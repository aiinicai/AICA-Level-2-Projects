"""Phase 7 end-to-end tests for the offline demo harness and web boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

import run_demo
import amg.web.app as web_app
from amg.config import get_settings
from amg.providers import reset_provider_state
from amg.db import connect, init_schema
from amg.demo.persona import SCENARIO_5A, SESSION_1
from amg.demo.scenarios import run_all
from amg.web.app import create_app


def test_run_all_returns_nine_passing_results_offline(tmp_path: Path) -> None:
    conn = connect(tmp_path / "scenarios.db")
    init_schema(conn)
    try:
        results = run_all(conn)
    finally:
        conn.close()

    assert [result.id for result in results] == [
        "1", "2", "2b", "3", "4", "5a", "5b", "6a", "6b"
    ]
    assert len(results) == 9
    assert all(result.passed for result in results), [
        result.model_dump(mode="json") for result in results if not result.passed
    ]
    assert all(result.evidence for result in results)


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "web.db"))


def test_every_web_endpoint_and_demo_action(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        assert client.get("/").status_code == 200
        session = client.post("/api/session/new", json={})
        assert session.status_code == 200
        assert session.json()["conversation_history_count"] == 0

        employer = client.post(
            "/api/turn", json={"text": SESSION_1["inputs"][0]}
        )
        assert employer.status_code == 200
        assert employer.json()["written_count"] == 2
        client.post("/api/turn", json={"text": SESSION_1["inputs"][1]}).raise_for_status()

        query = client.post("/api/query", json={"text": "Where do I work?"})
        assert query.status_code == 200
        assert query.json()["returned_count"] <= query.json()["top_k_max"] == 6

        wrong_export = client.post("/api/export", json={"passphrase": "wrong"})
        right_export = client.post(
            "/api/export", json={"passphrase": get_settings().export_passphrase}
        )
        assert wrong_export.status_code == right_export.status_code == 200
        assert wrong_export.json()["memories"] == []
        assert right_export.json()["memories"]

        memories = client.get("/api/memories")
        audit = client.get("/api/audit")
        status = client.get("/api/status")
        assert memories.status_code == audit.status_code == status.status_code == 200
        inferred_id = next(
            item["id"]
            for item in memories.json()["memories"]
            if item["source_type"] == "ai_inferred"
        )
        confirm = client.post(f"/api/memory/{inferred_id}/confirm", json={})
        assert confirm.status_code == 200
        assert confirm.json()["memory"]["confirmed_at"] is not None

        dietary_id = next(
            item["id"]
            for item in client.get("/api/memories").json()["memories"]
            if item["subject_key"] == "dietary_preference"
            and item["source_type"] == "user_stated"
        )
        cascade = client.get(f"/api/memory/{dietary_id}/cascade")
        assert cascade.status_code == 200
        assert len(cascade.json()["memory_ids"]) == 2
        refused_delete = client.request(
            "DELETE", f"/api/memory/{dietary_id}", json={"confirmed": False}
        )
        assert refused_delete.status_code == 200
        assert refused_delete.json()["erased"] is False

        new_employer = client.post(
            "/api/turn",
            json={"text": "Actually I've moved on — I'm at Silverline Logistics now."},
        )
        assert new_employer.status_code == 200
        conflicts = [
            item
            for item in client.get("/api/memories").json()["memories"]
            if item["subject_key"] == "employer" and item["status"] == "flagged_conflict"
        ]
        assert len(conflicts) == 2
        resolution = client.post(
            "/api/conflict/resolve",
            json={"keep_id": conflicts[1]["id"], "supersede_id": conflicts[0]["id"]},
        )
        assert resolution.status_code == 200

        client.post("/api/reset", json={}).raise_for_status()
        scenario = client.post("/api/scenario/1", json={})
        assert scenario.status_code == 200
        assert scenario.json()["passed"] is True
        client.post("/api/reset", json={}).raise_for_status()
        all_scenarios = client.post("/api/scenario/all", json={})
        assert all_scenarios.status_code == 200
        assert len(all_scenarios.json()["results"]) == 9
        assert all_scenarios.json()["passed"] is True

        tamper = client.post("/api/audit/tamper", json={})
        assert tamper.status_code == 200
        assert tamper.json()["chain"]["valid"] is False
        reset = client.post("/api/reset", json={})
        assert reset.status_code == 200
        assert client.get("/api/audit").json()["chain"]["valid"] is True


def test_endpoint_error_statuses_are_readable(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        assert client.post("/api/turn", json={"text": ""}).status_code == 422
        assert client.get("/api/memory/999/cascade").status_code == 404
        assert client.post("/api/scenario/unknown", json={}).status_code == 404
        assert client.post("/api/audit/tamper", json={}).status_code == 409
        body = client.post(
            "/api/conflict/resolve", json={"keep_id": 1, "supersede_id": 2}
        )
        assert body.status_code == 409
        assert "traceback" not in body.text.casefold()


def test_query_attack_refusal_contains_no_memory_content(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        client.post("/api/turn", json={"text": SESSION_1["inputs"][0]}).raise_for_status()
        stored = [
            item["content"]
            for item in client.get("/api/memories").json()["memories"]
        ]
        response = client.post(
            "/api/query", json={"text": SCENARIO_5A["inputs"][0]}
        )
        payload = response.json()
        assert response.status_code == 200
        assert payload["allowed"] is False
        assert payload["hits"] == []
        serialized = json.dumps(payload).casefold()
        assert all(content.casefold() not in serialized for content in stored)


def test_export_gate_wrong_and_right_paths(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        client.post("/api/turn", json={"text": SESSION_1["inputs"][0]}).raise_for_status()
        wrong = client.post("/api/export", json={"passphrase": "incorrect"})
        right = client.post(
            "/api/export", json={"passphrase": get_settings().export_passphrase}
        )
        assert wrong.status_code == right.status_code == 200
        assert wrong.json()["succeeded"] is False
        assert wrong.json()["memories"] == []
        assert "not confirmed" in wrong.json()["reason"].casefold()
        right_payload = right.json()
        assert right_payload["succeeded"] is True
        assert right_payload["memories"]
        assert {
            "content",
            "subject_key",
            "source_type",
            "status",
            "created_at",
            "source_session_id",
        } <= right_payload["memories"][0].keys()


def test_status_reports_stub_and_local_offline_without_keys(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        initial = client.get("/api/status").json()
        assert initial["llm"]["label"] == "Stub (offline)"
        assert initial["embeddings"]["label"] == "Local embeddings (offline)"
        client.post("/api/turn", json={"text": SESSION_1["inputs"][0]}).raise_for_status()
        served = client.get("/api/status").json()
        assert served["offline"] is True
        assert served["llm"]["provider"] == "stub"
        assert served["llm"]["state"] == "stub"
        assert served["llm"]["response_kind"] == "synthetic"
        assert served["embeddings"]["provider"] == "local"
        assert served["embeddings"]["state"] == "stub"
        assert served["embeddings"]["response_kind"] == "synthetic"


def test_provider_badges_distinguish_real_and_synthetic_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states = [
        ("live", "gemini"),
        ("cache", "gemini"),
        ("cache_after_error", "gemini"),
        ("stub", "stub"),
        ("fallback_after_error", "stub"),
        ("blocked_by_cap", "stub"),
        ("blocked_offline", "stub"),
    ]
    badges: list[dict[str, object]] = []
    for served_by, provider_name in states:
        monkeypatch.setattr(
            web_app,
            "last_provider_report",
            lambda served_by=served_by, provider_name=provider_name: {
                "llm": {
                    "provider_name": provider_name,
                    "model": "test-model",
                    "served_by": served_by,
                    "was_fallback": served_by
                    in {"fallback_after_error", "blocked_by_cap", "blocked_offline"},
                }
            },
        )
        badges.append(web_app._provider_status("llm"))

    assert [badge["state"] for badge in badges] == [state for state, _ in states]
    assert len({badge["label"] for badge in badges}) == len(states)
    assert [badge["response_kind"] for badge in badges[:3]] == ["real"] * 3
    assert [badge["response_kind"] for badge in badges[3:]] == ["synthetic"] * 4


def test_budget_cap_status_is_not_presented_as_provider_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        web_app,
        "last_provider_report",
        lambda: {
            "llm": {
                "provider_name": "stub",
                "model": "stub-rule-v1",
                "served_by": "blocked_by_cap",
                "was_fallback": True,
            }
        },
    )

    with _client(tmp_path) as client:
        status = client.get("/api/status").json()

    assert status["llm"]["state"] == "blocked_by_cap"
    assert "deliberately blocked" in status["fallback_notice"]
    assert "failed" not in status["fallback_notice"]


def test_prewarm_refuses_offline_before_provider_access(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AMG_OFFLINE", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "present-but-forbidden")
    monkeypatch.setenv("VOYAGE_API_KEY", "present-but-forbidden")
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)

    def forbidden(*_: object, **__: object) -> Any:
        raise AssertionError("provider access occurred before prewarm validation")

    monkeypatch.setattr(run_demo, "get_llm_provider", forbidden)

    assert run_demo._run_prewarm() == 2
    assert "refused before any provider call" in capsys.readouterr().err
