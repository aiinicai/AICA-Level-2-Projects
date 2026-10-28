from __future__ import annotations

import argparse
from pathlib import Path

from .converter import convert_to_docx, inspect_pdf, merge_pdfs, parse_ranges, split_pdf


def main():
    parser = argparse.ArgumentParser(prog="pdf-tool", description="Offline PDF converter, merger, and splitter")
    sub = parser.add_subparsers(dest="command", required=True)
    info = sub.add_parser("inspect", help="Inspect pages, text, images, and detectable tables")
    info.add_argument("pdf")
    cv = sub.add_parser("convert", help="Convert PDF to Word")
    cv.add_argument("pdf")
    cv.add_argument("docx")
    cv.add_argument("--mode", choices=("editable", "visual"), default="editable")
    cv.add_argument("--pages", help="One continuous range, e.g. 2-5")
    cv.add_argument("--ocr", action="store_true", help="Try local Tesseract OCR for scanned pages")
    mg = sub.add_parser("merge", help="Merge PDF files in the given order")
    mg.add_argument("output")
    mg.add_argument("pdfs", nargs="+")
    sp = sub.add_parser("split", help="Split PDF into one file per comma-separated range")
    sp.add_argument("pdf")
    sp.add_argument("output_dir")
    sp.add_argument("--ranges", required=True, help="For example 1-3,4,5-7")
    args = parser.parse_args()
    if args.command == "inspect":
        result = inspect_pdf(args.pdf)
        print(f"Pages: {result['page_count']}; selectable text: {result['selectable_text']}")
        for i, p in enumerate(result["pages"], 1):
            print(f"Page {i}: {p['size_pt']} pt; {p['text_chars']} text chars; {p['images']} images; tables {p['tables']}")
    elif args.command == "convert":
        parsed = parse_ranges(args.pages) if args.pages else None
        if parsed and len(parsed) != 1:
            parser.error("convert --pages accepts one continuous range, such as 2-5")
        if Path(args.docx).exists():
            parser.error(f"Output already exists: {args.docx}; choose another name")
        if Path(args.pdf).resolve() == Path(args.docx).resolve():
            parser.error("The output must be different from the input PDF")
        page_range = tuple(parsed[0]) if parsed else None
        result = convert_to_docx(args.pdf, args.docx, mode=args.mode, page_range=page_range, ocr=args.ocr)
        print(f"Saved {args.docx}: {result['pages']} page(s), {result['tables']} table(s), {result['images']} image(s)")
        for warning in result["warnings"]:
            print("WARNING:", warning)
    elif args.command == "merge":
        if Path(args.output).exists():
            parser.error(f"Output already exists: {args.output}; choose another name")
        if Path(args.output).resolve() in [Path(p).resolve() for p in args.pdfs]:
            parser.error("The output must be a new file, not one of the inputs")
        print(f"Saved {merge_pdfs(args.pdfs, args.output)} pages to {args.output}")
    else:
        outputs = split_pdf(args.pdf, args.output_dir, parse_ranges(args.ranges))
        print("Created:\n" + "\n".join(map(str, outputs)))


if __name__ == "__main__":
    main()
