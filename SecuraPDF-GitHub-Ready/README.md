# SecuraPDF

A Windows desktop application for converting PDFs to Word and Excel, merging and splitting PDFs, and compressing PDFs. The dashboard and all file processing run locally; the app does not upload documents.

## Build a Windows executable

The PyInstaller one-file build is created in `dist\SecuraPDF.exe`. It includes the Python runtime and application dependencies, so a recipient does not need to install Python. Build it on Windows for Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
.\build_exe.ps1
```

The build can take a few minutes. Share the executable with the corresponding source and notices. PyMuPDF is licensed under AGPL-3.0-or-later, with a commercial license also available; distributing a proprietary executable may require a suitable commercial license or compliance with the AGPL terms. See the [official PyMuPDF licensing page](https://pymupdf.io/licensing) before distributing the application.

## Requirements and setup

- Python 3.10 or newer (tested in this workspace with Python 3.14).
- Windows, macOS, or Linux with Tkinter installed. Tkinter is included with most Windows Python installers.
- Install dependencies in a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the desktop application from this project directory:

```powershell
python -m pdf_tool
```

Run the command line interface:

```powershell
python pdf_tool_cli.py inspect "PDF sample.pdf"
python pdf_tool_cli.py convert "PDF sample.pdf" "sample.docx"
python pdf_tool_cli.py convert input.pdf output.docx --mode visual
python pdf_tool_cli.py convert input.pdf output.docx --pages 2-5
python pdf_tool_cli.py merge combined.pdf first.pdf second.pdf
python pdf_tool_cli.py split input.pdf output_parts --ranges 1-3,4,5-7
```

## Features

- **Editable conversion:** extracts selectable text, preserves wide horizontal gaps between text spans with positioned tabs, separates headings and paragraphs using source line spacing, justifies multiline body paragraphs and long narrative table cells, embeds extracted images, and uses PyMuPDF table detection to create editable Word tables. Empty detector columns are folded into adjacent real columns. Horizontal merged cells are reconstructed, including merged title rows. Column headings and merged title rows are bold; for tables without a separate merged title row, the first data row is kept regular weight. Rows use Word's automatic height with compact cell padding so cells expand to fit their contents.
- **Visual copy:** places each rendered PDF page in Word as an image. This retains a closer page appearance but its text, tables, and images are not individually editable.
- **Local OCR option:** for scanned pages, the optional OCR path uses PyMuPDF's Tesseract integration. Install Tesseract separately and make its executable and English/Hindi (`eng`, `hin`) language data available locally. OCR is not required for text PDFs.
- **Merge and split:** merge input PDFs in the chosen order; split into separate PDFs using ranges such as `1-3,4,5-7`.
- **PDF to Excel:** detected tables are written to separate worksheets, and other selectable text is saved in page text worksheets. Whole-cell numeric values are written as Excel numbers, right-aligned, with decimal places retained for calculations. Dates and mixed text remain text. Scanned pages require OCR before text can be extracted.
- **Compress PDF:** choose High compress - Low quality, Medium compress - Moderate quality, or Low compress - High quality. The presets progressively preserve more image resolution and quality; the compressed file size depends on the source PDF.
- **CLI:** the same core operations can be run without the GUI.

## Project details

Created by **CA Gagan Jhavar** as a college project. Sample and generated documents are intentionally not included in this source package.

## Dependencies and licensing

- **PyMuPDF** provides text/image extraction, rendering, and table detection. It is available under AGPL-3.0-or-later or a commercial license. Review the [PyMuPDF licensing terms](https://pymupdf.io/licensing) before redistributing or using this application in a closed-source/commercial product; obtain a suitable license when needed.
- **python-docx** is MIT-licensed and writes Word documents.
- **pypdf** is BSD-3-Clause licensed and handles PDF merge/split operations.
- **openpyxl** is MIT-licensed and creates `.xlsx` workbooks.

Dependency versions are bounded in `requirements.txt`. Install them before going offline; application processing itself needs no internet connection.

## Troubleshooting

- **Missing Tesseract:** the application reports that OCR could not run. Install Tesseract and the needed language packs locally; regular text extraction remains available.
- **Encrypted PDFs:** unlock them using a trusted local PDF application before processing.
- **Existing outputs:** the GUI asks before replacing a conversion or merge target. Split outputs are never overwritten.
- **Fidelity:** always compare the generated Word file against the original PDF. No general-purpose conversion can guarantee identical appearance while also keeping all content structurally editable.


