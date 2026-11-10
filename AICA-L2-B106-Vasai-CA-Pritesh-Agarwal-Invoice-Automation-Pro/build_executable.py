"""
Cross-Platform Standalone Desktop App Builder for CA Firm Invoice & Practice Automation Pro
Works on Windows (.exe), macOS (.app), and Linux.
"""
import sys
import subprocess
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent

def build_app():
    print("=" * 65)
    print(" CA Firm Invoice & Practice Automation Pro - Desktop App Builder")
    print("=" * 65)

    # 1. Install PyInstaller
    print("\n[1/3] Ensuring PyInstaller is installed...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "PyQt6", "reportlab", "openpyxl", "requests"])

    # 2. Build parameters
    print("\n[2/3] Compiling standalone desktop executable...")
    script_path = BASE / "ca_firm_invoice_automation_pro.py"
    icon_path = BASE / "app_icon.ico"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "CA_Firm_Invoice_Pro",
        "--clean",
        str(script_path)
    ]
    
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])
        sep = ";" if sys.platform == "win32" else ":"
        cmd.extend(["--add-data", f"{icon_path}{sep}."])
        png_path = BASE / "app_icon.png"
        if png_path.exists():
            cmd.extend(["--add-data", f"{png_path}{sep}."])

    # Hidden imports
    for mod in ["PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets", "reportlab", "openpyxl", "requests"]:
        cmd.extend(["--hidden-import", mod])

    # Run PyInstaller
    res = subprocess.run(cmd, cwd=str(BASE))
    
    if res.returncode == 0:
        print("\n" + "=" * 65)
        print(" SUCCESS! Standalone Desktop App Built Successfully!")
        print("=" * 65)
        dist_dir = BASE / "dist"
        if sys.platform == "win32":
            exe_file = dist_dir / "CA_Firm_Invoice_Pro.exe"
            print(f"\nStandalone Executable: {exe_file}")
            print("You can right-click 'CA_Firm_Invoice_Pro.exe' and select 'Send to -> Desktop (create shortcut)'.")
        elif sys.platform == "darwin":
            print(f"\nmacOS Application Bundle: {dist_dir / 'CA_Firm_Invoice_Pro.app'}")
        else:
            print(f"\nLinux Binary: {dist_dir / 'CA_Firm_Invoice_Pro'}")
    else:
        print("\n[ERROR] PyInstaller build encountered an error.")

if __name__ == "__main__":
    build_app()
