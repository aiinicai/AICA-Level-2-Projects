import subprocess
import sys
import os

def install_pyinstaller():
    """Checks for PyInstaller and installs it if missing."""
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("PyInstaller is missing. Installing it now...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller installed successfully.")
        except Exception as e:
            print(f"Failed to install PyInstaller: {e}")
            sys.exit(1)

def build():
    install_pyinstaller()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_file = os.path.join(base_dir, "main.py")
    
    print("Initiating PyInstaller build process...")
    
    # PyInstaller arguments
    # --onefile: single EXE
    # --noconsole: hide prompt window
    # --clean: clean cache directories before building
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name=PuruNiti_Smart_Billing_system",
        main_file
    ]
    
    try:
        subprocess.check_call(cmd)
        print("\n" + "="*50)
        print("BUILD SUCCESSFUL!")
        print("Standalone Executable: dist/PuruNiti_Smart_Billing_system.exe")
        print("="*50 + "\n")
    except Exception as e:
        print(f"Build failed: {e}")

if __name__ == "__main__":
    build()
