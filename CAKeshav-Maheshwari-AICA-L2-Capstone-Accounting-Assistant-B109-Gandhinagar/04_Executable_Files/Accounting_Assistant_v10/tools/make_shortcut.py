"""Creates a Desktop shortcut 'Accounting Assistant' that starts the app without a console window.
Run once from the project folder:  python tools/make_shortcut.py
(Uses pythonw.exe, which is signed by the Python Software Foundation, so Smart App Control allows it.)"""
import os
import subprocess
import sys
from pathlib import Path

project = Path(__file__).resolve().parent.parent
pyw = Path(sys.executable).with_name("pythonw.exe")
if not pyw.exists():
    pyw = Path(sys.executable)
sys.path.insert(0, str(project))
from app.config import desktop_dir  # noqa: E402
desktop = desktop_dir()
lnk = desktop / "Accounting Assistant.lnk"
icon = project / "app_icon.ico"
try:                                            # the app's own icon for the Desktop shortcut
    from PyQt6.QtWidgets import QApplication
    _qa = QApplication.instance() or QApplication([])
    from app.ui.theme import save_icon_file
    save_icon_file(icon)
except Exception:
    pass
icon_ps = f"$s.IconLocation='{icon},0';" if icon.exists() else ""
ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
      f"$s.TargetPath='{pyw}';$s.Arguments='-m app.main';$s.WorkingDirectory='{project}';"
      f"$s.Description='Accounting Assistant';{icon_ps}$s.Save()")
r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True)
print(f"Shortcut created: {lnk}" if r.returncode == 0 else f"Could not create shortcut: {r.stderr}")

# One-click launchers in the project folder. They are written on this PC, not downloaded,
# so Windows does not mark them as coming from the internet.
py = Path(sys.executable)
launchers = {
    "Start Accounting Assistant.bat":
        f'@echo off\r\ncd /d "{project}"\r\nstart "" "{pyw}" -m app.main\r\n',
    "Check setup.bat":
        f'@echo off\r\ncd /d "{project}"\r\n"{py}" tools\\check_env.py\r\necho.\r\npause\r\n',
}
for name, body in launchers.items():
    enc = "mbcs" if os.name == "nt" else "utf-8"   # ANSI code page, which is what cmd.exe expects
    (project / name).write_text(body, encoding=enc, newline="")
    print(f"Created: {project / name}")
