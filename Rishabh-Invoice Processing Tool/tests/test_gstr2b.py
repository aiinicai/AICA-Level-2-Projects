from datetime import date
from decimal import Decimal as D

import pytest

from ipt.services.recon.gstr2b_parser import Gstr2bFormatError, parse_file
from tests.gstr2b_samples import make_2b_excel, make_2b_json
from tests.pdfgen import gst

S1 = gst("08AAACS1111A1Z")
S2 = gst("27AAACT2222B1Z")

B2B = [(S1, "Shree Traders", "ST/26-27/101", "05-10-2026", 10500, "08-Rajasthan", "No", 10000, 0, 250, 250, 0, "Yes"),
       (S2, "Tata Minerals", "TM-55", "12-10-2026", 11800, "08-Rajasthan", "No", 10000, 1800, 0, 0, 0, "No")]


def test_parse_portal_excel(tmp_path):
    p = make_2b_excel(tmp_path / "2b.xlsx", B2B,
                      cdnr=[(S1, "Shree Traders", "CN-7", "Credit Note", "20-10-2026", 525, 500, 0, 12.5, 12.5, "Yes")],
                      b2ba=[("ST/26-27/090", "28-09-2026", S1, "Shree Traders", "ST/26-27/090A", "28-09-2026", 2100,
                             2000, 0, 50, 50, "Yes")])
    r = parse_file(p)
    assert r.period == "2026-10" and r.source_format == "excel"
    assert r.counts() == {"B2B": 2, "B2BA": 1, "CDNR": 1}
    inv = next(x for x in r.records if x["doc_no"] == "ST/26-27/101")
    assert inv["supplier_gstin"] == S1 and inv["doc_date"] == date(2026, 10, 5) and inv["pos"] == "08"
    assert (inv["taxable_value"], inv["cgst"], inv["sgst"], inv["igst"]) == (D("10000.00"), D("250.00"),
                                                                            D("250.00"), D("0.00"))
    assert inv["itc_available"] == "Yes" and inv["doc_no_normalized"] == "ST101"
    cn = next(x for x in r.records if x["section"] == "CDNR")
    assert cn["doc_type"] == "CRN" and cn["taxable_value"] == D("500.00")
    am = next(x for x in r.records if x["section"] == "B2BA")
    assert am["original_doc_no"] == "ST/26-27/090" and am["doc_no"] == "ST/26-27/090A"
    assert any("Read me" in s for s in r.skipped)


@pytest.mark.parametrize("with_items", [True, False])
def test_parse_json_both_layouts(tmp_path, with_items):
    p = make_2b_json(tmp_path / "2b.json", B2B, with_items=with_items)
    r = parse_file(p)
    assert r.period == "2026-10" and r.counts() == {"B2B": 2}
    tm = next(x for x in r.records if x["doc_no"] == "TM-55")
    assert tm["igst"] == D("1800.00") and tm["itc_available"] == "No" and tm["supplier_name"] == "Tata Minerals"
    assert any("ecom" in s for s in r.skipped)


def test_not_a_2b_file(tmp_path):
    bad = tmp_path / "x.json"
    bad.write_text('{"hello": 1}')
    with pytest.raises(Gstr2bFormatError):
        parse_file(bad)
    with pytest.raises(Gstr2bFormatError):
        parse_file(tmp_path / "x.pdf")


def test_invoice_number_normalisation_fy_rules():
    from ipt.core.textnorm import normalize_invoice_no as n
    assert n("INV/001") == n("INV-001") == n("inv 0001") == "INV1"
    assert n("ST/26-27/101") == "ST101" and n("SM/2026-27/260") == "SM260" and n("229/2026-27") == "229"
    assert n("INV/1045") == "INV1045"            # 1045 is not a financial year
    assert n("26-27/640") == "640" and n("2627189") == "2627189"
