from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_SCRIPT = ROOT / "net_asset_report.py"
DIST_DIR = ROOT / "dist"


def locate_tesseract() -> tuple[Path, Path]:
    configured = os.environ.get("TESSERACT_DIR", "").strip().strip('"')
    candidates = [Path(configured)] if configured else []
    candidates.extend([
        ROOT / "vendor_tesseract_env_5_5_3_try4",
        ROOT / "vendor_tesseract_5_5_3_conda",
        Path(r"C:\Program Files\Tesseract-OCR"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR",
    ])
    for candidate in candidates:
        if not str(candidate):
            continue
        exe = candidate if candidate.is_file() and candidate.name.lower() == "tesseract.exe" else candidate / "tesseract.exe"
        if not exe.is_file():
            nested = list(candidate.glob("**/tesseract.exe")) if candidate.exists() else []
            exe = next((item for item in nested if "tessdata" not in str(item).lower()), Path())
        if not exe.is_file():
            continue
        for data_dir in (
            exe.parent / "tessdata",
            exe.parent.parent / "tessdata",
            exe.parent.parent.parent / "share" / "tessdata",
            exe.parent.parent / "share" / "tessdata",
        ):
            if (data_dir / "eng.traineddata").is_file():
                return exe, data_dir
    raise FileNotFoundError(
        "Tesseract OCR with English data was not found. Install the Windows version once on this build PC, "
        "or set TESSERACT_DIR to its installation folder. The generated EXE will include it for users.\n"
        "Windows installer: https://github.com/UB-Mannheim/tesseract/wiki"
    )


def stage_runtime(exe: Path, tessdata: Path, stage: Path) -> tuple[list[str], list[str]]:
    runtime = stage / "networth_ocr"
    runtime.mkdir(parents=True, exist_ok=True)
    staged_exe = runtime / "tesseract.exe"
    shutil.copy2(exe, staged_exe)

    dlls: dict[str, Path] = {}
    for dll in exe.parent.rglob("*.dll"):
        if "tessdata" in (part.lower() for part in dll.parts):
            continue
        prior = dlls.get(dll.name.lower())
        if prior and prior.read_bytes() != dll.read_bytes():
            raise RuntimeError(f"Two different DLLs share the name {dll.name}; cannot build a safe bundle.")
        dlls[dll.name.lower()] = dll
    for dll in dlls.values():
        shutil.copy2(dll, runtime / dll.name)

    staged_data = runtime / "tessdata"
    staged_data.mkdir()
    for source in tessdata.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(tessdata)
        # Keep English recognition plus Tesseract's configuration resources.
        if relative.as_posix().lower() != "eng.traineddata" and relative.parts[0].lower() not in ("configs", "tessconfigs"):
            continue
        target = staged_data / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    if not (staged_data / "eng.traineddata").is_file():
        raise FileNotFoundError("The Tesseract installation has no tessdata/eng.traineddata file.")

    # Preserve any upstream license/notice files shipped with the selected Windows distribution.
    license_dir = stage / "ocr_licenses"
    license_dir.mkdir()
    for pattern in ("LICENSE*", "COPYING*", "NOTICE*"):
        for source in exe.parent.glob(pattern):
            if source.is_file():
                shutil.copy2(source, license_dir / source.name)
    notice = license_dir / "THIRD_PARTY_NOTICES.txt"
    if not any(license_dir.glob("LICENSE*")):
        notice.write_text(
            "Bundled OCR runtime: Tesseract OCR for Windows, distributed by UB Mannheim.\n"
            "Tesseract is licensed under Apache License 2.0; Leptonica uses a BSD license.\n"
            "Retain this notice and consult the upstream license and notices at:\n"
            "https://github.com/tesseract-ocr/tesseract\n"
            "https://github.com/UB-Mannheim/tesseract/wiki\n",
            encoding="utf-8")
    binaries = [str(staged_exe)] + [str(p) for p in runtime.glob("*.dll")]
    datas = [str(staged_data), str(license_dir)]
    return binaries, datas


def main() -> int:
    if os.name != "nt":
        print("Build this Windows EXE on Windows with Windows Python and Tesseract. Cross-building is not supported.", file=sys.stderr)
        return 1
    if not APP_SCRIPT.is_file():
        print(f"App source not found: {APP_SCRIPT}", file=sys.stderr)
        return 1
    if not importlib.util.find_spec("PyInstaller"):
        print("PyInstaller is missing. Install it with: python -m pip install pyinstaller", file=sys.stderr)
        return 1
    try:
        tesseract_exe, tessdata = locate_tesseract()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    DIST_DIR.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="networth_ocr_build_") as temp_name:
        temp = Path(temp_name)
        try:
            binaries, datas = stage_runtime(tesseract_exe, tessdata, temp)
        except Exception as exc:
            print(f"Could not prepare the Tesseract bundle: {exc}", file=sys.stderr)
            return 1
        runtime = temp / "networth_ocr"
        (temp / "spec").mkdir()
        command = [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--onefile", "--windowed", "--name", "NetAssetReport",
            "--distpath", str(DIST_DIR), "--workpath", str(temp / "work"),
            "--specpath", str(temp / "spec"), "--hidden-import", "fitz",
            "--collect-all", "pymupdf", "--collect-all", "reportlab",
            "--collect-all", "selenium", "--hidden-import", "PIL.ImageTk",
            "--hidden-import", "docx", "--hidden-import", "openpyxl.cell.rich_text",
            "--add-binary", f"{runtime / 'tesseract.exe'};networth_ocr",
        ]
        for dll in runtime.glob("*.dll"):
            command.extend(["--add-binary", f"{dll};networth_ocr"])
        command.extend(["--add-data", f"{runtime / 'tessdata'};networth_ocr/tessdata",
                        "--add-data", f"{temp / 'ocr_licenses'};networth_ocr/licenses",
                        str(APP_SCRIPT)])
        print("Building one-file EXE with bundled local OCR. This can take several minutes...")
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    output = DIST_DIR / "NetAssetReport.exe"
    if not output.is_file():
        print("PyInstaller finished without the expected EXE.", file=sys.stderr)
        return 1
    print(f"Built: {output}")
    print("The EXE contains Tesseract plus English OCR data; other computers do not need a separate OCR install.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
