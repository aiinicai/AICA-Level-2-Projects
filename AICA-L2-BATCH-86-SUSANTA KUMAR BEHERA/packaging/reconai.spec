# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect submodules and data
hiddenimports = [
    'reconai',
    'reconai.models',
    'reconai.models.client',
    'reconai.models.transaction',
    'reconai.models.session',
    'reconai.config',
    'reconai.ai',
    'reconai.ai.client',
    'reconai.db',
    'reconai.db.database',
    'reconai.ingest',
    'reconai.ingest.base_parser',
    'reconai.ingest.document_parser',
    'reconai.ingest.statement_parser',
    'reconai.ingest.ledger_parser',
    'reconai.reconcile',
    'reconai.reconcile.deterministic',
    'reconai.reconcile.fuzzy',
    'reconai.reconcile.ai_matcher',
    'reconai.reconcile.matcher',
    'reconai.audit',
    'reconai.audit.rules_engine',
    'reconai.audit.ai_flagger',
    'reconai.audit.audit_manager',
    'reconai.report',
    'reconai.report.excel_exporter',
    'reconai.report.pdf_exporter',
    'reconai.report.report_builder',
    'reconai.ui',
    'reconai.ui.theme',
    'reconai.ui.main_window',
    'reconai.ui.components',
    'reconai.ui.components.stat_card',
    'reconai.ui.components.table_models',
    'reconai.ui.components.undo_commands',
    'reconai.ui.views',
    'reconai.ui.views.ingest_view',
    'reconai.ui.views.reconcile_view',
    'reconai.ui.views.audit_view',
    'reconai.ui.views.export_view',
    'reconai.ui.views.settings_dialog',
    'reconai.ui.views.client_master_dialog',
    'reconai.ui.workers',
    'reconai.ui.workers.background_workers',
    'docx',
    'pydantic',
    'rapidfuzz',
    'openpyxl',
    'reportlab',
    'pdfplumber',
    'pypdfium2',
    'pypdfium2_raw',
    'anthropic',
    'google.genai',
    'sqlite3',
]

datas = (
    collect_data_files('reportlab')
    + collect_data_files('pdfplumber')
    + collect_data_files('docx')
    + collect_data_files('pypdfium2')
)

a = Analysis(
    [str(Path('..') / 'run.py')],
    pathex=[str(Path('..').resolve())],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ReconAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
