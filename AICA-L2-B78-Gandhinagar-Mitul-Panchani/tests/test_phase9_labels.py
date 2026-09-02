"""Phase 9 static contracts for presentation-friendly, auditable UI labels."""

from __future__ import annotations

from enum import EnumType, StrEnum
from pathlib import Path
import re

import amg.models as models


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "src" / "amg" / "web" / "static" / "app.js"
STYLE_CSS = ROOT / "src" / "amg" / "web" / "static" / "style.css"
INDEX_HTML = ROOT / "src" / "amg" / "web" / "templates" / "index.html"


def _enum_types() -> list[type[StrEnum]]:
    return [
        value
        for value in vars(models).values()
        if isinstance(value, EnumType)
        and issubclass(value, StrEnum)
        and value is not StrEnum
    ]


def _label_lookup(app_js: str) -> str:
    return app_js.split("const DISPLAY_LABELS", maxsplit=1)[1].split(
        "function escapeHtml", maxsplit=1
    )[0]


def _export_handler(app_js: str) -> str:
    return app_js.split('$("#run-export")', maxsplit=1)[1].split(
        "$$('.scenario-button')", maxsplit=1
    )[0]


def test_demo_placeholders_are_distinct_from_scripted_inputs() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    scripted_turn = (
        'placeholder="I work as a financial controller at Northwind Textiles '
        'in Coimbatore."'
    )
    assert scripted_turn not in html
    assert 'placeholder="Where do I work?"' not in html
    assert (
        'placeholder="e.g. I work as a financial controller at Northwind Textiles."'
        in html
    )
    assert 'placeholder="e.g. Where do I work?"' in html
    assert 'placeholder="Passphrase"' in html


def test_placeholder_and_stage_wrapping_rules_are_explicit() -> None:
    css = STYLE_CSS.read_text(encoding="utf-8")
    stage_rule = css.split(".stage {", maxsplit=1)[1].split("}", maxsplit=1)[0]
    heading_rule = css.split(".stage strong {", maxsplit=1)[1].split(
        "}", maxsplit=1
    )[0]

    assert "::placeholder" in css
    assert "overflow-wrap: anywhere" not in stage_rule
    assert "overflow-wrap: break-word" in stage_rule
    assert "overflow-wrap: normal" in heading_rule
    assert "hyphens: none" in heading_rule


def test_label_lookup_covers_every_python_enum_and_served_by_value() -> None:
    app_js = APP_JS.read_text(encoding="utf-8")
    lookup = _label_lookup(app_js)
    labels = dict(re.findall(r'"([^"]+)": "([^"]+)",', lookup))

    for enum_type in _enum_types():
        for member in enum_type:
            assert member.value in labels, (
                f"DISPLAY_LABELS is missing {enum_type.__name__}.{member.name}"
            )
            assert labels[member.value] != member.value

    for served_by in models.ServedBy.__args__:
        assert served_by in labels, (
            f"DISPLAY_LABELS is missing ServedBy value {served_by}"
        )
        assert labels[served_by] != served_by


def test_raw_values_are_rendered_beneath_friendly_labels() -> None:
    app_js = APP_JS.read_text(encoding="utf-8")

    assert "DISPLAY_LABELS[group]?.[rawValue] ?? String(rawValue" in app_js
    assert (
        '<small class="technical-detail">${escapeHtml(group)}: '
        "${escapeHtml(rawValue)}</small>"
    ) in app_js
    assert "${escapeHtml(provider.served_by)}" in app_js
    assert "subject_key: ${escapeHtml(rawValue)}" in app_js


def test_offline_by_design_uses_a_neutral_note() -> None:
    app_js = APP_JS.read_text(encoding="utf-8")
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert 'servedBy.has("blocked_offline")' in app_js
    assert "Running in offline mode - the deterministic engine served this." in app_js
    assert '<div class="provider-note offline">' in app_js
    assert ".provider-note.offline" in css
    assert "A provider fallback served part of this candidate" not in app_js


def test_successful_export_handler_renders_complete_labeled_records() -> None:
    app_js = APP_JS.read_text(encoding="utf-8")
    handler = _export_handler(app_js)
    success_branch = handler.split("if (result.succeeded) {", maxsplit=1)[1].split(
        "} else {", maxsplit=1
    )[0]

    assert "result.memories.map((memory)" in success_branch
    for field in (
        "content",
        "subject_key",
        "source_type",
        "status",
        "created_at",
        "source_session_id",
    ):
        assert f"memory.{field}" in success_branch
    assert "memoryTrustTier(memory)" in success_branch
    assert 'subjectKeyValue(memory.subject_key)' in success_branch
    assert 'labeledValue("source_type", memory.source_type' in success_branch
    assert 'labeledValue("trust_tier", trustTier' in success_branch
    assert 'labeledValue("status", memory.status)' in success_branch
    assert "Complete record returned under the Section 11 access right" in success_branch


def test_refused_export_branch_cannot_render_memory_fields() -> None:
    app_js = APP_JS.read_text(encoding="utf-8")
    handler = _export_handler(app_js)
    failure_branch = handler.split("} else {", maxsplit=1)[1].split(
        "\n  }\n  await refreshAll()", maxsplit=1
    )[0]

    assert "REFUSED: ${result.reason} Zero rows returned." in failure_branch
    assert "result.memories" not in failure_branch
    assert "memory." not in failure_branch


def test_export_table_is_bounded_and_scrollable() -> None:
    app_js = APP_JS.read_text(encoding="utf-8")
    css = STYLE_CSS.read_text(encoding="utf-8")
    export_rule = css.split(".export-scroll {", maxsplit=1)[1].split(
        "}", maxsplit=1
    )[0]

    assert 'class="table-scroll export-scroll"' in _export_handler(app_js)
    assert "max-height:" in export_rule
    assert "overflow: auto" in export_rule
