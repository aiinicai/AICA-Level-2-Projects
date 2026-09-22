"""One-off script to generate PWA icon PNGs matching the app's navy/gold brand."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = os.path.dirname(__file__)
NAVY = (11, 31, 58)
GOLD = (201, 162, 39)
GOLD2 = (232, 208, 138)


def font(size):
    for name in ["arialbd.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_icon(size, path, maskable=False):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # maskable icons need a "safe zone" - keep the visual mark within ~80% of canvas
    pad = int(size * 0.1) if maskable else 0
    corner = int(size * 0.22)
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=corner, fill=NAVY)
    # gold accent bar
    bar_h = max(2, int(size * 0.06))
    d.rectangle([pad, size - pad - bar_h * 3, size - pad, size - pad - bar_h * 2], fill=GOLD)
    # "CA" mark centered
    f = font(int(size * 0.36))
    text = "CA"
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1] - size * 0.04), text, font=f, fill=GOLD2)
    img.save(path)


if __name__ == "__main__":
    make_icon(192, os.path.join(OUT_DIR, "icon-192.png"))
    make_icon(512, os.path.join(OUT_DIR, "icon-512.png"))
    make_icon(512, os.path.join(OUT_DIR, "icon-maskable-512.png"), maskable=True)
    make_icon(180, os.path.join(OUT_DIR, "apple-touch-icon.png"))
    print("Generated icons in", OUT_DIR)
