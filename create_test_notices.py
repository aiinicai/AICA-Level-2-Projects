"""Create fictional local smoke-test PDFs; run after installing dev requirements."""
from io import BytesIO
from pathlib import Path
import sys
import textwrap

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from services.demo_service import SAMPLE_TEXT


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    assets, qa = root / "assets", root / "qa"
    assets.mkdir(exist_ok=True)
    qa.mkdir(exist_ok=True)
    target = assets / "fictional_sample_notice.pdf"
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle("Fictional tax notice for testing")
    pdf.setAuthor("")
    text = pdf.beginText(45, 790)
    text.setFont("Helvetica", 10)
    text.setLeading(16)
    for line in SAMPLE_TEXT.replace("—", "-").splitlines():
        for wrapped in textwrap.wrap(line, width=90) or [""]:
            text.textLine(wrapped)
    pdf.drawText(text)
    pdf.save()
    target.write_bytes(output.getvalue())
    with pdfium.PdfDocument(output.getvalue()) as document:
        page = document[0]
        try:
            bitmap = page.render(scale=2)
            try:
                image = bitmap.to_pil().convert("RGB")
                try:
                    image.save(qa / "scanned_notice.pdf", "PDF", resolution=144)
                    image.save(qa / "sample_preview.png")
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            page.close()
    print("Created fictional searchable and scanned test notices.")


if __name__ == "__main__":
    main()
