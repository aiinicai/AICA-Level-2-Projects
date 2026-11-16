"""Create assets/app.ico (simple folder + magnifier mark)."""
import os
from PIL import Image, ImageDraw

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "app.ico")
os.makedirs(os.path.dirname(out), exist_ok=True)
S = 256
im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((16, 40, 240, 220), 28, fill=(37, 99, 235, 255))
d.rounded_rectangle((16, 22, 120, 70), 18, fill=(37, 99, 235, 255))
d.rounded_rectangle((30, 80, 226, 206), 18, fill=(219, 234, 254, 255))
for i, y in enumerate((104, 134, 164)):
    d.rectangle((52, y, 52 + 120 - i * 30, y + 14), fill=(37, 99, 235, 255))
d.ellipse((140, 120, 214, 194), outline=(30, 41, 59, 255), width=14)
d.line((200, 182, 238, 222), fill=(30, 41, 59, 255), width=18)
im.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(out)
