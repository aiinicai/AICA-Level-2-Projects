# -*- mode: python ; coding: utf-8 -*-
# Size-optimised PyInstaller recipe for IPO_Tracker (target: EXE under 25 MB).
# Build with:  python -m PyInstaller IPO_Tracker.spec --noconfirm --clean
import re

EXCLUDES = ['lxml', 'cryptography', 'OpenSSL', 'chardet', 'tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'unittest', 'pydoc',
            'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngine', 'PyQt5.QtWebChannel',
            'PyQt5.QtMultimedia', 'PyQt5.QtMultimediaWidgets', 'PyQt5.QtQml', 'PyQt5.QtQuick',
            'PyQt5.QtQuickWidgets', 'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtBluetooth', 'PyQt5.QtNetwork',
            'PyQt5.QtOpenGL', 'PyQt5.QtSvg', 'PyQt5.QtXml', 'PyQt5.QtPrintSupport', 'PyQt5.QtDesigner',
            'PyQt5.QtHelp', 'PyQt5.QtSensors', 'PyQt5.QtSerialPort', 'PyQt5.QtWebSockets', 'PyQt5.QtNfc',
            'PyQt5.QtPositioning', 'PyQt5.QtLocation', 'PyQt5.QtDBus', 'PyQt5.QtX11Extras',
            'PyQt5.QtWinExtras', 'PyQt5.QtRemoteObjects', 'PyQt5.QtTextToSpeech', 'PyQt5.Qt3DCore']

# Files that the app never needs (big ones first).
DROP = re.compile(r'(opengl32sw|d3dcompiler|libEGL|libGLESv2|translations|[\\/]imageformats[\\/]|iconengines|'
                  r'Qt5Svg|Qt5Network|Qt5Qml|Qt5Quick|Qt5WebSockets|Qt5Pdf|Qt5VirtualKeyboard|'
                  r'qtvirtualkeyboard|[\\/]generic[\\/]|[\\/]platforminputcontexts[\\/]|'
                  r'[\\/]bearer[\\/]|[\\/]playlistformats[\\/]|[\\/]mediaservice[\\/])', re.I)

a = Analysis(['ipo_tracker.py'], pathex=[], binaries=[], datas=[], hiddenimports=[],
             hookspath=[], runtime_hooks=[], excludes=EXCLUDES, noarchive=False)
a.binaries = [b for b in a.binaries if not DROP.search(b[0]) and not DROP.search(str(b[1]))]
a.datas = [d for d in a.datas if not DROP.search(d[0]) and not DROP.search(str(d[1]))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='IPO_Tracker', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=True, upx_exclude=[],
          runtime_tmpdir=None, console=False, disable_windowed_traceback=False)
