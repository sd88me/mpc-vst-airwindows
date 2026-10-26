#!/usr/bin/env python3
"""Offline look at a generated skin: one tab as MPC would draw it with the Model parameter on one model.

    tools/preview_skin.py vst/<Slug> <model name> [tab index] [out.png]

Draws the shared artwork (backgrounds, knob filmstrips at their middle frame) and stand-in text for live labels
(control names and values, the manual lines from gen/docs.cpp). Only components visible for that model are drawn.
Needs Pillow (run it in python:3.11-slim with `pip install pillow` when the host has none).
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONT_DIR = os.path.join(HERE, "art", "fonts")


def comp_strips(tui):
    """component type -> (filmstrip file, frame count) and button fills, from the skin's own local definitions."""
    out, fills = {}, {}
    for c in tui["pageData"]["componentDefinitions"]["localComponentDefinitions"]:
        txt = json.dumps(c["value"])
        m = re.search(r'"filmStrip": "([^"]+)", "numFrames": (\d+)', txt)
        if m:
            out[c["key"]] = (m.group(1), int(m.group(2)))
        fills[c["key"]] = c["value"]["backgroundData"]["focussed"]["colour"]
    return out, fills


def docs(port):
    src = open(os.path.join(port, "gen", "docs.cpp")).read()
    body = src.split("AW_DOCS[] = {", 1)[1].split("};", 1)[0]
    return [json.loads(s).split("\n") for s in re.findall(r'^    ("(?:[^"\\]|\\.)*"),$', body, re.M)]


def main(port, model, tab=0, out="preview.png"):
    sm = json.load(open(os.path.join(port, "gen", "skin_models.json")))
    plist = json.load(open(os.path.join(port, "params.json")))["params"]
    names = [m["name"] for m in sm["models"]]
    mi = names.index(model)
    mparams = sm["models"][mi]["params"]
    doc = docs(port)[mi]
    tui = json.load(open(os.path.join(port, "build", "skin", "%s - VST - %s" % (sm["vendor"], sm["name"]),
                                      "Plugin Skins", "TUI.json")))
    t = tui["pageData"]["tabs"][tab]
    page = t["componentDefinition"]
    strips, fills = comp_strips(tui)
    img = Image.new("RGBA", (1280, 628), "#" + page["backgroundData"]["focussed"]["colour"][2:])
    dr = ImageDraw.Draw(img)
    fonts = {}

    def font(h):
        h = max(8, int(h * 0.64))
        if h not in fonts:
            try:
                fonts[h] = ImageFont.truetype(os.path.join(FONT_DIR, "TitilliumWeb-Bold.ttf"), h)
            except OSError:
                fonts[h] = ImageFont.load_default()
        return fonts[h]

    def text_for(kind, p):
        key = plist[p]["key"]
        if key == "model":
            return model
        if key == "info":
            return "(one-line description)"
        if key == "man_info":
            return "page 1 / %d" % ((len(doc) + 11) // 12)
        if re.fullmatch(r"m\d+", key):
            i = int(key[1:]) - 1
            return doc[i] if i < len(doc) else ""
        if re.fullmatch(r"p\d+", key):
            i = int(key[1:]) - 1
            if i >= len(mparams):
                return ""
            return mparams[i]["name"] if kind == "Name" else "0.500"
        return plist[p]["name"]

    for c in page["componentsData"]:
        b = c["bounds"]
        conds = b.get("additionalInvalidatingHandles", [])
        if conds and not conds[0].startswith("IndexedEnabling/%d/" % mi):
            continue
        x, y, w, h = map(int, b["bounds"].split())
        cd = c["componentData"]
        if cd["type"] == "Image":
            f = os.path.normpath(os.path.join(port, "build", "skin", "x", "y", cd["data"]["image"]))
            im = Image.open(f).convert("RGBA")
            img.alpha_composite(im.crop((0, 0, min(w, im.width), min(h, im.height))), (x, y))
        elif cd["type"] in strips:
            f, n = strips[cd["type"]]
            im = Image.open(os.path.normpath(os.path.join(port, "build", "skin", "x", "y", f))).convert("RGBA")
            fh = im.height // n
            fr = im.crop((0, fh * (n // 2), im.width, fh * (n // 2 + 1)))
            img.alpha_composite(fr, (x + (w - fr.width) // 2, y + (h - fr.height) // 2))
        elif cd["type"] == "awBtn":
            col = fills["awBtn"]; dr.rounded_rectangle([x, y, x + w, y + h], 8, fill=(int(col[2:4], 16), int(col[4:6], 16), int(col[6:8], 16), 255))
            p = int(c["handle remapping"]["map"][0]["value"].split()[-1]); fnt = font(40)
            dr.text((x + w / 2, y + h / 2), plist[p]["name"], fill=(235, 235, 235, 255), font=fnt, anchor="mm")
        elif cd["type"] == "Label":
            d = cd["data"]
            p = int(d["handleName"].split()[-1])
            s = text_for(d["type"], p)
            st = d["textStyle"]
            col = st["colour"]
            rgba = (int(col[2:4], 16), int(col[4:6], 16), int(col[6:8], 16), int(col[0:2], 16))
            fnt = font(st["font"]["height"])
            tw = dr.textlength(s, font=fnt)
            tx = x if st["justification"].startswith("left") else x + w - tw if st["justification"].startswith("right") else x + (w - tw) / 2
            dr.text((tx, y + h / 2), s, fill=rgba, font=fnt, anchor="lm")
    img.save(out)
    print(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    main(os.path.abspath(a[0]), a[1], int(a[2]) if len(a) > 2 else 0, a[3] if len(a) > 3 else "preview.png")
