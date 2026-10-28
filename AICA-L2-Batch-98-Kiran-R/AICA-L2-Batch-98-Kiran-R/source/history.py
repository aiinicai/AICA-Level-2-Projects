"""History of audit-trail checks: one saved snapshot per company check, with its reports, exportable as Excel or PDF."""
from __future__ import annotations

import dataclasses
import io
import json
import pickle
import sqlite3
import zlib
from datetime import date, datetime
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY AUTOINCREMENT, saved_at TEXT, company TEXT, fy_start TEXT, fy_end TEXT,
  source TEXT, prepared_by TEXT, conclusion TEXT, vouchers INTEGER, log_events INTEGER, exceptions INTEGER, high INTEGER,
  tests_failed INTEGER, tests_total INTEGER, deleted INTEGER, altered INTEGER, notes TEXT, engagement TEXT);
CREATE INDEX IF NOT EXISTS ck_co ON checks(company, id);
CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT, check_id INTEGER, name TEXT, mime TEXT, data BLOB);
CREATE INDEX IF NOT EXISTS fl_ck ON files(check_id);
CREATE TABLE IF NOT EXISTS snap(check_id INTEGER PRIMARY KEY, data BLOB);
"""
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
COLS = ["id", "saved_at", "company", "fy_start", "fy_end", "source", "prepared_by", "conclusion", "vouchers", "log_events",
        "exceptions", "high", "tests_failed", "tests_total", "deleted", "altered", "notes"]
LABEL = {"id": "Ref", "saved_at": "Saved on", "company": "Company", "fy_start": "FY start", "fy_end": "FY end", "source": "Data source",
         "prepared_by": "Prepared by", "conclusion": "Suggested conclusion", "vouchers": "Vouchers", "log_events": "Log events",
         "exceptions": "Exceptions", "high": "High severity", "tests_failed": "Tests with exceptions", "tests_total": "Tests run",
         "deleted": "Deleted vouchers", "altered": "Alterations", "notes": "Notes"}


def pack(obj) -> bytes:
    return zlib.compress(pickle.dumps(obj, protocol=4), 6)


def unpack(b: bytes):
    return pickle.loads(zlib.decompress(b))


def eng_to_json(e) -> str:
    d = dataclasses.asdict(e)
    return json.dumps(d, default=lambda o: o.isoformat() if isinstance(o, (date, datetime)) else str(o))


def eng_from_json(txt: str, cls):
    d = json.loads(txt)
    names = {f.name: f for f in dataclasses.fields(cls)}
    kw = {k: v for k, v in d.items() if k in names}
    if "fy_end" in kw:
        kw["fy_end"] = date.fromisoformat(str(kw["fy_end"])[:10])
    return cls(**kw)


class History:
    def __init__(self, path: Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._c() as c:
            c.executescript(SCHEMA)

    def _c(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def save(self, meta: dict, files: list[tuple[str, str, bytes]], engagement: str = "", snapshot: dict | None = None) -> int:
        m = {k: meta.get(k, "") for k in COLS if k != "id"}
        m["saved_at"] = m["saved_at"] or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._c() as c:
            cur = c.execute(f"INSERT INTO checks({','.join(m)},engagement) VALUES({','.join('?' * len(m))},?)", [*m.values(), engagement])
            cid = cur.lastrowid
            c.executemany("INSERT INTO files(check_id,name,mime,data) VALUES(?,?,?,?)", [(cid, n, mt, b) for n, mt, b in files])
            if snapshot is not None:
                c.execute("INSERT OR REPLACE INTO snap(check_id,data) VALUES(?,?)", [cid, pack(snapshot)])
        return cid

    def snapshot(self, check_id: int) -> dict | None:
        """The data and settings the check was run on (this computer's own database, written by this app)."""
        with self._c() as c:
            r = c.execute("SELECT data FROM snap WHERE check_id=?", [check_id]).fetchone()
        try:
            return unpack(r[0]) if r else None
        except Exception:
            return None

    def has_snapshot(self, check_id: int) -> bool:
        with self._c() as c:
            return c.execute("SELECT 1 FROM snap WHERE check_id=?", [check_id]).fetchone() is not None

    def list(self, company: str | None = None) -> pd.DataFrame:
        with self._c() as c:
            q = f"SELECT {','.join(COLS)} FROM checks" + (" WHERE company=?" if company else "") + " ORDER BY id DESC"
            rows = c.execute(q, [company] if company else []).fetchall()
        df = pd.DataFrame([dict(r) for r in rows], columns=COLS)
        if len(df):                                   # change against the previous saved check of the same company
            df = df.sort_values("id")
            df["exceptions_vs_previous"] = df.groupby("company").exceptions.diff()
            df = df.sort_values("id", ascending=False)
        return df

    def companies(self) -> list[str]:
        with self._c() as c:
            return [r[0] for r in c.execute("SELECT DISTINCT company FROM checks ORDER BY company")]

    def files(self, check_id: int) -> list[dict]:
        with self._c() as c:
            return [dict(r) for r in c.execute("SELECT id,name,mime,data FROM files WHERE check_id=? ORDER BY id", [check_id])]

    def engagement(self, check_id: int) -> str:
        with self._c() as c:
            r = c.execute("SELECT engagement FROM checks WHERE id=?", [check_id]).fetchone()
        return r[0] if r else ""

    def delete(self, check_id: int):
        with self._c() as c:
            c.execute("DELETE FROM files WHERE check_id=?", [check_id])
            c.execute("DELETE FROM snap WHERE check_id=?", [check_id])
            c.execute("DELETE FROM checks WHERE id=?", [check_id])


def register_xlsx(df: pd.DataFrame) -> bytes:
    out = io.BytesIO()
    d = df.drop(columns=[c for c in df.columns if c not in LABEL and c != "exceptions_vs_previous"]).rename(
        columns={**LABEL, "exceptions_vs_previous": "Exceptions vs previous check"})
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        d.to_excel(xw, sheet_name="History", index=False)
        ws = xw.book["History"]
        ws.freeze_panes = "A2"
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(40, max(10, max(len(str(c.value or "")) for c in col[:60]) + 2))
    return out.getvalue()


def _pdf_table(rows, widths=None, font=8):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Table, TableStyle
    st = ParagraphStyle("c", fontName="Helvetica", fontSize=font, leading=font + 2)
    hs = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=font, leading=font + 2, textColor=colors.white)
    data = [[Paragraph(str(c).replace("&", "&amp;").replace("<", "&lt;"), hs if i == 0 else st) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f9")])]))
    return t


def _doc(title, story_fn):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28, title=title)
    ss = getSampleStyleSheet()

    def foot(c, d):
        c.saveState(); c.setFont("Helvetica", 7); c.drawString(28, 14, f"{title}  |  page {d.page}  |  Draft working paper: professional judgement of the auditor applies.")
        c.restoreState()
    doc.build(story_fn(ss), onFirstPage=foot, onLaterPages=foot)
    return buf.getvalue()


def register_pdf(df: pd.DataFrame) -> bytes:
    from reportlab.platypus import Paragraph, Spacer

    def story(ss):
        rows = [["Ref", "Saved on", "Company", "FY end", "Source", "Conclusion", "Vouchers", "Log events", "Exceptions", "High", "Deleted", "Prepared by"]]
        for r in df.itertuples():
            rows.append([r.id, r.saved_at, r.company, r.fy_end, r.source, r.conclusion, r.vouchers, r.log_events, r.exceptions, r.high,
                         r.deleted, r.prepared_by])
        return [Paragraph("EditLog Auditor: history of checks", ss["Title"]), Spacer(1, 6),
                _pdf_table(rows, [30, 80, 150, 55, 70, 80, 45, 50, 50, 35, 40, 70])]
    return _doc("EditLog Auditor history", story)


def check_pdf(meta: dict, summary: pd.DataFrame, controls: pd.DataFrame | None, exceptions: pd.DataFrame, deleted: pd.DataFrame | None,
              users: pd.DataFrame | None = None, caution: list[str] | None = None) -> bytes:
    from reportlab.platypus import PageBreak, Paragraph, Spacer

    def story(ss):
        e = []
        e.append(Paragraph(f"Rule 11(g) audit-trail check: {meta.get('company') or '[Company]'}", ss["Title"]))
        e.append(Paragraph(f"Financial year {meta.get('fy_start', '')} to {meta.get('fy_end', '')} &nbsp;|&nbsp; data source: {meta.get('source', '')}"
                           f" &nbsp;|&nbsp; prepared by: {meta.get('prepared_by', '') or '-'} &nbsp;|&nbsp; saved {meta.get('saved_at', '')}", ss["Normal"]))
        e.append(Spacer(1, 8))
        e.append(Paragraph(f"<b>Suggested conclusion:</b> {str(meta.get('conclusion', '')).upper() or 'PENDING'}", ss["Heading3"]))
        e.append(_pdf_table([["Vouchers in register", "Log events tested", "Exceptions", "High severity", "Tests with exceptions", "Deleted vouchers", "Alterations"],
                             [meta.get("vouchers"), meta.get("log_events"), meta.get("exceptions"), meta.get("high"),
                              f"{meta.get('tests_failed')} of {meta.get('tests_total')}", meta.get("deleted"), meta.get("altered")]], font=9))
        e.append(Spacer(1, 10)); e.append(Paragraph("Tests run", ss["Heading3"]))
        e.append(_pdf_table([list(summary.columns)] + summary.astype(str).values.tolist()))
        if controls is not None and len(controls):
            e.append(Spacer(1, 10)); e.append(Paragraph("Control assessment (ICAI Implementation Guide)", ss["Heading3"]))
            cc = controls[[c for c in ["Ref", "Area", "Result", "Note"] if c in controls]]
            e.append(_pdf_table([list(cc.columns)] + cc.astype(str).values.tolist(), [40, 200, 90, 400]))
        e.append(PageBreak()); e.append(Paragraph("Exceptions (first 60)", ss["Heading3"]))
        if len(exceptions):
            ex = exceptions.head(60)
            keep = [c for c in ["Severity", "Test", "VoucherType", "VoucherNo", "VoucherDate", "User", "Detail"] if c in ex]
            ex = ex[keep] if keep else ex
            e.append(_pdf_table([list(ex.columns)] + ex.astype(str).values.tolist()))
        else:
            e.append(Paragraph("No exceptions.", ss["Normal"]))
        if deleted is not None and len(deleted):
            e.append(Spacer(1, 10)); e.append(Paragraph("Deleted vouchers", ss["Heading3"]))
            dd = deleted.head(60)
            e.append(_pdf_table([list(dd.columns)] + dd.astype(str).values.tolist()))
        for c in caution or []:
            e.append(Spacer(1, 4)); e.append(Paragraph("Caution: " + c, ss["Normal"]))
        if meta.get("notes"):
            e.append(Spacer(1, 8)); e.append(Paragraph("Notes: " + str(meta["notes"]), ss["Normal"]))
        return e
    return _doc(f"Rule 11(g) check {meta.get('company', '')}", story)
