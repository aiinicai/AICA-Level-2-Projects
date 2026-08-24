"""Phase 10 static contracts for compact setup chrome and honest status."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from amg.web.app import create_app


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "src" / "amg" / "web" / "static" / "app.js"
STYLE_CSS = ROOT / "src" / "amg" / "web" / "static" / "style.css"


def test_home_contains_compact_status_bar_and_settings_dialog(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "phase10.db")) as client:
        response = client.get("/")

    assert response.status_code == 200
    html = response.text
    status_bar = html.split('<section id="status-bar"', maxsplit=1)[1].split(
        "</section>", maxsplit=1
    )[0]
    # The status bar carries ACTIONS and at-a-glance state only. Session
    # identity moved to the header beside the chain status: both answer
    # "what state is this system in", which is not an action.
    for element_id in (
        "provider-status",
        "new-session",
        "open-settings",
        "reset",
    ):
        assert f'id="{element_id}"' in status_bar

    # Session identity belongs in the header, not the action bar.
    header = html.split("<header", maxsplit=1)[1].split("</header>", maxsplit=1)[0]
    for element_id in ("chain-summary", "session-id", "session-note", "budget-status"):
        assert f'id="{element_id}"' in header
    assert 'id="session-id"' not in status_bar

    # The "fresh context" wording is a demo talking point and must survive.
    assert "zero conversation history" in html

    dialog = html.split('<dialog id="settings-dialog"', maxsplit=1)[1].split(
        "</dialog>", maxsplit=1
    )[0]
    for element_id in (
        "settings-mode",
        "gemini-key",
        "voyage-key",
        "gemini-model",
        "save-settings",
        "save-settings-close",
        "cancel-settings",
        "test-settings",
        "clear-settings",
    ):
        assert f'id="{element_id}"' in dialog


def test_left_column_contains_only_scripted_evidence() -> None:
    template = (
        ROOT / "src" / "amg" / "web" / "templates" / "index.html"
    ).read_text(encoding="utf-8")
    left_column = template.split(
        '<aside class="column controls-column"', maxsplit=1
    )[1].split("</aside>", maxsplit=1)[0]

    assert left_column.count('<section class="panel">') == 1
    assert "Scripted Evidence" in left_column
    assert "Session &amp; providers" not in left_column
    assert "AI provider settings" not in left_column
    assert "Demo controls" not in left_column


def test_four_honest_provider_indicator_states_remain_distinct() -> None:
    css = STYLE_CSS.read_text(encoding="utf-8")
    js = APP_JS.read_text(encoding="utf-8")

    expected = {
        "offline": "provider-offline",
        "live": "provider-live",
        "cached": "provider-cached",
        "fallback": "provider-fallback",
    }
    assert len(set(expected.values())) == 4
    for state, class_name in expected.items():
        assert f'{state}: {{ label:' in js
        assert f'className: "{class_name}"' in js
        assert f".{class_name}" in css


def test_demo_defence_wording_survives_the_move(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "wording.db")) as client:
        html = client.get("/").text

    assert "zero conversation history" in html
    assert "stored in plain text locally" in html


def test_dialog_behaviour_contracts_are_explicit() -> None:
    js = APP_JS.read_text(encoding="utf-8")

    assert '.showModal()' in js
    assert 'saveSettings(false)' in js
    assert 'saveSettings(true)' in js
    assert 'settingsDialog.addEventListener("cancel"' in js
    assert "event.preventDefault()" in js
    assert "restoreStoredSettings();" in js
    assert "if (outside) cancelSettingsDialog();" in js
    assert "if (opener) opener.focus();" in js
    assert '$("#gemini-key").value = "";' in js
    assert '$("#voyage-key").value = "";' in js
    assert "}, 8000);" in js
