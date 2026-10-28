"""AuditSignOff Suite UAE Review Automation - self-check. Run:  python doctor.py
Checks the PC (Python, packages, Tesseract, Word/LibreOffice) and then builds a review file in EVERY tab from bundled sample data,
re-opening each output to prove it is valid. Prints PASS / FAIL / WARN per line. Nothing leaves the PC."""
import importlib
import shutil
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
S = HERE / "samples"
ok = fail = warn = 0


def line(kind, msg):
    global ok, fail, warn
    ok += kind == "PASS"; fail += kind == "FAIL"; warn += kind == "WARN"
    print(f"[{kind}] {msg}")


def step(name, fn):
    try:
        r = fn()
        line("PASS", name + (f" - {r}" if r else ""))
    except Exception as e:
        line("FAIL", f"{name} - {type(e).__name__}: {str(e)[:300]}")
        if "-v" in sys.argv:
            traceback.print_exc()


print(f"Python {sys.version.split()[0]} on {sys.platform}")
line("PASS" if (3, 10) <= sys.version_info[:2] <= (3, 13) else "WARN", "Python 3.10-3.13 recommended (3.14 may lack some wheels)")
for mod, pipname in (("docx", "python-docx"), ("openpyxl", "openpyxl"), ("pdfplumber", "pdfplumber"), ("yaml", "PyYAML"), ("streamlit", "streamlit"),
                     ("pandas", "pandas"), ("PIL", "Pillow"), ("pytesseract", "pytesseract")):
    try:
        importlib.import_module(mod); line("PASS", f"package {pipname}")
    except ImportError:
        line("FAIL", f"package {pipname} missing -> python -m pip install {pipname}")

try:
    from auditsignoff.loaders import tesseract_setup
    exe, langs = tesseract_setup()
    line("PASS", f"Tesseract found: {exe} (languages used: {langs})")
    if "ara" not in langs:
        line("WARN", "Arabic language data not installed - Arabic text on scans will not be read (English is unaffected)")
except Exception as e:
    line("FAIL", f"Tesseract not usable ({e}) - scanned PDFs/images cannot be read; install from UB-Mannheim and add to PATH")

from auditsignoff.legacy import _soffice
line("PASS" if _soffice() else "WARN", "LibreOffice found (.doc/.xls conversion)" if _soffice() else
     "LibreOffice not found - .doc/.xls need Word/Excel on this PC or save as .docx/.xlsx; also needed for page-count checks on Word files")

tmp = Path(tempfile.mkdtemp(prefix="as_doctor_"))

# OCR round trip
def ocr():
    from PIL import Image, ImageDraw, ImageFont
    from auditsignoff.loaders import load_document
    im = Image.new("RGB", (1400, 300), "white"); d = ImageDraw.Draw(im)
    try:
        ft = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        ft = ImageFont.load_default()
    d.text((40, 60), "Total assets 500,000", fill="black", font=ft)
    d.text((40, 160), "Licence No. 709679", fill="black", font=ft)
    p = tmp / "ocr.png"; im.save(p)
    t = load_document(str(p)).all_text
    assert "Total assets" in t, f"OCR returned nothing usable: {t[:80]!r}"
    if "500,000" in t and "709679" in t:
        return "text and digits read correctly"
    line("WARN", f"OCR misread a digit ({t.strip()[:60]!r}) - always verify scanned figures against the original")
    return "text read"
step("OCR round trip on a generated image", ocr)

from auditsignoff import cli
def liq():
    r, ms, d = cli.review_liq(str(S / "liq_dmcc_clean.yaml"), tmp / "liq", date.today())
    return f"{len(r)} checks, file {d.name}"
step("Tab Liquidation (tracker only)", liq)

def liq_docs():
    import docx
    def mk(n, lines):
        dd = docx.Document()
        for l in lines: dd.add_paragraph(l)
        p = tmp / n; dd.save(p); return str(p)
    co = "TIDY TRADING DMCC"
    docs = {"br": mk("br.docx", [f"Board Resolution of {co}", "Dated 2 March 2026", f"RESOLVED to voluntarily liquidate {co}; Mr Ravi Kumar appointed liquidator. Signed."]),
            "soa": mk("soa.docx", [f"Statement of Affairs {co}", "As at 30 June 2026", "Total assets 500,000", "Total liabilities 100,000", "Net surplus 400,000", "VAT payable nil"]),
            "ctvat": [mk("ct.docx", ["Corporate Tax registration", "Corporate Tax TRN 100123456789012"])]}
    r, ms, d = cli.review_liq(str(S / "liq_dmcc_clean.yaml"), tmp / "liq2", date.today(), docs=docs)
    ran = [x.check_id for x in r if x.check_id in ("LQ-21", "LQ-22", "LQ-25") and x.status != "NOTRUN"]
    assert len(ran) == 3, f"document checks not run: {ran}"
    return "BR, SOA and CT/VAT checks ran"
step("Tab Liquidation (with documents)", liq_docs)

def fs():
    r, d = cli.review_fs(str(S / "engagement_clean.xlsx"), str(S / "fs_clean.docx"), str(S / "tb_clean.xlsx"), tmp / "fs")[:2]
    return f"{len(r)} checks"
step("Tab Statutory FS", fs)

def ct():
    out = cli.review_ct(str(S / "ct_demo_locked.xlsx"), tmp / "ct")
    return f"{len(out[0])} checks"
step("Tab Corporate Tax", ct)

def tp():
    sys.path.insert(0, str(HERE / "tests"))
    from tp_fixtures import make_report, make_workbook, stats
    rp = tmp / "tp.docx"; wb = tmp / "tp.xlsx"
    make_report(rp); make_workbook(wb)
    out = cli.review_tp(str(S / "engagement_clean.xlsx"), str(rp), str(wb), tmp / "tp")
    return f"{len(out[0])} checks"
step("Tab Transfer Pricing", tp)

def fa():
    sys.path.insert(0, str(HERE / "tests"))
    from fa_fixtures import make_gl
    gl = tmp / "gl.xlsx"; make_gl(gl)
    out = cli.review_fa("Doctor test", tmp / "fa", gl=str(gl), period_end="2025-12-31")
    sys.path.insert(0, str(HERE / "samples"))
    from make_forensic_case import build
    d = build(tmp / "case", fraud=True)                          # bank, signatures, FS and stock checks run on the ZENITH case
    out2 = cli.review_fa("Doctor case", tmp / "fa2", gl=str(d / "gl.xlsx"), period_end="2025-12-31", bank=str(d / "bank_statement.xlsx"), mandate=str(d / "mandate.xlsx"),
                         signatures=str(d / "signatures"), fs_data=str(d / "fs_data.xlsx"), stock=str(d / "stock_register.xlsx"))
    hit = {r.check_id for r in out2[0] if r.status == "EXC"}
    assert {"FA-11", "FA-12", "FA-13", "FA-14"} <= hit, hit
    return f"{len(out[0])} checks; case file finds {len(hit)} exception classes"
step("Tab Forensic", fa)

def wfl():
    import json
    from auditsignoff.workflow import Workflow
    w = Workflow(tmp / "wf.db"); w.create("DOC", "TP", "Doctor", "2025", "P")
    j = tmp / "r.json"; j.write_text(json.dumps({"results": [{"check": "X", "status": "EXC", "findings": [{"check_id": "TP-1", "title": "t", "severity": "High", "detail": "d"}]}]}))
    w.ingest("DOC", j, "S", "L1"); w.export_trail("DOC", tmp / "t.xlsx")
    return "review points, rounds and audit log"
step("Tab Review workflow", wfl)

print(f"\nSummary: {ok} passed, {warn} warnings, {fail} failed")
if fail:
    print("Fix the FAIL lines above, then run  python doctor.py  again. Add -v for details.")
sys.exit(1 if fail else 0)
