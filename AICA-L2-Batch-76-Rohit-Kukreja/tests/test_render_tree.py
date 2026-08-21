"""Node tree. Build Prompt v2 §3.4 — both renderers consume this."""

from __future__ import annotations

import pytest

from app.render.base import Document, Heading, NodeKind, Para, Signature, Table


def test_document_collects_nodes() -> None:
    doc = Document(id="auditors_report", title="Independent Auditor's Report")
    doc.add(Heading(text="Opinion", level=2))
    doc.add(Para(text="Body text.", clause_id="iar.opinion"))
    assert [n.kind for n in doc.nodes] == [NodeKind.HEADING, NodeKind.PARA]


def test_table_rejects_ragged_rows() -> None:
    # A ragged statutory table silently drops a column in the rendered
    # document, which is how a disputed-dues forum goes missing.
    with pytest.raises(ValueError, match="expected 3"):
        Table(headers=("A", "B", "C"), rows=(("1", "2"),))


def test_text_nodes_reach_every_visible_string() -> None:
    """The pre-export placeholder scan (§18.4) is only as good as this."""
    doc = Document(id="d", title="T")
    doc.add(Heading(text="H"))
    doc.add(Para(text="P"))
    doc.add(Table(headers=("h1",), rows=(("r1",),), caption="C"))
    doc.add(Signature(lines=("S",)))
    assert set(doc.text_nodes()) == {"H", "P", "h1", "r1", "C", "S"}
