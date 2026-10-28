"""Installer helper: copies files to %USERPROFILE%\\RedactIn60 and makes a Desktop shortcut.
Brings over your rules.xlsx / prompt from an older 'NoticeRedactor' install (the old folder is left untouched)."""
import os, sys, json, shutil, subprocess
from pathlib import Path

APP_NAME = "RedactIn60"
here = Path(__file__).parent
app = Path.home() / APP_NAME
old = Path.home() / "NoticeRedactor"
app.mkdir(exist_ok=True)

for f in ("redactor_core.py", "redactor_gui.pyw"):
    shutil.copy2(here / f, app / f)

# keep the user's own files; bring them over from the old install the first time
for name in ("rules.xlsx", "prompt_fixed.txt"):
    if not (app / name).exists():
        if (old / name).exists():
            shutil.copy2(old / name, app / name)
        elif name == "rules.xlsx":
            shutil.copy2(here / name, app / name)

# the saved settings may still point at the old folder's rules file
cfg = Path.home() / ".notice_redactor.json"
try:
    c = json.loads(cfg.read_text())
    if str(c.get("rules", "")).lower().startswith(str(old).lower()):
        c["rules"] = str(app / Path(c["rules"]).name)
        cfg.write_text(json.dumps(c))
except Exception:
    pass

pyw = Path(sys.executable).with_name("pythonw.exe")
target = str(pyw if pyw.exists() else sys.executable)
gui = str(app / "redactor_gui.pyw")

ps = (
    "$d=[Environment]::GetFolderPath('Desktop');"
    "$old=$d+'\\Notice Redactor.lnk'; if (Test-Path $old) { Remove-Item $old };"
    f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut($d+'\\{APP_NAME}.lnk');"
    f"$s.TargetPath='{target}';"
    f"$s.Arguments='\"{gui}\"';"
    f"$s.WorkingDirectory='{app}';"
    "$s.Save()"
)
try:
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    print(f"Desktop shortcut created: {APP_NAME}")
except Exception as e:
    print("Could not create shortcut automatically:", e)
    print("Run this file manually:", gui)
print("Installed in:", app)
