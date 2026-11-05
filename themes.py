"""themes.py - colours for Lumen: two themes + accent colours."""

ACCENTS = [
    ("Electric Blue", "#3D7BFF"),
    ("Violet", "#8B5CF6"),
    ("Emerald", "#10B981"),
    ("Coral", "#FF6B5E"),
    ("Amber", "#F5A524"),
    ("Cyan", "#22D3EE"),
]
DEFAULT_ACCENT = "#8B5CF6"

# Each theme is designed on its own (the light one is NOT an inverted dark one).
THEMES = {
    "dark": { # "Midnight"
        "bg": "#0B1020",
        "display": "#111833",
        "number": "#1A2240",
        "function": "#151C36",
        "clear": "#3A2230",
        "text": "#EEF1FF",
        "text_dim": "#7C86A8",
        "clear_text": "#FF8FA3",
        "accent_mix": 0.22,
    },
    "light": { # "Paper"
        "bg": "#E9E5DE",
        "display": "#F4F1EB",
        "number": "#FBF9F5",
        "function": "#DCD7CE",
        "clear": "#F3D9D4",
        "text": "#23252E",
        "text_dim": "#8A8678",
        "clear_text": "#C2412F",
        "accent_mix": 0.16,
    },
}


def hex_to_rgba(h, alpha=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, alpha)


def mix(c1, c2, t):
    """Blend colour c1 towards c2 by t (0 = all c1, 1 = all c2). RGBA tuples."""
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def readable_on(color):
    """Dark or light text, whichever is easier to read on this colour."""
    luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
    return (0.06, 0.07, 0.10, 1) if luminance > 0.6 else (1, 1, 1, 1)


def build_palette(theme_name, accent_hex):
    """Return every colour the app needs, as Kivy-ready RGBA tuples."""
    t = THEMES[theme_name]
    accent = hex_to_rgba(accent_hex)
    if theme_name == "light": # deeper accent so it stays readable on cream
        accent = mix(accent, (0, 0, 0, 1), 0.18)
    number = hex_to_rgba(t["number"])
    function = hex_to_rgba(t["function"])
    return {
        "bg": hex_to_rgba(t["bg"]),
        "display": hex_to_rgba(t["display"]),
        "text": hex_to_rgba(t["text"]),
        "text_dim": hex_to_rgba(t["text_dim"]),
        "accent": accent,
        "number": number,
        "number_text": hex_to_rgba(t["text"]),
        "function": mix(function, accent, t["accent_mix"] * 0.5),
        "function_text": hex_to_rgba(t["text"]),
        "operator": mix(number, accent, t["accent_mix"] + 0.1),
        "operator_text": accent,
        "clear": hex_to_rgba(t["clear"]),
        "clear_text": hex_to_rgba(t["clear_text"]),
        "equals": accent,
        "equals_text": readable_on(accent),
    }