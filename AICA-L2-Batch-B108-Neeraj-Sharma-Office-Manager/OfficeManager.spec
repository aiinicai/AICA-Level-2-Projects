# PyInstaller spec: run `pyinstaller OfficeManager.spec` on Windows.
from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("webview") + ["waitress", "cryptography.fernet"]
a = Analysis(["run_desktop.py"], datas=[("audit_manager/templates", "audit_manager/templates"), ("audit_manager/static", "audit_manager/static")],
             hiddenimports=hidden, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="OfficeManager", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="OfficeManager")
