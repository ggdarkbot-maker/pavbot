# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# --- АВТОМАТИЧЕСКИЙ ПОИСК TESSERACT ---
tesseract_datas = []
tesseract_binaries = []

if sys.platform == 'win32':
    # Пути, где обычно лежит Tesseract
    paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
    ]

    found_path = None
    for p in paths:
        if os.path.exists(p):
            found_path = p
            break

    if found_path:
        tess_dir = os.path.dirname(found_path)
        tessdata_dir = os.path.join(tess_dir, 'tessdata')

        if os.path.exists(tessdata_dir):
            print(f"[OK] Tesseract найден: {found_path}")
            # Копируем exe и папку с языками внутрь _internal
            tesseract_binaries = [(found_path, '.')]
            tesseract_datas = [(tessdata_dir, 'tessdata')]
        else:
            print("[WARNING] Папка tessdata не найдена!")
    else:
        print("[ERROR] Tesseract НЕ НАЙДЕН! Сборка будет без распознавания текста.")
        print("Установите Tesseract OCR и запустите сборку снова.")

# --- ПРОВЕРКА REGION SELECTOR ---
current_dir = os.getcwd()
region_exe_path = os.path.join(current_dir, 'region_selector.exe')

if not os.path.exists(region_exe_path):
    # Пробуем найти в dist, если забыли скопировать
    dist_region = os.path.join(current_dir, 'dist', 'region_selector.exe')
    if os.path.exists(dist_region):
        region_exe_path = dist_region
        print("[INFO] region_selector.exe найден в dist, копируем...")
    else:
        raise FileNotFoundError("Критическая ошибка: region_selector.exe не найден! Соберите его сначала.")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=tesseract_binaries, # Встраиваем Tesseract.exe
    datas=[
        ('region_selector.exe', '.'), # Кладем region_selector.exe рядом с главным exe
        ('license_manager.py', '.'),
    ] + tesseract_datas, # Встраиваем языковые пакеты
    hiddenimports=[
        'keyboard', 'pytesseract', 'cv2', 'numpy', 'mss',
        'cryptography.fernet', 'PIL._tkinter_finder', 'encodings.utf_8',
        'multiprocessing.popen_spawn_win32'
    ],
    hookspath=[],
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
    name='PavilionBot_v7',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    onefile=False, # ВАЖНО: Создаем папку, а не один файл
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)