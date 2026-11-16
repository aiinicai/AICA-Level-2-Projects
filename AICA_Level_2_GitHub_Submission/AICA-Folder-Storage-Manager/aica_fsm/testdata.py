"""Generate deterministic test folders.

  python tools/make_test_data.py bulk  <folder> <count> [seed]
  python tools/make_test_data.py docs  <folder>
"""
from __future__ import annotations

import os
import random
import sys


def make_bulk(folder: str, count: int, seed: int = 1, dup_groups: int = 20) -> list[str]:
    rnd = random.Random(seed)
    os.makedirs(folder, exist_ok=True)
    exts = ["txt", "csv", "log", "dat", "md", "json", "xml", "bin"]
    subdirs = [""] + [os.path.join(f"Dept{d:02d}", f"Year{y}") for d in range(1, 9) for y in (2023, 2024, 2025)] + \
              [f"Dept{d:02d}" for d in range(1, 9)]
    paths = []
    # duplicate groups first (3 copies each) - counted within *count*
    made = 0
    for g in range(dup_groups):
        if made + 3 > count:
            break
        content = f"duplicate group {seed}-{g}\n".encode() * (50 + g * 7)
        for c in range(3):
            sd = rnd.choice(subdirs)
            p = os.path.join(folder, sd, f"dup_{g:03d}_copy{c}.dat")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(content)
            paths.append(p)
            made += 1
    i = 0
    while made < count:
        sd = rnd.choice(subdirs)
        ext = rnd.choice(exts)
        p = os.path.join(folder, sd, f"file_{seed}_{i:06d}.{ext}")
        i += 1
        os.makedirs(os.path.dirname(p), exist_ok=True)
        size = rnd.choice([0, 17, 200, 1024, 4096, 20000, 75000])
        with open(p, "wb") as f:
            f.write(f"seed={seed} idx={i}\n".encode())
            if size:
                f.write(rnd.randbytes(size))
        paths.append(p)
        made += 1
    return paths


# ------------------------------------------------------------------------------ documents
def _pdf_text(path: str, lines: list[str]) -> None:
    """Minimal valid PDF with a real text layer (Helvetica)."""
    content = ["BT", "/F1 14 Tf", "72 760 Td", "18 TL"]
    for ln in lines:
        esc = ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content.append(f"({esc}) Tj T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(path, "wb") as f:
        f.write(out)


def _text_image(lines: list[str], size=(1400, 700)):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except OSError:
        font = ImageFont.load_default()
    y = 60
    for ln in lines:
        d.text((60, y), ln, fill="black", font=font)
        y += 70
    return img


def make_docs(folder: str) -> dict:
    os.makedirs(folder, exist_ok=True)
    import docx
    out = {}
    out["text_pdf"] = os.path.join(folder, "Invoice_2025_001.pdf")
    _pdf_text(out["text_pdf"], ["TAX INVOICE", "Client: Sharma Textiles Pvt Ltd", "Invoice No 2025/001",
                                "Amount payable Rs 45,000"])
    out["scanned_pdf"] = os.path.join(folder, "Scan_0007.pdf")
    _text_image(["BANK CONFIRMATION", "Client: Mehta Exports", "Balance as on 31 March 2025"]).save(
        out["scanned_pdf"], "PDF", resolution=150)
    out["word"] = os.path.join(folder, "Engagement letter.docx")
    d = docx.Document()
    d.add_heading("Engagement Letter", 1)
    d.add_paragraph("Date: 1 April 2025")
    d.add_paragraph("To the Board of Directors of Gupta Agro Industries,")
    d.add_paragraph("We are pleased to confirm our acceptance of the audit engagement.")
    d.save(out["word"])
    out["image"] = os.path.join(folder, "receipt_photo.png")
    _text_image(["PAYMENT RECEIPT", "Received from Sharma Textiles", "Rs 12,500 by cheque"]).save(out["image"])
    out["no_name"] = os.path.join(folder, "notes.txt")
    with open(out["no_name"], "w", encoding="utf-8") as f:
        f.write("General notes with no client mentioned.\n")
    # version pair: similar text, different hashes
    out["ver1"] = os.path.join(folder, "Audit report v1.docx")
    out["ver2"] = os.path.join(folder, "Audit report v2.docx")
    body = ["Independent Auditor's Report", "Opinion: We have audited the financial statements of the company.",
            "Basis for opinion: We conducted our audit in accordance with the Standards on Auditing.",
            "Key audit matters: Revenue recognition and inventory valuation were reviewed in detail.",
            "Responsibilities of management for the financial statements are described below."]
    d1 = docx.Document()
    for ln in body:
        d1.add_paragraph(ln)
    d1.save(out["ver1"])
    d2 = docx.Document()
    for ln in body[:-1] + ["Responsibilities of management and those charged with governance are described below.",
                           "Other matter: The comparative figures were audited by another auditor."]:
        d2.add_paragraph(ln)
    d2.save(out["ver2"])
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "bulk":
        p = make_bulk(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
        print(f"{len(p)} files in {sys.argv[2]}")
    elif cmd == "docs":
        print(make_docs(sys.argv[2]))
