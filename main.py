"""main.py - starts Lumen, the scientific calculator."""

import json
import os

from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform

from history import History
from themes import DEFAULT_ACCENT, build_palette
from ui import CalculatorScreen, make_click_sound

DEFAULTS = {"theme": "dark", "accent": DEFAULT_ACCENT, "sound": False,
            "degrees": True, "sci": False}

# keyboard shortcuts for when you use it on the Mac
TEXT_KEYS = {"+": "+", "-": "-", "*": "×", "/": "÷", ".": ".", "(": "(", ")": ")",
             "^": "^", "%": "%", "!": "!", "p": "π", "e": "e"}
for digit in "0123456789":
    TEXT_KEYS[digit] = digit


class LumenApp(App):
    title = "Lumen"

    def build(self):
        folder = self.user_data_dir
        os.makedirs(folder, exist_ok=True)
        self.settings_path = os.path.join(folder, "settings.json")
        self.settings = self.load_settings()

        if platform in ("macosx", "win", "linux"):
            Window.size = (390, 760) # phone-shaped window while developing
        Window.clearcolor = build_palette(self.settings["theme"], self.settings["accent"])["bg"]

        self.screen = CalculatorScreen(self.settings, History(folder), self.save_settings,
                                       make_click_sound(folder))
        Window.bind(on_key_down=self.on_key_down, on_textinput=self.on_textinput)
        return self.screen

    # ---- settings file ----------------------------------------------------
    def load_settings(self):
        settings = dict(DEFAULTS)
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if saved.get("theme") in ("dark", "light"):
                settings["theme"] = saved["theme"]
            accent = saved.get("accent")
            if isinstance(accent, str) and len(accent) == 7 and accent.startswith("#"):
                int(accent[1:], 16)
                settings["accent"] = accent
            for key in ("sound", "degrees", "sci"):
                if isinstance(saved.get(key), bool):
                    settings[key] = saved[key]
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return settings

    def save_settings(self):
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f)
        except OSError:
            pass

    # ---- keyboard ---------------------------------------------------------
    def on_textinput(self, window, text):
        for ch in text:
            if ch == "=":
                self.screen.send("=")
            elif ch in TEXT_KEYS:
                self.screen.send(TEXT_KEYS[ch])

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        if key in (13, 271):
            self.screen.send("=")
        elif key == 8:
            self.screen.send("DEL")

    # ---- phone life-cycle (for Android later) -----------------------------
    def on_pause(self):
        self.save_settings()
        return True

    def on_stop(self):
        self.save_settings()


if __name__ == "__main__":
    LumenApp().run()