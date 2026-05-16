import customtkinter as ctk
import threading
import time
import pydirectinput
from tkinter import messagebox
from pynput import keyboard

from ocr_timer import TimerMonitor
from keypress import KeyPressController
from config_manager import ConfigManager
import utils

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class TimerWindow(ctk.CTkToplevel):
    # ... (без изменений, как в вашей работающей версии) ...
    def __init__(self, parent, initial_seconds, on_timeout, on_cancel):
        super().__init__(parent)
        self.parent = parent
        self.remaining = initial_seconds
        self.on_timeout = on_timeout
        self.on_cancel = on_cancel
        self.running = True
        self.title("Обратный отсчёт")
        self.geometry("300x200")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.label = ctk.CTkLabel(self, text=self._format_time(), font=("Arial", 48, "bold"))
        self.label.pack(expand=True, fill="both", padx=20, pady=20)
        self.cancel_btn = ctk.CTkButton(self, text="Отменить", command=self._cancel)
        self.cancel_btn.pack(pady=10)
        self.update_timer()
    def _format_time(self):
        return f"{self.remaining:.1f} сек"
    def update_timer(self):
        if not self.running:
            return
        if self.remaining <= 0:
            self.running = False
            self.on_timeout()
            self.destroy()
            return
        self.label.configure(text=self._format_time())
        self.remaining -= 0.05
        self.after(50, self.update_timer)
    def _cancel(self):
        self.running = False
        self.on_cancel()
        self.destroy()

class RegionSelector:
    # ... (без изменений) ...
    def __init__(self, parent, on_selected):
        self.parent = parent
        self.on_selected = on_selected
        self.selector_window = None
        self.start_x = self.start_y = 0
        self.rect = None
    def start(self):
        self.selector_window = ctk.CTkToplevel(self.parent)
        self.selector_window.attributes('-fullscreen', True)
        self.selector_window.attributes('-alpha', 0.3)
        self.selector_window.attributes('-topmost', True)
        self.selector_window.configure(cursor="cross")
        from tkinter import Canvas
        self.canvas = Canvas(self.selector_window, highlightthickness=0, bg='gray')
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)
    def on_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)
    def on_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        width = abs(end_x - self.start_x)
        height = abs(end_y - self.start_y)
        self.selector_window.destroy()
        self.on_selected(int(left), int(top), int(width), int(height))

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.current_scale = self.config.get("ui_scaling", 1.0)
        self.title("Amazing Pavilion Bot - Recr3nt")
        self.geometry("500x600")
        self.minsize(400, 480)
        self.resizable(True, True)
        self.key_controller = KeyPressController()
        self.monitor = None
        self.timer_window = None
        self.processing = False
        self.global_listener = None
        self.settings_window = None
        self.buttons = []
        self.create_widgets()
        self.apply_theme(self.config.get("theme", "dark"))
        self.apply_scaling(self.current_scale)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.start_global_hotkey()

    def apply_scaling(self, scale):
        scale = max(0.6, min(2.0, scale))
        ctk.set_widget_scaling(scale)
        ctk.set_window_scaling(scale)
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.update_scale(scale)

    def start_global_hotkey(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f12 and not self.processing:
                    threading.Thread(target=self.capture_and_start, daemon=True).start()
            except:
                pass
        self.global_listener = keyboard.Listener(on_press=on_press)
        self.global_listener.daemon = True
        self.global_listener.start()

    def capture_and_start(self):
        if self.processing:
            return
        self.processing = True
        try:
            ok, msg = utils.check_tesseract()
            if not ok:
                messagebox.showerror("Ошибка", msg)
                return
            utils.set_tesseract_path()
            region = self.config.get("region")
            if not region:
                messagebox.showerror("Ошибка", "Сначала выберите область с таймером в настройках")
                return
            pydirectinput.press('e')
            time.sleep(0.05)
            pydirectinput.press('enter')
            time.sleep(0.3)
            self.monitor = TimerMonitor(region)
            seconds_left = self.monitor.get_remaining_seconds()
            if seconds_left is not None and seconds_left > 0:
                self.status_label.configure(text=f"Состояние: отсчёт {seconds_left:.1f} сек")
                trigger_sec = self.config.get("trigger_seconds", 1.2)
                calibration_ms = self.config.get("calibration_ms", 0)
                wait_time = seconds_left - trigger_sec + (calibration_ms / 1000.0)
                if wait_time < 0:
                    wait_time = 0
                self.timer_window = TimerWindow(
                    self, seconds_left,
                    on_timeout=self.start_clicks,
                    on_cancel=self.cancel_timer
                )
                threading.Thread(target=self._wait_and_clicks, args=(wait_time,), daemon=True).start()
                return  # Выходим, чтобы не показывать ошибку
            else:
                messagebox.showerror("Ошибка", "Не удалось распознать время. Убедитесь, что таймер виден и область выделена.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при запуске: {e}")
        finally:
            self.processing = False

    def _wait_and_clicks(self, wait_time):
        time.sleep(wait_time)
        if self.timer_window and self.timer_window.running:
            self.start_clicks()

    def start_clicks(self):
        self.status_label.configure(text="Состояние: КЛИКАЮ (захват)")
        click_delay_ms = self.config.get("click_delay_ms", 15)
        self.key_controller.start_spam(click_delay_ms)
        def check():
            time.sleep(2.0)
            if self.key_controller.is_running():
                self.key_controller.stop_spam()
                self.status_label.configure(text="Состояние: Ошибка (спам-защита?)")
                if self.timer_window and self.timer_window.winfo_exists():
                    self.timer_window.destroy()
        threading.Thread(target=check, daemon=True).start()

    def cancel_timer(self):
        self.key_controller.stop_spam()
        self.status_label.configure(text="Состояние: Отменено")
        self.processing = False

    def emergency_stop(self):
        self.key_controller.stop_spam()
        if self.timer_window and self.timer_window.winfo_exists():
            self.timer_window.destroy()
        self.processing = False
        self.status_label.configure(text="Состояние: Остановлен (F12)")

    def apply_theme(self, theme):
        if theme == "light":
            bg_color = "#dbdbdb"
            button_color = "#3B8ED0"
            ctk.set_appearance_mode("light")
        else:
            bg_color = "#2b2b2b"
            button_color = "#3B8ED0"
            ctk.set_appearance_mode("dark")
        self.configure(fg_color=bg_color)
        for btn in self.buttons:
            btn.configure(fg_color=button_color)
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.update_colors_from_theme(theme)

    def create_widgets(self):
        self.buttons = []
        self.title_label = ctk.CTkLabel(self, text="Recr3nt PRODUCT", font=("Arial", 24, "bold"))
        self.title_label.pack(pady=20)
        self.start_btn = ctk.CTkButton(self, text="Запустить мониторинг", command=self.capture_and_start, width=200, height=40)
        self.start_btn.pack(pady=10)
        self.buttons.append(self.start_btn)
        self.settings_btn = ctk.CTkButton(self, text="Настройки", command=self.open_settings, width=200, height=40)
        self.settings_btn.pack(pady=10)
        self.buttons.append(self.settings_btn)
        self.exit_btn = ctk.CTkButton(self, text="Выход", command=self.on_close, width=200, height=40)
        self.exit_btn.pack(pady=10)
        self.buttons.append(self.exit_btn)
        self.status_label = ctk.CTkLabel(self, text="Состояние: Не запущен", font=("Arial", 14))
        self.status_label.pack(pady=20)
        self.tg_label = ctk.CTkLabel(self, text="Telegram: @your_channel", font=("Arial", 12), text_color="gray")
        self.tg_label.pack(side="bottom", pady=10)

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self)
        else:
            self.settings_window.lift()

    def on_close(self):
        self.emergency_stop()
        if self.global_listener:
            self.global_listener.stop()
        self.destroy()

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Настройки")
        self.geometry("520x650")
        self.resizable(False, False)
        self.config = parent.config
        self.create_widgets()
        self.update_colors_from_theme(self.config.get("theme", "dark"))

    def create_widgets(self):
        ctk.CTkLabel(self, text="Масштаб интерфейса", font=("Arial", 14)).pack(pady=10)
        self.scale_var = ctk.DoubleVar(value=self.config.get("ui_scaling", 1.0))
        scale_slider = ctk.CTkSlider(self, from_=0.6, to=2.0, number_of_steps=140, variable=self.scale_var, command=self.on_scale_change)
        scale_slider.pack(pady=5, padx=40, fill="x")
        self.scale_label = ctk.CTkLabel(self, text=f"{self.scale_var.get():.2f}")
        self.scale_label.pack()
        ctk.CTkLabel(self, text="Выбор темы", font=("Arial", 14)).pack(pady=10)
        theme_frame = ctk.CTkFrame(self)
        theme_frame.pack(pady=5)
        self.theme_var = ctk.StringVar(value=self.config.get("theme", "dark"))
        for text, val in [("Светлая", "light"), ("Тёмная", "dark")]:
            rb = ctk.CTkRadioButton(theme_frame, text=text, variable=self.theme_var, value=val, command=self.save_theme)
            rb.pack(side="left", padx=10)
        ctk.CTkLabel(self, text="Область с таймером", font=("Arial", 14)).pack(pady=(20,5))
        region = self.config.get("region")
        self.region_label = ctk.CTkLabel(self, text=f"X:{region['left']} Y:{region['top']} W:{region['width']} H:{region['height']}")
        self.region_label.pack()
        self.select_region_btn = ctk.CTkButton(self, text="Выбрать область", command=self.select_region)
        self.select_region_btn.pack(pady=5)
        ctk.CTkLabel(self, text="Задержка между кликами (мс)", font=("Arial", 14)).pack(pady=(20,5))
        self.click_delay_var = ctk.IntVar(value=self.config.get("click_delay_ms", 15))
        delay_slider = ctk.CTkSlider(self, from_=5, to=50, number_of_steps=45, variable=self.click_delay_var, command=self.update_delay_label)
        delay_slider.pack(pady=5, padx=40, fill="x")
        self.delay_label = ctk.CTkLabel(self, text=f"{self.click_delay_var.get()} мс")
        self.delay_label.pack()
        ctk.CTkLabel(self, text="Начать клики за (сек) до слёта", font=("Arial", 14)).pack(pady=(20,5))
        self.trigger_var = ctk.DoubleVar(value=self.config.get("trigger_seconds", 1.2))
        trigger_slider = ctk.CTkSlider(self, from_=1.0, to=3.0, number_of_steps=40, variable=self.trigger_var, command=self.update_trigger_label)
        trigger_slider.pack(pady=5, padx=40, fill="x")
        self.trigger_label = ctk.CTkLabel(self, text=f"{self.trigger_var.get():.1f} сек")
        self.trigger_label.pack()
        ctk.CTkLabel(self, text="Коррекция времени (мс)", font=("Arial", 14)).pack(pady=(20,5))
        self.calibration_var = ctk.IntVar(value=self.config.get("calibration_ms", 0))
        calib_slider = ctk.CTkSlider(self, from_=-200, to=200, number_of_steps=400, variable=self.calibration_var, command=self.update_calib_label)
        calib_slider.pack(pady=5, padx=40, fill="x")
        self.calib_label = ctk.CTkLabel(self, text=f"{self.calibration_var.get():+d} мс")
        self.calib_label.pack()
        ctk.CTkButton(self, text="Сохранить всё", command=self.save_all).pack(pady=20)

    def on_scale_change(self, value):
        scale = float(value)
        self.scale_label.configure(text=f"{scale:.2f}")
        self.config.set("ui_scaling", scale)
        self.parent.apply_scaling(scale)

    def update_scale(self, scale):
        self.scale_var.set(scale)
        self.scale_label.configure(text=f"{scale:.2f}")

    def save_theme(self):
        theme = self.theme_var.get()
        self.config.set("theme", theme)
        self.parent.apply_theme(theme)
        self.notify("Тема сохранена")

    def select_region(self):
        def on_selected(x, y, w, h):
            self.config.set("region", {"left": x, "top": y, "width": w, "height": h})
            self.region_label.configure(text=f"X:{x} Y:{y} W:{w} H:{h}")
            self.notify("Область сохранена")
        selector = RegionSelector(self, on_selected)
        selector.start()

    def update_delay_label(self, val):
        self.delay_label.configure(text=f"{int(val)} мс")

    def update_trigger_label(self, val):
        self.trigger_label.configure(text=f"{val:.1f} сек")

    def update_calib_label(self, val):
        self.calib_label.configure(text=f"{int(val):+d} мс")

    def save_all(self):
        self.config.set("click_delay_ms", int(self.click_delay_var.get()))
        self.config.set("trigger_seconds", round(self.trigger_var.get(), 1))
        self.config.set("calibration_ms", int(self.calibration_var.get()))
        self.config.set("theme", self.theme_var.get())
        self.notify("Все настройки сохранены")

    def update_colors_from_theme(self, theme):
        if theme == "light":
            bg_color = "#dbdbdb"
            button_color = "#3B8ED0"
        else:
            bg_color = "#2b2b2b"
            button_color = "#3B8ED0"
        self.configure(fg_color=bg_color)
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkButton):
                child.configure(fg_color=button_color)

    def notify(self, msg):
        notif = ctk.CTkLabel(self, text=msg, text_color="green")
        notif.pack(pady=5)
        self.after(2000, notif.destroy)

if __name__ == "__main__":
    app = App()
    app.mainloop()