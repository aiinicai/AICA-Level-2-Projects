import os
import shutil
import zipfile
from pathlib import Path

source_app = Path(r"c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView")
github_dir = Path(r"C:\Users\ADMIN\Desktop\Capstone\Github")
extracted_app = github_dir / "FinstockEventScope"
how_to_run_file = github_dir / "HOW_TO_RUN.txt"

instructions_content = how_to_run_file.read_text(encoding="utf-8")

# Sync files to github_dir / FinstockEventScope
shutil.copy2(source_app / "Sample_Financial_Events.xlsx", extracted_app / "Sample_Financial_Events.xlsx")
shutil.copy2(source_app / "Sample_Financial_Events.csv", extracted_app / "Sample_Financial_Events.csv")
shutil.copy2(source_app / "data" / "eventscope.db", extracted_app / "data" / "eventscope.db")
shutil.copy2(how_to_run_file, extracted_app / "HOW_TO_RUN.txt")

zip_path = github_dir / "FinstockEventScope_Windows_Portable.zip"
print(f"Creating portable standalone ZIP: {zip_path}...")
base_folder = "FinstockEventScope"

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    # 1. Add instructions
    zf.writestr(f"{base_folder}/HOW_TO_RUN.txt", instructions_content)
    
    # 2. Add executable
    exe = extracted_app / "FinstockEventScope.exe"
    if exe.exists():
        zf.write(exe, f"{base_folder}/{exe.name}")
        print("Added FinstockEventScope.exe")
        
    # 3. Add Sample files
    for sample_file in ["Sample_Financial_Events.xlsx", "Sample_Financial_Events.csv", "README.md"]:
        p = extracted_app / sample_file
        if p.exists():
            zf.write(p, f"{base_folder}/{p.name}")
            print(f"Added {p.name}")
            
    # 4. Add data/eventscope.db
    db_file = extracted_app / "data" / "eventscope.db"
    if db_file.exists():
        zf.write(db_file, f"{base_folder}/data/eventscope.db")
        print(f"Added data/eventscope.db ({db_file.stat().st_size:,} bytes)")
        
    # 5. Add docs/
    docs_dir = extracted_app / "docs"
    if docs_dir.exists():
        for item in docs_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(extracted_app)
                zf.write(item, f"{base_folder}/{rel.as_posix()}")
        print("Added docs/")
        
    # 6. Add _internal/
    internal_dir = extracted_app / "_internal"
    if internal_dir.exists():
        count = 0
        for item in internal_dir.rglob("*"):
            if item.is_file() and "__pycache__" not in item.parts:
                rel = item.relative_to(extracted_app)
                zf.write(item, f"{base_folder}/{rel.as_posix()}")
                count += 1
        print(f"Added _internal/ ({count} files)")

print(f"ZIP archive created successfully! Size: {zip_path.stat().st_size:,} bytes")

# Verify ZIP integrity
with zipfile.ZipFile(zip_path, "r") as zf:
    bad = zf.testzip()
    if bad is None:
        print("ZIP integrity test PASSED: 100% clean archive.")
    else:
        print(f"ZIP corrupted at: {bad}")
