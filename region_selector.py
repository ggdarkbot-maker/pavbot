import tkinter as tk
import mss
import sys
import os
from PIL import Image, ImageTk


def take_screenshot_and_select():
    # Создаем скрытое корневое окно
    root = tk.Tk()
    root.withdraw()

    try:
        # Быстрый скриншот
        with mss.mss() as sct:
            mon = sct.monitors[1]
            img = sct.grab(mon)

        # Конвертация изображения
        img_pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        bg_image = ImageTk.PhotoImage(img_pil)

        # Окно выделения
        selector = tk.Toplevel(root)
        selector.title("Select Region")
        selector.attributes('-fullscreen', True)
        selector.attributes('-topmost', True)
        selector.configure(cursor="cross")
        selector.overrideredirect(True)  # Убираем рамки Windows для скорости

        canvas = tk.Canvas(selector, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        # Устанавливаем фон
        canvas.bg_img = bg_image  # Сохраняем ссылку, чтобы не удалился сборщиком мусора
        canvas.create_image(0, 0, anchor=tk.NW, image=bg_image)

        # Полупрозрачный оверлей (серый)
        overlay_id = canvas.create_rectangle(0, 0, img.size[0], img.size[1], fill="gray", stipple="gray50")

        rect_id = None
        start_x = 0
        start_y = 0

        def on_press(event):
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            # Удаляем старый прямоугольник если есть
            if rect_id: canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='#00FF00', width=2)

        def on_drag(event):
            if rect_id:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)

        def on_release(event):
            x1, y1 = min(start_x, event.x), min(start_y, event.y)
            x2, y2 = max(start_x, event.x), max(start_y, event.y)
            w, h = x2 - x1, y2 - y1

            # Возвращаем координаты
            if w > 10 and h > 10:
                print(f"{x1},{y1},{w},{h}")
                sys.stdout.flush()

            # Корректное закрытие
            selector.destroy()
            root.destroy()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        selector.bind("<Escape>", lambda e: (selector.destroy(), root.destroy()))

        selector.mainloop()

    except Exception as e:
        print(f"ERROR:{str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            root.destroy()
        except:
            pass


if __name__ == "__main__":
    take_screenshot_and_select()