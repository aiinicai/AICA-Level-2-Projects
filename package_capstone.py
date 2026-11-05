"""
What's cooking today? - Capstone Packaging Script
Creates a clean, production-ready ZIP archive of the project for Google Drive / submission.
"""
import zipfile
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_ZIP = BASE_DIR / "Whats_Cooking_Today_Capstone.zip"

EXCLUDE_DIRS = {"__pycache__", ".venv", "env", "venv", "staticfiles", ".git"}
EXCLUDE_FILES = {"Whats_Cooking_Today_Capstone.zip", "Khane_Mein_Kya_Hain_Capstone.zip"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".log"}

def package():
    print("Packaging Capstone Project...")
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if f in EXCLUDE_FILES or any(f.endswith(ext) for ext in EXCLUDE_EXTS):
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, BASE_DIR)
                zipf.write(full_path, rel_path)
    
    size_kb = os.path.getsize(OUTPUT_ZIP) / 1024
    print(f"SUCCESS: Created {OUTPUT_ZIP.name} ({size_kb:.1f} KB)")
    print(f"Location: {OUTPUT_ZIP}")

if __name__ == "__main__":
    package()
