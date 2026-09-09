"""
Pytest configuration for offline pipeline tests.

These tests run the full pipeline against local fixture folders (no OneDrive) and
stub the OpenAI calls (no API key / network), so every change can be verified fast
and deterministically.
"""

import json
import os

import pytest

# A dummy key so lazy OpenAI() construction never blocks; all LLM calls are stubbed.
# Run pytest with PYTHONIOENCODING=utf-8 so emoji logging is safe on any console.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
# app_standalone intentionally refuses to start without an explicit session key.
os.environ.setdefault("FLASK_SECRET_KEY", "test-only-flask-secret-key")
# Worker imports construct Supabase clients, but the offline suite never makes a
# Supabase request. CI therefore needs syntactically valid, non-secret placeholders.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYW5vbiJ9.test-signature",
)

# The offline pipeline integration test pins the plain (stubbed) validator regardless
# of the developer's local .env (which may enable panel/tool-loop). The agentic loop and
# panel have their own unit tests (test_tool_validator.py / test_panel*.py).
os.environ["AI_TOOL_LOOP_ENABLED"] = "false"
os.environ["AI_PANEL_ENABLED"] = "false"
os.environ["AI_PANEL_TIEBREAKER_ENABLED"] = "false"

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def fixtures_dir():
    return FIXTURES


@pytest.fixture
def stub_llms(monkeypatch):
    """
    Stub the criteria engine and generic validator LLM seams with canned JSON.

    The criteria engine returns a reconcile checklist; the validator only needs to
    answer the non-deterministic criteria (deterministic ones are computed locally).
    """
    import services.criteria_engine as ce
    import services.generic_validator as gv

    def fake_criteria(self, prompt):
        return json.dumps({
            "task_summary": "Reconcile the output table against the input table.",
            "criteria": [
                {"id": "C1", "statement": "Every input id appears in the output",
                 "type": "deterministic", "severity": "critical", "source": "workflow"},
                {"id": "C2", "statement": "Amount matches per id",
                 "type": "deterministic", "severity": "error", "source": "workflow"},
                {"id": "C3", "statement": "Output has the same number of rows as input",
                 "type": "deterministic", "severity": "warning", "source": "workflow"},
                {"id": "C4", "statement": "The output is clearly formatted",
                 "type": "semantic", "severity": "info", "source": "inferred"},
            ],
        })

    def fake_validate(self, prompt):
        # Only the semantic criterion needs an AI answer here.
        return json.dumps({"criteria_results": [
            {"id": "C4", "status": "PASS", "evidence": "single clean header row", "explanation": "well formatted"},
        ]})

    monkeypatch.setattr(ce.CriteriaEngine, "_complete", fake_criteria)
    monkeypatch.setattr(gv.GenericValidator, "_complete", fake_validate)
