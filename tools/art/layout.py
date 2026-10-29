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
SECTION = (84, 152, 1196, 566)       # x0, y0, x1, y1
BTN = (56, 56)
BTN_MODEL = ((100, 54), (612, 54))   # previous / next model, around the model name
MODEL_BOX = (164, 52, 440, 60)       # live model name (between the arrows)
INFO_BOX = (104, 112, 700, 28)       # live one-line description
CAT_PLATE = (836, 58, 360, 36)       # the category accent plate (controls tabs)
PAGE_BOX = (940, 52, 150, 60)        # live "page X / Y", between the page arrows (manual tab)
BTN_PAGE = ((876, 54), (1098, 54))
MANUAL_LINES = (100, 178, 950, 31)   # x, y0, width, line step (12 lines)
LEGEND_BOX = (1066, 190, 120, 360)   # the knob-colour legend, inside the manual panel (swatch left, label right)

STYLES = {
    "A": {"legend": "ffe2e4e8", "value": "ffbcc0c8", "title": "ffe8eaee", "info": "ffb8bcc4", "btn_fill": "ff34373c", "btn_text": "ffe8eaee", "body": "ffd6d9de"},
    "C": {"legend": "ff28282a", "value": "ff48484c", "title": "ff222224", "info": "ff48484c", "btn_fill": "ff8e8e8a", "btn_text": "ff222224", "body": "ff2a2a2c"},
}

# SSL convention: the cap colour says what the control is for
ROLE_RX = [(r"dry/?wet|mix|wet", "white"),
           (r"gain|input|output|drive|trim|level|master|fader|boost|inv|top ?db|air|fire|stone", "red"),
           (r"freq|frq|time|size|big|delay|length|cutoff|filter|rt60|predl|speed|atk|attack|rls|release|sust|range|hipass|highpas|lowpass|lag|spd", "blue"),
           (r"tone|bright|treb|bass|dark|damp|mid|vibr|flavor|distnc|furnish|high|low|reso|crush|more", "green")]
ROLE_LABEL = [("red", "Gain"), ("blue", "Time"), ("green", "Tone"), ("white", "Mix"), ("black", "Other")]


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


# Q-Link badge: centre offset left of the knob centre, clear of a typical name (85th percentile width / 2 + badge radius)
BADGE_DX = {"large": 67, "normal": 58, "small": 50}

GROUP = [(0.95, 0.62, 0.15), (0.30, 0.72, 0.85), (0.80, 0.45, 0.80), (0.55, 0.80, 0.35)]   # Q-Link column colours

# category accents (footer LED and plate), one per upstream category
ACCENT = {"Console Strips": (0.80, 0.18, 0.30), "Ambience": (0.25, 0.75, 0.70), "Amp Sims": (0.95, 0.55, 0.15), "Bass": (0.75, 0.20, 0.20), "Biquads": (0.50, 0.55, 0.75),
          "Brightness": (0.95, 0.85, 0.25), "Clipping": (0.85, 0.30, 0.65), "Consoles": (0.85, 0.20, 0.20), "Distortion": (0.95, 0.40, 0.15),
          "Dithers": (0.60, 0.60, 0.62), "Dynamics": (0.30, 0.75, 0.35), "Effects": (0.65, 0.45, 0.90), "Filter": (0.30, 0.55, 0.90),
          "Lo-Fi": (0.70, 0.55, 0.35), "Noise": (0.55, 0.55, 0.55), "Reverb": (0.25, 0.50, 0.90), "Saturation": (0.90, 0.60, 0.20),
          "Stereo": (0.35, 0.80, 0.85), "Subtlety": (0.75, 0.75, 0.50), "Tape": (0.80, 0.50, 0.30), "Tone Color": (0.90, 0.45, 0.55),
          "Unclassified": (0.65, 0.65, 0.65), "Utility": (0.55, 0.65, 0.70), "XYZ Filters": (0.45, 0.60, 0.95)}


# ---- Console Strips: the controls of one model grouped onto tabs of at most STRIP_TAB controls ------------------------------
# a tab is rows of sections, each (title, [control names]); one tab holds at most STRIP_TAB = PAGE controls (14, the same as a Consoles page)
STRIP_TAB = 14
_EQ_X = [[("TREBLE", ["Tr Freq", "Treble", "Tr Reso"]), ("HIGH MID", ["HM Freq", "HighMid", "HM Reso"])],
         [("LOW MID", ["LM Freq", "LowMid", "LM Reso"]), ("BASS", ["Bs Freq", "Bass", "Bs Reso"])]]
_EQ_H = [[("TREBLE", ["Tr Freq", "Treble", "TrCrush"]), ("HIGH MID", ["HM Freq", "HighMid", "HMCrush"])],
         [("LOW MID", ["LM Freq", "LowMid", "LMCrush"]), ("BASS", ["Bs Freq", "Bass", "BsCrush"])]]
STRIP_TABS = {
    "X": [[[("FILTER", ["Highpas", "Lowpass"]), ("TONE", ["Air", "Fire", "Stone", "Range"]), ("OUTPUT", ["Top dB", "Pan", "Fader"])]],
          _EQ_X,
          [[("FAST COMPRESSOR", ["FC Thrs", "FC Rati", "FC Atk", "FC Rls"]), ("SLOW COMPRESSOR", ["SC Thrs", "SC Rati", "SC Atk", "SC Rls"])]],
          [[("FAST GATE", ["FG Thrs", "FG Rati", "FG Sust", "FG Rls"]), ("SLOW GATE", ["SG Thrs", "SG Rati", "SG Sust", "SG Rls"])]]],
    "H": [[[("INPUT", ["Trim", "More"]), ("SHAPE", ["High", "Mid", "Low", "CrossFd"]), ("DYNAMICS", ["Thresh", "Attack", "Release", "Gate"])],
           [("FILTER", ["Hipass", "Lowpass"]), ("OUTPUT", ["Pan", "Fader"])]],
          _EQ_H],
    "X2": [[[("INPUT", ["Trim", "More"]), ("EQ", ["High", "HMid", "LMid", "Bass"])], [("EQ FREQUENCY", ["HighF", "HMidF", "LMidF", "BassF"])]],
           [[("DYNAMICS", ["Thresh", "Attack", "Release", "Gate"])], [("FILTER", ["Hipass", "Lowpass"]), ("OUTPUT", ["Pan", "Fader"])]]],
    "X3": [[[("EQ", ["High", "HMid", "LMid", "Bass"]), ("EQ FREQUENCY", ["HighF", "HMidF", "LMidF", "BassF"])], [("DYNAMICS", ["Thresh", "Attack", "Release"])]],
           [[("INPUT", ["Input", "Inv/Wet", "Cha/Bus", "Smooth", "More"])], [("FILTER", ["Hipass", "HipassQ", "Lowpass", "LowpasQ"]), ("OUTPUT", ["Pan", "Fader"])]]],
}
STRIP_OF = {"ConsoleXBuss": "X", "ConsoleXChannel": "X", "ConsoleXPre": "X", "ConsoleHChannel": "H", "ConsoleHPre": "H",
            "ConsoleX2Channel": "X2", "ConsoleX2Pre": "X2", "ConsoleX3": "X3"}
STRIP_DROP = {"ConsoleX2Pre": ["Pan"], "ConsoleHPre": ["Pan"]}
STRIP_NTABS = max(len(t) for t in STRIP_TABS.values())


def strip_variant(model):
    """-> (key, tabs) for a strips model: tabs of rows of sections, minus controls the model lacks. Models of one key share backgrounds."""
    fam = STRIP_OF[model]; drop = STRIP_DROP.get(model, [])
    tabs = []
    for tab in STRIP_TABS[fam]:
        rows = []
        for row in tab:
            secs = [(t, [n for n in ns if n not in drop]) for t, ns in row]
            secs = [(t, ns) for t, ns in secs if ns]
            if secs:
                rows.append(secs)
        tabs.append(rows)
    return fam + ("p" if drop else ""), tabs


STRIP_VARIANTS = dict(strip_variant(m) for m in STRIP_OF)


def strip_slot_order(model):
    """The model's controls in tab order, each tab padded to STRIP_TAB slots with None: the engine's slot map (slot -> control name)."""
    key, tabs = strip_variant(model); out = []
    for rows in tabs:
        names = [n for row in rows for _, ns in row for n in ns]
        assert len(names) <= STRIP_TAB, (model, len(names))
        out += names + [None] * (STRIP_TAB - len(names))
    return out + [None] * (STRIP_TAB * (STRIP_NTABS - len(tabs)))


def strip_geometry(rows):
    """One tab -> (sections [(title, (x0, y0, x1, y1), title_xy)], cells {name: (cx, cy)}, cell_w, rowcy). Knobs are 'small', as on a
    two-row Consoles page: one row sits at y 352, two rows at 268 and 474; a section is an engraved box with its title."""
    x0s, y0s, x1s, y1s = SECTION
    gap = 18; pad = 12
    cw = min(140, int((x1s - x0s - 40 - max((len(r) - 1) * gap + len(r) * pad for r in rows)) / max(sum(len(ns) for _, ns in r) for r in rows)))
    cys = [352] if len(rows) == 1 else [268, 474]
    secs, cells = [], {}
    for row, cy in zip(rows, cys):
        total = sum(len(ns) * cw + pad for _, ns in row) + (len(row) - 1) * gap
        x = (x0s + x1s) / 2 - total / 2
        for title, ns in row:
            w = len(ns) * cw + pad
            top = cy - 112
            secs.append((title, (round(x), top, round(x + w), cy + 84), (round(x + 10), top + 14)))
            for i, n in enumerate(ns):
                cells[n] = (x + pad / 2 + (i + 0.5) * cw, cy)
            x += w + gap
    return secs, cells, cw
