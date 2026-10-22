# -*- mode: python ; coding: utf-8 -*-
# Сборка Windows: pyinstaller --distpath dist --workpath build --noconfirm Launcher.spec
# Сборка Linux: python -m PyInstaller --distpath dist --workpath build --noconfirm Launcher.spec              


import os
from PyInstaller.utils.hooks import collect_all

# Каталог spec-файла. SPECPATH предоставляется PyInstaller.
HERE = os.path.abspath(SPECPATH)

# Путь к репозиторию с обновляемым кодом
REPO_DIR = HERE

# Зависимости, которые нужно упаковать целиком (launcher.py их не импортирует)
PACKAGES = ['openpyxl', 'filelock', 'PyQt6', 'PyQt6-Qt6', 'PyQt6_sip', 'reportlab', 'pyperclip']

datas, binaries, hiddenimports = [], [], []
for pkg in PACKAGES:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [os.path.join(HERE, 'src', 'launcher.py')],
    pathex=[REPO_DIR, os.path.join(REPO_DIR, 'src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['PyQt5'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ONP_Система_ВОР',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    version=os.path.join(REPO_DIR, 'version_info.txt'),
    icon=os.path.join(REPO_DIR, 'src', 'UI', 'resources', 'icons', 'icon_main.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='ONP_Система_ВОР',
)