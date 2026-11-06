# -*- mode: python ; coding: utf-8 -*-
# Сборка Windows: pyinstaller --distpath dist --workpath build --noconfirm Launcher.spec
# Сборка Linux: python -m PyInstaller --distpath dist --workpath build --noconfirm Launcher.spec


import os
import sys
from os import path
from PyInstaller.utils.hooks import collect_all

# Каталог spec-файла. SPECPATH предоставляется PyInstaller.
HERE = os.path.abspath(SPECPATH)

# Путь к репозиторию с обновляемым кодом
REPO_DIR = HERE

# Зависимости, которые нужно упаковать целиком (launcher.py их не импортирует).
# jsonschema и jsonschema_specifications добавлены, чтобы после обновления исходников
# через лаунчер модуль Core/Convertor_BoQ.py мог импортировать валидатор.
PACKAGES = [
    'openpyxl',
    'filelock',
    'PyQt6',
    'PyQt6-Qt6',
    'PyQt6_sip',
    'reportlab',
    'pyperclip',
    'jsonschema',
    'jsonschema_specifications',
]

datas, binaries, hiddenimports = [], [], []
for pkg in PACKAGES:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Страховка: если collect_all по какой-то причине не собрал файлы пакетов
# jsonschema / jsonschema_specifications (нестандартная установка, namespace-пакет и т.п.),
# добавляем директории пакетов явно — этот приём уже доказал работоспособность.
# PyInstaller дедуплицирует совпадающие записи при сборке, поэтому дубликатов в итоге не будет.
site_packages = next(
    (p for p in sys.path if p.endswith(('site-packages', 'dist-packages'))),
    None,
)
if site_packages:
    for pkg_name in ('jsonschema', 'jsonschema_specifications'):
        pkg_path = path.join(site_packages, pkg_name)
        if path.isdir(pkg_path):
            datas.append((pkg_path, pkg_name))

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