# PyInstaller Spec for RealEstate360.exe (Standalone Desktop Executable)
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('web_dist', 'web_dist'),
        ('seed_dataset.json', '.'),
        ('../docs', 'docs'),
    ],
    hiddenimports=['PySide6.QtWebEngineWidgets', 'sqlite3', 'http.server'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RealEstate360',
    debug=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='RealEstate360',
)
