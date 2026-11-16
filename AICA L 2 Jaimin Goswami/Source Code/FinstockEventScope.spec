# Reproducible Windows onedir build; no API credentials or databases are bundled.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root=Path(SPECPATH)
datas=[(str(root/name),name) for name in ('migrations','assets','sample_data','docs')]
datas+=copy_metadata('windows-toasts')+copy_metadata('keyring')
hidden=collect_submodules('winrt')+['keyring.backends.Windows','windows_toasts','feedparser','tzdata','app.data_sources.finnhub']
a=Analysis([str(root/'launch.py')],pathex=[str(root)],binaries=[],datas=datas,hiddenimports=hidden,
 excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineQuick','PySide6.QtQml','PySide6.QtQuick','PySide6.QtQuickWidgets','PySide6.QtPdf','PySide6.QtPdfWidgets','PySide6.QtCharts','matplotlib','IPython','pytest'],noarchive=False)
# Qt on Windows 11 uses the operating system's ICU API. A different ICU DLL
# from a developer tool on PATH can be collected accidentally and break QtCore.
# Leave those OS APIs to Windows rather than redistributing a mismatched DLL.
a.binaries=[entry for entry in a.binaries if Path(entry[0]).name.lower() not in {'icuuc.dll','icudt78.dll'}]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='FinstockEventScope',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,icon=str(root/'assets/finstock.ico'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='FinstockEventScope')

