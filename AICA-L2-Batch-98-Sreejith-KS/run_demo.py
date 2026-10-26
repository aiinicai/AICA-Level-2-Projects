"""
Launcher for the Trial Balance demo.
Save this file in the same folder as tb_demo_app.py, then run it:
    python run_demo.py
(or double-click it if .py files open with Python on your computer)
"""
import os
import subprocess
import sys

folder = os.path.dirname(os.path.abspath(__file__))
os.chdir(folder)

print("Checking what the demo needs (first time only)...")
subprocess.call([sys.executable, "-m", "pip", "install", "-q",
                 "streamlit", "pandas", "requests", "openpyxl"])

print("Starting the demo. Your browser will open in a few seconds.")
print("To stop it, close this window or press Ctrl+C.")
subprocess.call([sys.executable, "-m", "streamlit", "run", "tb_demo_app.py"])
input("Press Enter to close...")
