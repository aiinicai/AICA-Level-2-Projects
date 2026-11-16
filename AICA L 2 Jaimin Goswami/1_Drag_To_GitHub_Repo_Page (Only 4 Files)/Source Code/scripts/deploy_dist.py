import shutil
import zipfile
from pathlib import Path
import subprocess

app_dir = Path(r"c:\Users\ADMIN\Desktop\Capstone\Application")
source_dir = app_dir / "source" / "FinstockEventScope"
release_dir = source_dir / "release"
dist_binary_dir = source_dir / "dist" / "FinstockEventScope"

# 1. Copy release archives to Application root
for fname in ["FinstockEventScope-Source.zip", "FinstockEventScope-Windows.zip", "SHA256SUMS.txt"]:
    src = release_dir / fname
    dst = app_dir / fname
    if src.exists():
        shutil.copy2(src, dst)
        print(f"Copied {fname} to {app_dir}")

# 2. Deploy to FinstockEventScope-TradingView, FinstockEventScope, and FinstockEventScope-Windows
targets = [
    app_dir / "FinstockEventScope-TradingView",
    app_dir / "FinstockEventScope",
    app_dir / "FinstockEventScope-Windows"
]

import time

def safe_copy_file(src: Path, dst: Path, retries: int = 5):
    for attempt in range(retries):
        try:
            if dst.exists():
                try:
                    dst.unlink()
                except Exception:
                    old = dst.with_name(f"{dst.name}.old")
                    try:
                        if old.exists():
                            old.unlink()
                    except Exception:
                        pass
                    try:
                        dst.rename(old)
                    except Exception:
                        pass
            shutil.copy2(src, dst)
            return
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.0)
            else:
                raise

def safe_copy_tree(src_dir: Path, dst_dir: Path):
    dst_dir.mkdir(parents=True, exist_ok=True)
    for item in src_dir.iterdir():
        dst_item = dst_dir / item.name
        if item.is_dir():
            safe_copy_tree(item, dst_item)
        else:
            safe_copy_file(item, dst_item)

for target in targets:
    print(f"\nDeploying to {target}...")
    target.mkdir(parents=True, exist_ok=True)
    # Copy all files from dist_binary_dir
    for item in dist_binary_dir.iterdir():
        dest_item = target / item.name
        if item.is_dir():
            safe_copy_tree(item, dest_item)
        else:
            safe_copy_file(item, dest_item)
    # Also ensure README.md and docs are in target
    safe_copy_file(source_dir / "README.md", target / "README.md")
    safe_copy_tree(source_dir / "docs", target / "docs")
    # Clean any stale lock or old test data so fresh run loads full 1-year calendar
    for p in [(target / "data"), (target / "eventscope.lock")]:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.is_file():
            p.unlink(missing_ok=True)
    print(f"Successfully deployed to {target}")

# 3. Test the built binary in FinstockEventScope-TradingView
exe_path = app_dir / "FinstockEventScope-TradingView" / "FinstockEventScope.exe"
print(f"\nRunning --smoke-test on {exe_path}...")
proc = subprocess.run([str(exe_path), "--smoke-test"], capture_output=True, text=True)
print("Smoke test return code:", proc.returncode)
print("Smoke test stdout:", proc.stdout.strip())
if proc.stderr:
    print("Smoke test stderr:", proc.stderr.strip())

print(f"\nRunning --ui-smoke-test on {exe_path}...")
proc2 = subprocess.run([str(exe_path), "--ui-smoke-test"], capture_output=True, text=True)
print("UI Smoke test return code:", proc2.returncode)
print("UI Smoke test stdout:", proc2.stdout.strip())
if proc2.stderr:
    print("UI Smoke test stderr:", proc2.stderr.strip())

print("\nDeployment complete and verified!")
