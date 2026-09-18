"""Tests for core.form_engine: AcroForm list/fill/export/flatten."""
from __future__ import annotations

import fitz
import pytest

from core.form_engine import export_form_data, fill_form, flatten_form, list_form_fields
from utils.validation import ValidationError


def _make_form_pdf(path, fields: dict[str, tuple[float, float, float, float]]):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    for name, rect in fields.items():
        widget = fitz.Widget()
        widget.field_name = name
        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        widget.field_type_string = "Text"
        widget.rect = fitz.Rect(*rect)
        widget.field_value = ""
        page.add_widget(widget)
    doc.save(str(path))
    doc.close()
    return path


def test_list_form_fields(tmp_path):
    src = _make_form_pdf(tmp_path / "form.pdf", {"client_name": (200, 85, 400, 110), "amount": (200, 135, 400, 160)})
    fields = list_form_fields(src)
    names = {f.name for f in fields}
    assert names == {"client_name", "amount"}
    assert all(f.field_type == "Text" for f in fields)


def test_fill_form_sets_values(tmp_path):
    src = _make_form_pdf(tmp_path / "form.pdf", {"client_name": (200, 85, 400, 110)})
    out = tmp_path / "filled.pdf"
    updated = fill_form(src, out, {"client_name": "Kishor Singh and Co."})
    assert updated == 1
    data = export_form_data(out)
    assert data["client_name"] == "Kishor Singh and Co."


def test_fill_form_ignores_unknown_field_names(tmp_path):
    src = _make_form_pdf(tmp_path / "form.pdf", {"client_name": (200, 85, 400, 110)})
    out = tmp_path / "filled.pdf"
    updated = fill_form(src, out, {"nonexistent_field": "value"})
    assert updated == 0


def test_export_form_data_reflects_current_values(tmp_path):
    src = _make_form_pdf(tmp_path / "form.pdf", {"amount": (200, 135, 400, 160)})
    filled = tmp_path / "filled.pdf"
    fill_form(src, filled, {"amount": "118000"})
    data = export_form_data(filled)
    assert data == {"amount": "118000"}


def test_flatten_form_bakes_values_and_removes_widgets(tmp_path):
    src = _make_form_pdf(tmp_path / "form.pdf", {"client_name": (200, 85, 400, 110)})
    filled = tmp_path / "filled.pdf"
    fill_form(src, filled, {"client_name": "Test Client"})

    flat = tmp_path / "flat.pdf"
    count = flatten_form(filled, flat)
    assert count == 1

    with fitz.open(str(flat)) as doc:
        assert "Test Client" in doc[0].get_text()
        assert list(doc[0].widgets() or []) == []


def test_original_file_untouched_by_fill(tmp_path):
    src = _make_form_pdf(tmp_path / "form.pdf", {"client_name": (200, 85, 400, 110)})
    original_bytes = src.read_bytes()
    fill_form(src, tmp_path / "out.pdf", {"client_name": "X"})
    assert src.read_bytes() == original_bytes


def test_non_form_pdf_has_no_fields(tmp_path):
    doc = fitz.open()
    doc.new_page(width=595, height=842).insert_text((72, 100), "No form fields here.")
    src = tmp_path / "plain.pdf"
    doc.save(str(src))
    doc.close()
    assert list_form_fields(src) == []
