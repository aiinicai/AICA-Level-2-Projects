# -*- mode: python ; coding: utf-8 -*-

import sys
import os
import streamlit
from PyInstaller.utils.hooks import copy_metadata

block_cipher = None

# 1. Base files to bundle
datas = [
    ('app.py', '.'),
]

# 2. Package metadata (using exact pip distribution names)
datas += copy_metadata('streamlit')
datas += copy_metadata('google-genai')
datas += copy_metadata('pydantic')
datas += copy_metadata('pdfplumber')
datas += copy_metadata('python-docx')

# 3. Streamlit static UI assets
streamlit_static_dir = os.path.join(os.path.dirname(streamlit.__file__), 'static')
datas.append((streamlit_static_dir, 'streamlit/static'))

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'streamlit',
        'streamlit.web.cli',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'streamlit.runtime.scriptrunner',
        'streamlit.runtime.caching',
        'streamlit.runtime.state',
        'google.genai',
        'google.genai.types',
        'pydantic',
        'pdfplumber',
        'docx',
        'pandas',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TaxLitigatorAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TaxLitigatorAI',
)