"""
Render the project's Markdown documents as PDFs.

The repository's documentation is written in Markdown, which is the right
format for GitHub but the wrong one for a laptop: on most Windows machines
a .md file has no sensible default application, and double-clicking it
opens whatever last claimed the extension — often Adobe Acrobat, which
reports the file as damaged. Shipping PDFs alongside the Markdown removes
that entirely.

    python docs/build_pdfs.py

Requires: markdown, playwright (with Chromium). Both are optional for the
application itself and are only needed to rebuild the PDFs.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCUMENTS: list[tuple[str, str, str]] = [
    ("README.md", "AuditLens.pdf", "AuditLens — statutory audit analytical review"),
    ("PROJECT_SUMMARY.md", "PROJECT_SUMMARY.pdf", "AuditLens — project summary"),
    ("docs/statutory_basis.md", "docs/statutory_basis.pdf", "AuditLens — statutory basis"),
    ("docs/architecture.md", "docs/architecture.pdf", "AuditLens — architecture"),
    ("docs/video_script.md", "docs/video_script.pdf", "AuditLens — video script"),
    ("docs/recording_guide.md", "docs/recording_guide.pdf", "AuditLens — recording guide"),
]

# Print styling: a professional document, not a rendered web page.
STYLE = """
@page { size: A4; margin: 20mm 18mm 18mm 18mm; }
* { box-sizing: border-box; }
body {
  font-family: "Source Serif 4", Georgia, "Times New Roman", serif;
  font-size: 10.5pt; line-height: 1.55; color: #14201C; margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1, h2, h3, h4 {
  font-family: "Segoe UI", Helvetica, Arial, sans-serif;
  color: #14201C; line-height: 1.2; margin: 1.4em 0 0.5em;
  page-break-after: avoid;
}
h1 { font-size: 22pt; letter-spacing: -0.02em; margin-top: 0;
     border-bottom: 2px solid #1E5A4A; padding-bottom: 8px; }
h2 { font-size: 14pt; color: #1E5A4A; border-bottom: 1px solid #D7DCD5; padding-bottom: 4px; }
h3 { font-size: 11.5pt; }
p { margin: 0 0 0.75em; orphans: 3; widows: 3; }
strong { font-weight: 700; }
a { color: #1E5A4A; text-decoration: none; }
ul, ol { margin: 0 0 0.9em; padding-left: 1.4em; }
li { margin-bottom: 0.28em; }
blockquote {
  margin: 1em 0; padding: 10px 16px; border-left: 3px solid #B77515;
  background: #F7ECD9; font-style: normal;
}
blockquote p { margin: 0; }
table {
  border-collapse: collapse; width: 100%; margin: 0.9em 0;
  font-family: "Segoe UI", Helvetica, Arial, sans-serif; font-size: 8.5pt;
  page-break-inside: avoid;
}
th, td { border: 1px solid #D7DCD5; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #E3EDE7; font-weight: 600; }
tr:nth-child(even) td { background: #FAFBF9; }
code {
  font-family: Consolas, "Courier New", monospace; font-size: 8.5pt;
  background: #EDEFE9; padding: 1px 4px; border-radius: 2px;
}
pre {
  background: #F3F4F0; border: 1px solid #D7DCD5; border-radius: 3px;
  padding: 10px 12px; overflow-x: auto; page-break-inside: avoid;
}
pre code { background: none; padding: 0; font-size: 8pt; line-height: 1.45; }
hr { border: 0; border-top: 1px solid #D7DCD5; margin: 1.6em 0; }
.footer {
  margin-top: 2.2em; padding-top: 10px; border-top: 1px solid #D7DCD5;
  font-family: "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 8pt; color: #7C8983;
}
"""

FOOTER = (
    "AuditLens · AICA Level 2 Module C capstone · CA. Rajendra Bagade · "
    "Machine-generated analytical output requires the review of a Chartered Accountant."
)


def to_html(markdown_text: str, title: str) -> str:
    import markdown

    body = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
    )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>{STYLE}</style></head>"
        f"<body>{body}<div class='footer'>{FOOTER}</div></body></html>"
    )


def build() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "playwright is not installed. Run:\n"
            "  pip install markdown playwright\n"
            "  playwright install chromium",
            file=sys.stderr,
        )
        return 1

    built: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for source_name, output_name, title in DOCUMENTS:
            source = ROOT / source_name
            if not source.exists():
                print(f"  skipped (not found): {source_name}")
                continue
            html = to_html(source.read_text(encoding="utf-8"), title)
            page.set_content(html, wait_until="load")
            output = ROOT / output_name
            output.parent.mkdir(parents=True, exist_ok=True)
            page.pdf(
                path=str(output),
                format="A4",
                print_background=True,
                margin={"top": "18mm", "bottom": "16mm", "left": "16mm", "right": "16mm"},
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=(
                    "<div style='width:100%;font-family:Segoe UI,Arial,sans-serif;"
                    "font-size:7pt;color:#7C8983;padding:0 16mm;display:flex;"
                    "justify-content:space-between;'>"
                    f"<span>{title}</span>"
                    "<span>Page <span class='pageNumber'></span> of "
                    "<span class='totalPages'></span></span></div>"
                ),
            )
            size_kb = output.stat().st_size / 1024
            print(f"  {output_name}  ({size_kb:.0f} KB)")
            built.append(output_name)
        browser.close()

    print(f"\n{len(built)} PDF(s) built.")
    return 0


if __name__ == "__main__":
    sys.exit(build())
