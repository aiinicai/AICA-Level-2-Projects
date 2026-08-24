"""Phase 11 contracts for the tabbed, continuously visible evidence surface."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient

from amg.web.app import create_app


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "src" / "amg" / "web" / "static" / "app.js"
STYLE_CSS = ROOT / "src" / "amg" / "web" / "static" / "style.css"


class _StructureParser(HTMLParser):
    """Capture element attributes and id ancestry without another dependency."""

    VOID_ELEMENTS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__()
        self.elements: list[dict[str, object]] = []
        self._stack: list[tuple[str, str | None]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        self.elements.append(
            {
                "tag": tag,
                "attrs": attributes,
                "ancestors": tuple(
                    element_id for _, element_id in self._stack if element_id
                ),
            }
        )
        if tag not in self.VOID_ELEMENTS:
            self._stack.append((tag, attributes.get("id")))

    def handle_endtag(self, tag: str) -> None:
        while self._stack:
            open_tag, _ = self._stack.pop()
            if open_tag == tag:
                break

    def by_id(self, element_id: str) -> dict[str, object]:
        return next(
            element
            for element in self.elements
            if element["attrs"].get("id") == element_id  # type: ignore[union-attr]
        )


def _served_structure(tmp_path: Path) -> _StructureParser:
    with TestClient(create_app(tmp_path / "phase11.db")) as client:
        response = client.get("/")

    assert response.status_code == 200
    parser = _StructureParser()
    parser.feed(response.text)
    return parser


def test_evidence_panel_has_exactly_two_semantic_tabs(tmp_path: Path) -> None:
    parser = _served_structure(tmp_path)
    tablist = parser.by_id("evidence-tabs")
    assert tablist["attrs"].get("role") == "tablist"  # type: ignore[union-attr]

    tabs = [
        element
        for element in parser.elements
        if element["attrs"].get("role") == "tab"  # type: ignore[union-attr]
    ]
    assert len(tabs) == 2
    assert all("evidence-tabs" in element["ancestors"] for element in tabs)
    assert [element["attrs"].get("aria-controls") for element in tabs] == [  # type: ignore[union-attr]
        "memory-pane",
        "audit-pane",
    ]


def test_memory_pane_is_the_only_visible_pane_on_load(tmp_path: Path) -> None:
    parser = _served_structure(tmp_path)
    memory_tab = parser.by_id("memory-tab")
    audit_tab = parser.by_id("audit-tab")
    memory_pane = parser.by_id("memory-pane")
    audit_pane = parser.by_id("audit-pane")

    assert memory_pane["attrs"].get("role") == "tabpanel"  # type: ignore[union-attr]
    assert audit_pane["attrs"].get("role") == "tabpanel"  # type: ignore[union-attr]
    assert "hidden" not in memory_pane["attrs"]
    assert "hidden" in audit_pane["attrs"]
    assert memory_tab["attrs"].get("aria-selected") == "true"  # type: ignore[union-attr]
    assert audit_tab["attrs"].get("aria-selected") == "false"  # type: ignore[union-attr]


def test_count_badges_are_distinct_elements_inside_their_tabs(tmp_path: Path) -> None:
    parser = _served_structure(tmp_path)
    memory_count = parser.by_id("memory-count")
    audit_count = parser.by_id("audit-count")
    labels = [
        element
        for element in parser.elements
        if element["attrs"].get("class") == "tab-label"  # type: ignore[union-attr]
    ]

    assert memory_count["tag"] == audit_count["tag"] == "span"
    assert memory_count["attrs"].get("class") == "count-badge"  # type: ignore[union-attr]
    assert audit_count["attrs"].get("class") == "count-badge"  # type: ignore[union-attr]
    assert "memory-tab" in memory_count["ancestors"]
    assert "audit-tab" in audit_count["ancestors"]
    assert len(labels) == 2
    assert [element["ancestors"][-1] for element in labels] == [
        "memory-tab",
        "audit-tab",
    ]


def test_chain_summary_and_controls_remain_in_the_right_places(tmp_path: Path) -> None:
    parser = _served_structure(tmp_path)
    pane_ids = {"memory-pane", "audit-pane"}
    chain = parser.by_id("chain-summary")
    assert pane_ids.isdisjoint(chain["ancestors"])

    expected_ancestors = {
        "refresh-memories": "memory-pane",
        "verify-chain": "audit-pane",
        "tamper": "audit-pane",
        "repair": "audit-pane",
    }
    for element_id, pane_id in expected_ancestors.items():
        assert pane_id in parser.by_id(element_id)["ancestors"]

    audit_control_order = [
        next(
            index
            for index, element in enumerate(parser.elements)
            if element["attrs"].get("id") == element_id  # type: ignore[union-attr]
        )
        for element_id in ("verify-chain", "tamper", "repair")
    ]
    assert audit_control_order == sorted(audit_control_order)
    assert audit_control_order[2] == audit_control_order[1] + 1


def test_tab_interaction_counts_and_scrolling_contracts_are_explicit() -> None:
    js = APP_JS.read_text(encoding="utf-8")
    css = STYLE_CSS.read_text(encoding="utf-8")

    for key in ("ArrowLeft", "ArrowRight"):
        assert f'event.key === "{key}"' in js
    assert 'tab.addEventListener("keydown", handleEvidenceTabKeydown)' in js
    assert 'updateEvidenceCount("#memory-count", data.count' in js
    assert 'updateEvidenceCount("#audit-count", data.count' in js
    assert "previous === undefined || previous === next" in js
    assert "}, 1200);" in js

    verify_handler = js.split('$("#verify-chain")', maxsplit=1)[1].split(
        '$("#tamper")', maxsplit=1
    )[0]
    tamper_handler = js.split('$("#tamper").addEventListener', maxsplit=1)[1].split(
        'window.addEventListener("DOMContentLoaded"', maxsplit=1
    )[0]
    assert 'activateEvidenceTab($("#audit-tab"))' in verify_handler
    assert 'activateEvidenceTab($("#audit-tab"))' in tamper_handler

    panel_rule = css.split(".evidence-panel {", maxsplit=1)[1].split(
        "}", maxsplit=1
    )[0]
    pane_rule = css.split(".evidence-pane {", maxsplit=1)[1].split(
        "}", maxsplit=1
    )[0]
    assert "flex-direction: column" in panel_rule
    assert "overflow: hidden" in panel_rule
    assert "overflow: auto" in pane_rule
    assert ".evidence-pane[hidden] { display: none; }" in css
    assert "count-badge-flash 1.2s" in css
