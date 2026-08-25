"""Ensure `src/` is importable for run_demo.py / run_web.py and ad-hoc scripts."""
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
