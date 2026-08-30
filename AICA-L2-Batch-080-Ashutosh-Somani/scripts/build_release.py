import os
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime

VERSION = "1.0.0"
RELEASE_NAME = f"BankStatementConverter_v{VERSION}"
ZIP_NAME = f"{RELEASE_NAME}.zip"

EXCLUDES = [
    ".git", ".venv", "__pycache__", ".pytest_cache", 
    "logs", "temp", "output", "data", "profiles",
    ".gitignore", "bump_version.py"
]

def should_exclude(path, root_dir):
    rel_path = Path(path).relative_to(root_dir)
    parts = rel_path.parts
    for ex in EXCLUDES:
        if ex in parts:
            return True
    if rel_path.name.endswith('.db') or rel_path.name.endswith('.sqlite'):
        return True
    if rel_path.name.endswith('.zip') and 'Backup' in rel_path.name:
        return True
    if rel_path.name == ZIP_NAME:
        return True
    return False

def hash_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def build_release():
    root = Path(__file__).parent.parent.resolve()
    zip_path = root / ZIP_NAME
    
    print(f"Building {ZIP_NAME}...")
    manifest_lines = [
        f"Bank Statement Converter v{VERSION}",
        f"Build Date: {datetime.now().isoformat()}",
        "\nIncluded Files and SHA-256 Checksums:\n"
    ]
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root_dir, dirs, files in os.walk(root):
            for file in files:
                file_path = Path(root_dir) / file
                if not should_exclude(file_path, root):
                    arcname = file_path.relative_to(root)
                    zf.write(file_path, arcname)
                    
                    if not arcname.name.endswith('.zip'):
                        manifest_lines.append(f"{hash_file(file_path)}  {arcname}")
        
        # Write manifest
        zf.writestr('manifest.txt', "\n".join(manifest_lines))
        
    print(f"Release built successfully at: {zip_path}")

if __name__ == "__main__":
    build_release()
