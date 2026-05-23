import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import sys
import os
from license_manager import generate_key, SECRET_PHRASE

if SECRET_PHRASE == "MySuperSecretPhraseForPavilionBot2024!":
    root_err = ctk.CTk()
    ctk.CTkLabel(root_err, text="ОШИБКА: Сначала настройте SECRET_PHRASE в license_manager.py!", text_color="red").pack(
        pady=20)
    ctk.CTkButton(root_err, text="OK", command=root_err.destroy).pack()
    root_err.mainloop()
    sys.exit(1)

ADMIN_PASSWORD = "455245455245"  # Пароль админа


class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🔐 Вход для администратора")
        self.geometry("350x250")
        self.resizable(False, False)
        self.configure(fg_color="#1a1a1a")

        ctk.CTkLabel(self, text="ВВЕДИТЕ ПАРОЛЬ", font=("Arial", 16, "bold"), text_color="#fff").pack(pady=20)

        self.entry = ctk.CTkEntry(self, show="*", width=250, height=40)
        self.entry.pack(pady=10)
        self.entry.focus()
        self.entry.bind("<Return>", lambda e: self.check_password())

        self.btn = ctk.CTkButton(self, text="ВОЙТИ", command=self.check_password, fg_color="#3B82F6", width=250)
        self.btn.pack(pady=10)

        self.status = ctk.CTkLabel(self, text="", text_color="red")
        self.status.pack()

    def check_password(self):
        if self.entry.get() == ADMIN_PASSWORD:
            self.destroy()
            start_generator()
        else:
            self.status.configure(text="Неверный пароль!")
            self.entry.delete(0, 'end')


class GeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🔑 Генератор ключей")
        self.geometry("550x500")
        self.resizable(True, True)
        self.configure(fg_color="#2b2b2b")

        ctk.CTkLabel(self, text="ГЕНЕРАТОР ЛИЦЕНЗИЙ", font=("Arial", 20, "bold"), text_color="#3B82F6").pack(pady=20)

        frame_opts = ctk.CTkFrame(self, fg_color="transparent")
        frame_opts.pack(pady=10)

        self.var = ctk.StringVar(value="7")
        opts = [("1 день", "1"), ("3 дня", "3"), ("7 дней", "7"), ("30 дней", "30")]

        for text, val in opts:
            rb = ctk.CTkRadioButton(frame_opts, text=text, variable=self.var, value=val)
            rb.pack(side="left", padx=10)

        self.rb_perm = ctk.CTkRadioButton(self, text="♾️ НАВСЕГДА", variable=self.var, value="0",
                                          fg_color="gold", hover_color="orange", text_color="gold")
        self.rb_perm.pack(pady=10)

        self.btn_gen = ctk.CTkButton(self, text="СГЕНЕРИРОВАТЬ", command=self.generate,
                                     fg_color="#10B981", height=50, font=("Arial", 16, "bold"))
        self.btn_gen.pack(pady=20, padx=40, fill="x")

        ctk.CTkLabel(self, text="Ключ:", text_color="#aaa").pack()

        self.result_entry = ctk.CTkEntry(self, width=400, height=40, font=("Courier", 12))
        self.result_entry.pack(pady=10)

        self.btn_copy = ctk.CTkButton(self, text="КОПИРОВАТЬ", command=self.copy_to_clipboard, fg_color="#3B82F6")
        self.btn_copy.pack(pady=5)

    def generate(self):
        try:
            days = int(self.var.get())
            key = generate_key(days)
            self.result_entry.delete(0, 'end')
            self.result_entry.insert(0, key)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def copy_to_clipboard(self):
        key = self.result_entry.get()
        if key:
            self.clipboard_clear()
            self.clipboard_append(key)
            messagebox.showinfo("Успех", "Ключ скопирован!")


def start_generator():
    app = GeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    login = LoginWindow()
    login.mainloop()