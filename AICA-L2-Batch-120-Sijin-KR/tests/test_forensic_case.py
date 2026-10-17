"""The ZENITH TRADING FZCO case: every seeded fraud scenario must be found, and the clean twin must raise nothing."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "samples"))
from make_forensic_case import HOLIDAYS, build            # noqa: E402
from auditsignoff.models import load_params               # noqa: E402
from auditsignoff.rules_fa import run_fa                  # noqa: E402

P = load_params()


def _run(d, **over):
    kw = dict(period_end="2025-12-31", scope_years=[2025], vendors=d / "vendors.xlsx", employees=d / "employees.xlsx", related=["Faisal Nazir", "Nazir Consultancy"],
              bank=d / "bank_statement.xlsx", mandate=d / "mandate.xlsx", signatures=d / "signatures", fs_data=d / "fs_data.xlsx", stock=d / "stock_register.xlsx", holidays=HOLIDAYS)
    kw.update(over)
    res, _ = run_fa(P, d / "gl.xlsx", kw.pop("period_end"), kw.pop("scope_years"), kw.pop("vendors"), kw.pop("employees"), kw.pop("related"), **kw)
    return {r.check_id: r for r in res}


def _text(r):
    return " | ".join(f"{f.title} {f.detail}" for f in r.findings)


@pytest.fixture(scope="module")
def fraud(tmp_path_factory):
    return build(tmp_path_factory.mktemp("fraud"), fraud=True)


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    return build(tmp_path_factory.mktemp("clean"), fraud=False)


def test_clean_twin_raises_no_exception(clean):
    r = _run(clean)
    assert {k: [f.title for f in v.findings] for k, v in r.items() if v.status == "EXC"} == {}
    assert {"FA-05", "FA-06", "FA-11", "FA-12", "FA-13", "FA-14"} <= {k for k, v in r.items() if v.status == "PASS"}


def test_holiday_weekend_night_round_and_splitting(fraud):
    t = _text(_run(fraud)["FA-05"])
    for k in ("weekends / public holidays", "created at night", "round-thousand", "backdated", "prepared and approved"):
        assert k in t, k


def test_holiday_input_matters(fraud):
    with_h = _text(_run(fraud)["FA-05"]); without = _text(_run(fraud, holidays=None)["FA-05"])
    n = lambda s: int(s.split("weekends / public holidays")[1].split(" lines")[0].strip(" |"))
    assert n(with_h) > n(without), (n(with_h), n(without))


def test_ghost_vendor_is_the_employee(fraud):
    t = _text(_run(fraud)["FA-06"])
    assert "same bank account" in t and "Faisal Nazir" in t and "Nazir Consultancy Services" in t


def test_signature_forgery_paste_expiry_limit_and_outsider(fraud):
    t = _text(_run(fraud)["FA-11"])
    assert "does not resemble the specimen" in t and "CHQ-10455" in t                 # forged
    assert "Identical signature image" in t and "CHQ-10340" in t                      # pasted
    assert "had ended on the document date" in t and "CHQ-10402" in t                 # authority ended
    assert "single-signature limit" in t and "CHQ-10417" in t                         # over limit
    assert "not an authorised signatory" in t and "Faisal Nazir" in t                 # not on the mandate


def test_genuine_signatures_are_not_called_forged(fraud):
    t = _text(_run(fraud)["FA-11"])
    forged = [x for x in t.split(" | ") if "does not resemble" in x]
    assert len(forged) == 1 and "CHQ-10455" in forged[0], forged


def test_bank_diversion_paths(fraud):
    t = _text(_run(fraud)["FA-12"])
    for k in ("not the one in the vendor master", "Account swept", "Pass-through", "no matching credit to the bank account in the GL",
              "employee's bank account", "person of interest", "cash or bearer"):
        assert k in t, k
    assert "Gulf Horizon Trading" in t and "Alpha Supplies LLC" in t


def test_fs_over_and_understatement_indicators(fraud):
    t = _text(_run(fraud)["FA-13"])
    for k in ("Receivables grew much faster", "Gross margin moved", "not backed by operating cash flow", "Inventory days rose", "Payable days fell", "Operating expenses fell",
              "Beneish", "does not agree to the general ledger", "reversed after year-end", "does not agree to the stock register"):
        assert k in t, k


def test_inventory_diversion_and_unrecorded(fraud):
    t = _text(_run(fraud)["FA-14"])
    for k in ("roll-forward does not agree", "short of book stock", "exceeds book stock", "Negative book stock", "dispatched but not invoiced", "invoice not booked",
              "never received", "negative stock adjustments", "unusual locations"):
        assert k in t, k


def test_missing_inputs_are_not_run_never_pass(fraud):
    r = _run(fraud, bank=None, mandate=None, signatures=None, fs_data=None, stock=None)
    assert {r[k].status for k in ("FA-11", "FA-12", "FA-13", "FA-14")} == {"NOTRUN"}


def test_cli_end_to_end_and_audit_trail(fraud, tmp_path):
    from auditsignoff.cli import main
    d = fraud
    assert main(["fa", "--case", "ZENITH TRADING FZCO", "--gl", str(d / "gl.xlsx"), "--period-end", "2025-12-31", "--years", "2025", "--vendors", str(d / "vendors.xlsx"),
                 "--employees", str(d / "employees.xlsx"), "--bank", str(d / "bank_statement.xlsx"), "--mandate", str(d / "mandate.xlsx"), "--signatures", str(d / "signatures"),
                 "--fs-data", str(d / "fs_data.xlsx"), "--stock", str(d / "stock_register.xlsx"), "--holidays", *HOLIDAYS, "--related", "Faisal Nazir", "--out", str(tmp_path)]) == 0
    j = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    hashed = " ".join(j["inputs_sha256"])
    assert "bank_statement.xlsx" in hashed and "stock_register.xlsx" in hashed and "fs_data.xlsx" in hashed


def _flat_signatures(fraud, tmp_path, rename_register=None, upper_ext=False, as_pdf=()):
    """Signatures supplied the way the app saves uploads: everything flat in one folder."""
    import shutil
    from PIL import Image
    sig = tmp_path / "sig"
    sig.mkdir()
    for f in (fraud / "signatures").glob("*"):
        name = f.name
        if rename_register and "regist" in name.lower():
            name = rename_register
        if upper_ext and f.suffix.lower() == ".png":
            name = f.stem + ".PNG"
        shutil.copy(f, sig / name)
    for n in as_pdf:                      # scan saved as PDF, referenced by the same stem
        Image.open(fraud / "signatures" / n).convert("RGB").save(sig / (Path(n).stem + ".pdf"), "PDF", resolution=150)
    return sig


def test_uploaded_signature_set_matches_folder_result(fraud, tmp_path):
    base = _text(_run(fraud)["FA-11"])
    assert _text(_run(fraud, signatures=_flat_signatures(fraud, tmp_path))["FA-11"]) == base


def test_single_spreadsheet_is_taken_as_register_and_extension_case_ignored(fraud, tmp_path):
    sig = _flat_signatures(fraud, tmp_path, rename_register="my_cheques.xlsx", upper_ext=True)
    t = _text(_run(fraud, signatures=sig)["FA-11"])
    assert "CHQ-10455" in t and "Identical signature image" in t


def test_pdf_scan_of_signature_is_readable():
    import tempfile
    from PIL import Image, ImageDraw
    from auditsignoff.rules_fa2 import _ink
    d = Path(tempfile.mkdtemp())
    im = Image.new("RGB", (300, 120), "white")
    ImageDraw.Draw(im).line([(10, 90), (80, 20), (150, 100), (290, 40)], fill="black", width=4)
    im.save(d / "s.pdf", "PDF", resolution=100)
    im.save(d / "s.png")
    from auditsignoff.rules_fa2 import _corr
    assert _corr(_ink(d / "s.pdf"), _ink(d / "s.png")) > 0.9


def test_no_register_in_folder_is_not_run_not_pass(fraud, tmp_path):
    (tmp_path / "x.png").write_bytes((fraud / "signatures" / next(p.name for p in (fraud / "signatures").glob("*.png"))).read_bytes())
    assert _run(fraud, signatures=tmp_path)["FA-11"].status == "NOTRUN"
