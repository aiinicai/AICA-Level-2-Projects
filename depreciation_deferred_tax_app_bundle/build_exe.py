#!/usr/bin/env python3
"""
Helper script to compile taxshield_ca_desktop.py into a single-file Windows .exe executable.
Run: python build_exe.py
"""
import subprocess
import sys

def main():
    print("Installing PyInstaller if needed...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("Building standalone executable TaxShield_CA_Depreciation_Suite.exe ...")
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "TaxShield_CA_Depreciation_Suite",
        "taxshield_ca_desktop.py"
    ])
    print("\nSUCCESS! Executable created in ./dist/TaxShield_CA_Depreciation_Suite.exe")

if __name__ == "__main__":
    main()
