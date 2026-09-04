"""PyInstaller packaging script for building a standalone Windows application."""
import os
import subprocess
import sys
from pathlib import Path


def build_app():
    root = Path(__file__).resolve().parent
    run_script = root / "run.py"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ScheduleIIIRatioAnalyser",
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--paths={root}",
        str(run_script)
    ]
    
    print("Building application with PyInstaller...")
    print("Command:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(root))
    if result.returncode == 0:
        print("\nBuild completed successfully! Distributable folder located in dist/ScheduleIIIRatioAnalyser/")
    else:
        print(f"\nBuild failed with exit code: {result.returncode}")


if __name__ == "__main__":
    build_app()
