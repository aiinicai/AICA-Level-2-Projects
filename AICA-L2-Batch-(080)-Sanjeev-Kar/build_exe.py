"""
build_exe.py
-------------
Builds a standalone Windows .exe for Folder Lock using PyInstaller.

This is a BUILD-TIME script, not something end users run. It must be run
in an environment that already has every runtime dependency installed
(see requirements.txt) — PyInstaller can only bundle what is actually
importable in the environment it runs in. `bootstrap.py`'s first-run
auto-installer is for end users running the app from source
(`python main.py`); once frozen into an .exe by this script, bootstrap.py
detects it is running frozen and does nothing (see bootstrap._is_frozen()).

Usage:
    pip install -r requirements.txt
    pip install pyinstaller
    python build_exe.py

Output:
    dist/FolderLock/FolderLock.exe   (a --onedir build — more reliable
    than --onefile for OpenCV's native binaries, and starts faster).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "FolderLock"
ENTRY_POINT = "main.py"


def main() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. Run: pip install pyinstaller", file=sys.stderr)
        sys.exit(1)

    missing_runtime = []
    for module_name in ("cryptography", "argon2", "numpy", "PIL", "cv2"):
        try:
            __import__(module_name)
        except ImportError:
            missing_runtime.append(module_name)
    if missing_runtime:
        print(
            "Cannot build: the following runtime packages are not installed "
            f"in THIS environment: {', '.join(missing_runtime)}\n"
            "Install them first (pip install -r requirements.txt), then re-run this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    import cv2
    if not hasattr(cv2, "face") or not hasattr(cv2.face, "LBPHFaceRecognizer_create"):
        print(
            "Cannot build: the installed OpenCV is missing the 'face' (contrib) module.\n"
            "Install the contrib build: pip uninstall opencv-python -y && "
            "pip install opencv-contrib-python",
            file=sys.stderr,
        )
        sys.exit(1)

    project_dir = Path(__file__).resolve().parent
    resources_dir = project_dir / "resources"
    if not (resources_dir / "haarcascade_frontalface_default.xml").exists():
        print(f"Cannot build: missing {resources_dir}/haarcascade_frontalface_default.xml", file=sys.stderr)
        sys.exit(1)

    dist_dir = project_dir / "dist"
    build_dir = project_dir / "build"
    spec_file = project_dir / f"{APP_NAME}.spec"
    for stale in (dist_dir, build_dir):
        if stale.exists():
            shutil.rmtree(stale)
    if spec_file.exists():
        spec_file.unlink()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",              # GUI app: no console window
        "--onedir",                # reliable for OpenCV's native libs
        "--noconfirm",
        "--collect-all", "cv2",
        "--hidden-import", "PIL._tkinter_finder",
        "--add-data", f"{resources_dir}{';' if sys.platform == 'win32' else ':'}resources",
        str(project_dir / ENTRY_POINT),
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(project_dir))
    if result.returncode != 0:
        print("PyInstaller build failed.", file=sys.stderr)
        sys.exit(result.returncode)

    exe_path = dist_dir / APP_NAME / f"{APP_NAME}.exe"
    print(f"\nBuild complete: {exe_path}")
    print("Copy the whole 'dist/FolderLock' folder when distributing — the .exe depends on the files next to it.")


if __name__ == "__main__":
    main()
