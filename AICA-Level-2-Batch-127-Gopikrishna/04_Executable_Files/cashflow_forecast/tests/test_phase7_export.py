"""Phase 7: Excel export with live formulas, checked by LibreOffice recalculation.

Tests marked ``needs_lo`` run only where LibreOffice is installed; the others always run.
"""
import re
from decimal import Decimal

import pytest
from openpyxl import load_workbook
from sqlalchemy import select

from app.db import session_scope
from app.engine.loader import run_forecast
from app.export import recalc
from app.export.workbook import build_workbook
from app.models import AuditLog, ExportLog
from tests.test_phase6_web import app_client, csrf_of, loaded, login, token  # noqa: F401  (fixtures)

needs_lo = pytest.mark.skipif(recalc.find_soffice() is None, reason="LibreOffice is not installed")


def _export(c):
    r = c.post("/export", data={"csrf_token": token(c)}, follow_redirects=False)
    assert r.status_code == 303
    return r.headers["location"], c.get(r.headers["location"]).text


# ------------------------------------------------------------------ always
def test_workbook_is_formulas_over_data_sheets(loaded, tmp_path):
    with session_scope() as db:
        fc = run_forecast(db)
    expected = build_workbook(fc, tmp_path / "x.xlsx", cached=False)
    wb = load_workbook(tmp_path / "x.xlsx")
    assert wb.sheetnames == ["Forecast", "Items", "Holds", "Bank", "About"]
    ws = wb["Forecast"]
    formulas = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")]
    assert sum("SUMIFS(Items!" in f for f in formulas) > 20 and any("SUMIFS(Holds!" in f for f in formulas)
    assert any(f.startswith("=Bank!") for f in formulas)
    assert len(formulas) == sum(1 for k in expected if k[0] == "Forecast")       # every formula is checked
    labels = [ws.cell(row=5, column=c).value for c in range(3, ws.max_column + 1)]
    assert "01-10 Dec" in labels and "Horizon total" in labels
    n_items = sum(1 for _ in wb["Items"].iter_rows(min_row=2))
    assert n_items == len(fc.items)
    # the app's own figures are what the check compares against
    fp_row = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value ==
                  "NET FUNDING POSITION AFTER HOLDS")
    assert expected[("Forecast", f"C{fp_row}")] == fc.lines["fp_after"][0]


def test_export_blocked_without_libreoffice(loaded, monkeypatch):
    c = loaded
    monkeypatch.setattr("app.services.export_service.find_soffice", lambda _=None: None)
    loc, page = _export(c)
    assert "Export blocked" in page and "LibreOffice is not installed" in page
    assert "Download Excel" not in page
    r = c.get(loc + "/download")
    assert r.status_code == 403 and "blocked" in r.text
    with session_scope() as db:
        log = db.scalars(select(ExportLog)).one()
        assert not log.released and log.check_status.value == "not_run"
        assert db.scalar(select(AuditLog).where(AuditLog.action == "export.create")).after["released"] is False
    assert "blocked: not checked" in c.get("/exports").text


def test_compare_reports_differences(tmp_path):
    import xlsxwriter
    p = tmp_path / "v.xlsx"
    wb = xlsxwriter.Workbook(str(p))
    ws = wb.add_worksheet("Forecast")
    ws.write("A3", "Opening")
    ws.write("C5", "01-10 Dec")
    ws.write_formula("C3", "=1+1", None, 2)
    ws.write_formula("D3", '="No gap"', None, "No gap")
    wb.close()
    exp = {("Forecast", "C3"): Decimal("2.0004"), ("Forecast", "D3"): "No gap"}
    assert recalc.compare(p, exp) == []                                 # within 0.0005
    exp[("Forecast", "C3")] = Decimal("2.001")
    d = recalc.compare(p, exp)
    assert len(d) == 1 and d[0]["cell"] == "C3" and d[0]["item"] == "Opening / 01-10 Dec"


# ------------------------------------------------------------------ with LibreOffice
@needs_lo
def test_export_recalculates_to_screen_figures_and_downloads(loaded):
    c = loaded
    loc, page = _export(c)
    assert "Formula check passed" in page, page[page.find("alert"):][:600]
    r = c.get(loc + "/download")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    assert "attachment" in r.headers["content-disposition"]
    with session_scope() as db:
        log = db.scalars(select(ExportLog)).one()
        assert log.released and log.check_status.value == "passed" and len(log.sha256) == 64
        assert db.scalar(select(AuditLog).where(AuditLog.action == "export.download")) is not None


@needs_lo
def test_hold_then_export_still_matches(loaded):
    """Acceptance: holding a PDC changes the workbook exactly as the screen, and the check still passes."""
    c = loaded
    page = c.get("/pdcs?lot=1").text
    key = re.search(r'name="key" value="([^"]+)"', page).group(1)
    r = c.post("/items/action", data={"source": "vendor_pdc", "key": key, "action": "hold", "mode": "pdc",
                                      "new_date": "2027-01-25", "reason": "Await delivery note"},
               headers={"X-CSRF-Token": csrf_of(page), "HX-Request": "true"})
    assert "On hold" in r.text
    loc, page = _export(c)
    assert "Formula check passed" in page
    with session_scope() as db:
        fc = run_forecast(db)
    import io
    wb = load_workbook(io.BytesIO(c.get(loc + "/download").content), data_only=True)
    hs = wb["Holds"]
    assert hs["B2"].value == key and hs["L2"].value >= 1


@needs_lo
def test_any_difference_blocks_the_export(loaded):
    from app.services.export_service import create_export

    def tamper(expected):
        k = next(k for k, v in expected.items() if k[0] == "Forecast" and not isinstance(v, str) and v)
        expected[k] = expected[k] + Decimal("0.001")
    with session_scope() as db:
        log = create_export(db, run_forecast(db), None, tamper=tamper)
        assert log.check_status.value == "failed" and not log.released
        assert len(log.differences) == 1 and "BLOCKED" in log.note
        log_id = log.id
    assert loaded.get(f"/exports/{log_id}/download").status_code == 403
