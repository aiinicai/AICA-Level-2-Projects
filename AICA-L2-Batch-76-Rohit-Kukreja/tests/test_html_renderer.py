"""HTML adapter. Build Prompt v2 §3.4 and §13."""

from __future__ import annotations

from app.render.base import Bullet, Document, Heading, Para, Signature, Table
from app.render.html import render, render_node


class TestEscaping:
    def test_escapes_markup_in_text(self) -> None:
        # §13 — the prototype injected everything through unescaped innerHTML.
        html = render_node(Para(text="<script>alert(1)</script>"))
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_escapes_ampersands_in_table_cells(self) -> None:
        html = render_node(Table(headers=("A & B",), rows=(("C & D",),)))
        assert "A &amp; B" in html
        assert "C &amp; D" in html

    def test_escapes_attribute_values(self) -> None:
        html = render_node(Para(text="x", clause_id='" onload="evil()'))
        assert 'onload="evil()"' not in html


class TestStructure:
    def test_heading_level_clamped(self) -> None:
        assert "<h1" in render_node(Heading(text="T", level=0))
        assert "<h6" in render_node(Heading(text="T", level=99))

    def test_clause_number_rendered_separately(self) -> None:
        html = render_node(Para(text="Body.", number="(viii)", clause_id="caro.viii"))
        assert 'class="clause-no"' in html
        assert 'data-clause="caro.viii"' in html

    def test_bullets_wrapped_in_one_list(self) -> None:
        doc = Document(id="d", title="T")
        doc.add(Bullet(text="one"))
        doc.add(Bullet(text="two"))
        doc.add(Para(text="after"))
        html = render(doc)
        assert html.count("<ul") == 1
        assert html.count("</ul>") == 1
        assert html.index("</ul>") < html.index("after")

    def test_document_surface_is_the_print_target(self) -> None:
        html = render(Document(id="d", title="T"))
        assert 'class="document-surface"' in html

    def test_the_rendered_document_carries_no_version_stamp(self) -> None:
        """Removed 19 August 2026 with the .docx stamp, and for the same reason.

        The preview exists to show what will be signed, so a version marker
        printed inside it would be the one thing on the page the exported
        document does not carry. It is still shown in the page chrome ABOVE the
        document, where it describes the file rather than forming part of it.
        """
        doc = Document(id="d", title="T", template_version="0.1.0-phase1")
        assert "0.1.0-phase1" not in render(doc)

    def test_signature_lines(self) -> None:
        html = render_node(Signature(lines=("For X & Co.", "FRN 000000W")))
        assert "For X &amp; Co." in html
        assert "FRN 000000W" in html
