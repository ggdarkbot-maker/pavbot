import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
import json
import os
import sys
import subprocess
import mss
import cv2
import numpy as np
import pytesseract
import keyboard
from datetime import datetime

from license_manager import check_license, activate_key, LICENSE_FILE, reset_license

# --- КОНФИГУРАЦИЯ ---
CONFIG_FILE = "config.json"
HOTKEY_START = 'f12'
HOTKEY_CAPTURE = 'f11'

# Настройка Tesseract
if sys.platform == 'win32':
    paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Tesseract-OCR', 'tesseract.exe')
    ]
    if getattr(sys, 'frozen', False):
        paths.append(os.path.join(sys._MEIPASS, 'tesseract.exe'))
    for p in paths:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break

COLORS_DARK = {"bg": "#121212", "frame": "#1E1E1E", "text": "#FFFFFF", "text_dim": "#A0A0A0", "primary": "#3B82F6",
               "success": "#10B981", "danger": "#EF4444", "warning": "#F97316"}
COLORS_LIGHT = {"bg": "#F0F0F0", "frame": "#FFFFFF", "text": "#000000", "text_dim": "#555555", "primary": "#3B82F6",
                "success": "#10B981", "danger": "#EF4444", "warning": "#F97316"}

app_instance = None
current_theme = "dark"
current_colors = COLORS_DARK


class TimerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Timer")
        self.geometry("350x120+100+100")
        self.attributes('-topmost', True)
        self.configure(fg_color="black")
        self.label = ctk.CTkLabel(self, text="00.000", font=("Courier New", 56, "bold"), text_color="#00FF94")
        self.label.pack(expand=True)
        self.drag_x = self.drag_y = 0
        self.label.bind("<ButtonPress-1>", lambda e: setattr(self, 'drag_x', e.x) or setattr(self, 'drag_y', e.y))
        self.label.bind("<B1-Motion>", lambda e: self.geometry(f"+{e.x_root - self.drag_x}+{e.y_root - self.drag_y}"))

    def set_time(self, val, critical=False):
        ms = int((val % 1) * 1000)
        s = int(val)
        self.label.configure(text=f"{s:02d}.{ms:03d}", text_color="#FF0000" if critical else "#00FF94")


class LicenseWindow(ctk.CTk):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.title("🔐 Активация Pavilion Bot")
        self.geometry("450x400")
        self.resizable(False, False)
        self.configure(fg_color=COLORS_DARK["bg"])

        # Заголовок (без ошибки сверху)
        ctk.CTkLabel(self, text="🔒 ЛИЦЕНЗИОННЫЙ КЛЮЧ", font=("Arial", 18, "bold"),
                     text_color=COLORS_DARK["primary"]).pack(pady=20)
        ctk.CTkLabel(self, text="Введите ключ для доступа:", text_color=COLORS_DARK["text_dim"]).pack()

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=15)

        self.key_entry = ctk.CTkEntry(entry_frame, width=300, height=40, font=("Arial", 14), justify="center")
        self.key_entry.pack(side="left", padx=(0, 10))

        paste_btn = ctk.CTkButton(entry_frame, text="📋", width=40, height=40, command=self.paste_key,
                                  fg_color=COLORS_DARK["frame"], hover_color=COLORS_DARK["primary"])
        paste_btn.pack(side="left")

        ctk.CTkLabel(self, text="(Нажмите 📋 или ПКМ)", text_color=COLORS_DARK["text_dim"], font=("Arial", 10)).pack(
            pady=(0, 10))

        self.status_lbl = ctk.CTkLabel(self, text="", text_color=COLORS_DARK["danger"], font=("Arial", 12))
        self.status_lbl.pack()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="АКТИВИРОВАТЬ", command=self.activate, fg_color=COLORS_DARK["success"],
                      hover_color="#059669", width=160, height=40).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="ВЫХОД", command=self.exit_app, fg_color=COLORS_DARK["danger"],
                      hover_color="#B91C1C", width=100, height=40).pack(side="right", padx=10)

    def paste_key(self):
        try:
            text = self.clipboard_get()
            self.key_entry.delete(0, 'end')
            self.key_entry.insert(0, text)
        except:
            pass

    def activate(self):
        key = self.key_entry.get().strip()
        if not key:
            self.status_lbl.configure(text="Введите ключ!", text_color=COLORS_DARK["danger"])
            return

        # Пытаемся активировать
        success, msg = activate_key(key)

        if success:
            self.status_lbl.configure(text=f"Успешно! ({msg})", text_color=COLORS_DARK["success"])
            self.update()
            time.sleep(0.8)
            self.destroy()
            if self.on_success: self.on_success()
        else:
            self.status_lbl.configure(text=msg, text_color=COLORS_DARK["danger"])

    def exit_app(self):
        self.destroy()
        sys.exit(0)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Pavilion Bot [Release] v7.0")
        self.geometry("450x650")
        self.minsize(400, 550)
        self.attributes('-topmost', True)
        self.configure(fg_color=current_colors["bg"])

        self.is_valid, self.msg_status, self.expiry_date = check_license()
        self.config = self.load_config()

        self.is_running = False
        self.stop_flag = False
        self.waiting_for_timer = False  # Новый флаг состояния
        self.timer_win = None
        self.hotkey_registered = False

        self.status_var = tk.StringVar(value="● Ожидание (F12)")
        self.region_var = tk.StringVar(value=self.get_region_str())

        self.build_ui()
        self.register_hotkey()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_subscription_timer()

    def build_ui(self):
        for widget in self.winfo_children(): widget.destroy()
        self.configure(fg_color=current_colors["bg"])

        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=10)
        self.sub_label = ctk.CTkLabel(top_bar, text="", font=("Arial", 11, "bold"),
                                      text_color=current_colors["primary"])
        self.sub_label.pack(side="left")
        if self.is_valid:
            ctk.CTkButton(top_bar, text="🚪", width=30, height=30, command=self.logout,
                          fg_color=current_colors["danger"], hover_color="#CC0000").pack(side="left", padx=5)

        theme_icon = "☀️" if current_theme == "dark" else "🌙"
        self.theme_btn = ctk.CTkButton(top_bar, text=theme_icon, width=40, height=40, command=self.toggle_theme,
                                       fg_color=current_colors["frame"], hover_color=current_colors["primary"],
                                       text_color=current_colors["text"])
        self.theme_btn.pack(side="right")

        ctk.CTkLabel(self, text="PAVILION BOT", font=("Arial", 24, "bold"), text_color=current_colors["text"]).pack(
            pady=5)
        ctk.CTkLabel(self, textvariable=self.status_var, font=("Arial", 13),
                     text_color=current_colors["text_dim"]).pack(pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(self, fg_color=current_colors["frame"], corner_radius=10)
        scroll.pack(fill="both", expand=True, padx=15, pady=5)

        frm_reg = ctk.CTkFrame(scroll, fg_color=current_colors["bg"], corner_radius=8)
        frm_reg.pack(fill="x", pady=8)
        ctk.CTkLabel(frm_reg, text="📍 Область (F11)", font=("Arial", 13, "bold"),
                     text_color=current_colors["text"]).pack(pady=5)
        ctk.CTkLabel(frm_reg, textvariable=self.region_var, text_color=current_colors["primary"],
                     font=("Arial", 12)).pack()
        ctk.CTkButton(frm_reg, text="Изменить", command=self.select_region, fg_color=current_colors["primary"],
                      height=32).pack(pady=8)

        frm_set = ctk.CTkFrame(scroll, fg_color=current_colors["bg"], corner_radius=8)
        frm_set.pack(fill="x", pady=8)
        ctk.CTkLabel(frm_set, text="⚙️ Настройки", font=("Arial", 13, "bold"), text_color=current_colors["text"]).pack(
            pady=5)

        ctk.CTkLabel(frm_set, text="Скорость клика (мс)", text_color=current_colors["text_dim"], anchor="w").pack(
            fill="x", padx=10, pady=(5, 0))
        self.sl_delay = ctk.CTkSlider(frm_set, from_=10, to=200, number_of_steps=190, command=self.update_delay)
        self.sl_delay.set(self.config.get("click_delay_ms", 50))
        self.sl_delay.pack(fill="x", padx=10, pady=5)
        self.lbl_delay = ctk.CTkLabel(frm_set, text=f"{int(self.sl_delay.get())} мс", text_color=current_colors["text"])
        self.lbl_delay.pack()

        ctk.CTkLabel(frm_set, text="Спам за (сек)", text_color=current_colors["text_dim"], anchor="w").pack(fill="x",
                                                                                                            padx=10,
                                                                                                            pady=(5, 0))
        self.sl_trig = ctk.CTkSlider(frm_set, from_=0.5, to=10.0, number_of_steps=190, command=self.update_trigger)
        self.sl_trig.set(self.config.get("trigger_seconds", 3.0))
        self.sl_trig.pack(fill="x", padx=10, pady=5)
        self.lbl_trig = ctk.CTkLabel(frm_set, text=f"{self.sl_trig.get():.2f} сек", text_color=current_colors["text"])
        self.lbl_trig.pack(pady=(0, 5))

        btn_frm = ctk.CTkFrame(self, fg_color="transparent")
        btn_frm.pack(fill="x", padx=15, pady=10)

        self.btn_action = ctk.CTkButton(btn_frm, text="ЗАПУСК (F12)", command=self.toggle_bot_manual,
                                        fg_color=current_colors["success"], height=50, font=("Arial", 16, "bold"),
                                        text_color="#000000")
        self.btn_action.pack(fill="x")
        ctk.CTkButton(btn_frm, text="СТОП", command=self.stop_bot, fg_color=current_colors["danger"], height=40,
                      text_color="#FFFFFF").pack(fill="x", pady=(10, 0))

        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(footer_frame, text="1. F12 (Ожидание)\n2. E+Enter в игре\n3. Бот сам поймает таймер",
                     text_color=current_colors["text_dim"], justify="center", font=("Arial", 11)).pack(pady=5)
        ctk.CTkLabel(footer_frame, text="telega: @BYYNAII", text_color=current_colors["text_dim"],
                     font=("Arial", 10, "bold")).pack(pady=2)

    def register_hotkey(self):
        try:
            keyboard.add_hotkey(HOTKEY_START, self.toggle_bot_safe)
            keyboard.add_hotkey(HOTKEY_CAPTURE, self.select_region_safe)
            self.hotkey_registered = True
        except Exception as e:
            self.status_var.set(f"Ошибка прав: {e}")

    def select_region_safe(self):
        if not self.winfo_exists(): return
        self.after(0, self.select_region)

    def update_subscription_timer(self):
        if self.is_valid and self.expiry_date:
            remaining = self.expiry_date - datetime.now()
            if remaining.total_seconds() > 0:
                days = remaining.days
                hours = int(remaining.seconds // 3600)
                self.sub_label.configure(text=f"📅 Подписка: {days} дн. {hours} ч.",
                                         text_color=current_colors["primary"])
            else:
                self.sub_label.configure(text="⚠️ Истекает сегодня!", text_color=current_colors["danger"])
        elif self.is_valid:
            self.sub_label.configure(text="♾️ Навсегда", text_color=current_colors["success"])
        else:
            self.sub_label.configure(text="")
        if self.winfo_exists(): self.after(1000, self.update_subscription_timer)

    def toggle_theme(self):
        global current_theme, current_colors
        if current_theme == "dark":
            current_theme = "light"
            current_colors = COLORS_LIGHT
        else:
            current_theme = "dark"
            current_colors = COLORS_DARK
        self.build_ui()

    def logout(self):
        if messagebox.askyesno("Выход", "Сбросить лицензию?"):
            reset_license()
            self.stop_bot()
            self.destroy()
            login_win = LicenseWindow(on_success=lambda: main())
            login_win.mainloop()

    def get_region_str(self):
        r = self.config.get("region")
        return f"{r[0]}, {r[1]} ({r[2]}x{r[3]})" if r else "Не выбрана"

    def select_region(self):
        try:
            self.withdraw()
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
                selector_exe = os.path.join(base_path, "region_selector.exe")
                if not os.path.exists(selector_exe): raise FileNotFoundError("region_selector.exe not found")
                cmd = [selector_exe]
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
                selector_py = os.path.join(base_path, "region_selector.py")
                cmd = [sys.executable, selector_py]

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if stderr: print(f"Error: {stderr}")

            if stdout:
                parts = stdout.strip().split(',')
                if len(parts) == 4:
                    x, y, w, h = map(int, parts)
                    self.after(0, lambda: self.save_region(x, y, w, h))
                else:
                    self.after(0, self.deiconify)
            else:
                self.after(0, self.deiconify)
        except Exception as e:
            self.after(0, self.deiconify)
            self.status_var.set(f"Ошибка F11: {str(e)[:20]}")

    def save_region(self, x, y, w, h):
        self.config["region"] = [x, y, w, h]
        self.save_config()
        self.region_var.set(f"{x}, {y} ({w}x{h})")
        self.status_var.set("● Область сохранена")
        self.deiconify()

    def update_delay(self, val):
        v = int(val)
        self.lbl_delay.configure(text=f"{v} мс")
        self.config["click_delay_ms"] = v
        self.save_config()

    def update_trigger(self, val):
        v = float(val)
        self.lbl_trig.configure(text=f"{v:.2f} сек")
        self.config["trigger_seconds"] = v
        self.save_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content: return {"region": None, "click_delay_ms": 50, "trigger_seconds": 3.0}
                    return json.loads(content)
            except:
                pass
        return {"region": None, "click_delay_ms": 50, "trigger_seconds": 3.0}

    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def toggle_bot_safe(self):
        if not self.winfo_exists(): return
        self.after(0, self.toggle_bot_manual)

    def toggle_bot_manual(self):
        if self.is_running or self.waiting_for_timer:
            self.stop_bot()
        else:
            self.start_bot_wait_mode()

    def start_bot_wait_mode(self):
        """Режим ожидания таймера"""
        if not self.config.get("region"):
            self.status_var.set("❌ Выделите область (F11)!")
            return

        self.is_running = False
        self.waiting_for_timer = True
        self.stop_flag = False

        # UI Обновление: Оранжевый цвет
        self.btn_action.configure(text="⏳ ОЖИДАНИЕ ТАЙМЕРА...", fg_color=current_colors["warning"],
                                  text_color="#FFFFFF")
        self.status_var.set("⏳ Жму E+Enter в игре...")

        if self.timer_win and self.timer_win.winfo_exists(): self.timer_win.destroy()

        threading.Thread(target=self.wait_and_detect_loop, daemon=True).start()

    def wait_and_detect_loop(self):
        """Цикл ожидания появления цифр"""
        region = self.config["region"]
        detected = -1
        attempts = 0
        max_attempts = 100  # ~5 секунд ожидания (0.05 * 100)

        while attempts < max_attempts and not self.stop_flag and self.waiting_for_timer:
            time.sleep(0.05)
            attempts += 1

            try:
                with mss.mss() as sct:
                    mon = {"left": region[0], "top": region[1], "width": region[2], "height": region[3]}
                    img = np.array(sct.grab(mon))
                    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
                    txt = pytesseract.image_to_string(thresh, config='--psm 7 digits')
                    nums = ''.join(filter(str.isdigit, txt))

                    if nums:
                        val = int(nums)
                        if 0 < val <= 60:
                            detected = val
                            break
            except:
                pass

        if detected != -1 and not self.stop_flag:
            # Таймер найден! Запускаем основной цикл
            self.after(0, lambda: self.start_bot_logic(detected))
        else:
            # Не найдено
            if not self.stop_flag:
                self.after(0, lambda: self.status_var.set("❌ Таймер не найден (5 сек)"))
                self.after(0, self.stop_bot)

    def start_bot_logic(self, initial_time):
        """Основная логика бота после обнаружения таймера"""
        self.waiting_for_timer = False
        self.is_running = True

        # UI Обновление: Зеленый цвет
        self.btn_action.configure(text="РАБОТАЕТ", fg_color=current_colors["success"], text_color="#000000")
        self.status_var.set("● Активен")

        if self.timer_win and self.timer_win.winfo_exists(): self.timer_win.destroy()
        self.timer_win = TimerWindow(self)

        threading.Thread(target=self.bot_loop, args=(initial_time,), daemon=True).start()

    def stop_bot(self):
        self.stop_flag = True
        self.is_running = False
        self.waiting_for_timer = False
        self.btn_action.configure(text="ЗАПУСК (F12)", fg_color=current_colors["success"], text_color="#000000")
        self.status_var.set("● Остановлен")
        if self.timer_win and self.timer_win.winfo_exists(): self.timer_win.destroy()
        self.timer_win = None

    def bot_loop(self, start_val):
        try:
            trigger = self.config.get("trigger_seconds", 3.0)
            current = float(start_val)

            while current > 0 and not self.stop_flag:
                step = 0.05
                time.sleep(step)
                current -= step

                is_crit = (current <= trigger + 0.5)
                if self.timer_win and self.timer_win.winfo_exists():
                    self.timer_win.set_time(current, is_crit)

                if current <= trigger:
                    self.spam_clicks(trigger)
                    break

            if current <= 0 and not self.stop_flag:
                if trigger <= 0: self.spam_clicks(0)
        except Exception as e:
            self.after(0, lambda: self.status_var.set(f"❌ Ошибка: {str(e)[:20]}"))
            self.after(0, self.stop_bot)

    def spam_clicks(self, duration):
        delay = self.config.get("click_delay_ms", 50) / 1000.0
        total_time = duration + 0.5
        start = time.time()
        self.after(0, lambda: self.status_var.set("⚡ СПАМ!"))
        while (time.time() - start) < total_time and not self.stop_flag:
            keyboard.press('e')
            keyboard.press('enter')
            time.sleep(0.02)
            keyboard.release('e')
            keyboard.release('enter')
            time.sleep(delay)
        self.after(0, lambda: self.status_var.set("● Готово"))
        self.after(0, self.stop_bot)

    def on_close(self):
        self.stop_bot()
        if self.hotkey_registered:
            try:
                keyboard.remove_hotkey(HOTKEY_START)
                keyboard.remove_hotkey(HOTKEY_CAPTURE)
            except:
                pass
        self.destroy()
        sys.exit(0)


def main():
    global app_instance
    is_valid, msg, expiry = check_license()
    ctk.set_appearance_mode("Dark")

    if is_valid:
        app_instance = App()
        app_instance.mainloop()
    else:
        # Если ошибка CORRUPTED_DELETED, просто показываем окно ввода
        login_win = LicenseWindow(on_success=lambda: main())
        login_win.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal Error: {e}")
        input("Press Enter to exit...")