import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

LOGOS_DIR = Path(__file__).resolve().parent / "backend" / "uploads" / "logos"
LOGOS_DIR.mkdir(parents=True, exist_ok=True)

def create_tata_logo():
    # Crisp Tata Logo (Classic Blue rounded shield with T icon and TATA typography)
    width, height = 400, 140
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Blue color: #005696 / #004B87
    blue = "#004B87"
    
    # Draw stylized T logo icon on the left
    draw.rounded_rectangle([(10, 10), (120, 120)], radius=20, fill=blue)
    
    # Stylized T in white
    # Top bar
    draw.rounded_rectangle([(25, 30), (105, 52)], radius=5, fill="white")
    # Center stem
    draw.rounded_rectangle([(54, 50), (76, 105)], radius=5, fill="white")
    # Inner curves / accent lines
    draw.line([(35, 65), (50, 95)], fill="white", width=4)
    draw.line([(95, 65), (80, 95)], fill="white", width=4)

    # Draw TATA text on right
    try:
        font_tata = ImageFont.truetype("arialbd.ttf", 52)
        font_sub = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_tata = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((145, 28), "TATA", fill=blue, font=font_tata)
    draw.text((148, 85), "LEADERSHIP WITH TRUST", fill="#64748B", font=font_sub)

    out_path = LOGOS_DIR / "tata_logo.png"
    img.save(out_path, format="PNG")
    print(f"Created Tata logo at {out_path}")

def create_reliance_logo():
    # Crisp Reliance Industries Logo (Iconic red/blue globe/flame and RELIANCE typography)
    width, height = 400, 140
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Colors: Navy #0A2540, Red #E11D48
    navy = "#0B2545"
    crimson = "#D9222A"

    # Draw Emblem icon
    draw.ellipse([(15, 15), (115, 115)], fill=navy)
    draw.pieslice([(15, 15), (115, 115)], start=30, end=150, fill=crimson)
    draw.ellipse([(35, 35), (95, 95)], fill="white")
    draw.ellipse([(45, 45), (85, 85)], fill=navy)

    # Text
    try:
        font_rel = ImageFont.truetype("arialbd.ttf", 44)
        font_sub = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_rel = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((135, 32), "Reliance", fill=navy, font=font_rel)
    draw.text((138, 85), "Industries Limited • Growth is Life", fill="#64748B", font=font_sub)

    out_path = LOGOS_DIR / "reliance_logo.png"
    img.save(out_path, format="PNG")
    print(f"Created Reliance logo at {out_path}")

if __name__ == "__main__":
    create_tata_logo()
    create_reliance_logo()
