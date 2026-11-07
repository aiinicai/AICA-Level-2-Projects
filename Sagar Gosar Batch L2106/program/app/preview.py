"""Page images with highlighted regions (scan viewer and report extracts)."""
from PIL import Image, ImageDraw

from .extract_pdf import render_page_image


def union_region(regions, page=None):
    rs = [r for r in regions if page is None or r[0] == page]
    if not rs:
        return None
    return (min(r[1] for r in rs), min(r[2] for r in rs), max(r[3] for r in rs), max(r[4] for r in rs))


def page_with_highlight(doc, page, regions, dpi=110, color=(220, 30, 30)):
    img = render_page_image(doc, page, dpi)
    if img is None:
        return None, None
    W, H = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(overlay); first_y = None
    for r in regions:
        if r[0] != page:
            continue
        x0, y0, x1, y1 = r[1] * W, r[2] * H, r[3] * W, r[4] * H
        d.rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], fill=color + (45,), outline=color + (255,), width=3)
        first_y = y0 if first_y is None else min(first_y, y0)
    out = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return out, (first_y if first_y is not None else 0)


def crop_for_report(doc, page, regions, dpi=130, pad=0.045, color=(220, 30, 30), max_w=900):
    """The part of the scanned page around the difference, with the region outlined."""
    img = render_page_image(doc, page, dpi)
    if img is None:
        return None
    u = union_region(regions, page)
    if u is None:
        return None
    W, H = img.size
    d = ImageDraw.Draw(img, "RGBA")
    for r in regions:
        if r[0] == page:
            d.rectangle([r[1] * W - 3, r[2] * H - 3, r[3] * W + 3, r[4] * H + 3], outline=color + (255,), width=3, fill=color + (30,))
    x0, y0, x1, y1 = u
    box = (0, int(max(0, y0 - pad) * H), W, int(min(1, y1 + pad) * H))
    if box[3] - box[1] < 60:
        box = (0, max(0, box[1] - 30), W, min(H, box[3] + 30))
    c = img.crop(box)
    if c.width > max_w:
        c = c.resize((max_w, max(1, int(c.height * max_w / c.width))), Image.LANCZOS)
    return c.convert("RGB")
