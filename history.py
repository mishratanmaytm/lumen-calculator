"""history.py - remembers past calculations and saves them to a file."""

import json
import os

MAX_ITEMS = 100


class History:
    def __init__(self, folder):
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, "history.json")
        self.items = [] # newest first: [{"expr": "9×8", "result": "72"}, ...]
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.items = [x for x in data if "expr" in x and "result" in x][:MAX_ITEMS]
        except (OSError, ValueError, TypeError):
            self.items = []

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.items, f, ensure_ascii=False)
        except OSError:
            pass # saving is nice-to-have; never crash the app

    def add(self, expr, result):
        if self.items and self.items[0] == {"expr": expr, "result": result}:
            return
        self.items.insert(0, {"expr": expr, "result": result})
        del self.items[MAX_ITEMS:]
        self.save()

    def clear(self):
        self.items = []
        self.save()