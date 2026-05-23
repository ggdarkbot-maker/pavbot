import json
import os
import socket
import uuid
import hashlib
import hmac
import base64
from datetime import datetime, timedelta

LICENSE_FILE = "license.dat"

# !!! ВСТАВЬ СЮДА ЛЮБУЮ СЛОЖНУЮ ФРАЗУ (минимум 16 символов) !!!
SECRET_PHRASE = "MySuperSecretBaKSeForPavilionBot2024!"


def get_hwid():
    mac = uuid.getnode()
    hostname = socket.gethostname()
    raw = f"{mac}-{hostname}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _sign(data_str):
    """Создает короткую подпись"""
    return hmac.new(SECRET_PHRASE.encode(), data_str.encode(), hashlib.sha256).hexdigest()[:16]


def generate_key(days: int):
    """Генерирует короткий ключ формата: ПОДПИСЬ-ДНИ-СОЛЬ"""
    if days == 0:
        payload = f"PERM-{uuid.uuid4().hex[:8]}"
    else:
        payload = f"{days}-{uuid.uuid4().hex[:8]}"

    signature = _sign(payload)
    return f"{signature}-{payload}"


def check_license():
    """Проверяет лицензию. Возвращает (True/False, Сообщение, Дата окончания)"""
    if not os.path.exists(LICENSE_FILE):
        return False, "NOT_FOUND", None

    try:
        with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                raise ValueError("Empty file")
            data = json.loads(content)
    except Exception:
        # Файл битый - удаляем его молча, чтобы пользователь ввел ключ заново
        try:
            os.remove(LICENSE_FILE)
        except:
            pass
        return False, "CORRUPTED_DELETED", None

    # Проверка структуры
    if "key" not in data or "hwid" not in data or "expiry" not in data:
        try:
            os.remove(LICENSE_FILE)
        except:
            pass
        return False, "CORRUPTED_DELETED", None

    current_hwid = get_hwid()

    # Привязка к ПК при первой активации
    if data["hwid"] is None:
        data["hwid"] = current_hwid
        _save_data(data)
    elif data["hwid"] != current_hwid:
        return False, "HWID_MISMATCH", None

    # Проверка подписи ключа
    key = data["key"]
    try:
        sig, payload = key.split('-', 1)
        if _sign(payload) != sig:
            raise ValueError("Bad signature")
    except:
        try:
            os.remove(LICENSE_FILE)
        except:
            pass
        return False, "INVALID_KEY", None

    # Проверка срока
    expiry_str = data.get("expiry")
    if not expiry_str:
        return False, "NO_EXPIRY", None

    try:
        expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
    except:
        return False, "DATE_ERROR", None

    if datetime.now() > expiry_dt:
        return False, "EXPIRED", None

    return True, "OK", expiry_dt


def activate_key(key):
    """Активирует ключ. Создает файл лицензии."""
    # 1. Проверка формата ключа
    try:
        sig, payload = key.split('-', 1)
        if _sign(payload) != sig:
            return False, "Неверный формат ключа (подпись)"

        parts = payload.split('-')
        days_str = parts[0]

        if days_str == "PERM":
            expiry_dt = datetime(2099, 12, 31, 23, 59, 59)  # Условно навсегда
            msg = "Навсегда"
        else:
            days = int(days_str)
            # РОВНО N ДНЕЙ ОТ ТЕКУЩЕГО МОМЕНТА
            expiry_dt = datetime.now() + timedelta(days=days)
            msg = f"{days} дн."

    except Exception as e:
        return False, f"Ошибка ключа: {str(e)}"

    # 2. Сохранение
    data = {
        "key": key,
        "hwid": None,  # Будет заполнено при первом запуске check_license
        "expiry": expiry_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        _save_data(data)
        return True, msg
    except Exception as e:
        return False, f"Ошибка записи: {str(e)}"


def _save_data(data):
    with open(LICENSE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def reset_license():
    if os.path.exists(LICENSE_FILE):
        os.remove(LICENSE_FILE)