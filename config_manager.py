import json
import os

DEFAULT_CONFIG = {
    "region": {"left": 53, "top": 599, "width": 261, "height": 111},
    "click_delay_ms": 15,
    "trigger_seconds": 1.2,
    "calibration_ms": 0,
    "theme": "dark",
    "ui_scaling": 1.0,                # новая опция
    "custom_bg_color": "#2b2b2b",
    "custom_text_color": "#ffffff",
    "custom_button_color": "#3B8ED0",
    "hotkey_stop": "f12"
}

class ConfigManager:
    def __init__(self, filepath="config.json"):
        self.filepath = filepath
        self.config = self.load()

    def load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                saved = json.load(f)
                return {**DEFAULT_CONFIG, **saved}
        return DEFAULT_CONFIG.copy()

    def save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()