import re
import pytesseract
import mss
from PIL import Image

class TimerMonitor:
    def __init__(self, region):
        self.region = region   # dict: left, top, width, height
        self.sct = mss.mss()

    def capture_region(self):
        """Быстрый скриншот области"""
        screenshot = self.sct.grab(self.region)
        # Конвертируем в PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img

    def preprocess_image(self, img):
        """Препроцессинг: оттенки серого + бинаризация"""
        gray = img.convert('L')
        threshold = 150
        binary = gray.point(lambda p: 255 if p > threshold else 0)
        return binary

    def get_remaining_seconds(self):
        """Возвращает float (секунды до слета) или None, если не распознано"""
        img = self.capture_region()
        processed = self.preprocess_image(img)

        custom_config = r'--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.:м'
        try:
            text = pytesseract.image_to_string(processed, config=custom_config, lang='rus+eng')
        except Exception as e:
            print(f"[OCR Error] {e}")
            return None

        # Ищем число с плавающей точкой (например, 44.5)
        numbers = re.findall(r'\d+\.\d+', text)
        if numbers:
            return float(numbers[0])
        # Если не нашли, пробуем целые секунды
        integers = re.findall(r'\b\d+\b', text)
        if integers:
            return float(integers[-1])
        return None