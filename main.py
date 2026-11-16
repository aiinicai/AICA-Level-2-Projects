"""Smart Billing Manager launcher: installs missing dependencies only."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
sys.path.insert(0, str(BASE/'.vendor'))

def bootstrap():
    def available(module):
        try: return importlib.util.find_spec(module) is not None
        except ModuleNotFoundError: return False
    missing = not all(available(module) for module in ['PyQt6.QtWidgets','pymupdf','reportlab','cryptography'])
    if missing:
        if getattr(sys,'frozen',False):
            raise RuntimeError('Packaged dependencies are missing. Rebuild the executable.')
        print('First run: installing required libraries. Internet is needed for this step only.',flush=True)
        subprocess.check_call([sys.executable,'-m','pip','install','--upgrade','--target',str(BASE/'.vendor'),'-r',str(BASE/'requirements.txt')])
        importlib.invalidate_caches()

if __name__ == '__main__':
    try:
        bootstrap()
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from gui import MainWindow
        app = QApplication(sys.argv)
        app.setApplicationName('Smart Billing Manager')
        if '--self-test' in sys.argv:
            from packaged_smoke import run
            run(app,sys.argv[sys.argv.index('--self-test')+1])
            sys.exit(0)
        # A single writer prevents accidental invoice number collisions.
        from PyQt6.QtCore import QLockFile
        (BASE/'database').mkdir(exist_ok=True)
        lock = QLockFile(str(BASE/'database'/'application.lock'))
        if not lock.tryLock(100):
            QMessageBox.warning(None,'Already open','Smart Billing Manager is already running in this folder.')
            sys.exit(0)
        window = MainWindow(BASE)
        window.show()
        sys.exit(app.exec())
    except Exception as exc:
        print('Unable to start:',exc)
        if 'QApplication' in globals() and QApplication.instance():
            QMessageBox.critical(None,'Startup error',str(exc))
        else:
            input('Press Enter to close...')
        sys.exit(1)
