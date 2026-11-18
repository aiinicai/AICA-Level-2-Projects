"""Draws app.ico: navy rounded square with 'GST' in white."""
import sys
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1]
S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=48, fill=(31, 56, 100, 255))
try:
    font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 92)
except OSError:
    font = ImageFont.load_default()
box = d.textbbox((0, 0), "GST", font=font)
w, h = box[2] - box[0], box[3] - box[1]
d.text(((S - w) / 2 - box[0], (S - h) / 2 - box[1] - 14), "GST", font=font, fill="white")
d.rounded_rectangle([60, 178, S - 60, 190], radius=6, fill=(21, 128, 61, 255))
img.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
