import shutil
from pathlib import Path

app_dir = Path(r"c:\Users\ADMIN\Desktop\Capstone\Application")
source_dir = app_dir / "source" / "FinstockEventScope"
dist_dir = source_dir / "dist" / "FinstockEventScope"
target_dir = app_dir / "FinstockEventScope-TradingView"

def safe_copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
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

def safe_copy_tree(src_dir: Path, dst_dir: Path):
    dst_dir.mkdir(parents=True, exist_ok=True)
    for item in src_dir.iterdir():
        if item.name == "data":
            # NEVER overwrite existing database
            continue
        dst_item = dst_dir / item.name
        if item.is_dir():
            safe_copy_tree(item, dst_item)
        else:
            safe_copy_file(item, dst_item)

print(f"Deploying built binary from {dist_dir} to {target_dir}...")
safe_copy_tree(dist_dir, target_dir)
print("Deployment completed successfully!")
