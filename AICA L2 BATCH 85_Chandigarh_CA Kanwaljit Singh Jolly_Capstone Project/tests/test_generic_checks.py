"""Unit tests for the generic deterministic checks (coverage / value / count)."""

import contextlib
import io
import os
import shutil
import tempfile

from models.check_spec import CheckSpec
from services.file_source import LocalDirSource
from services.generic_checks import _quoted_phrases, run_generic_checks
from services.section2_ingestion import Section2Ingestion
from services.section3_normalization import Section3Normalization

SPEC = CheckSpec.from_ai_dict({"criteria": [
    {"id": "COV", "statement": "Every input id appears in the output", "type": "deterministic", "severity": "critical"},
    {"id": "VAL", "statement": "Amount values match per id", "type": "deterministic", "severity": "error"},
    {"id": "CNT", "statement": "Output has the same number of rows as input", "type": "deterministic", "severity": "warning"},
]})


def _normalize(out_csv):
    base = tempfile.mkdtemp(prefix="gc_")
    work = tempfile.mkdtemp(prefix="gcw_")
    os.makedirs(base + "/Inputs")
    os.makedirs(base + "/Outputs")
    open(base + "/Inputs/source.csv", "w").write("id,amount\n1,100\n2,200\n3,300\n")
    open(base + "/Outputs/result.csv", "w").write(out_csv)
    open(base + "/Workflow.txt", "w").write("1. copy rows\n")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            m = Section2Ingestion("t", "/", work, file_source=LocalDirSource(base)).ingest()
            return Section3Normalization(m, task_id="tds_26q").normalize()
    finally:
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


def test_all_pass_when_output_correct():
    r = run_generic_checks(SPEC, _normalize("id,amount\n1,100\n2,200\n3,300\n"))
    assert r["COV"]["status"] == "PASS"
    assert r["VAL"]["status"] == "PASS"
    assert r["CNT"]["status"] == "PASS"


def test_value_mismatch_detected():
    r = run_generic_checks(SPEC, _normalize("id,amount\n1,100\n2,200\n3,999\n"))
    assert r["COV"]["status"] == "PASS"
    assert r["VAL"]["status"] == "FAIL"
    assert r["CNT"]["status"] == "PASS"


def test_missing_row_detected():
    r = run_generic_checks(SPEC, _normalize("id,amount\n1,100\n2,200\n"))
    assert r["COV"]["status"] == "FAIL"
    assert r["CNT"]["status"] == "FAIL"


# ---- prose / document checks ----

PROSE_SPEC = CheckSpec.from_ai_dict({"criteria": [
    {"id": "P1", "statement": 'Output must include an "Executive Summary" section', "type": "deterministic", "severity": "error"},
    {"id": "P2", "statement": 'The report must contain a "Conclusion"', "type": "deterministic", "severity": "warning"},
    {"id": "P3", "statement": "Output must not be empty", "type": "deterministic", "severity": "critical"},
]})


def _normalize_prose(out_text):
    base = tempfile.mkdtemp(prefix="pr_")
    work = tempfile.mkdtemp(prefix="prw_")
    os.makedirs(base + "/Inputs")
    os.makedirs(base + "/Outputs")
    open(base + "/Inputs/brief.txt", "w").write("Write a report with an Executive Summary and a Conclusion.")
    open(base + "/Outputs/report.txt", "w").write(out_text)
    open(base + "/Workflow.txt", "w").write("1. write report\n")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            m = Section2Ingestion("t", "/", work, file_source=LocalDirSource(base)).ingest()
            return Section3Normalization(m, task_id="tds_26q").normalize()
    finally:
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


def test_required_phrases_present():
    r = run_generic_checks(PROSE_SPEC, _normalize_prose("Executive Summary: ok.\nConclusion: done."))
    assert r["P1"]["status"] == "PASS"
    assert r["P2"]["status"] == "PASS"
    assert r["P3"]["status"] == "PASS"


def test_required_phrases_missing():
    r = run_generic_checks(PROSE_SPEC, _normalize_prose("Some text without the required sections."))
    assert r["P1"]["status"] == "FAIL"
    assert r["P2"]["status"] == "FAIL"
    assert r["P3"]["status"] == "PASS"


def test_quoted_phrase_extraction_ignores_apostrophes():
    # The apostrophe in "class's" must NOT open a bogus span; only real quoted labels.
    text = "Each class's student list (e.g. 'Opening Students') and a \"Summary\" tab"
    phrases = _quoted_phrases(text)
    assert "Opening Students" in phrases
    assert "Summary" in phrases
    assert not any(p.startswith("s student list") for p in phrases)


def test_phrase_presence_skipped_for_tabular_output():
    # A spreadsheet output: phrase-presence is unreliable, so a "must contain" phrase
    # criterion is deferred to AI (no deterministic verdict), not falsely failed/passed.
    in_t = {"name": "A", "headers": ["regNo", "amount"], "rows": [["1", "10"]]}
    out_t = {"name": "B", "headers": ["regNo", "amount"], "rows": [["1", "10"]]}
    spec = CheckSpec.from_ai_dict({"criteria": [
        {"id": "PH", "statement": "The output must contain a 'Reconciliation Summary' section",
         "type": "deterministic", "severity": "error"}]})
    r = run_generic_checks(spec, _nd(in_t, out_t))
    assert "PH" not in r   # deferred to AI for a tabular output


# ---- overlap gate: unrelated tables sharing a column name must NOT FAIL ----

def _nd(in_table, out_table):
    return {
        "normalized_inputs": [{"file": "in.xlsx", "document_type": "SPREADSHEET", "tables": [in_table]}],
        "normalized_outputs": [{"file": "out.xlsx", "document_type": "SPREADSHEET", "tables": [out_table]}],
    }


def test_unrelated_tables_sharing_column_name_do_not_fail():
    # Two tables both have a "code" column but DISJOINT key sets — they are not a
    # reconciliation pair. The engine must not fabricate a coverage/value FAIL.
    in_t = {"name": "A", "headers": ["code", "name"],
            "rows": [["1081", "Kavita"], ["1123", "Raj"], ["1125", "Harbans"], ["1126", "Sita"]]}
    out_t = {"name": "B", "headers": ["code", "name"],
             "rows": [["9001", "Foo"], ["9002", "Bar"], ["9003", "Baz"], ["9004", "Qux"]]}
    r = run_generic_checks(SPEC, _nd(in_t, out_t))
    # Coverage/value left UNDECIDED (handed to AI), never a deterministic FAIL.
    assert r.get("COV", {}).get("status") != "FAIL"
    assert r.get("VAL", {}).get("status") != "FAIL"


def test_serial_number_column_is_not_used_as_key():
    # Both tables have an S.No 1..N counter that overlaps by coincidence, plus a real
    # but DIFFERENT roster per side. The serial must be rejected as a key, so no FAIL.
    in_t = {"name": "ClassA", "headers": ["S.No", "reg_no", "name"],
            "rows": [["1", "1081", "A"], ["2", "1123", "B"], ["3", "1125", "C"],
                     ["4", "1126", "D"], ["5", "1138", "E"], ["6", "1144", "F"]]}
    out_t = {"name": "Summary", "headers": ["S.No", "class", "closing"],
             "rows": [["1", "Nursery", "30"], ["2", "LKG", "28"], ["3", "UKG", "31"],
                      ["4", "I", "40"], ["5", "II", "38"], ["6", "III", "35"]]}
    r = run_generic_checks(SPEC, _nd(in_t, out_t))
    assert r.get("COV", {}).get("status") != "FAIL"
    assert r.get("VAL", {}).get("status") != "FAIL"


def test_derived_logic_criteria_defer_to_ai():
    # A real reconcilable pair exists (so a fact IS computed), but criteria about the
    # output's DERIVED logic (exception-report selection, remarks, differences) must
    # NOT receive that fact — they go to the AI instead of a bogus deterministic FAIL.
    in_t = {"name": "A", "headers": ["regNo", "amount"],
            "rows": [["1081", "100"], ["1123", "200"], ["1125", "300"],
                     ["1126", "400"], ["1138", "500"], ["1144", "600"]]}
    out_t = {"name": "B", "headers": ["regNo", "amount"],
             "rows": [["1081", "100"], ["1123", "200"], ["1125", "300"]]}
    spec = CheckSpec.from_ai_dict({"criteria": [
        {"id": "EXC", "statement": "The Exception Report must only include classes with mismatches",
         "type": "deterministic", "severity": "critical"},
        {"id": "REM", "statement": "The Remarks column must indicate Matched or Mismatched",
         "type": "deterministic", "severity": "critical"},
        {"id": "DIFF", "statement": "Each Difference column equals SchoolPad minus Manual",
         "type": "deterministic", "severity": "error"},
    ]})
    r = run_generic_checks(spec, _nd(in_t, out_t))
    assert "EXC" not in r   # deferred to AI, not a deterministic verdict
    assert "REM" not in r
    assert "DIFF" not in r


def test_genuinely_related_pair_still_flags_missing_key():
    # High overlap (3/4 keys present) — a real pair; the one missing key is a real FAIL.
    in_t = {"name": "A", "headers": ["id", "amount"],
            "rows": [["1", "100"], ["2", "200"], ["3", "300"], ["4", "400"]]}
    out_t = {"name": "B", "headers": ["id", "amount"],
             "rows": [["1", "100"], ["2", "200"], ["3", "300"]]}
    r = run_generic_checks(SPEC, _nd(in_t, out_t))
    assert r["COV"]["status"] == "FAIL"
