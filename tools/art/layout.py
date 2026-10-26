"""Shared geometry and look of the AW skins: the renderer (render_assets.py) and the skin generator (gen_skin.py) both
read it, so a knob drawn into a background and a knob placed by the skin always land on the same pixel.

The look is original (procedural, no third-party artwork): a walnut-framed console box, an engraved panel, SSL-style
caps coloured by what the control does (the role), and a per-category accent. Two panel styles, A (graphite) and C (grey).
"""
import re

W, H = 1280, 628                     # the plugin area MPC gives a skin

# knob sizes by control count: radius of the cap collar in px, filmstrip frames (MPC garbles strips over 16384 px)
SIZES = {"large": (64, 48), "normal": (50, 48), "small": (38, 48)}   # 48 frames keep a plugin's filmstrips in MPC's memory budget
ROLES = ["red", "blue", "green", "white", "black", "step"]

# MPC draws a label of "height" h about MPC_K * h tall in a font of that nominal size (measured on a Force, 2026-10-27:
# widths of Titillium Web text matched PIL's at 0.64 * h); text is sized by its visual px P, so the label height is P / MPC_K
MPC_K = 0.64
LEGEND_P = {"large": 26, "normal": 21, "small": 18}
VALUE_P = {"large": 27, "normal": 22, "small": 19}


def mpc_h(p):
    return round(p / MPC_K)


# the panel: frame 46 px; header row (model stepper, description, category plate); one big engraved section
FRAME = 46
SECTION = (84, 146, 1196, 566)       # x0, y0, x1, y1
BTN = (56, 56)
BTN_MODEL = ((100, 62), (612, 62))   # previous / next model, around the model name
MODEL_BOX = (164, 60, 440, 60)       # live model name (between the arrows)
INFO_BOX = (104, 118, 700, 28)       # live one-line description
CAT_PLATE = (836, 66, 360, 36)       # the category accent plate (controls tabs)
PAGE_BOX = (822, 60, 300, 60)        # live "page X / Y", between the page arrows (manual tab)
BTN_PAGE = ((760, 62), (1130, 62))
MANUAL_LINES = (100, 158, 950, 33)   # x, y0, width, line step (12 lines)
LEGEND_BOX = (1066, 170, 120, 380)   # the knob-colour legend, inside the manual panel (swatch left, label right)

STYLES = {
    "A": {"legend": "ffe2e4e8", "value": "ffbcc0c8", "title": "ffe8eaee", "info": "ffb8bcc4", "btn_fill": "ff34373c", "btn_text": "ffe8eaee", "body": "ffd6d9de"},
    "C": {"legend": "ff28282a", "value": "ff48484c", "title": "ff222224", "info": "ff48484c", "btn_fill": "ff8e8e8a", "btn_text": "ff222224", "body": "ff2a2a2c"},
}

# SSL convention: the cap colour says what the control is for
ROLE_RX = [(r"dry/?wet|mix|wet", "white"),
           (r"gain|input|output|drive|trim|level|master|fader|boost|inv|top ?db|air|fire|stone", "red"),
           (r"freq|frq|time|size|big|delay|length|cutoff|filter|rt60|predl|speed|atk|attack|rls|release|sust|range|hipass|highpas|lowpass|lag|spd", "blue"),
           (r"tone|bright|treb|bass|dark|damp|mid|vibr|flavor|distnc|furnish|high|low|reso|crush|more", "green")]
ROLE_LABEL = [("red", "Gain / drive"), ("blue", "Time / freq"), ("green", "Tone"), ("white", "Mix"), ("black", "Other")]


def role_of(name, stepped=False):
    if stepped:
        return "step"
    n = name.lower()
    for rx, r in ROLE_RX:
        if re.search(rx, n):
            return r
    return "black"


def size_of(n):
    return "large" if n <= 3 else "normal" if n <= 7 else "small"


def frame_px(size):
    """Side of one filmstrip frame: room for the scale, its 0/10 labels and the drop shadow."""
    r = SIZES[size][0]
    return int(2 * (1.66 * r + 16)) // 2 * 2 if size != "small" else int(2 * (1.46 * r + 12)) // 2 * 2


def layout(n):
    """Rows of knob centres for n controls (0..14) -> (rows, size name, legend dy, value dy, bracket dy)."""
    if n == 0:
        return [], None, 0, 0, 0
    sz = size_of(n); r = SIZES[sz][0]
    if n <= 7:
        cy = 352
        step = 0 if n == 1 else (300 if n <= 3 else min(190, 1100 / n))
        row = [(640 + (i - (n - 1) / 2) * step, cy) for i in range(n)]
        return [row], sz, -(1.46 * r + 24), 1.17 * r + 30, 1.17 * r + 62
    k1 = (n + 1) // 2; k2 = n - k1; rows = []
    st = min(160, 1100 / max(k1, k2))
    for k, cy in ((k1, 252), (k2, 440)):
        rows.append([(640 + (i - (k - 1) / 2) * st, cy) for i in range(k)])
    return rows, sz, -(1.46 * r + 18), 1.17 * r + 22, 0


GROUP = [(0.95, 0.62, 0.15), (0.30, 0.72, 0.85), (0.80, 0.45, 0.80), (0.55, 0.80, 0.35)]   # Q-Link column colours

# category accents (footer LED and plate), one per upstream category
ACCENT = {"Ambience": (0.25, 0.75, 0.70), "Amp Sims": (0.95, 0.55, 0.15), "Bass": (0.75, 0.20, 0.20), "Biquads": (0.50, 0.55, 0.75),
          "Brightness": (0.95, 0.85, 0.25), "Clipping": (0.85, 0.30, 0.65), "Consoles": (0.85, 0.20, 0.20), "Distortion": (0.95, 0.40, 0.15),
          "Dithers": (0.60, 0.60, 0.62), "Dynamics": (0.30, 0.75, 0.35), "Effects": (0.65, 0.45, 0.90), "Filter": (0.30, 0.55, 0.90),
          "Lo-Fi": (0.70, 0.55, 0.35), "Noise": (0.55, 0.55, 0.55), "Reverb": (0.25, 0.50, 0.90), "Saturation": (0.90, 0.60, 0.20),
          "Stereo": (0.35, 0.80, 0.85), "Subtlety": (0.75, 0.75, 0.50), "Tape": (0.80, 0.50, 0.30), "Tone Color": (0.90, 0.45, 0.55),
          "Unclassified": (0.65, 0.65, 0.65), "Utility": (0.55, 0.65, 0.70), "XYZ Filters": (0.45, 0.60, 0.95)}
