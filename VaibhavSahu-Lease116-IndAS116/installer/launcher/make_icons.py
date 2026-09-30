"""Build the launcher icons (classic BMP entries with AND masks, readable by every Windows icon API)."""
import struct
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "app" / "static" / "img" / "lease116.png"


def _entry(img: Image.Image, size: int) -> bytes:
    im = img.resize((size, size), Image.LANCZOS).convert("RGBA")
    px = im.load()
    xor = bytearray()
    for y in range(size - 1, -1, -1):                     # bottom-up rows, BGRA
        for x in range(size):
            r, g, b, a = px[x, y]
            xor += bytes((b, g, r, a))
    row = ((size + 31) // 32) * 4                           # 1-bpp mask rows padded to 32 bits
    mask = bytearray()
    for y in range(size - 1, -1, -1):
        bits = bytearray(row)
        for x in range(size):
            if px[x, y][3] == 0:                            # fully transparent → mask bit set
                bits[x // 8] |= 0x80 >> (x % 8)
        mask += bits
    hdr = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, len(xor) + len(mask), 0, 0, 0, 0)
    return hdr + bytes(xor) + bytes(mask)


def write_ico(path: Path, sizes: list[int]) -> None:
    img = Image.open(SRC).convert("RGBA")
    blobs = [_entry(img, s) for s in sizes]
    out = bytearray(struct.pack("<HHH", 0, 1, len(sizes)))
    off = 6 + 16 * len(sizes)
    for s, b in zip(sizes, blobs):
        out += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(b), off)
        off += len(b)
    for b in blobs:
        out += b
    path.write_bytes(bytes(out))


if __name__ == "__main__":
    write_ico(HERE / "lease116_launcher.ico", [16, 20, 24, 32, 40, 48, 64, 256])   # exe / shortcut icon
    write_ico(HERE / "lease116_tray.ico", [16, 20, 24, 32, 40, 48])                # notification-area icon
    for f in ("lease116_launcher.ico", "lease116_tray.ico"):
        print(f, (HERE / f).stat().st_size, "bytes")
