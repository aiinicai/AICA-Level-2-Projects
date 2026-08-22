# pdf_studio_pro.spec
# Build with:  pyinstaller pdf_studio_pro.spec
#
# This spec exists (instead of a plain one-line pyinstaller command) because
# pyhanko/cryptography pull in submodules dynamically that PyInstaller's
# static analysis can miss. collect_all() forces those in explicitly so the
# built .exe doesn't fail at runtime on a teammate's PC with an
# ImportError that never showed up on the build machine.

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    "pycparser.lextab",
    "pycparser.yacctab",
    "PyQt5.sip",
]

for pkg in ("pyhanko", "asn1crypto", "oscrypto", "cryptography", "pyhanko_certvalidator"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ["pdf_studio_pro_v2.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PDF Studio Pro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # no black terminal window behind the app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="app_icon.ico",   # uncomment and add a .ico file if you want a custom icon
)
