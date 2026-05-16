import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import is_admin, run_as_admin, check_tesseract, set_tesseract_path
import gui

if __name__ == "__main__":
    if not is_admin():
        print("Требуются права администратора. Перезапуск...")
        run_as_admin()
    ok, msg = check_tesseract()
    if not ok:
        import tkinter.messagebox as mb
        mb.showerror("Ошибка", msg + "\n\nПрограмма закроется.")
        sys.exit(1)
    set_tesseract_path()
    app = gui.App()
    app.mainloop()