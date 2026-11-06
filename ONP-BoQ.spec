# -*- mode: python ; coding: utf-8 -*-
# Сборка Windows: pyinstaller ONP-BoQ.spec
# Сборка Linux:  python -m PyInstaller ONP-BoQ.spec

from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata
import sys
from os import path

block_cipher = None

# Собираем все подмодули для jsonschema и jsonschema_specifications
hiddenimports = [
    'openpyxl',
    'jsonschema',
    'jsonschema_specifications',
] + collect_submodules('jsonschema') + collect_submodules('jsonschema_specifications')

# Собираем файлы данных и метаданные
datas = [
    ('src/UI/resources', 'UI/resources'),
] + collect_data_files('jsonschema') + collect_data_files('jsonschema_specifications')

# Явно копируем метаданные пакетов, чтобы избежать ошибок DistributionNotFound
datas += copy_metadata('jsonschema')
datas += copy_metadata('jsonschema_specifications')


a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    hiddenimports=hiddenimports,
    datas=datas,
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
    console=False,
    icon='src/UI/resources/icons/icon_main.ico',
    version='version_info.txt',
)