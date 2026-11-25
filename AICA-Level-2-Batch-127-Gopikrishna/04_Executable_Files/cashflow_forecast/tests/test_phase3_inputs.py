import csv
import importlib.util
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest
from rapidfuzz import fuzz, process, utils

from app.importers.specs import SPECS, normalise_header
from app.models import SourceType

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tpl = _load("make_templates")
syn = _load("make_synthetic")


# ---------------------------------------------------------------- specs
def test_every_spec_is_a_known_source_type():
    assert set(SPECS) <= {s.value for s in SourceType}


@pytest.mark.parametrize("st", list(SPECS))
def test_spec_keys_exist_and_headers_are_unambiguous(st):
    s = SPECS[st]
    keys = [c.key for c in s.columns]
    assert len(keys) == len(set(keys))
    assert all(k in keys for k in s.key_columns)
    seen = {}
    for c in s.columns:
        for h in (c.label, *c.aliases):
            n = normalise_header(h)
            assert seen.setdefault(n, c.key) == c.key, f"{st}: header '{h}' maps to two columns"


def test_normalise_header():
    assert normalise_header("  Outstanding Amt. (OMR) ") == "outstanding amt omr"
    assert normalise_header("Chq_Date") == "chq date"


# ---------------------------------------------------------------- templates
@pytest.mark.parametrize("st", list(SPECS))
def test_template_built_from_spec(tmp_path, st):
    path = tpl.build(SPECS[st], tmp_path)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames[:2] == ["Data", "Example"] and "Instructions" in wb.sheetnames
    ws = wb["Data"]
    assert [c.value for c in ws[1]] == [c.label for c in SPECS[st].columns]
    assert ws.max_row == 1  # header only: nothing to import by accident


@pytest.mark.parametrize("st", list(SPECS))
def test_committed_templates_match_specs(st):
    path = ROOT / "input_templates" / SPECS[st].template_file
    assert path.exists(), "run python scripts/make_templates.py"
    ws = openpyxl.load_workbook(path)["Data"]
    assert [c.value for c in ws[1]] == [c.label for c in SPECS[st].columns]


# ---------------------------------------------------------------- synthetic data
def test_synthetic_is_deterministic_and_obviously_fake():
    a = syn.build_day1(syn.date(2026, 11, 24), 3, 26)
    b = syn.build_day1(syn.date(2026, 11, 24), 3, 26)
    assert a == b
    parties = {r[1] for r in a.receivables} | {r[1] for r in a.pdcs} | {r[0] for r in a.plan}
    assert all("(synthetic)" in p for p in parties)


def test_planted_cases_present():
    d1 = syn.build_day1(syn.date(2026, 11, 24), 3, 26)
    keys = [(p[0], p[2]) for p in d1.pdcs]
    assert len(keys) - len(set(keys)) == 1                      # one duplicate PDC
    overlap = next(p for p in d1.plan if p[1] == "PINV-OVERLAP-1")
    assert any(p[1] == overlap[0] and p[4] == overlap[3] for p in d1.pdcs)
    financed = next(b[5] for b in d1.bank if b[0] == "DISC-7781")
    assert financed in {r[0] for r in d1.receivables}           # bill-discounted invoice
    assert any(r[3] < d1.as_of for r in d1.receivables)         # overdue items
    assert sum(1 for r in d1.receivables if r[5] == "Y") == 3   # risk flags


def test_unknown_header_gets_alias_suggestion():
    choices = {}
    for name, *_rest, aliases in syn.CATEGORIES:
        choices[name] = name
        for a in aliases.split(";"):
            choices[a.strip()] = name
    best, score, _ = process.extractOne("Visa Renewal Fees", list(choices), scorer=fuzz.WRatio,
                                        processor=utils.default_process)
    assert choices[best] == "Visa & labour fees" and score >= 80
    _, low, _ = process.extractOne("Marketing campaign", list(choices), scorer=fuzz.WRatio,
                                   processor=utils.default_process)
    # below the auto-accept level -> the user decides (map or add new). Phase 4 tunes the scorer:
    # plain WRatio over-scores very short aliases such as 'Rent' (67.5 here).
    assert low < 80


def test_day2_keeps_keys_stable():
    d1 = syn.build_day1(syn.date(2026, 11, 24), 3, 26)
    d2 = syn.build_day2(d1, 26)
    k1 = {(p[0], p[2]) for p in d1.pdcs}
    new = {(p[0], p[2]) for p in d2.pdcs} - k1
    assert new == {("PV-26-3501", "309001"), ("PV-26-3502", "309002")}
    assert all(p[3] >= d2.as_of for p in d2.pdcs)               # cleared cheques gone


def test_acceptance_fixture_totals_agree_with_independent_recount():
    folder = ROOT / "synthetic_data" / "acceptance"
    ws = openpyxl.load_workbook(folder / "pdc_month_2026_12.xlsx")["Data"]
    rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
    assert len(rows) == 70
    recount = {1: Decimal(0), 2: Decimal(0), 3: Decimal(0)}
    for r in rows:
        day = r[3].day
        lot = 1 if day <= 10 else 2 if day <= 20 else 3
        recount[lot] += Decimal(repr(r[4])).quantize(Decimal("0.001"))
    with (folder / "pdc_month_2026_12_expected.csv").open(encoding="utf-8") as fh:
        expected = {int(r["lot"]): Decimal(r["total"]) for r in csv.DictReader(fh)}
    assert recount == expected
    days = {r[3].day for r in rows}
    assert {1, 10, 11, 20, 21, 31} <= days                      # lot boundaries covered
