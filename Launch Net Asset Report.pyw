"""No-console launcher that always uses the project virtual environment."""
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
venv_python=root/'.venv'/'Scripts'/'pythonw.exe'
if venv_python.exists() and Path(sys.executable).resolve()!=venv_python.resolve():
    subprocess.Popen([str(venv_python),str(root/'net_asset_report.py')],cwd=str(root))
    raise SystemExit

from net_asset_report import App
App().mainloop()
