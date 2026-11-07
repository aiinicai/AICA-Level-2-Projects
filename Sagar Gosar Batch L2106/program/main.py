"""Agreement Compare.

    python main.py                       open the desktop application (Qt interface)
    python main.py --cli DRAFT.docx EXECUTED.pdf --out reports --export word,pdf
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def cli(argv):
    ap = argparse.ArgumentParser(prog="main.py --cli", description="Compare a Word draft with an executed (scanned) copy.")
    ap.add_argument("draft"); ap.add_argument("executed")
    ap.add_argument("--out", default="."); ap.add_argument("--export", default="word,pdf", help="word, pdf, both or none (comma separated)")
    ap.add_argument("--force-ocr", action="store_true"); ap.add_argument("--dpi", type=int, default=300); ap.add_argument("--lang", default="eng")
    ap.add_argument("--pages", default="", help="pages of the executed copy to use, e.g. 2-9,11")
    ap.add_argument("--upright", action="store_true", help="do not auto-detect upside-down pages"); ap.add_argument("--rotate", default="", help="page:degrees, e.g. 3:180,4:90")
    ap.add_argument("--no-reflow", action="store_true"); ap.add_argument("--keep-stamps", action="store_true"); ap.add_argument("--no-scans", action="store_true")
    ap.add_argument("--redline", action="store_true"); ap.add_argument("--include-ocr", action="store_true")
    a = ap.parse_args(argv)
    from app.models import CompareOptions
    from app.pages import page_count, parse_pages
    from app.pipeline import run_comparison
    o = CompareOptions(force_ocr=a.force_ocr, ocr_dpi=a.dpi, ocr_lang=a.lang, reflow=not a.no_reflow, ignore_stamps=not a.keep_stamps, auto_rotate=not a.upright)
    if a.pages and a.executed.lower().endswith(".pdf"):
        o.pages = parse_pages(a.pages, page_count(a.executed))
    if a.rotate:
        o.page_rotation = {int(k): int(v) for k, v in (x.split(":") for x in a.rotate.split(","))}
    res = run_comparison(a.draft, a.executed, o, progress=lambda f, m: print(f"\r{f * 100:5.1f}%  {m:<50}", end="", file=sys.stderr))
    print(file=sys.stderr)
    print("\n".join(__import__("app.report_model", fromlist=["x"]).summary_lines(res)))
    for it in res.items:
        if not it.ocr_only:
            print(f"#{it.id:<3} {it.severity:<8} {','.join(it.categories):<26} {(it.label_a or it.label_b or '-'):<6} {it.summary}")
    os.makedirs(a.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(a.executed))[0]
    kinds = {x.strip() for x in a.export.split(",")}
    if "both" in kinds:
        kinds |= {"word", "pdf"}
    kw = dict(include_scans=not a.no_scans, include_redline=a.redline, include_ocr=a.include_ocr)
    if "word" in kinds:
        from app.export_word import export_word
        print("Word report:", export_word(res, os.path.join(a.out, f"Comparison_Report_{base}.docx"), **kw))
    if "pdf" in kinds:
        from app.export_pdf import export_pdf
        print("PDF report: ", export_pdf(res, os.path.join(a.out, f"Comparison_Report_{base}.pdf"), **kw))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        sys.exit(cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--selfcheck":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from app.qt.selfcheck import main
        sys.exit(main())
    from app.qt.window import run
    run()
