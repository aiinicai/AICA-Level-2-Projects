"""
capex_npv.launch_dashboard
===========================
Console-script entry point that launches the Streamlit dashboard
via `streamlit run`, so users can just type `capex-npv-dashboard`
instead of remembering the streamlit invocation.
"""

import sys
import subprocess
from pathlib import Path


def main():
    dashboard_path = Path(__file__).parent / "dashboard.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_path)])


if __name__ == "__main__":
    main()
