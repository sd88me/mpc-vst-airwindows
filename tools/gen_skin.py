#!/usr/bin/env python3
"""Write a category plugin's MPC skin, after tools/build_port.sh has built it:

    tools/gen_skin.py vst/<Slug> [--style A|C] [--no-qlink-overlay]

Needs the artwork from tools/art/run.sh (build/art/<style>/). Into vst/<Slug>/build/skin/:
    <vendor> - VST - <name>/Plugin Skins/{TUI.json, Q-Links.json, Q-Links - 8by1.json}, version.xml
    AW Skin/        the shared artwork (this repo's own, tools/art), installed once next to the plugins in Synths/

The layout rules (the per-count panel method, drawn with our own art): one big knob for a single control, large knobs for two or
three, one row of four to seven, two rows of up to fourteen; stepped controls get a detent knob. Every model of the category
gets that panel on one screen, shown only while the Model parameter is on it (IndexedEnabling). A model with more than
fourteen controls continues on CONTROLS sub-pages. The MANUAL tab pages through the model's documentation.
Cap colours follow what a control does (tools/art/layout.py ROLE_RX). AW_QLINK_NATIVE=1 also asks MPC to outline the
Q-Link columns (experimental: only checked on an MPC One).
"""
import json
import math
import os
import re
import shutil
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "art"))
import layout as LY  # noqa: E402

SHARED = "AW Skin"
SELF_CONTAINED = "--self-contained" in sys.argv    # releases: the artwork goes inside the plugin folder, no shared folder
A = ("../%s/" if SELF_CONTAINED else "../../%s/") % SHARED   # from <plugin>/Plugin Skins/ to the artwork
AKAI = "/usr/share/Akai/Content/Synths/"
PAGE = 14
W, H = LY.W, LY.H
QLINK = [13, 9, 5, 1, 14, 10, 6, 2, 15, 11, 7, 3, 16, 12, 8, 4]   # Force knob banks: grid slots 0-7 = bank 1, 8-15 = bank 2
FONT = "Titillium Web"
FONT_DIR = os.path.join(HERE, "art", "fonts")
_fonts = {}


def text_w(px, text):
    """Width of Titillium Web Bold text at a visual size of px (MPC draws a label of height px / MPC_K at that size)."""
    from PIL import ImageFont
    if px not in _fonts:
        _fonts[px] = ImageFont.truetype(os.path.join(FONT_DIR, "TitilliumWeb-Bold.ttf"), px)
    return _fonts[px].getlength(text)


def bounds(x, y, w, h, focus="No", cond=None, show="Show"):
    b = {"version": 2, "acceptsHWFocus": focus, "showWhenDataModelInvalid": show, "whenVisible": "Always",
         "boundsType": "Absolute", "bounds": "%d %d %d %d" % (x, y, w, h), "additionalInvalidatingHandles": []}
    if cond:
        b["additionalInvalidatingHandles"].append(cond)
    return b


def image(img, x, y, w, h, cond=None):
    return {"version": 2, "componentData": {"version": 1, "name": "Image", "type": "Image",
            "data": {"version": 2, "imageType": "Regular", "colour": "0", "image": A + img}},
            "handle remapping": {"version": 1, "map": [{"key": "Data", "value": "Invalid"}]},
            "bounds": bounds(x, y, w, h, cond=cond)}


def control(ctype, name, pidx, x, y, w, h, cond=None):
    return {"version": 2, "componentData": {"version": 1, "name": name, "type": ctype,
            "data": {"version": 1, "handleName": "Data"}},
            "handle remapping": {"version": 1, "map": [{"key": "Data", "value": "Parameter %d" % pidx}]},
            "bounds": bounds(x, y, w, h, focus="Yes", cond=cond)}


def label(kind, pidx, x, y, w, h, size, colour, just="horizontallyCentred verticallyCentred", style="Bold", cond=None):
    return {"version": 2, "componentData": {"version": 1, "name": "Label", "type": "Label", "data": {
        "version": 1, "textStyle": {"version": 1, "font": {"version": 1, "name": FONT, "style": style, "height": float(size)},
                                    "colour": colour, "justification": just, "case": "Original"},
        "type": kind, "handleName": "Parameter %d" % pidx}},
        "handle remapping": {"version": 1, "map": []}, "bounds": bounds(x, y, w, h, cond=cond)}


def _sub(ctype, data, bnd, name=""):
    return {"version": 2, "componentData": {"version": 1, "name": name, "type": ctype, "data": data},
            "handle remapping": {"version": 1, "map": []}, "bounds": bnd}


def _action(on, handler, extra="", handle="Data"):
    return {"version": 2, "onAction": on, "handler": handler, "handleName": "" if handler == "Show Overlay" else handle,
            "additionalData": extra, "handle remapping": {"version": 1, "map": []}}


def _local(key, actions, children, fill=None):
    clear = fill or {"version": 1, "colour": "0", "image": ""}
    return {"key": key, "value": {"version": 4, "actions": actions,
                                  "backgroundData": {"version": 1, "focussed": clear, "unfocussed": clear},
                                  "ignoreMousePresses": False, "disableCoarseDataWheel": False, "repeats": 1,
                                  "hideQLinkBounds": True, "componentsData": children}}


def _focus(w, h, colour="ffe81f40", visible="WhenFocussed", thick=2.0):
    return _sub("Focus", {"version": 1, "backgroundColour": "00000000", "outlineColour": colour, "backgroundInset": 2.0,
                          "outlineThickness": thick}, bounds(0, 0, w, h, focus="No") | {"whenVisible": visible}, "Focus")


def knob_def(size, role):
    """A filmstrip knob: drag it, Q-Link it, double-click for the numeric overlay. The strip carries the scale and shadow."""
    S = LY.frame_px(size); frames = LY.SIZES[size][1]
    return _local("awKnob_%s_%s" % (size, role),
                  [_action("Mouse Down", "Q-Link"), _action("Double Click", "Show Overlay", "knob overlay"),
                   _action("Enter Pressed", "Show Overlay", "knob overlay")],
                  [_focus(S, S, colour="00000000"),
                   _sub("Knob", {"version": 5, "knobType": "FilmStrip", "filmStrip": A + "knob_%s_%s.png" % (size, role),
                                 "numFrames": frames, "invert": False, "dragOrientation": "Vertical", "handleName": "Data"},
                        bounds(0, 0, S, S), "Knob")])


def selector_def(key, w, h):
    """A touch/data-wheel target with only a focus ring: the live text over it is the control (a model)."""
    return _local(key, [_action("Mouse Down", "Q-Link")], [_focus(w, h)])


def hit_png(path, w, h):
    """A near-invisible plate (alpha 1) so a button's caption still receives the tap."""
    row = b"\x00" + b"\x00\x00\x00\x01" * w

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(row * h)) + chunk(b"IEND", b"") )


BTN_W, BTN_H = LY.BTN
BTN_HIT = "aw_btn_hit_%dx%d.png" % (BTN_W, BTN_H)


def button_def(style):
    """A touch step button: its caption is the momentary parameter's name; a hit plate under it takes the tap."""
    st = LY.STYLES[style]; fill = {"version": 1, "colour": st["btn_fill"], "image": ""}
    kids = [_focus(BTN_W, BTN_H),
            _sub("Label", {"version": 1, "textStyle": {"version": 1, "font": {"version": 1, "name": FONT, "style": "Bold", "height": 40.0},
                                                       "colour": st["btn_text"], "justification": "horizontallyCentred verticallyCentred",
                                                       "case": "Original"}, "type": "Name", "handleName": "Data"},
                 bounds(0, 0, BTN_W, BTN_H), "Name"),
            _sub("Button", {"version": 2, "onImage": BTN_HIT, "offImage": BTN_HIT, "buttonId": 1, "numButtonsInGroup": 1,
                            "handleName": "Data", "gestureBehaviour": "Instant"}, bounds(0, 0, BTN_W, BTN_H), "Button")]
    d = _local("awBtn", [_action("Mouse Down", "Toggle Switch"), _action("Enter Pressed", "Toggle Switch")], kids, fill)
    return d


def step_buttons(idx, prev_key, next_key, pos):
    return [control("awBtn", "Step", idx[k], x, y, BTN_W, BTN_H) for k, (x, y) in zip((prev_key, next_key), pos)]


def header(idx, style, info=True):
    """[<] model name [>] and the description under it (every tab)."""
    st = LY.STYLES[style]; x, y, w, h = LY.MODEL_BOX; ix, iy, iw, ih = LY.INFO_BOX
    return ([control("awSelect", "Model", idx["model"], x, y, w, h),
             label("Value", idx["model"], x, y, w, h, LY.mpc_h(40), st["title"], "horizontallyCentred verticallyCentred"),
             ] + ([label("Value", idx["info"], ix, iy, iw, ih, LY.mpc_h(19), st["info"], "left verticallyCentred", "Regular")] if info else [])
            + step_buttons(idx, "model_prev", "model_next", LY.BTN_MODEL))


def model_panel(params, first, pidx_of_slot, cond, style, qover):
    """One model's controls on one page: params[first:first+14]."""
    ps = params[first:first + PAGE]; n = len(ps); st = LY.STYLES[style]
    rows, sz, ldy, vdy, bdy = LY.layout(n)
    out = [image("bg_none.png" if n == 0 else "bg_controls.png", 0, 0, W, H, cond)]
    if n and qover:
        out.append(image("qover_%d.png" % n, 0, 0, W, H, cond))
    S = LY.frame_px(sz) if n else 0
    flat = [(i, x, cy) for i, (x, cy) in enumerate(p for r in rows for p in r)]
    spacing = min(180, rows[0][1][0] - rows[0][0][0] - 8) if rows and len(rows[0]) > 1 else 420
    lp, vp = (LY.LEGEND_P[sz], LY.VALUE_P[sz]) if n else (0, 0)
    lh, vh = round(LY.mpc_h(lp) * 1.15), round(LY.mpc_h(vp) * 1.15)
    for i, x, cy in flat:
        p = ps[i]; pi = pidx_of_slot(first + i); role = LY.role_of(p["name"], p["stepped"])
        out.append(control("awKnob_%s_%s" % (sz, role), p["name"], pi, round(x - S / 2), round(cy - S / 2), S, S, cond))
        out.append(label("Name", pi, round(x - spacing / 2), round(cy + ldy - lh / 2), round(spacing), lh, LY.mpc_h(lp), st["legend"], cond=cond))
        if qover:   # the Q-Link badge in front of the name (64 x 64 image, badge in the middle: see render_badges)
            bx = x - text_w(lp, p["name"]) / 2 - 16
            out.append(image("badge_%d_%d.png" % ((i // 4) % 4, i % 8 + 1), round(bx - 32), round(cy + ldy - 32), 64, 64, cond))
        out.append(label("Value", pi, round(x - spacing / 2), round(cy + vdy - vh / 2), round(spacing), vh, LY.mpc_h(vp), st["value"],
                         style="SemiBold", cond=cond))
    return out


def strip_panel(m, pidx_of_slot, cond, style, qover, tab):
    """One strips model on one tab: the tab's sections of 'small' knobs, Q-Link badges on all of them (slot k's Q-Link is
    k % 14 of tab k // 14: the engine's slot map puts each tab's controls in that tab's 14 slots)."""
    key, tabs = LY.strip_variant(m["name"]); st = LY.STYLES[style]
    if tab >= len(tabs):
        return [image("bg_tabempty.png", 0, 0, W, H, cond)]
    secs, cells, cw = LY.strip_geometry(tabs[tab])
    order = LY.strip_slot_order(m["name"]); stepped = {p["name"]: p["stepped"] for p in m["params"]}
    out = [image("bg_strip_%s_%d.png" % (key, tab), 0, 0, W, H, cond)]
    rows, sz, ldy, vdy, bdy = LY.layout(14)
    S = LY.frame_px("small"); lp, vp = LY.LEGEND_P["small"], LY.VALUE_P["small"]
    lh, vh = round(LY.mpc_h(lp) * 1.15), round(LY.mpc_h(vp) * 1.15)
    for n, (cx, cy) in cells.items():
        k = order.index(n); pi = pidx_of_slot(k)
        out.append(control("awKnob_small_%s" % LY.role_of(n, stepped[n]), n, pi, round(cx - S / 2), round(cy - S / 2), S, S, cond))
        out.append(label("Name", pi, round(cx - cw / 2), round(cy + ldy - lh / 2), round(cw), lh, LY.mpc_h(lp), st["legend"], cond=cond))
        out.append(label("Value", pi, round(cx - cw / 2), round(cy + vdy - vh / 2), round(cw), vh, LY.mpc_h(vp), st["value"], style="SemiBold", cond=cond))
        if qover:
            j = k % LY.STRIP_TAB
            bx = cx - text_w(lp, n) / 2 - 16
            out.append(image("badge_%d_%d.png" % ((j // 4) % 4, j % 8 + 1), round(bx - 32), round(cy + ldy - 32), 64, 64, cond))
    return out


def page_def(name, comps, native=None):
    d = {"version": 2, "actions": [], "backgroundData": {
        "version": 1, "focussed": {"version": 1, "colour": "ff101214", "image": ""},
        "unfocussed": {"version": 1, "colour": "ff101214", "image": ""}},
        "ignoreMousePresses": False, "disableCoarseDataWheel": False, "componentsData": comps}
    return d


def native_bounds():
    """Experimental: one rectangle per Q-Link column on a 6-knob row (knobs 1-4 = column 1, 5-6 = column 2)."""
    rows, sz, *_ = LY.layout(6); r = LY.SIZES[sz][0]; row = rows[0]; cy = row[0][1]
    def rect(seg):
        x0 = seg[0][0] - r * 1.5; x1 = seg[-1][0] + r * 1.5
        return "%d %d %d %d" % (x0, cy - r * 1.9, x1 - x0, r * 4.4)
    return [rect(row[:4]), rect(row[4:]), "0 0 0 0", "0 0 0 0"]


def qlinks(slot_to_param):
    ql = {"Q-Link %d" % (q + 1): -1 for q in range(16)}
    for s, p in slot_to_param.items():
        ql["Q-Link %d" % QLINK[s]] = p
    return ql


STRIPS_QLINKS = LY.STRIP_TAB


def main(port, style, qover):
    sm = json.load(open(os.path.join(port, "gen", "skin_models.json")))
    plist = json.load(open(os.path.join(port, "params.json")))["params"]
    idx = {p["key"]: i for i, p in enumerate(plist)}
    models, slots = sm["models"], sm["slots"]
    nm = len(models); model_i = idx["model"]; st = LY.STYLES[style]
    slot_param = lambda s: idx["p%d" % (s + 1)]
    cond = lambda m: "IndexedEnabling/%d/%d/Parameter %d" % (m, nm, model_i) if nm > 1 else None
    native = os.environ.get("AW_QLINK_NATIVE") == "1"

    tabs, qmap = [], []
    strips = sm["category"] == "Console Strips"
    per = STRIPS_QLINKS if strips else PAGE
    npages = max(1, math.ceil(slots / per))
    cat_img = "cat_%s.png" % "".join(c for c in sm["category"].lower() if c.isalnum())
    for pg in range(npages):
        comps = []
        for mi, m in enumerate(models):
            comps += (strip_panel(m, slot_param, cond(mi), style, qover, pg) if strips
                      else model_panel(m["params"], pg * PAGE, slot_param, cond(mi), style, qover))
        comps += header(idx, style)
        px, py, pw, ph = LY.CAT_PLATE
        comps.append(image(cat_img, px, py, pw, ph))
        # strips: each page is a real MPC page (own fn key); other categories nest their pages as sub pages
        title = "CONTROLS" if npages == 1 else ("PAGE %d" % (pg + 1) if strips else "CONTROLS %d/%d" % (pg + 1, npages))
        tabs.append({"version": 1, "tabName": title, "fnKeyIndex": pg if strips else 0, "fnKeySubIndex": 0 if strips else pg,
                     "componentDefinition": page_def(title, comps), "qlinkBoundsData": native_bounds() if native else ["0 0 0 0"]})
        here = min(per, slots - pg * per)
        sl = {s: slot_param(pg * per + s) for s in range(here)}
        sl[7 if here <= 7 else 15] = model_i
        qmap.append({"Tab": pg + 1 if strips else 1, "SubTab": 1 if strips else pg + 1, "Bank Direction": "Column", "Q-Links": qlinks(sl)})

    gx, gy, gw, gh = LY.PAGE_BOX
    man = [image("bg_manual.png", 0, 0, W, H)] + header(idx, style, info=False)
    man.append(control("awPage", "Page", idx["man_page"], gx, gy, gw, gh))
    man.append(label("Value", idx["man_info"], gx, gy, gw, gh, LY.mpc_h(26), st["info"], "horizontallyCentred verticallyCentred", "SemiBold"))
    man += step_buttons(idx, "page_prev", "page_next", LY.BTN_PAGE)
    mx, my, mw, mstep = LY.MANUAL_LINES
    for i in range(12):
        man.append(label("Value", idx["m%d" % (i + 1)], mx, my + i * mstep, mw, mstep, LY.mpc_h(20), st["body"], "left verticallyCentred", "Regular"))
    tabs.append({"version": 1, "tabName": "MANUAL", "fnKeyIndex": npages if strips else 1, "fnKeySubIndex": 0,
                 "componentDefinition": page_def("MANUAL", man), "qlinkBoundsData": ["0 0 0 0"]})
    qmap.append({"Tab": (npages if strips else 1) + 1, "SubTab": 1, "Bank Direction": "Column", "Q-Links": qlinks({0: idx["man_page"], 1: model_i})})

    if strips:
        used = sorted({("small", LY.role_of(p["name"], p["stepped"])) for m in models for p in m["params"]})
    else:
        used = sorted({(LY.size_of(min(PAGE, len(m["params"]) - pg * PAGE)), LY.role_of(p["name"], p["stepped"]))
                       for m in models for pg in range(npages) for p in m["params"][pg * PAGE:(pg + 1) * PAGE]
                       if len(m["params"]) > pg * PAGE})
    # a page with exactly 0 controls beyond the first never draws a knob; sizes follow each page's own count
    defs = [selector_def("awSelect", LY.MODEL_BOX[2], LY.MODEL_BOX[3]), selector_def("awPage", LY.PAGE_BOX[2], LY.PAGE_BOX[3]),
            button_def(style)] + [knob_def(s, r) for s, r in used]
    tui = {"pageData": {"version": 1, "componentDefinitions": {
        "version": 2, "importFiles": [AKAI + "Generic/Generic Knob Overlay.json", AKAI + "Generic/Generic Menu Overlay.json"],
        "localComponentDefinitions": defs},
        "info": {"version": 1, "type": "CompleteDescription"}, "tabs": tabs}}
    ql = {"version": 4, "info": {"version": 1, "type": "CompleteDescription"},
          "Screen Mode Q-Links": {"version": 4, "map": qmap},
          "Program Mode Q-Links": dict(qmap[0]["Q-Links"])}

    out = os.path.join(port, "build", "skin")
    d = os.path.join(out, "%s - VST - %s" % (sm["vendor"], sm["name"]))
    skin = os.path.join(d, "Plugin Skins")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(skin)
    for f, obj in (("TUI.json", tui), ("Q-Links.json", ql), ("Q-Links - 8by1.json", ql)):
        json.dump(obj, open(os.path.join(skin, f), "w"), separators=(",", ":"))
    hit_png(os.path.join(skin, BTN_HIT), BTN_W, BTN_H)
    open(os.path.join(d, "version.xml"), "w").write(
        "<?xml version='1.0' encoding='utf-8'?>\n<plugincontent version=\"1.0\">\n"
        "\t<identifier>%s.vst.%s</identifier>\n\t<version>1.0.0.0</version>\n</plugincontent>\n"
        % (sm["vendor"], sm["name"].lower().replace(" ", "")))
    src = os.path.join(ROOT, "build", "art", style)
    if not os.path.isdir(src):
        sys.exit("no %s: run tools/art/run.sh --style %s --out build/art/%s first" % (src, style, style))
    # only the artwork this plugin's skin references (32-bit PNGs kept as drawn): a release zip then carries ~11-14 MB, not all
    # 18 MB; skins of several plugins installed side by side merge into one AW Skin/ folder
    dst = os.path.join(d, SHARED) if SELF_CONTAINED else os.path.join(out, SHARED)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    used = set(re.findall(re.escape(SHARED) + r"/([A-Za-z0-9_.\-]+\.png)", json.dumps(tui)))
    for f in sorted(used):
        shutil.copy2(os.path.join(src, f), dst)
    ncomp = sum(len(t["componentDefinition"]["componentsData"]) for t in tabs)
    mb = sum(os.path.getsize(os.path.join(dst, f)) for f in used) / 1e6
    print("skin: %s (%d models, %d page(s), %d components, style %s) + %s/ (%d images, %.1f MB)" % (d, nm, npages, ncomp, style, SHARED, len(used), mb))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    style = "A"
    if "--style" in sys.argv:
        style = sys.argv[sys.argv.index("--style") + 1]; args = [a for a in args if a != style]
    if len(args) != 1 or style not in LY.STYLES:
        sys.exit(__doc__)
    main(args[0], style, "--no-qlink-overlay" not in sys.argv)
