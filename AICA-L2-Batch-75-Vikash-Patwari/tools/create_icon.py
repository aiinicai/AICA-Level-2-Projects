"""Generate the multi-resolution Windows icon from the product's 45 mark."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int):
    candidates = [
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def main() -> None:
    output = Path("assets")
    output.mkdir(exist_ok=True)
    size = 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((36, 36, 988, 988), radius=220, fill="#12233A")
    draw.rounded_rectangle((92, 92, 932, 932), radius=180, fill="#0F766E")
    face = font(475)
    text = "45"
    box = draw.textbbox((0, 0), text, font=face)
    x = (size - (box[2] - box[0])) / 2
    y = (size - (box[3] - box[1])) / 2 - box[1] - 18
    draw.text((x, y), text, font=face, fill="white")
    image.save(output / "clock45.png", optimize=True)
    image.save(
        output / "clock45.ico", format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("Created assets\\clock45.ico and assets\\clock45.png")


if __name__ == "__main__":
    main()
