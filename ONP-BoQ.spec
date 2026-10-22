# -*- mode: python ; coding: utf-8 -*-
# Сборкa Windows: pyinstaller ONP-BoQ.spec
# Сборкa Linux:  python -m PyInstaller ONP-BoQ.spec    

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/UI/resources', 'UI/resources')],
    hiddenimports=['openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5'],
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
    name='ONP_Система_ВОР',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                            # на Linux не имеет эффекта, оставлено для совместимости
    icon='src/UI/resources/icons/icon_main.ico',  # на Linux игнорируется
    version='version_info.txt',               # только для Windows — на Linux не работает
)