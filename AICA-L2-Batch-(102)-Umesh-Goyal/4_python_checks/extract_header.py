r"""Read the header fields of an SCN from a PDF with a text layer (or from an OCR .txt file).

Run:  py extract_header.py ..\5_samples\sample_scn_text.pdf
      py extract_header.py              (opens a file chooser)

Output: the fields on screen and a <name>_header.json next to the PDF.
Several candidates are kept for dates and sections because the first regex hit is often wrong.
Always confirm every field against the original notice.
"""
import json
import os
import sys

from scn_common import header_fields, pdf_text


def choose_file():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Choose the SCN PDF or OCR text file",
                                      filetypes=[("PDF or text", "*.pdf *.txt")])


def main():
    interactive = len(sys.argv) < 2
    path = sys.argv[1] if not interactive else choose_file()
    if not path:
        sys.exit("No file chosen.")

    if path.lower().endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            text, pages = f.read(), None
    else:
        text, pages = pdf_text(path)
        if len(text.strip()) < 50:
            sys.exit("No text layer found - this looks like a scanned PDF. Use ocr_scanned_pdf.py.")

    result = header_fields(text, pages)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    out = os.path.splitext(path)[0] + "_header.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\nSaved:", out)
    if interactive:
        input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
