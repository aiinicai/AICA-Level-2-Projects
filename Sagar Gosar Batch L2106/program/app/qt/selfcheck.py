"""python main_qt.py --selfcheck  – verifies that the new interface matches the engine installed next to it."""
import dataclasses
import importlib
import os
import sys


def main():
    ok_all = True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all &= bool(cond)
        print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {detail}" if detail and not cond else ""))

    print("Agreement Compare – interface self-check")
    mods = {}
    for m in ("config", "models", "pipeline", "comparer", "report_model", "preview", "adjust", "pages", "extract_pdf", "export_word", "export_pdf"):
        try:
            mods[m] = importlib.import_module("app." + m); check(f"engine module app.{m}", True)
        except Exception as ex:   # noqa
            check(f"engine module app.{m}", False, repr(ex))
    if not ok_all:
        print("\nSome engine files are missing – copy this package into your existing agreement_compare folder."); return 1
    need = {"models": ["CompareOptions"], "pipeline": ["run_comparison"], "comparer": ["compare_documents"], "preview": ["page_with_highlight"],
            "adjust": ["working_copy", "merge", "split", "edit", "set_ignored", "ignore_range", "build_inputs", "save_session", "load_session", "index_of", "next_uid"],
            "report_model": ["summary_lines", "meta_rows", "clause_label", "runs_for_item", "redline_runs", "STYLE_DEF", "PLAIN", "DISCLAIMER"],
            "pages": ["page_count", "format_pages", "parse_pages"], "extract_pdf": ["Cancelled", "reocr_page", "render_page_image"],
            "config": ["APP_NAME", "PREVIEW_DPI", "configure_tesseract"]}
    for m, names in need.items():
        for n in names:
            check(f"app.{m}.{n}", hasattr(mods[m], n))
    fields = {f.name for f in dataclasses.fields(mods["models"].CompareOptions)}
    for f in ("ignore_case", "compare_punct", "ocr_tolerance", "force_ocr", "ocr_dpi", "ocr_lang", "pages", "reflow", "ignore_stamps", "ignore_colour_ink", "enhance_scan"):
        check(f"CompareOptions.{f}", f in fields)
    print("  note  auto_rotate present:", "auto_rotate" in fields, "(rotation check toggle is skipped if absent)")
    if not ok_all:
        return 1
    # real comparison on the bundled samples
    base = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "samples")
    a, b = os.path.join(base, "Draft_Agreement.docx"), os.path.join(base, "Executed_text.pdf")
    if not (os.path.isfile(a) and os.path.isfile(b)):
        print("  skip  samples not found – run the comparison from the window instead"); return 0 if ok_all else 1
    res = mods["pipeline"].run_comparison(a, b, mods["models"].CompareOptions())
    for attr in ("items", "rows", "stats", "observations", "doc_a", "doc_b", "raw_a", "raw_b", "anchors_used"):
        check(f"result.{attr}", hasattr(res, attr))
    it = res.items[0] if res.items else None
    if it:
        for attr in ("id", "severity", "categories", "summary", "text_a", "text_b", "ocr_only", "pages_b", "regions_b", "kind"):
            check(f"item.{attr}", hasattr(it, attr))
    if res.rows:
        for attr in ("label_a", "label_b"):
            check(f"row.{attr}", hasattr(res.rows[0], attr))
    check("stats['by_severity']", all(k in res.stats["by_severity"] for k in ("Critical", "Major", "Minor", "Info")))
    # build the window headless with the real result
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from app.qt.classic import ClassicWindow
    w = ClassicWindow(); w.show()
    try:
        w.set_result(res, fresh=True)
        for k in ("setup", "summary", "analysis", "sbs", "redline", "align", "reports"):
            w.goto(k); app.processEvents()
        check("window renders the real result", True)
    except Exception as ex:   # noqa
        import traceback; traceback.print_exc(); check("window renders the real result", False, repr(ex))
    print("\nRESULT:", "ALL CHECKS PASSED" if ok_all else "SOME CHECKS FAILED – send me the lines marked FAIL")
    return 0 if ok_all else 1
