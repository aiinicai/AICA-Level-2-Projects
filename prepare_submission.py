"""Validate the project against the ICAI AICA GitHub submission rules and build a zip.
Usage:  python prepare_submission.py "Your-Name"      (renames output folder to Your-Name-AI-CFO-Enterprise-Platform)
Rules checked: one clearly named folder, README.md present, no .git, no file > 100 MB, < 100 files per upload batch.
"""
import os, shutil, sys, zipfile, pathlib

SKIP = {"__pycache__", ".venv", ".git", ".pytest_cache", ".DS_Store"}
here = pathlib.Path(__file__).resolve().parent
name = (sys.argv[1] if len(sys.argv) > 1 else "YourName").strip().replace(" ", "-")
out_dir = here.parent / f"{name}-AI-CFO-Enterprise-Platform"
if out_dir.exists():
    shutil.rmtree(out_dir)
shutil.copytree(here, out_dir, ignore=lambda d, fs: [f for f in fs if f in SKIP or f.endswith(".pyc")])
files = [p for p in out_dir.rglob("*") if p.is_file()]
problems = []
if not (out_dir / "README.md").exists(): problems.append("README.md missing")
if any(".git" in p.parts for p in files): problems.append(".git folder present")
big = [p for p in files if p.stat().st_size > 100 * 1024 * 1024]
if big: problems.append(f"files over 100 MB: {big}")
n = len(files)
print(f"Folder: {out_dir.name}\nFiles: {n}  Size: {sum(p.stat().st_size for p in files)/1e6:.1f} MB")
if n >= 100:
    print("NOTE: 100+ files. GitHub web upload takes <100 files at a time - upload in batches (data_generator/, cfo_system/, views/, knowledge_base/, sample_data/, docs/ ...) or use the zip + git push.")
print("OK - ready for submission" if not problems else "PROBLEMS: " + "; ".join(problems))
z = out_dir.parent / f"{out_dir.name}.zip"
with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in files:
        zf.write(p, pathlib.Path(out_dir.name) / p.relative_to(out_dir))
print("Zip:", z)
