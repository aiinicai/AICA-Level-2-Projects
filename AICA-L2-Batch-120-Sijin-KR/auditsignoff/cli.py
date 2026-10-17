"""Command line: python -m auditsignoff.cli fs|liq ..."""
from __future__ import annotations
import argparse
import re
import sys
from datetime import date
from pathlib import Path

from .loaders import load_document
from .inputs import load_input
from .models import load_params
from .report import sha256, verify_outputs, write_json, write_memo, write_xlsx
from .rules_fs import run_fs
from .rules_liq import run_liq
from .rules_ct import CT, run_ct
from .rules_fa import run_fa
from .rules_tp import run_tp


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


ENG = {}       # set by the app: db, ref  -> every generated paper is stamped with the live review status
TEAM = {}      # set by the app: prepared_by, reviewer1, reviewer2, reviewer3 (names picked from the staff list)


def _stamp(docx_path, meta=None):
    """Stamp the live review status, sign-offs and trail on the paper. With auto=True and no engagement chosen, the engagement is created
    from the review itself (client + module + year) and the people picked in the sidebar are assigned. Never blocks the review."""
    if not ENG:
        return
    try:
        from .workflow import Workflow
        w = Workflow(ENG["db"])
        ref = ENG.get("ref")
        if not ref and ENG.get("auto") and meta:
            client = str(meta.get("Client") or meta.get("Case") or "").strip()
            module = str(meta.get("Module") or "Review").split(" - ")[0].strip() or "Review"
            period = str(meta.get("Financial year") or meta.get("Period") or str(meta.get("As at") or meta.get("Generated") or "")[:4])
            if client and TEAM.get("Prepared by"):
                ref = f"{_slug(client)[:30]}-{_slug(module)[:6]}-{_slug(period)[:10]}"
                try:
                    w.eng(ref)
                except Exception:
                    w.create(ref, str(meta.get("Module") or module), client, period, TEAM["Prepared by"])
                for rl, key in (("preparer", "Prepared by"), ("L1", "Reviewer 1"), ("L2", "Reviewer 2"), ("L3", "Reviewer 3")):
                    if TEAM.get(key):
                        w.assign(ref, rl, TEAM[key], TEAM["Prepared by"], "preparer")
                ENG["last_ref"] = ref
        if ref:
            w.stamp_docx(ref, docx_path, docx_path)
    except Exception as ex:      # stamping is a control aid; a failure must not stop the review file being produced
        ENG["error"] = f"{type(ex).__name__}: {ex}"


def set_engagement(db=None, ref=None, auto=False):
    ENG.clear()
    if db and (ref or auto):
        ENG.update({"db": db, "ref": ref, "auto": auto})


def set_team(prepared_by='', reviewer1='', reviewer2='', reviewer3=''):
    TEAM.clear(); TEAM.update({'Prepared by': prepared_by, 'Reviewer 1': reviewer1, 'Reviewer 2': reviewer2, 'Reviewer 3': reviewer3})


def _ocr_meta(meta):
    for k, v in TEAM.items():
        if v:
            meta[k] = v
    if TEAM.get('Prepared by'):
        from datetime import datetime as _dt
        meta['Prepared at'] = _dt.now().strftime('%d-%b-%Y %H:%M')
    if any(TEAM.values()):
        meta['Prepared by / Reviewed by'] = ' / '.join(v or '____' for v in TEAM.values())
    from .loaders import OCR_NOTES
    if OCR_NOTES:
        meta['OCR quality warning'] = ' | '.join(sorted(set(OCR_NOTES)))
        OCR_NOTES.clear()


def review_fs(engagement, fs_path, tb_path=None, out_dir="out"):
    eng = load_input(engagement, "engagement")
    params = load_params()
    doc = load_document(fs_path)
    results = run_fs(eng, doc, params, tb_path)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    base = f"{_slug(eng['client']['name'])}_FY{eng['fy']}_Final_Review_Paper"
    meta = {"Client": eng["client"]["name"], "Financial year": eng["fy"], "Module": "A - Statutory audit FS pack",
            "Document reviewed": Path(fs_path).name, "Trial balance": Path(tb_path).name if tb_path else "not supplied",
            "Fact sheet source": Path(engagement).name + (" (OCR - verify every name against the original)" if eng.get("_source", {}).get("ocr") else ""),
            "Generated": date.today().isoformat(), "Prepared by / Reviewed by": "____________ / ____________"}
    inputs = {str(fs_path): sha256(fs_path), str(engagement): sha256(engagement)}
    if tb_path:
        inputs[str(tb_path)] = sha256(tb_path)
    _ocr_meta(meta)
    write_memo(out / f"{base}.docx", "Final Review Paper - Statutory Audit FS Pack", meta, results, "A", inputs=inputs)
    write_xlsx(out / f"{base}.xlsx", results, "A")
    write_json(out / f"{base}.json", meta, results, inputs=inputs)
    verify_outputs(out / f"{base}.docx", out / f"{base}.xlsx", out / f"{base}.json")
    _stamp(out / f"{base}.docx", meta)
    return results, out / f"{base}.docx"


def review_liq(input_path, out_dir="out", today=None, docs=None):
    inp = load_input(input_path, "liquidation")
    params = load_params()
    results, ms = run_liq(inp, params, today)
    from .rules_liqdocs import run_liq_docs, DOC_ROLES
    dres, dobj = run_liq_docs(inp, params, docs or {})
    results = sorted(results + dres, key=lambda r: int(r.check_id.split("-")[1]))
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    base = f"{_slug(inp['company'])}_Liquidation_{_slug(str(inp['authority']).upper())}_Review_Paper"
    meta = {"Client": inp["company"], "Authority": str(inp["authority"]).upper(), "Module": "B - Liquidation clock and tracker",
            "As at": (today or date.today()).isoformat(), "Prepared by / Reviewed by": "____________ / ____________"}
    inputs = {str(input_path): sha256(input_path)}
    for role, pl in (docs or {}).items():
        for pth in (pl if isinstance(pl, (list, tuple)) else [pl]):
            if pth:
                inputs[str(pth)] = sha256(pth)
                meta[DOC_ROLES.get(role, role)] = (meta.get(DOC_ROLES.get(role, role), "") + "; " if meta.get(DOC_ROLES.get(role, role)) else "") + Path(pth).name
    for role, err in dobj.errors.items():
        meta["Not readable: " + DOC_ROLES.get(role, role)] = err
    _ocr_meta(meta)
    write_memo(out / f"{base}.docx", "Final Review Paper - Liquidation", meta, results, "B", milestones=ms, inputs=inputs)
    write_xlsx(out / f"{base}.xlsx", results, "B", milestones=ms)
    write_json(out / f"{base}.json", meta, results, milestones=ms, inputs=inputs)
    verify_outputs(out / f"{base}.docx", out / f"{base}.xlsx", out / f"{base}.json")
    _stamp(out / f"{base}.docx", meta)
    return results, ms, out / f"{base}.docx"


def _pairs(path):
    """label -> value pairs from any document (EmaraTax return printout, summary sheet...)."""
    from .inputs import _pairs_from_document
    return {k: v for k, v in _pairs_from_document(load_document(path))}


def review_ct(ct_path, out_dir="out", return_path=None, tp_report_adj=None, filing_date=None, fs_path=None, client=None):
    params = load_params()
    fs_profit = None
    if fs_path:
        from .loaders import find_row
        r = find_row(load_document(fs_path).tables, r"profit (before tax|for the year|/\(loss\))|net profit|profit or loss")
        fs_profit = r[1][0] if r else None
    results, c = run_ct(ct_path, params, _pairs(return_path) if return_path else None, tp_report_adj, filing_date, fs_profit)
    name = client or str(c.inp("01_CLIENT_INFO", "C16") or "Client")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    base = f"{_slug(name)}_CT_Review_Paper"
    meta = {"Client": name, "Module": "D - Corporate tax working sheet review", "Working sheet": Path(ct_path).name,
            "Return figures": Path(return_path).name if return_path else "not supplied",
            "Independent recomputation": f"Taxable income {c.ti:,.0f}; CT payable {c.payable:,.0f}",
            "Generated": date.today().isoformat(), "Prepared by / Reviewed by": "____________ / ____________"}
    inputs = {str(p): sha256(p) for p in (ct_path, return_path, fs_path) if p}
    _ocr_meta(meta)
    write_memo(out / f"{base}.docx", "Final Review Paper - Corporate Tax", meta, results, "D", inputs=inputs)
    write_xlsx(out / f"{base}.xlsx", results, "D")
    write_json(out / f"{base}.json", meta, results, inputs=inputs)
    verify_outputs(out / f"{base}.docx", out / f"{base}.xlsx", out / f"{base}.json")
    _stamp(out / f"{base}.docx", meta)
    return results, out / f"{base}.docx"


def review_tp(engagement, report_path, workbook_path=None, out_dir="out", fs_path=None, ct_path=None, facts=None, birf_path=None):
    eng = load_input(engagement, "engagement")
    params = load_params()
    ct_adj = CT(ct_path, params).tp_adj if ct_path else None
    results, ctx = run_tp(report_path, workbook_path, eng, params, fs_path, ct_adj, facts, birf_path=birf_path)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    base = f"{_slug(eng['client']['name'])}_FY{eng['fy']}_TP_Review_Paper"
    wbn = ""
    if ctx.wb and ctx.wb.comps:
        wbn = f"{len(ctx.wb.comps)} comparables, quartile method {params['tp']['quartile_method']}"
    meta = {"Client": eng["client"]["name"], "Financial year": eng["fy"], "Module": "C - Transfer pricing report review",
            "TP report": Path(report_path).name, "Benchmarking workbook": (Path(workbook_path).name + f" ({wbn})") if workbook_path else "not supplied",
            "BIRF": Path(birf_path).name if birf_path else "not supplied",
            "Generated": date.today().isoformat(), "Prepared by / Reviewed by": "____________ / ____________"}
    inputs = {str(p): sha256(p) for p in (engagement, report_path, workbook_path, fs_path, ct_path, birf_path) if p}
    _ocr_meta(meta)
    write_memo(out / f"{base}.docx", "Final Review Paper - Transfer Pricing", meta, results, "C", inputs=inputs)
    write_xlsx(out / f"{base}.xlsx", results, "C")
    write_json(out / f"{base}.json", meta, results, inputs=inputs)
    verify_outputs(out / f"{base}.docx", out / f"{base}.xlsx", out / f"{base}.json")
    _stamp(out / f"{base}.docx", meta)
    return results, out / f"{base}.docx"


def review_fa(case, out_dir="out", gl=None, period_end=None, scope_years=None, vendors=None, employees=None, related=None, register=None, evidence_dir=None,
              bank=None, mandate=None, signatures=None, fs_data=None, stock=None, holidays=None):
    params = load_params()
    results, c = run_fa(params, gl, period_end, scope_years, vendors, employees, related, register, evidence_dir,
                        bank=bank, mandate=mandate, signatures=signatures, fs_data=fs_data, stock=stock, holidays=holidays)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    base = f"{_slug(case)}_Forensic_Review_Paper"
    meta = {"Case / client": case, "Module": "E - Forensic analytics and evidence integrity",
            "GL lines analysed": f"{len(c.gl.rows):,}" if c.gl else "no GL supplied", "Period end": str(period_end or "not given"),
            "Note": "Analytics identify items to examine; they are indicators, not proof of fraud.",
            "Generated": date.today().isoformat(), "Prepared by / Reviewed by": "____________ / ____________"}
    inputs = {str(p): sha256(p) for p in (gl, vendors, employees, register, bank, mandate, fs_data, stock) if p}
    _ocr_meta(meta)
    write_memo(out / f"{base}.docx", "Final Review Paper - Forensic", meta, results, "E", inputs=inputs)
    write_xlsx(out / f"{base}.xlsx", results, "E")
    write_json(out / f"{base}.json", meta, results, inputs=inputs)
    verify_outputs(out / f"{base}.docx", out / f"{base}.xlsx", out / f"{base}.json")
    _stamp(out / f"{base}.docx", meta)
    return results, out / f"{base}.docx"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="auditsignoff", description="AuditSignOff Suite UAE - Partner/Manager Review Automation (offline)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("fs", help="Review a statutory audit FS pack")
    a.add_argument("--engagement", required=True); a.add_argument("--fs", required=True)
    a.add_argument("--tb"); a.add_argument("--out", default="out")
    b = sub.add_parser("liq", help="Liquidation clock and tracker")
    b.add_argument("--input", required=True); b.add_argument("--out", default="out"); b.add_argument("--today")
    t = sub.add_parser("tp", help="Transfer pricing report review")
    t.add_argument("--engagement", required=True); t.add_argument("--report", required=True)
    t.add_argument("--workbook"); t.add_argument("--fs"); t.add_argument("--ct"); t.add_argument("--birf"); t.add_argument("--out", default="out")
    k = sub.add_parser("ct", help="Corporate tax working sheet review")
    k.add_argument("--ct", required=True); k.add_argument("--return-figures"); k.add_argument("--fs"); k.add_argument("--out", default="out")
    k.add_argument("--tp-adjustment", type=float); k.add_argument("--filed")
    f = sub.add_parser("fa", help="Forensic analytics and evidence integrity")
    f.add_argument("--case", required=True); f.add_argument("--gl"); f.add_argument("--period-end"); f.add_argument("--years", type=int, nargs="*")
    f.add_argument("--vendors"); f.add_argument("--employees"); f.add_argument("--related", nargs="*")
    f.add_argument("--register"); f.add_argument("--evidence"); f.add_argument("--out", default="out")
    f.add_argument("--bank"); f.add_argument("--mandate"); f.add_argument("--signatures"); f.add_argument("--fs-data"); f.add_argument("--stock")
    f.add_argument("--holidays", nargs="*", help="public holidays in the period, YYYY-MM-DD")
    args = ap.parse_args(argv)
    if args.cmd == "fs":
        res, path = review_fs(args.engagement, args.fs, args.tb, args.out)
    elif args.cmd == "liq":
        res, _, path = review_liq(args.input, args.out, date.fromisoformat(args.today) if args.today else None)
    elif args.cmd == "tp":
        res, path = review_tp(args.engagement, args.report, args.workbook, args.out, args.fs, args.ct, birf_path=args.birf)
    elif args.cmd == "ct":
        res, path = review_ct(args.ct, args.out, args.return_figures, args.tp_adjustment,
                              date.fromisoformat(args.filed) if args.filed else None, args.fs)
    else:
        res, path = review_fa(args.case, args.out, args.gl, args.period_end, args.years, args.vendors, args.employees, args.related, args.register, args.evidence,
                           args.bank, args.mandate, args.signatures, args.fs_data, args.stock, args.holidays)
    n = lambda st: sum(1 for r in res if r.status == st)
    print(f"{len(res)} checks run: {n('PASS')} pass, {n('EXC')} exception(s) [{sum(len(r.findings) for r in res if r.status == 'EXC')} finding(s)], "
          f"{n('REVIEW')} for reviewer judgement, {n('NOTRUN')} not run, {n('NA')} n/a. Review paper: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
