"""The synthetic ABC COMPANY managerial-remuneration set (samples/make_abc_tp_sample.py): clean set is clean, seeded defects are all found."""
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

from auditsignoff.cli import review_tp

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def abc(tmp_path_factory):
    d = tmp_path_factory.mktemp("abc")
    subprocess.run([sys.executable, str(ROOT / "samples" / "make_abc_tp_sample.py"), str(d)], check=True)
    return d


def _run(d, errors, tmp):
    sfx = "_ERRORS" if errors else ""
    res, _ = review_tp(d / "engagement_abc.yaml", d / f"ABC_COMPANY_FY2024_TP_Report{sfx}.docx", d / f"ABC_COMPANY_FY2024_TP_Benchmark_Workbook{sfx}.xlsx",
                       tmp, d / "ABC_FS_Notes.docx", None, birf_path=d / "ABC_BIRF.xlsx")
    return {r.check_id: r for r in res}


def test_workbook_range_ties_to_the_report_figures(abc):
    wb = openpyxl.load_workbook(abc / "ABC_COMPANY_FY2024_TP_Benchmark_Workbook.xlsx", data_only=True)
    s = {r[0]: r[1] for r in wb["Summary"].iter_rows(min_row=4, max_row=9, values_only=True)}
    assert (s["Lower quartile (25%)"], s["Median"], s["Upper quartile (75%)"]) == (1103333, 1525809, 2775669)
    assert s["Number of comparables"] == 27 and s["Lowest value"] == 207793 and s["Highest value"] == 11887150


def test_clean_set_has_only_the_one_judgement_exception(abc, tmp_path):
    r = _run(abc, False, tmp_path)
    exc = {k: [f.title for f in v.findings if f.severity != "Info"] for k, v in r.items() if v.status == "EXC"}
    assert set(exc) == {"TP-11"}, exc                      # shareholder is a company, KMPs are individuals: a genuine review point
    for k in ("TP-14", "TP-16", "TP-34", "TP-45", "TP-46", "TP-47", "TP-49"):
        assert r[k].status in ("PASS", "REVIEW"), (k, r[k].status, r[k].note)


def test_seeded_defects_are_all_found(abc, tmp_path):
    r = _run(abc, True, tmp_path)
    want = {"TP-03": "Cover years", "TP-14": "Remuneration in the report", "TP-16": "BIRF", "TP-33": "Duplicate", "TP-34": "error values",
            "TP-45": "differs", "TP-46": "Q3", "TP-73": "placeholder", "TP-74": "Doubled"}
    for k, word in want.items():
        assert r[k].status == "EXC", (k, r[k].status)
        assert any(word.lower() in (f.title + f.detail).lower() for f in r[k].findings), (k, [f.title for f in r[k].findings])
    assert any("hidden" in f.title.lower() for f in r["TP-34"].findings)
