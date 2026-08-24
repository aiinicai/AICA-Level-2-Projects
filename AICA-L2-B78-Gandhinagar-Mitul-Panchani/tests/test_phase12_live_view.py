"""Phase 12 contracts for opt-in, presentation-safe live view polling."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from amg.web.app import create_app


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "src" / "amg" / "web" / "static" / "app.js"
STYLE_CSS = ROOT / "src" / "amg" / "web" / "static" / "style.css"


def _function(source: str, name: str, next_name: str) -> str:
    return source.split(f"function {name}", maxsplit=1)[1].split(
        f"function {next_name}", maxsplit=1
    )[0]


def test_served_live_view_is_visible_but_default_polling_is_off(
    tmp_path: Path,
) -> None:
    with TestClient(create_app(tmp_path / "phase12.db")) as client:
        html_response = client.get("/")
        js_response = client.get("/static/app.js")

    assert html_response.status_code == 200
    assert js_response.status_code == 200
    assert 'id="live-view-status"' in html_response.text
    assert "LIVE VIEW" in html_response.text
    assert 'class="live-view-status" role="status" hidden' in html_response.text

    js = js_response.text
    interval_function = _function(js, "liveViewInterval", "newlySeenIds")
    startup = js.split(
        'window.addEventListener("DOMContentLoaded"', maxsplit=1
    )[1]
    assert 'new URLSearchParams(search).get("live")' in interval_function
    assert "if (rawValue === null) return null;" in interval_function
    assert "if (interval !== null) enableLiveView(interval);" in startup
    assert (
        "if (interval !== null) window.setInterval(pollLiveView, interval);"
        in startup
    )


def test_live_view_interval_is_defaulted_and_clamped() -> None:
    js = APP_JS.read_text(encoding="utf-8")
    interval_function = _function(js, "liveViewInterval", "newlySeenIds")

    assert "const LIVE_VIEW_DEFAULT_INTERVAL_MS = 1500;" in js
    assert "const LIVE_VIEW_MIN_INTERVAL_MS = 500;" in js
    assert "const LIVE_VIEW_MAX_INTERVAL_MS = 10000;" in js
    assert (
        'rawValue === "1" ? LIVE_VIEW_DEFAULT_INTERVAL_MS : Number(rawValue)'
        in interval_function
    )
    assert "Math.min(" in interval_function
    assert "LIVE_VIEW_MAX_INTERVAL_MS" in interval_function
    assert "Math.max(LIVE_VIEW_MIN_INTERVAL_MS, requested)" in interval_function


def test_poll_reuses_refreshers_without_tab_switches_toasts_or_settings() -> None:
    js = APP_JS.read_text(encoding="utf-8")
    poll = js.split("async function pollLiveView", maxsplit=1)[1].split(
        "function enableLiveView", maxsplit=1
    )[0]

    assert "refreshEvidence()" in poll
    assert "refreshStatus()" in poll
    assert "Promise.allSettled" in poll
    assert "refreshSettings()" not in poll
    assert "refreshAll()" not in poll
    assert "activateEvidenceTab" not in poll
    assert "toast(" not in poll
    assert "captureRefreshFocus()" in poll
    assert "restoreRefreshFocus(focusTarget)" in poll
    assert "catch (_)" in poll


def test_new_rows_flash_only_after_an_id_baseline_exists() -> None:
    js = APP_JS.read_text(encoding="utf-8")
    css = STYLE_CSS.read_text(encoding="utf-8")
    detector = _function(js, "newlySeenIds", "captureRefreshFocus")

    assert "liveViewEnabled && previousIds !== null" in detector
    assert "!previousIds.has(id)" in detector
    assert "previousMemoryIds = seen.currentIds;" in js
    assert "previousAuditIds = seen.currentIds;" in js
    assert 'seen.newIds.has(String(item.id)) ? "row-changed"' in js
    assert 'seen.newIds.has(String(row.id)) ? " row-changed"' in js
    assert ".row-changed { animation: evidence-row-flash 1.5s ease-out; }" in css
    assert "--change-flash: #ffd36a;" in css
    assert "background: var(--change-flash)" in css
    assert "background-color: var(--change-flash)" in css
