"""Draws the Tally MIS app icon and writes app/assets/tally_mis.ico (16–256 px) and docs/screenshots/app-icon.png.

  python tools/make_icon.py            (needs Pillow: pip install pillow; only for making the icon, not for running the app)

Design: a deep-green rounded square (the app's accent colour) with three rising white bars and an amber trend line:
a simple "dashboard going up" picture that stays readable down to 16 px.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
S = 1024  # draw large, then shrink for smooth edges


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # background: vertical gradient inside a rounded square
    top, bottom = (31, 107, 79), (10, 52, 38)
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        gd.line([(0, y), (S, y)], fill=lerp(top, bottom, y / S) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([24, 24, S - 24, S - 24], radius=210, fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    # soft highlight on the top edge
    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle([24, 24, S - 24, S // 2], radius=210, fill=(255, 255, 255, 22))
    hl.putalpha(Image.composite(hl.getchannel("A"), Image.new("L", (S, S), 0), mask))  # keep it inside the rounded square
    img = Image.alpha_composite(img, hl)
    d = ImageDraw.Draw(img)
    # three rising bars
    base, w, gap, x0 = 780, 150, 62, 196
    heights = [220, 360, 520]
    for i, h in enumerate(heights):
        x = x0 + i * (w + gap)
        d.rounded_rectangle([x, base - h, x + w, base], radius=34, fill=(255, 255, 255, 245 - i * 12))
    # amber trend line above the bars, with an arrow head
    pts = [(210, 560), (400, 430), (560, 470), (790, 250)]
    d.line(pts, fill=(255, 193, 59, 255), width=58, joint="curve")
    for p in pts:
        d.ellipse([p[0] - 29, p[1] - 29, p[0] + 29, p[1] + 29], fill=(255, 193, 59, 255))
    d.polygon([(830, 205), (700, 238), (800, 340)], fill=(255, 193, 59, 255))
    return img


def main() -> None:
    img = draw()
    out = ROOT / "app" / "assets"
    out.mkdir(parents=True, exist_ok=True)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    img.resize((256, 256), Image.LANCZOS).save(out / "tally_mis.ico", sizes=sizes)
    prev = ROOT / "docs" / "screenshots"
    prev.mkdir(parents=True, exist_ok=True)
    img.resize((256, 256), Image.LANCZOS).save(prev / "app-icon.png")
    print("wrote", out / "tally_mis.ico", "and", prev / "app-icon.png")


if __name__ == "__main__":
    main()
