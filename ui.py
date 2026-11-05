"""ui.py - everything you see on screen in Lumen."""

import colorsys
import math
import os
import struct
import wave

from kivy.animation import Animation
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider

from entry import Entry, plain_number
from themes import ACCENTS, build_palette, hex_to_rgba, mix, readable_on

# (label, what it types, button style)
KEYS = [
    [("π", "π", "function"), ("e", "e", "function"), ("^", "^", "function"), ("%", "%", "function")],
    [("AC", "AC", "clear"), ("(", "(", "function"), (")", ")", "function"), ("÷", "÷", "operator")],
    [("7", "7", "number"), ("8", "8", "number"), ("9", "9", "number"), ("×", "×", "operator")],
    [("4", "4", "number"), ("5", "5", "number"), ("6", "6", "number"), ("–", "-", "operator")],
    [("1", "1", "number"), ("2", "2", "number"), ("3", "3", "number"), ("+", "+", "operator")],
    [("0", "0", "number"), (".", ".", "number"), ("DEL", "DEL", "clear"), ("=", "=", "equals")],
]

# The scientific drawer: three tabs, one row of big buttons each.
TABS = [
    ("Trig", [("sin", "sin("), ("cos", "cos("), ("tan", "tan("),
              ("asin", "asin("), ("acos", "acos("), ("atan", "atan(")]),
    ("Log & Roots", [("log", "log("), ("ln", "ln("), ("sqrt", "sqrt("),
                     ("abs", "abs("), ("x²", "^2"), ("n!", "!")]),
    ("More", [("Ans", "ANS"), ("x³", "^3"), ("10^x", "10^"),
              ("e^x", "e^"), ("1/x", "1÷(")]),
]
DRAWER_HEIGHT = dp(100)


def make_click_sound(folder):
    """Creates a tiny click sound file (once) so we don't need any assets."""
    path = os.path.join(folder, "click.wav")
    try:
        if not os.path.exists(path):
            rate = 22050
            n = int(rate * 0.03)
            frames = bytearray()
            for i in range(n):
                fade = 1 - i / n
                value = int(9000 * fade * fade * math.sin(2 * math.pi * 1800 * i / rate))
                frames += struct.pack("<h", value)
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(bytes(frames))
    except Exception:
        return None
    return path


def left(label):
    label.halign = "left"
    label.valign = "middle"
    label.bind(size=lambda lbl, size: setattr(lbl, "text_size", size))
    return label


# ---------------------------------------------------------------- building blocks
class Card(BoxLayout):
    """A box with a rounded coloured background."""

    def __init__(self, radius=None, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._color = Color(0.1, 0.1, 0.2, 1)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size,
                                          radius=[radius or dp(22)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def set_color(self, rgba):
        self._color.rgba = rgba


class RoundButton(ButtonBehavior, Label):
    """A rounded button that squishes a little when pressed."""

    glow = NumericProperty(0)

    def __init__(self, text="", kind="number", value=None, radius=None, size_sp=22, **kw):
        super().__init__(text=text, font_size=sp(size_sp), **kw)
        self.kind = kind
        self.value = text if value is None else value
        self.fixed_bg = None # used by the accent colour dots
        self.palette = None
        self._base = (0.2, 0.2, 0.3, 1)
        self._hint = (1, 1, 1, 1)
        with self.canvas.before:
            self._color = Color(*self._base)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size,
                                          radius=[radius or dp(16)])
        self.bind(pos=self._sync, size=self._sync, glow=self._sync)

    def _sync(self, *args):
        inset = self.glow * dp(2.5)
        self._rect.pos = (self.x + inset, self.y + inset)
        self._rect.size = (max(0, self.width - 2 * inset), max(0, self.height - 2 * inset))
        self._color.rgba = mix(self._base, self._hint, 0.14 * self.glow)

    def on_state(self, widget, value):
        Animation.cancel_all(self, "glow")
        if value == "down":
            Animation(glow=1, d=0.06).start(self)
        else:
            Animation(glow=0, d=0.2, t="out_quad").start(self)

    def set_palette(self, p):
        self.palette = p
        self._base = self.fixed_bg or p[self.kind]
        self._hint = p["text"]
        if not self.fixed_bg:
            self.color = p[self.kind + "_text"]
        self._sync()

    def set_kind(self, kind):
        self.kind = kind
        if self.palette:
            self.set_palette(self.palette)


class TapLabel(ButtonBehavior, Label):
    """A label you can tap."""


# ---------------------------------------------------------------- popups
class Sheet(ModalView):
    """A rounded popup panel. Settings and History are built on this."""

    def __init__(self, palette, size_hint=(0.92, 0.8), **kw):
        super().__init__(size_hint=size_hint, background="", background_color=(0, 0, 0, 0),
                         overlay_color=(0, 0, 0, 0.55), **kw)
        self.card = Card(orientation="vertical", padding=dp(18), spacing=dp(12))
        self.add_widget(self.card)
        self.buttons = []
        self.labels = []
        self.p = palette
        self.restyle(palette)

    def label(self, text, size=16, dim=False, **kw):
        lbl = left(Label(text=text, font_size=sp(size), **kw))
        self.labels.append((lbl, "text_dim" if dim else "text"))
        return lbl

    def button(self, text, kind="function", **kw):
        b = RoundButton(text, kind=kind, **kw)
        self.buttons.append(b)
        b.set_palette(self.p)
        return b

    def restyle(self, p):
        self.p = p
        self.card.set_color(p["display"])
        for lbl, role in self.labels:
            lbl.color = p[role]
        for b in self.buttons:
            b.set_palette(p)


class HistorySheet(Sheet):
    def __init__(self, palette, history, on_use_expr, on_use_answer, **kw):
        super().__init__(palette, size_hint=(0.92, 0.78), **kw)
        self.history = history
        self.on_use_expr = on_use_expr
        self.on_use_answer = on_use_answer

        head = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        head.add_widget(self.label("History", 22, bold=True))
        clear = self.button("Clear", kind="clear", size_sp=14, radius=dp(12),
                            size_hint=(None, 1), width=dp(72))
        clear.bind(on_release=lambda w: self._clear())
        head.add_widget(clear)
        self.card.add_widget(head)

        hint = self.label("Tap an expression to edit it, or an answer to use it.", 12, dim=True,
                          size_hint_y=None, height=dp(18))
        self.card.add_widget(hint)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.list.bind(minimum_height=self.list.setter("height"))
        scroll.add_widget(self.list)
        self.card.add_widget(scroll)
        self.fill()

    def fill(self):
        p = self.p
        self.list.clear_widgets()
        if not self.history.items:
            self.list.add_widget(Label(
                text="Nothing here yet.\nYour calculations will show up here.",
                font_size=sp(15), color=p["text_dim"], size_hint_y=None, height=dp(140),
                halign="center"))
            return
        for item in self.history.items:
            row = Card(radius=dp(14), size_hint_y=None, height=dp(64),
                       padding=[dp(14), 0, dp(14), 0], spacing=dp(6))
            row.set_color(mix(p["display"], p["text"], 0.07))
            expr = TapLabel(text=item["expr"], font_size=sp(16), color=p["text_dim"],
                            halign="left", valign="middle", shorten=True,
                            shorten_from="left", size_hint_x=0.55)
            expr.bind(size=lambda lbl, size: setattr(lbl, "text_size", size))
            expr.bind(on_release=lambda w, e=item["expr"]: self._use_expr(e))
            result = TapLabel(text="= " + item["result"], font_size=sp(22), color=p["accent"],
                              halign="right", valign="middle", shorten=True,
                              shorten_from="right", size_hint_x=0.45)
            result.bind(size=lambda lbl, size: setattr(lbl, "text_size", size))
            result.bind(on_release=lambda w, r=item["result"]: self._use_answer(r))
            row.add_widget(expr)
            row.add_widget(result)
            self.list.add_widget(row)

    def _use_expr(self, expr):
        self.dismiss()
        self.on_use_expr(expr)

    def _use_answer(self, result):
        self.dismiss()
        self.on_use_answer(result)

    def _clear(self):
        self.history.clear()
        self.fill()


class SettingsSheet(Sheet):
    def __init__(self, palette, settings, on_change, **kw):
        super().__init__(palette, size_hint=(0.92, None), **kw)
        self.height = dp(440)
        self.settings = settings
        self.on_change = on_change
        self._lock = False
        c = self.card

        c.add_widget(self.label("Settings", 22, bold=True, size_hint_y=None, height=dp(34)))

        c.add_widget(self._caption("Theme"))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        self.theme_btns = {}
        for key, name in (("dark", "Midnight"), ("light", "Paper")):
            b = self.button(name, size_sp=15, radius=dp(14))
            b.bind(on_release=lambda w, k=key: self.on_change("theme", k, True))
            self.theme_btns[key] = b
            row.add_widget(b)
        c.add_widget(row)

        c.add_widget(self._caption("Accent colour"))
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.dots = []
        for name, hx in ACCENTS:
            d = RoundButton("", size_sp=22, radius=dp(16))
            d.fixed_bg = hex_to_rgba(hx)
            d.color = readable_on(d.fixed_bg)
            d.hex = hx
            d.set_palette(self.p)
            d.bind(on_release=lambda w, h=hx: self._pick(h))
            self.buttons.append(d)
            self.dots.append(d)
            row.add_widget(d)
        c.add_widget(row)

        c.add_widget(self._caption("Custom colour"))
        hue = colorsys.rgb_to_hsv(*hex_to_rgba(settings["accent"])[:3])[0] * 360
        self.slider = Slider(min=0, max=360, value=hue, size_hint_y=None, height=dp(40),
                             cursor_size=(dp(28), dp(28)), value_track=True)
        self.slider.bind(value=self._slide)
        c.add_widget(self.slider)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        row.add_widget(self.label("Key sounds", 16))
        self.sound_btn = self.button("Off", size_sp=15, radius=dp(14),
                                     size_hint=(None, 1), width=dp(90))
        self.sound_btn.bind(on_release=lambda w: self.on_change(
            "sound", not self.settings.get("sound"), False))
        row.add_widget(self.sound_btn)
        c.add_widget(row)

        done = self.button("Done", kind="equals", size_sp=17, size_hint_y=None, height=dp(48))
        done.bind(on_release=lambda w: self.dismiss())
        c.add_widget(done)
        self.restyle(palette)
        self.refresh_selection()

    def _caption(self, text):
        return self.label(text, 13, dim=True, size_hint_y=None, height=dp(20))

    def _pick(self, hex_colour):
        hue = colorsys.rgb_to_hsv(*hex_to_rgba(hex_colour)[:3])[0] * 360
        self._lock = True
        self.slider.value = hue
        self._lock = False
        self.on_change("accent", hex_colour, True)

    def _slide(self, slider, value):
        if self._lock:
            return
        r, g, b = colorsys.hsv_to_rgb(value / 360, 0.70, 1.0)
        self.on_change("accent", "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255)),
                       False)

    def refresh_selection(self):
        for key, b in self.theme_btns.items():
            b.set_kind("equals" if self.settings["theme"] == key else "function")
        for d in self.dots:
            d.text = "•" if d.hex.lower() == self.settings["accent"].lower() else ""
        on = bool(self.settings.get("sound"))
        self.sound_btn.text = "On" if on else "Off"
        self.sound_btn.set_kind("equals" if on else "function")

    def restyle(self, p):
        super().restyle(p)
        if hasattr(self, "slider"):
            self.slider.value_track_color = p["accent"]


# ---------------------------------------------------------------- main screen
class CalculatorScreen(BoxLayout):
    def __init__(self, settings, history, on_save, sound_path, **kw):
        super().__init__(orientation="vertical", padding=[dp(14), dp(10), dp(14), dp(14)],
                         spacing=dp(10), **kw)
        self.settings = settings
        self.history = history
        self.on_save = on_save
        self.entry = Entry(history)
        self.entry.degrees = bool(settings.get("degrees", True))
        self.sci = False
        self.sheet = None
        self.buttons = []
        self.palette = build_palette(settings["theme"], settings["accent"])

        self.sound = None
        try:
            if sound_path:
                self.sound = SoundLoader.load(sound_path)
        except Exception:
            self.sound = None

        with self.canvas.before:
            self._bg = Color(*self.palette["bg"])
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self._build_top_bar()
        self._build_display()

        area = BoxLayout(orientation="vertical", size_hint_y=0.68, spacing=0)
        self._build_drawer()
        area.add_widget(self.drawer)
        self._build_keypad()
        area.add_widget(self.keypad)
        self.add_widget(area)

        self.apply_theme(animate=False)
        self.show_tab("Trig")
        if settings.get("sci"):
            self.toggle_sci(animate=False)

    def _sync_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    # ---- building ---------------------------------------------------------
    def _wire(self, button):
        button.bind(on_press=self._click, on_release=lambda b: self.send(b.value))
        self.buttons.append(button)
        return button

    def _pill(self, text, callback, kind):
        b = RoundButton(text, kind=kind, size_sp=13, radius=dp(12), size_hint=(None, 1),
                        width=dp(54))
        b.bind(on_press=self._click, on_release=lambda w: callback())
        self.buttons.append(b)
        return b

    def _build_top_bar(self):
        bar = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.title = left(Label(text="LUMEN", bold=True, font_size=sp(15)))
        bar.add_widget(self.title)
        self.deg_btn = self._pill("DEG" if self.entry.degrees else "RAD", self.toggle_angle,
                                  "operator")
        self.sci_btn = self._pill("SCI", self.toggle_sci, "function")
        self.hist_btn = self._pill("HIST", self.open_history, "function")
        self.set_btn = self._pill("SET", self.open_settings, "function")
        for b in (self.deg_btn, self.sci_btn, self.hist_btn, self.set_btn):
            bar.add_widget(b)
        self.add_widget(bar)

    def _line(self, **kw):
        lbl = Label(halign="right", shorten=True, shorten_from="left", **kw)
        lbl.bind(size=lambda l, size: setattr(l, "text_size", size))
        return lbl

    def _build_display(self):
        self.card = Card(orientation="vertical", size_hint_y=0.32,
                         padding=[dp(16), dp(8), dp(16), dp(10)])
        self.prev_label = self._line(font_size=sp(14), valign="middle",
                                     size_hint_y=None, height=dp(20))
        self.expr_label = self._line(font_size=sp(46), valign="bottom", size_hint_y=0.5)
        self.result_label = self._line(font_size=sp(24), valign="top", size_hint_y=0.5)
        for w in (self.prev_label, self.expr_label, self.result_label):
            self.card.add_widget(w)
        self.card.bind(size=lambda *a: self.refresh(False))
        self.add_widget(self.card)

    def _build_drawer(self):
        self.drawer = BoxLayout(orientation="vertical", size_hint_y=None, height=0, opacity=0,
                                spacing=dp(8), padding=[0, 0, 0, dp(10)], disabled=True)
        tabs = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        self.fn_grid = GridLayout(cols=6, size_hint_y=None, height=dp(48), spacing=dp(8))
        self.tab_btns = {}
        self.fn_buttons = {}
        for name, items in TABS:
            chip = RoundButton(name, kind="function", size_sp=13, radius=dp(12))
            chip.bind(on_press=self._click, on_release=lambda w, n=name: self.show_tab(n))
            self.buttons.append(chip)
            self.tab_btns[name] = chip
            tabs.add_widget(chip)
            self.fn_buttons[name] = []
            for label, value in items:
                b = RoundButton(label, kind="function", value=value, size_sp=15, radius=dp(12))
                self._wire(b)
                self.fn_buttons[name].append(b)
        self.drawer.add_widget(tabs)
        self.drawer.add_widget(self.fn_grid)

    def _build_keypad(self):
        self.keypad = GridLayout(cols=4, spacing=dp(10))
        sizes = {"number": 28, "operator": 30, "function": 22, "clear": 20, "equals": 32}
        for row in KEYS:
            for label, value, kind in row:
                b = RoundButton(label, kind=kind, value=value, size_sp=sizes[kind])
                self._wire(b)
                self.keypad.add_widget(b)

    # ---- keys -------------------------------------------------------------
    def _click(self, *args):
        if self.sound and self.settings.get("sound"):
            try:
                self.sound.stop()
                self.sound.volume = 0.35
                self.sound.play()
            except Exception:
                pass

    def send(self, value):
        entry = self.entry
        before = entry.status
        done = entry.press(value)
        self.refresh(animate=(before != entry.status or done),
                     pulse=(done or entry.status == "error"))

    # ---- display ----------------------------------------------------------
    def _fit(self, text, base, smallest, label):
        width = label.width if label.width > 50 else dp(300)
        chars_that_fit = width / (0.56 * base)
        n = max(len(text), 1)
        return base if n <= chars_that_fit else max(smallest, base * chars_that_fit / n)

    def refresh(self, animate=False, pulse=False):
        p, e = self.palette, self.entry
        big = max(sp(30), min(sp(60), self.result_label.height * 0.78))
        if e.status == "typing":
            expr_text = e.expr or "0"
            expr_size = self._fit(expr_text, sp(46), sp(22), self.expr_label)
            expr_color = p["text"] if e.expr else p["text_dim"]
            res_text, res_size, res_color = e.preview(), sp(24), p["text_dim"]
        elif e.status == "result":
            expr_text = e.expr
            expr_size = self._fit(expr_text, sp(22), sp(14), self.expr_label)
            expr_color = p["text_dim"]
            res_text, res_color = e.answer, p["accent"]
            res_size = self._fit(res_text, big, sp(26),self.result_label)
        else:
            expr_text = e.expr
            expr_size = self._fit(expr_text, sp(34), sp(18), self.expr_label)
            expr_color = p["text"]
            res_text, res_size, res_color = e.error, sp(22), p["clear_text"]

        self.prev_label.text = e.last_line if e.status == "typing" else ""
        self.prev_label.color = p["text_dim"]
        self.expr_label.text = expr_text
        self.result_label.text = res_text

        for label in (self.expr_label, self.result_label):
            Animation.cancel_all(label)
        if animate:
            ease = dict(d=0.22, t="out_cubic")
            Animation(font_size=expr_size, color=expr_color, **ease).start(self.expr_label)
            Animation(font_size=res_size, color=res_color, **ease).start(self.result_label)
        else:
            self.expr_label.font_size, self.expr_label.color = expr_size, expr_color
            self.result_label.font_size, self.result_label.color = res_size, res_color
        if pulse:
            self.result_label.opacity = 0.25
            Animation(opacity=1, d=0.3).start(self.result_label)
        else:
            self.result_label.opacity = 1

    # ---- modes ------------------------------------------------------------
    def toggle_angle(self):
        self.entry.degrees = not self.entry.degrees
        self.settings["degrees"] = self.entry.degrees
        self.deg_btn.text = "DEG" if self.entry.degrees else "RAD"
        self.refresh(False)
        self.on_save()

    def toggle_sci(self, animate=True):
        self.sci = not self.sci
        self.settings["sci"] = self.sci
        self.sci_btn.set_kind("equals" if self.sci else "function")
        height = DRAWER_HEIGHT if self.sci else 0
        opacity = 1 if self.sci else 0
        Animation.cancel_all(self.drawer)
        if self.sci:
            self.drawer.disabled = False
        if animate:
            anim = Animation(height=height, opacity=opacity, d=0.28, t="out_cubic")
            if not self.sci:
                anim.bind(on_complete=lambda *a: setattr(self.drawer, "disabled", True))
            anim.start(self.drawer)
        else:
            self.drawer.height, self.drawer.opacity = height, opacity
            self.drawer.disabled = not self.sci
        self.on_save()

    def show_tab(self, name):
        for tab, chip in self.tab_btns.items():
            chip.set_kind("operator" if tab == name else "function")
        self.fn_grid.clear_widgets()
        for b in self.fn_buttons[name]:
            self.fn_grid.add_widget(b)
        self.fn_grid.opacity = 0
        Animation(opacity=1, d=0.18).start(self.fn_grid)

    # ---- theme ------------------------------------------------------------
    def apply_theme(self, animate=True):
        def apply(*args):
            p = self.palette = build_palette(self.settings["theme"], self.settings["accent"])
            self._bg.rgba = p["bg"]
            self.card.set_color(p["display"])
            self.title.color = p["text_dim"]
            for b in self.buttons:
                b.set_palette(p)
            self.refresh(False)
            if self.sheet:
                self.sheet.restyle(p)

        if animate:
            Animation.cancel_all(self, "opacity")
            fade_out = Animation(opacity=0, d=0.1)
            fade_out.bind(on_complete=lambda *a: (apply(), Animation(opacity=1, d=0.2).start(self)))
            fade_out.start(self)
        else:
            apply()

    def on_setting(self, key, value, animate=True):
        self.settings[key] = value
        if key in ("theme", "accent"):
            self.apply_theme(animate)
        self.on_save()
        if self.sheet:
            self.sheet.refresh_selection()

    # ---- popups -----------------------------------------------------------
    def open_settings(self):
        self.sheet = SettingsSheet(self.palette, self.settings, self.on_setting)
        self.sheet.bind(on_dismiss=lambda *a: setattr(self, "sheet", None))
        self.sheet.open()

    def open_history(self):
        HistorySheet(self.palette, self.history, self.use_expression, self.use_answer).open()

    def use_expression(self, expr):
        self.entry.expr, self.entry.status, self.entry.last_line = expr, "typing", ""
        self.refresh(True)

    def use_answer(self, text):
        self.entry.expr, self.entry.status, self.entry.last_line = plain_number(text), "typing", ""
        self.refresh(True)