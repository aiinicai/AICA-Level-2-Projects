import services.jury as jury
from models.check_spec import CheckSpec


def _spec(types_sevs):
    return CheckSpec.from_ai_dict({"criteria": [
        {"id": f"C{i}", "statement": "x", "type": t, "severity": s}
        for i, (t, s) in enumerate(types_sevs)]})


def test_auto_convenes_panel_on_many_blocking_judgment(monkeypatch):
    monkeypatch.delenv("AI_PANEL_ENABLED", raising=False)
    spec = _spec([("semantic", "critical"), ("hybrid", "error"), ("semantic", "error")])
    assert jury.should_convene_panel(spec) is True


def test_auto_skips_panel_when_mostly_deterministic(monkeypatch):
    monkeypatch.delenv("AI_PANEL_ENABLED", raising=False)
    spec = _spec([("deterministic", "critical"), ("deterministic", "error"), ("semantic", "info")])
    assert jury.should_convene_panel(spec) is False


def test_explicit_on_off_override(monkeypatch):
    spec = _spec([("deterministic", "critical")])
    monkeypatch.setenv("AI_PANEL_ENABLED", "on")
    assert jury.should_convene_panel(spec) is True
    monkeypatch.setenv("AI_PANEL_ENABLED", "off")
    spec2 = _spec([("semantic", "critical"), ("semantic", "error"), ("hybrid", "critical")])
    assert jury.should_convene_panel(spec2) is False
