"""One-command launcher: creates a virtual environment on first run, installs requirements, starts the app.
Usage:  python run.py"""
import os
import subprocess
import sys

root = os.path.dirname(os.path.abspath(__file__))
venv = os.path.join(root, '.venv')
py = os.path.join(venv, 'Scripts' if os.name == 'nt' else 'bin', 'python')
if not os.path.exists(py):
    print('First run: creating virtual environment and installing requirements…')
    subprocess.check_call([sys.executable, '-m', 'venv', venv])
    subprocess.check_call([py, '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.check_call([py, '-m', 'pip', 'install', '-r', os.path.join(root, 'requirements.txt')])
os.chdir(root)
sys.exit(subprocess.call([py, '-m', 'ifrs16lessee'] + sys.argv[1:]))
