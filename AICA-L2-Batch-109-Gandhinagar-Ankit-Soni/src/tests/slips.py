"""Fixtures: confirmation letters as a party would send them back."""
import io, random
import pymupdf
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"


def slip_rect(pdf_data):
    """Where the blank after 'is INR' sits on the letter."""
    doc = pymupdf.open(stream=pdf_data, filetype="pdf")
    page = doc[0]
    hits = page.search_for("We hereby confirm")
    words = [w for w in page.get_text("words") if "____" in w[4] and w[1] > hits[0].y0 - 2]
    words.sort(key=lambda w: (w[1], w[0]))
    rect = pymupdf.Rect(words[0][:4])
    doc.close()
    return rect


def typed(pdf_data, figure):
    """The party typed the figure onto the PDF (it is in the text layer)."""
    rect = slip_rect(pdf_data)
    doc = pymupdf.open(stream=pdf_data, filetype="pdf")
    doc[0].insert_text((rect.x0 + 2, rect.y1 - 3), figure, fontsize=10)
    out = doc.tobytes(); doc.close()
    return out


def annotated(pdf_data, figure):
    """The figure was added as a comment box: not in the text layer."""
    rect = slip_rect(pdf_data)
    doc = pymupdf.open(stream=pdf_data, filetype="pdf")
    box = pymupdf.Rect(rect.x0, rect.y0 - 4, rect.x0 + 110, rect.y1 + 3)
    doc[0].add_freetext_annot(box, figure, fontsize=10)
    out = doc.tobytes(); doc.close()
    return out


def handwrite(image, origin, text, size, seed=7, ink=(25, 40, 140)):
    """Uneven, slanted, jittered characters: a stand-in for handwriting."""
    rng = random.Random(seed)
    x, y = origin
    for ch in text:
        font = ImageFont.truetype(FONT, int(size * rng.uniform(0.9, 1.15)))
        w = int(font.getlength(ch)) + 8
        glyph = Image.new("RGBA", (w + 10, int(size * 1.8)), (0, 0, 0, 0))
        ImageDraw.Draw(glyph).text((5, 4), ch, font=font, fill=ink + (255,),
                                   stroke_width=rng.choice((0, 1)), stroke_fill=ink + (255,))
        glyph = glyph.rotate(rng.uniform(-9, 9), expand=True, resample=Image.BICUBIC)
        image.paste(glyph, (int(x), int(y + rng.uniform(-3, 3))), glyph)
        x += w * rng.uniform(0.78, 0.98)
    return image


def scanned(pdf_data, figure=None, handwritten=False, dpi=150, skew=0.0,
            extra=None, seed=7):
    """Print, fill in, sign and scan: an image-only PDF with no text layer."""
    rect = slip_rect(pdf_data)
    doc = pymupdf.open(stream=pdf_data, filetype="pdf")
    pix = doc[0].get_pixmap(dpi=dpi)
    doc.close()
    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    scale = dpi / 72.0
    if figure:
        if handwritten:
            handwrite(image, (rect.x0 * scale + 6, rect.y0 * scale - 14),
                      figure, int(13 * scale), seed=seed)
        else:
            font = ImageFont.truetype(FONT.replace("-Oblique", ""), int(10 * scale))
            ImageDraw.Draw(image).text((rect.x0 * scale + 6, rect.y0 * scale - 3),
                                       figure, font=font, fill=(0, 0, 0))
    for (dx, dy, text) in (extra or []):
        handwrite(image, (rect.x0 * scale + dx, rect.y0 * scale + dy), text,
                  int(11 * scale), seed=seed + 3)
    if skew:
        image = image.rotate(skew, expand=True, fillcolor=(255, 255, 255),
                             resample=Image.BICUBIC)
    # scanner noise and JPEG artefacts
    buffer = io.BytesIO(); image.save(buffer, "JPEG", quality=62)
    out = pymupdf.open()
    page = out.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=buffer.getvalue())
    data = out.tobytes(); out.close()
    return data, buffer.getvalue()
