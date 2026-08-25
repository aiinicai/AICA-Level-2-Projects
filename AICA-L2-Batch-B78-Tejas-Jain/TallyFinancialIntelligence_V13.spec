# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ("Tally_Accounting_Extractor_Full_Financial_Rev13.py", "."),
    ("dashboard_server_v8.py", "."),
    ("dashboard", "dashboard"),
]
binaries=[]
hiddenimports=[]

# No Streamlit dependency is required by the CLIENT EXE.
# The extraction engine is imported directly and Tkinter provides the UI.
for package in ["pandas","openpyxl","pyodbc"]:
    try:
        d,b,h=collect_all(package)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

def uniq(items):
    seen=set(); out=[]
    for x in items:
        k=tuple(x) if isinstance(x,(list,tuple)) else x
        if k not in seen:
            seen.add(k); out.append(x)
    return out

datas=uniq(datas); binaries=uniq(binaries); hiddenimports=uniq(hiddenimports)

a=Analysis(
    ["Tally_Financial_Intelligence_Client_V12.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["streamlit"],
    noarchive=False,
)
pyz=PYZ(a.pure)
exe=EXE(
    pyz,a.scripts,[],exclude_binaries=True,
    name="TallyFinancialIntelligence",
    debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=True,
)
coll=COLLECT(
    exe,a.binaries,a.datas,strip=False,upx=False,upx_exclude=[],
    name="TallyFinancialIntelligence",
)
