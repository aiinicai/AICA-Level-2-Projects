"""
Draws the application icon (assets/app.ico + assets/app.png) with Pillow.
Run once before building:  python make_icon.py   (build_exe.bat does this).
Replace the two files with your own artwork if you prefer.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "assets"
S = 512                                   # draw large, scale down


def font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # vertical gradient navy -> blue inside a rounded square
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    top, bottom = (20, 48, 110), (30, 77, 183)
    for y in range(S):
        t = y / (S - 1)
        gd.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * t)
                                             for a, b in zip(top, bottom)) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([16, 16, S - 16, S - 16], radius=110,
                                           fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    # shield
    cx = S // 2
    shield = [(cx, 70), (cx + 150, 120), (cx + 140, 260), (cx, 370),
              (cx - 140, 260), (cx - 150, 120)]
    d.polygon(shield, fill=(255, 255, 255, 255))
    # green check mark
    d.line([(cx - 70, 215), (cx - 15, 275), (cx + 85, 160)],
           fill=(27, 122, 46, 255), width=42, joint="curve")
    # label
    f = font(92)
    text = "MSME"
    w = d.textlength(text, font=f)
    d.text((cx - w / 2, 385), text, font=f, fill=(255, 255, 255, 255))
    return img


def main():
    OUT.mkdir(exist_ok=True)
    img = draw()
    img.resize((256, 256), Image.LANCZOS).save(OUT / "app.png")
    img.save(OUT / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                                     (64, 64), (128, 128), (256, 256)])
    print(f"Icon written to {OUT}")


if __name__ == "__main__":
    main()
