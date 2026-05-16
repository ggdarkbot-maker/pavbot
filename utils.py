import sys
import ctypes
import os
import subprocess
import pytesseract


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()


def check_tesseract():
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    ]
    tesseract_found = any(os.path.exists(p) for p in tesseract_paths)
    if not tesseract_found:
        return False, "Tesseract не найден. Скачайте с https://github.com/UB-Mannheim/tesseract/wiki"

    try:
        result = subprocess.run([tesseract_paths[0], "--list-langs"], capture_output=True, text=True)
        if "rus" not in result.stdout:
            return False, "Русский язык не установлен в Tesseract. Установите language pack 'Russian'."
    except:
        pass
    return True, "OK"


def set_tesseract_path():
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return
    raise Exception("Tesseract не найден")