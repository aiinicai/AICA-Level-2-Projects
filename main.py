"""BreakBuddy Pro v4.0 - run with:  python main.py   (Windows: double-click run_windows.bat)"""
import sys

try:
    from breakbuddy.app import App
except ModuleNotFoundError as ex:
    if "tkinter" in str(ex):
        print("tkinter is missing. Windows/Mac: reinstall Python from python.org. "
              "Ubuntu/Debian: sudo apt install python3-tk")
        sys.exit(1)
    raise

if __name__ == "__main__":
    App().run()
