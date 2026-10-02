"""
Build the ICAI submission folder (and a ZIP backup) from the committed files.

Usage:  python tools/build_submission.py <BatchNo> <Name> <Surname>
        -> E:/AICA project/submission/AICA-L2-Batch-<BatchNo>-<Name>-<Surname>/  and  <same>.zip
           and submission/upload_batches/1..n/ (the same folder in parts of < 100 files, for GitHub's browser upload)

Checks, and refuses to finish if any fails (ICAI Annexure D, GitHub limits, public-safety):
  * only committed files (git ls-files); dev-only files excluded; no .env, cache, logs or AMC spreadsheets
  * every file < 25 MiB (GitHub web upload), total < 100 MB (ICAI Ver 3.0 ZIP limit)
  * no personal identifiers or secrets in any text file
"""
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_BASE = ROOT.parent / "submission"
EXCLUDE = (".claude/",)
BANNED = re.compile(r"ssrathi|cassrathi|shrikant26|LOOKTHROUGH_N8N_TOKEN=[A-Za-z0-9_-]{30,}|BEGIN [A-Z ]*PRIVATE KEY|sk-ant-|AKIA[0-9A-Z]{16}", re.I)
SELF = "tools/build_submission.py"  # holds the patterns themselves


def main(batch, name, surname):
    if not re.fullmatch(r"\d{1,4}", batch):
        raise SystemExit("Batch number must be numeric (as on the ICAI form).")
    folder = f"AICA-L2-Batch-{batch}-{name.strip().title()}-{surname.strip().title()}"
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        raise SystemExit("Uncommitted changes - commit first so the package matches the repository.")
    files = [f for f in subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
             if not f.startswith(EXCLUDE)]
    dest = OUT_BASE / folder
    if dest.exists():
        shutil.rmtree(dest)
    problems, total = [], 0
    for f in files:
        src = ROOT / f
        size = src.stat().st_size
        total += size
        if size >= 25 * 1024 * 1024:
            problems.append(f"{f}: {size / 2**20:.1f} MiB (GitHub web upload limit is 25 MiB)")
        if f == ".env" or f.startswith(("data/cache/", "data/live/", "logs/")) and not f.endswith("_README.txt"):
            problems.append(f"{f}: must not be submitted")
        if f != SELF and (src.suffix.lower() in (".py", ".js", ".ts", ".md", ".json", ".txt", ".csv", ".bat", ".html", ".css", ".example", ".sh") or src.name.startswith(".")):
            text = src.read_text(encoding="utf-8", errors="ignore")
            if BANNED.search(text):
                problems.append(f"{f}: contains a personal identifier or secret ({BANNED.search(text).group(0)[:20]}...)")
        (dest / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / f)
    if total >= 100 * 1000 * 1000:
        problems.append(f"total {total / 1e6:.1f} MB exceeds 100 MB")
    if problems:
        shutil.rmtree(dest)
        raise SystemExit("NOT BUILT:\n  " + "\n  ".join(problems))
    zpath = OUT_BASE / f"{folder}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(dest / f, f"{folder}/{f}")
    print(f"Built {dest}\n  {len(files)} files, {total / 1e6:.2f} MB; ZIP {zpath.stat().st_size / 1e6:.2f} MB")
    print("  largest:", sorted(((ROOT / f).stat().st_size, f) for f in files)[-3:])
    # GitHub's browser upload takes fewer than 100 files per drop. Each batch holds the same top folder, so dropping the
    # batches one after another (at the fork's root) builds one folder. Units are top-level folders; a unit too big for
    # one batch is split by its sub-folders.
    LIMIT = 95
    units: dict[str, list[str]] = {}
    for f in files:
        parts = f.split("/")
        units.setdefault(parts[0] if len(parts) > 1 else "(root files)", []).append(f)
    for k in [k for k, v in units.items() if len(v) > LIMIT]:
        for f in units.pop(k):
            units.setdefault("/".join(f.split("/")[:2]), []).append(f)
    if any(len(v) > LIMIT for v in units.values()):
        raise SystemExit("A folder has more than 95 files even after splitting; upload with git instead.")
    batches: list[list[str]] = []
    for k in sorted(units, key=lambda k: -len(units[k])):
        b = next((b for b in batches if len(b) + len(units[k]) <= LIMIT), None)
        if b is None:
            batches.append(list(units[k]))
        else:
            b.extend(units[k])
    up = OUT_BASE / "upload_batches"
    if up.exists():
        shutil.rmtree(up)
    for i, b in enumerate(batches, 1):
        for f in b:
            (up / str(i) / folder / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest / f, up / str(i) / folder / f)
    assert sum(len(b) for b in batches) == len(files)
    print(f"  GitHub browser upload: {len(batches)} batches in {up} ({', '.join(str(len(b)) for b in batches)} files); "
          f"drop the {folder} folder from each numbered batch in turn")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
