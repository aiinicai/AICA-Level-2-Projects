"""AcroForm handling: list fields, fill values, export data, flatten to static content.

Only classic AcroForm fields are supported (text, checkbox, radio button,
combo box, list box) via PyMuPDF's widget API. XFA forms (a separate,
legacy Adobe form technology embedded in some government/bank PDFs) are
explicitly detected and rejected with a clear message rather than silently
producing an empty or wrong result.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from core.pdf_engine import open_pdf
from utils.validation import ValidationError


@dataclass
class FormField:
    name: str
    field_type: str  # PyMuPDF's field_type_string: "Text", "CheckBox", "RadioButton", "ComboBox", "ListBox", ...
    page_index: int
    current_value: str
    choices: list[str]  # populated for ComboBox/ListBox/RadioButton


def has_xfa_form(doc: fitz.Document) -> bool:
    try:
        xml = doc.xref_get_key(doc.pdf_catalog(), "AcroForm")
        if xml[0] == "null":
            return False
        acroform_xref = int(xml[1].strip("0 R").split()[0]) if "R" in xml[1] else None
        if acroform_xref:
            xfa = doc.xref_get_key(acroform_xref, "XFA")
            return xfa[0] != "null"
    except Exception:  # noqa: BLE001 - detection is best-effort; treat inconclusive as "not XFA"
        pass
    return False


def list_form_fields(source_path: str | Path) -> list[FormField]:
    with open_pdf(source_path) as doc:
        if has_xfa_form(doc):
            raise ValidationError(
                "This PDF uses an XFA form (a legacy Adobe form format), which is not supported. "
                "Only standard AcroForm fields (the common case for most fillable PDFs) can be read."
            )
        fields: list[FormField] = []
        for page_index in range(doc.page_count):
            for widget in doc[page_index].widgets() or []:
                fields.append(
                    FormField(
                        name=widget.field_name or "",
                        field_type=widget.field_type_string,
                        page_index=page_index,
                        current_value=str(widget.field_value) if widget.field_value is not None else "",
                        choices=list(widget.choice_values) if widget.choice_values else [],
                    )
                )
        return fields


def fill_form(source_path: str | Path, output_path: str | Path, field_values: dict[str, str]) -> int:
    """Set the given field values (by name) and save as a new PDF. Returns the count actually set."""
    updated = 0
    with open_pdf(source_path) as doc:
        if has_xfa_form(doc):
            raise ValidationError("This PDF uses an XFA form and cannot be filled by this tool.")
        for page_index in range(doc.page_count):
            for widget in doc[page_index].widgets() or []:
                if widget.field_name in field_values:
                    widget.field_value = field_values[widget.field_name]
                    widget.update()
                    updated += 1
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=3, deflate=True)
    return updated


def export_form_data(source_path: str | Path) -> dict[str, str]:
    return {f.name: f.current_value for f in list_form_fields(source_path) if f.name}


def flatten_form(source_path: str | Path, output_path: str | Path) -> int:
    """Bake every field's current value into normal page content and remove the
    interactive widgets, so the result behaves like a plain (non-fillable) PDF.

    Returns the number of fields flattened.
    """
    flattened = 0
    with open_pdf(source_path) as doc:
        if has_xfa_form(doc):
            raise ValidationError("This PDF uses an XFA form and cannot be flattened by this tool.")
        for page_index in range(doc.page_count):
            page = doc[page_index]
            for widget in list(page.widgets() or []):
                value = widget.field_value
                rect = widget.rect
                if value:
                    page.insert_textbox(rect, str(value), fontsize=min(11, rect.height * 0.7), fontname="helv")
                page.delete_widget(widget)
                flattened += 1
        # Removing the last widget can leave the AcroForm/NeedAppearances catalog
        # entries pointing at nothing; a normal garbage-collecting save cleans this up.
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=4, deflate=True)
    return flattened
