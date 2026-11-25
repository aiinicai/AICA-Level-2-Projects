"""Acceptance tests from the specification, run end to end through the web app (and Excel where possible).

1. About 70 PDCs reproduce the hand-worked lot totals.
2. Holding a PDC raises its lot and every later lot by exactly its amount.
3. Deferring moves the amount with no loss.
4. A re-upload keeps all overrides.
5. The exported workbook recalculates to the same figures as the screen.   (needs LibreOffice)
6. A new category header appears in the report after mapping.
"""
import csv
import io
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.db import session_scope
from app.engine.loader import run_forecast
from app.export.recalc import find_soffice
from app.web.templating import money
from tests.test_phase6_web import (DAY1, ROOT, app_client, csrf_of, loaded, login, token,  # noqa: F401
                                   upload)

ACC = ROOT / "synthetic_data" / "acceptance"
DAY2 = ROOT / "synthetic_data" / "day2_2026-11-25"
needs_lo = pytest.mark.skipif(find_soffice() is None, reason="LibreOffice is not installed")


def act(c, source, key, action, **data):
    page = c.get("/pdcs").text
    return c.post("/items/action", data={"source": source, "key": key, "action": action, "mode": "pdc", **data},
                  headers={"X-CSRF-Token": csrf_of(page), "HX-Request": "true"})


def fc_now(**kw):
    with session_scope() as db:
        return run_forecast(db, **kw)


def pdc_in_lot(fc, lot, skip=()):
    return next(i for i in fc.items if i.source == "vendor_pdc" and i.lot == lot and i.status == "active"
                and i.key not in skip)


def export_workbook(c):
    r = c.post("/export", data={"csrf_token": token(c)}, follow_redirects=True)
    assert "Formula check passed" in r.text, r.text[r.text.find("alert"):][:500]
    link = re.search(r'href="(/exports/\d+/download)"', r.text).group(1)
    return load_workbook(io.BytesIO(c.get(link).content), data_only=True)


def row_values(ws, label, ncols):
    r = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value == label)
    return [Decimal(str(ws.cell(row=r, column=3 + j).value)).quantize(Decimal("0.001")) for j in range(ncols)]


# 1 ------------------------------------------------------------------------------------------------
def test_1_seventy_pdcs_reproduce_hand_worked_lot_totals(app_client):
    c = app_client
    login(c, "prep1")
    tok = token(c)
    for src, path in (("category_list", DAY1 / "category_list.xlsx"), ("vendor_pdc", ACC / "pdc_month_2026_12.xlsx")):
        assert "rejected" not in upload(c, src, path, tok).text.split("Upload #")[1][:300]
    expected = list(csv.DictReader((ACC / "pdc_month_2026_12_expected.csv").open()))
    grid = c.get("/forecast?as_of=2026-12-01&months=1").text               # the screen
    for e in expected:
        assert money(Decimal(e["total"])) in grid, e
    fc = fc_now(as_of=date(2026, 12, 1))
    assert sum(1 for i in fc.items if i.status == "active") == 70
    pdc = next(r for r in fc.outflow_rows if r.name == "Vendor PDCs")
    assert [str(v) for v in pdc.values[:3]] == [e["total"] for e in expected]
    assert [sum(1 for i in fc.items if i.lot == k) for k in range(3)] == [int(e["count"]) for e in expected]
    if find_soffice():                                                     # and the Excel export agrees
        ws = export_workbook(c)["Forecast"]
        assert [str(v) for v in row_values(ws, "Vendor PDCs", 3)] == [e["total"] for e in expected]


# 2 ------------------------------------------------------------------------------------------------
def test_2_hold_raises_its_lot_and_every_later_lot_by_exactly_its_amount(loaded):
    c = loaded
    before = fc_now()
    pdc = pdc_in_lot(before, 1)
    r = act(c, "vendor_pdc", pdc.key, "hold", open_ended="1", reason="Vendor dispute")
    assert "On hold" in r.text
    after = fc_now()
    for k in range(len(before.fc_lots)):
        diff = after.lines["fp_after"][k] - before.lines["fp_after"][k]
        assert diff == (pdc.eff_amount if k >= 1 else 0), (k, diff)
    assert after.lines["closing"] == before.lines["closing"]                # rows B-F stay as per ERP


# 3 ------------------------------------------------------------------------------------------------
def test_3_deferring_moves_the_amount_with_no_loss(loaded):
    c = loaded
    before = fc_now()
    pdc = pdc_in_lot(before, 0)
    target = next(k for k, lt in enumerate(before.fc_lots) if lt.start == date(2026, 12, 21))
    assert "Defer to lot saved" in act(c, "vendor_pdc", pdc.key, "defer", lot_start="2026-12-21").text
    after = fc_now()
    d = [a - b for a, b in zip(after.lines["outflows"], before.lines["outflows"])]
    assert d[0] == -pdc.eff_amount and d[target] == pdc.eff_amount
    assert sum(d) == 0 and after.lines["closing"][-1] == before.lines["closing"][-1]


# 4 ------------------------------------------------------------------------------------------------
def test_4_reupload_keeps_all_overrides(loaded):
    c = loaded
    fc = fc_now()
    held = pdc_in_lot(fc, 2)
    deferred = pdc_in_lot(fc, 3, skip={held.key})
    excluded = pdc_in_lot(fc, 4, skip={held.key, deferred.key})
    act(c, "vendor_pdc", held.key, "hold", new_date="2027-01-15", reason="Await delivery note")
    act(c, "vendor_pdc", deferred.key, "defer", lot_start="2027-01-11")
    act(c, "vendor_pdc", excluded.key, "exclude", reason="Duplicate cheque")
    r = upload(c, "vendor_pdc", DAY2 / "erp_pdc_register.xlsx", token(c))     # next day's ERP file
    assert "rejected" not in r.text.split("Upload #")[1][:300]
    after = {i.key: i for i in fc_now(as_of=date(2026, 11, 24)).items}
    assert after[held.key].hold is not None and after[held.key].hold.honour_date == date(2027, 1, 15)
    assert "deferred" in after[deferred.key].flags and after[deferred.key].eff_date >= date(2027, 1, 11)
    assert after[excluded.key].status == "excluded"


# 5 ------------------------------------------------------------------------------------------------
@needs_lo
def test_5_exported_workbook_recalculates_to_the_screen_figures(loaded):
    c = loaded
    act(c, "vendor_pdc", pdc_in_lot(fc_now(), 1).key, "hold", new_date="2027-01-15")
    grid = c.get("/forecast").text
    fc = fc_now()
    n = len([col for col in fc.columns if col.kind == "lot"]) + len([col for col in fc.columns if col.kind != "lot"])
    ws = export_workbook(c)["Forecast"]
    shown = row_values(ws, "NET FUNDING POSITION AFTER HOLDS", n)
    for v in shown:
        assert money(v, False) in grid                                     # every column is on the screen too


# 6 ------------------------------------------------------------------------------------------------
def test_6_new_category_header_appears_after_mapping(loaded):
    c = loaded
    r = upload(c, "other", DAY1 / "other_recurring_long.xlsx", token(c))
    assert "Marketing campaign" not in c.get("/forecast").text
    exc = c.get("/exceptions").text
    exc_id = re.search(r'action="/exceptions/(\d+)"[^>]*>(?:(?!</form>).)*Marketing campaign', exc, re.S)
    exc_id = exc_id.group(1) if exc_id else re.findall(r'action="/exceptions/(\d+)"', exc)[0]
    r = c.post(f"/exceptions/{exc_id}", data={"how": "new", "direction": "outflow", "group": "Overheads",
                                              "csrf_token": csrf_of(exc)}, follow_redirects=True)
    assert "Resolved" in r.text
    grid = c.get("/forecast").text
    assert "Marketing campaign" in grid
