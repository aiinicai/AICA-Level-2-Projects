"""Specialization router: generic by default, TDS when its doc types appear."""

from services.specialization_router import detect_specialization
from services.task_loader import load_task


def test_generic_when_no_specialization():
    nd = {
        "normalized_inputs": [{"document_type": "SPREADSHEET", "file": "a.csv"}],
        "normalized_outputs": [{"document_type": "SPREADSHEET", "file": "b.csv"}],
    }
    assert detect_specialization(nd) is None


def test_tds_detected_from_doc_types():
    nd = {
        "normalized_inputs": [
            {"document_type": "pdf_challan", "file": "c.pdf"},
            {"document_type": "excel_bsct", "file": "b.xlsx"},
        ],
        "normalized_outputs": [{"document_type": "output_26q", "file": "26q.xlsm"}],
    }
    assert detect_specialization(nd) == "tds_26q"


def test_tds_matches_confidence():
    task = load_task("tds_26q")
    generic = {"normalized_inputs": [{"document_type": "SPREADSHEET"}], "normalized_outputs": []}
    tds = {"normalized_inputs": [], "normalized_outputs": [{"document_type": "output_26q"}]}
    assert task.matches(generic) == 0.0
    assert task.matches(tds) == 1.0
