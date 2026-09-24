"""
CA IPO Compass — Desktop
Run with:  python main.py
"""
import sys
from pathlib import Path
PROJECT_DIR=Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / 'vendor'))


def main():
    if not getattr(sys, "frozen", False) and not (PROJECT_DIR/'app'/'webapp.py').exists():
        message=('CA IPO Compass cannot run from inside the ZIP preview.\n\n'
                 'Right-click the downloaded ZIP, choose Extract All, open the extracted '
                 'ca_ipo_compass folder, and run START_IPO_COMPASS.cmd again.')
        if sys.platform=='win32':
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0,message,'Extract CA IPO Compass first',0x30)
                return 2
            except Exception: pass
        print(message)
        return 2
    if '--classic' in sys.argv:
        from app.ui.compat_window import MainWindow
        window = MainWindow(auto_refresh='--no-refresh' not in sys.argv)
        window.mainloop()
    else:
        from app.webapp import main as open_dashboard
        open_dashboard(auto_refresh='--no-refresh' not in sys.argv)


if __name__ == "__main__":
    raise SystemExit(main() or 0)
