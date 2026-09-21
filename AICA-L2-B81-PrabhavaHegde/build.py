"""
Build the single-file Windows executable.

    pip install -r requirements.txt
    python build.py

Output: dist/DPDP_Assessor.exe  (double-click to run; opens the browser)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
NAME = "DPDP_Assessor"

# Data read at runtime. PyInstaller cannot infer these from imports: a folder
# left out builds cleanly and then fails when the exe starts.
SEP = ";" if sys.platform == "win32" else ":"
DATA = [f"rules{SEP}rules", f"ui{SEP}ui", f"config.yaml{SEP}."]

# uvicorn loads parts of itself dynamically. Without these the exe builds
# cleanly and then fails at startup.
HIDDEN = [
    "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    # The app's own modules; demo_seed is imported only on first run.
    "ai_layer", "catalogue", "demo_seed", "models", "report", "role", "python_multipart",
]

# python-docx opens its default template from its own folder at report time.
COLLECT_DATA = ["docx"]

EXCLUDE = ["matplotlib", "numpy", "pandas", "tkinter", "google.generativeai", "anthropic", "openai"]


def main() -> None:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", NAME,
        "--onefile",
        "--noconfirm",
        "--clean",
        "--console",          # the console shows the address, the AI mode and any startup error
        "--log-level", "WARN",
        str(BASE / "app.py"),
    ]
    for d in DATA:
        cmd += ["--add-data", d]
    for h in HIDDEN:
        cmd += ["--hidden-import", h]
    for c in COLLECT_DATA:
        cmd += ["--collect-data", c]
    for e in EXCLUDE:
        cmd += ["--exclude-module", e]

    print(" ".join(cmd), "\n")
    code = subprocess.call(cmd, cwd=BASE)
    if code == 0:
        print(f"\nBuilt {BASE / 'dist' / (NAME + '.exe')}")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
