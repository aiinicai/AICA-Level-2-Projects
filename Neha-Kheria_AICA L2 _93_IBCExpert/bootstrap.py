"""Standalone first-run dependency setup entry point."""
from pathlib import Path

from app.core.bootstrap_ui import run_bootstrap_progress


if __name__ == "__main__":
    run_bootstrap_progress(Path(__file__).resolve().parent)
    print("Dependency setup completed successfully.")
