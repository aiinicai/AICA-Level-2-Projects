from datetime import date

import pytest

from auditsignoff.cli import review_fs
from auditsignoff.loaders import parse_number, load_document
from auditsignoff.models import load_params, load_catalogue
from auditsignoff.rules_fs import fuzzy_hits, run_fs
from auditsignoff.loaders import load_docx
from auditsignoff.models import load_yaml


def _run(samples, tag, ext="docx", tb=True, tmp=None):
    res, _ = review_fs(samples / f"engagement_{tag}.yaml", samples / f"fs_{tag}.{ext}",
                       samples / f"tb_{tag}.xlsx" if tb else None, tmp)
    return {r.check_id: r for r in res}


def test_parse_number():
    assert parse_number("(1,234)") == -1234
    assert parse_number("1,234.50") == 1234.5
    assert parse_number("-") == 0
    assert parse_number("Total assets") is None


def test_fuzzy_name():
    hits = fuzzy_hits("The accounts of GOLDEN CREST TRADNG DMCC are", "GOLDEN CREST TRADING DMCC")
    assert hits and hits[0][0] == "GOLDEN CREST TRADNG DMCC"


def test_clean_pack_has_no_exceptions(samples, tmp_path):
    r = _run(samples, "clean", tmp=tmp_path)
    exc = {k: [f.title for f in v.findings] for k, v in r.items() if v.status == "EXC"}
    assert exc == {}, exc
    assert all(v.status in ("PASS", "NOTRUN", "REVIEW", "NA") for v in r.values())
    assert sum(1 for v in r.values() if v.status == "PASS") >= 20


# seeded error -> (check id, text that must appear in the finding title or detail)
SEEDED = {
    "name misspelt": ("SA-01", "TRADNG"),
    "wrong CY header (2024|2023)": ("SA-06", "Comparative column headers"),
    "period-end date 30 Dec": ("SA-06", "Period-end date"),
    "Arial font": ("SA-13", "Arial"),
    "9pt text": ("SA-14", "9 pt"),
    "left margin 1.0": ("SA-15", "left 1.00"),
    "unjustified narrative": ("SA-16", "not justified"),
    "SOFP does not balance": ("SA-20", "does not balance"),
    "cash flow cash != SOFP cash": ("SA-21", "closing cash"),
    "signatory spelling": ("SA-04", "Mohamed"),
    "one signatory for three shareholders, no BR": ("SA-05", "Board Resolution"),
    "report date missing": ("SA-07", "date missing"),
    "licence number missing": ("SA-08", "licence"),
    "report reference missing": ("SA-08", "reference"),
    "wrong authority DED": ("SA-09", "DED"),
    "addressee singular": ("SA-10", "Shareholder"),
    "end-of-service note missing": ("SA-29", "End of service"),
    "IFRS 18 missing": ("SA-30", "IFRS 18"),
    "TB does not balance": ("SA-24", "does not balance"),
    "FS profit != TB profit": ("SA-24", "Profit"),
    "manager review not done": ("SA-46", "manager"),
    "print check not done": ("SA-47", "not completed"),
}


def test_seeded_errors_recall(samples, tmp_path):
    r = _run(samples, "errors", tmp=tmp_path)
    missed = []
    for label, (cid, needle) in SEEDED.items():
        blob = " ".join(f"{f.title} {f.detail}" for f in r[cid].findings)
        if needle.lower() not in blob.lower():
            missed.append(label)
    assert not missed, f"missed: {missed}"
    print(f"\nrecall on seeded errors: {len(SEEDED) - len(missed)}/{len(SEEDED)}")


def test_missing_tb_is_not_run_not_pass(samples, tmp_path):
    r = _run(samples, "clean", tb=False, tmp=tmp_path)
    assert r["SA-24"].status == "NOTRUN"


def test_every_implemented_check_has_a_rule():
    from auditsignoff.rules_fs import REGISTRY as R1
    from auditsignoff.rules_fs2 import A2_REGISTRY, ASSIST2_REGISTRY
    REGISTRY = {**R1, **A2_REGISTRY, **ASSIST2_REGISTRY}
    from auditsignoff.rules_liq import run_liq
    impl = {c["id"] for c in load_catalogue() if c["impl"] and c["mod"] == "A"}
    # SA-50 is the memo generator itself
    assert impl - {"SA-50"} == set(REGISTRY), impl ^ set(REGISTRY)


def test_catalogue_integrity():
    cat = load_catalogue()
    ids = [c["id"] for c in cat]
    assert len(ids) == len(set(ids))
    assert {c["cls"] for c in cat} == {"A", "B", "C"}
    assert all(c["sev"] in ("High", "Medium", "Low") for c in cat)


def test_pdf_path(samples, tmp_path):
    import shutil, subprocess
    if not shutil.which("soffice"):
        pytest.skip("LibreOffice not available to make a PDF")
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(samples),
                    str(samples / "fs_errors.docx")], check=True, capture_output=True)
    r = _run(samples, "errors", ext="pdf", tmp=tmp_path)
    for cid in ("SA-01", "SA-04", "SA-06", "SA-07", "SA-08", "SA-09", "SA-20", "SA-21", "SA-24", "SA-29", "SA-30"):
        assert r[cid].status == "EXC", cid
    assert r["SA-16"].status == "NOTRUN"
