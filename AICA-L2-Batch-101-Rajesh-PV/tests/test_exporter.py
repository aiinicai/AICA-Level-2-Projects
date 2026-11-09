from datetime import datetime

import pymupdf as fitz
import pytest
from conftest import SAMPLE_REPORT
from docx import Document

from judgment_analyzer.exporter import (build_export_document, markdown_to_plain, parse_blocks, safe_filename,
                                        save_docx, save_pdf, save_text, split_inline, strip_inline)
from judgment_analyzer.response_parser import parse_report


@pytest.fixture
def export_doc():
    report = parse_report(SAMPLE_REPORT)
    return build_export_document(report.ordered_sections(), "sample_judgment.pdf", 3, "gemini-3.8-flash",
                                 "Single pass", ["OCR was used on 1 page(s)."], datetime(2026, 10, 12, 9, 30))


def test_parse_blocks_kinds():
    blocks = parse_blocks("## Head\nPara line one\ncontinues\n\n- bullet\n  - nested\n3. numbered\n> quote\n---")
    kinds = [(b.kind, b.level) for b in blocks]
    assert kinds == [("heading", 2), ("paragraph", 0), ("blank", 0), ("bullet", 0), ("bullet", 1),
                     ("numbered", 0), ("quote", 0)]
    assert blocks[1].text == "Para line one continues"
    assert blocks[5].number == "3"


def test_inline_formatting():
    assert split_inline("a **b** *c* ***d*** `e`") == [
        ("a ", False, False), ("b", True, False), (" ", False, False), ("c", False, True),
        (" ", False, False), ("d", True, True), (" ", False, False), ("e", False, False)]
    assert strip_inline("Section 2*3 and 4*5") == "Section 2*3 and 4*5"


def test_markdown_to_plain():
    text = markdown_to_plain("## 1. Case Details\n- **Court:** X\n\nBody *text*.")
    assert "1. CASE DETAILS" in text
    assert "• Court: X" in text
    assert "**" not in text and "*" not in text


def test_build_export_document_metadata(export_doc):
    meta = dict(export_doc.metadata)
    assert meta["Source document"] == "sample_judgment.pdf"
    assert meta["Pages"] == "3"
    assert meta["Generated"] == "12 Oct 2026 09:30"
    assert export_doc.sections[-1][0] == "Disclaimer"
    md = export_doc.to_markdown()
    assert md.index("13. Key Insights") < md.index("14. Points for Consideration") < md.index("## Disclaimer")


def test_build_export_requires_content_and_disclaimer():
    with pytest.raises(ValueError):
        build_export_document([], "x.pdf")
    with pytest.raises(ValueError):
        build_export_document([("1. Case Details", "x")], "x.pdf")


def test_safe_filename():
    assert safe_filename("SC: Judgment/2024*final", ".docx") == "SC_ Judgment_2024_final_analysis.docx"
    assert safe_filename("", ".txt") == "analysis_analysis.txt"


def test_save_text(tmp_path, export_doc):
    path = save_text(export_doc, tmp_path / "out.txt")
    content = path.read_text(encoding="utf-8")
    assert "JUDGEMENT INSIGHTS ANALYSIS" in content
    assert "Civil Appeal No. 123 of 2024" in content
    assert "not legal advice" in content


def test_save_docx(tmp_path, export_doc):
    path = save_docx(export_doc, tmp_path / "out.docx")
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert "14. Points for Consideration" in text
    assert "Scope of section 9" in text
    assert "Disclaimer" in text


def test_save_pdf(tmp_path, export_doc):
    path = save_pdf(export_doc, tmp_path / "out.pdf")
    with fitz.open(path) as doc:
        text = "".join(page.get_text() for page in doc)
    assert "Judgement Insights Analysis" in text
    assert "Points for Consideration" in text
    assert "not legal advice" in text


def test_pdf_escapes_special_characters(tmp_path):
    doc = build_export_document([("1. Case Details", "A < B & C > D"), ("Disclaimer", "x")], "a.pdf")
    path = save_pdf(doc, tmp_path / "special.pdf")
    with fitz.open(path) as d:
        assert "A < B & C > D" in d[0].get_text()
