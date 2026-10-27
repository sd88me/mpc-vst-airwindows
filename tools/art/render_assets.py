#!/usr/bin/env python3
"""Render the AW skin artwork (original, procedural): framed console-box backgrounds, SSL-style knob filmstrips,
Q-Link overlay layers and per-category footer plates.

    render_assets.py --style A|C --out build/art/A [--fonts DIR] [--only bg,knobs,qover,cats,manual]

Needs numpy and Pillow (run it in a python container: see README "Skin artwork"). Every image is drawn from a height map
lit from the top left (Blinn-Phong), so the frame, the engraving and the knobs share one light.
Writes into --out: bg_controls.png bg_none.png bg_manual.png knob_<size>_<role>.png qover_<n>.png badge_<g>_<k>.png cat_<slug>.png
"""
import argparse
import glob
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY  # noqa: E402

SS = 2
W, H = LY.W, LY.H
rng = np.random.default_rng(11)
L = np.array([-0.45, -0.62, 0.64]); L /= np.linalg.norm(L)
Hh = L + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
FONTS = {"b": None, "r": None}

CAPS = {"A": {"red": (0.78, 0.12, 0.10), "blue": (0.16, 0.36, 0.78), "green": (0.18, 0.62, 0.30), "white": (0.92, 0.92, 0.90),
              "black": (0.16, 0.16, 0.17), "step": (0.14, 0.14, 0.15)},
        "C": {"red": (0.64, 0.16, 0.12), "blue": (0.14, 0.28, 0.58), "green": (0.16, 0.46, 0.26), "white": (0.86, 0.86, 0.84),
              "black": (0.16, 0.16, 0.17), "step": (0.14, 0.14, 0.15)}}
INK = {"A": ((232, 234, 238), (190, 194, 200)), "C": ((40, 40, 42), (70, 70, 74))}


def font(kind, px):
    return ImageFont.truetype(FONTS[kind], int(px))


def box(a, r, axis):
    r = max(1, int(r)); c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode="edge"), axis=axis)
    n = 2 * r + 1
    return (np.take(c, range(n, c.shape[axis]), axis=axis) - np.take(c, range(0, c.shape[axis] - n), axis=axis)) / n


def blur(a, r, axes=(0, 1)):
    for _ in range(3):
        for ax in axes:
            a = box(a, max(1, r // 2), ax)
    return a


def noise(shape, sx, sy, amt):
    n = rng.normal(0, 1, shape)
    if sx > 1: n = blur(n, sx, axes=(1,))
    if sy > 1: n = blur(n, sy, axes=(0,))
    return n / (n.std() + 1e-9) * amt


def shade(h, albedo, spec_k, spec_p, ambient=0.34, gain=1.0, kz=1.0):
    gy, gx = np.gradient(h)
    n = np.stack([-gx * kz, -gy * kz, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    dif = np.clip(n @ L, 0, 1)[..., None]
    sp = np.clip(n @ Hh, 0, 1) ** spec_p
    sk = spec_k[..., None] if isinstance(spec_k, np.ndarray) else spec_k
    return np.clip(albedo * (ambient + gain * dif) + sk * sp[..., None], 0, 1)


def smooth(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)


def rrect(x0, y0, x1, y1, r, size, width=0):
    m = Image.new("L", size, 0); d = ImageDraw.Draw(m)
    if width: d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], r * SS, outline=255, width=int(width * SS))
    else: d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], r * SS, fill=255)
    return np.asarray(m, float) / 255


def text_mask(items, size):
    m = Image.new("L", size, 0); d = ImageDraw.Draw(m)
    for (x, y), s, px, anch in items:
        d.text((x * SS, y * SS), s, font=font("b", px * SS), fill=255, anchor=anch)
    return np.asarray(m, float) / 255


# ---- knobs -------------------------------------------------------------------------------------------------------------
def ssl_knob(R, cap, ang, collar=(0.13, 0.13, 0.14)):
    """SSL-4000 style: dark collar, tall flat-topped coloured cap with fine side grip, white line indicator."""
    S = int(R * 3.0); c = S / 2
    yy, xx = np.mgrid[0:S, 0:S].astype(float); dx, dy = xx - c, yy - c; d = np.hypot(dx, dy) / R; th = np.arctan2(dy, dx)
    alb = np.zeros((S, S, 3)); spk = np.zeros((S, S)); spp = np.full((S, S), 30.0)
    coll = d < 1.0; capm = d < 0.74
    h = np.where(coll, 0.30 * smooth((1.0 - d) / 0.05), 0)
    alb[:] = collar; spk[:] = 0.25
    ring = (d > 0.76) & (d < 0.80); h = np.where(ring, h - 0.03, h)
    side = (d >= 0.69) & (d < 0.74)
    h = np.where(capm, 0.30 + 0.55 * smooth((0.74 - d) / 0.055) + 0.012 * (np.cos(th * 72) * 0.5 + 0.5) * side + 0.012 * (1 - (d / 0.69) ** 2), h)
    alb = np.where(capm[..., None], np.array(cap), alb); spk = np.where(capm, 0.55, spk); spp = np.where(capm, 60.0, spp)
    ux, uy = math.sin(ang), -math.cos(ang); along = dx * ux + dy * uy; across = -dx * uy + dy * ux
    pm = (along > 0.04 * R) & (along < 0.70 * R) & (np.abs(across) < 0.032 * R)
    alb = np.where(pm[..., None], np.array([0.96, 0.96, 0.94]), alb); h = np.where(pm, h - 0.015, h)
    rgb = shade(blur(h, 1) * R * 0.55, alb, spk, spp, ambient=0.30, gain=0.95)
    return rgb, np.clip((1.0 - d) * R, 0, 1)


def knob_frame(style, size, role, val):
    """One filmstrip frame: the knob, its drop shadow and the printed scale (dots for a stepped control), on transparency."""
    R0, _ = LY.SIZES[size]; S = LY.frame_px(size); R = R0 * SS; P = S * SS
    rgb, a = ssl_knob(R, CAPS[style][role], math.radians(-135 + 270 * val)); k = rgb.shape[0]
    cx = P // 2; x0 = cx - k // 2
    m = np.zeros((P, P)); m[x0:x0 + k, x0:x0 + k] = a
    off = int(R * 0.16)
    sh = np.clip(0.60 * blur(np.roll(np.roll(m, off, 0), int(off * 0.6), 1), int(R * 0.24)) + 0.35 * blur(np.roll(m, int(R * 0.05), 0), int(R * 0.07)), 0, 0.85)
    full = np.zeros((P, P, 3)); full[x0:x0 + k, x0:x0 + k] = rgb
    oa = m + sh * (1 - m)
    orgb = np.where(oa[..., None] > 1e-4, full * m[..., None] / np.maximum(oa, 1e-4)[..., None], 0)
    img = Image.fromarray((np.clip(np.dstack([orgb, oa]), 0, 1) * 255).astype("uint8"), "RGBA")
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    tc = tuple(INK[style][1]) + (255,)
    c = P / 2
    if role == "step":
        for ang in (-135, 0, 135):
            a_ = math.radians(ang); x2, y2 = c + math.sin(a_) * R * 1.40, c - math.cos(a_) * R * 1.40
            d.ellipse([x2 - 3.2 * SS, y2 - 3.2 * SS, x2 + 3.2 * SS, y2 + 3.2 * SS], fill=tc)
    else:
        for i in range(11):
            a_ = math.radians(-135 + 270 * i / 10); big = i in (0, 5, 10)
            r2 = R * (1.46 if big else 1.34)
            d.line([c + math.sin(a_) * R * 1.20 + 1, c - math.cos(a_) * R * 1.20 + 1.4, c + math.sin(a_) * r2 + 1, c - math.cos(a_) * r2 + 1.4], fill=(0, 0, 0, 80), width=int(2.2 * SS))
            d.line([c + math.sin(a_) * R * 1.20, c - math.cos(a_) * R * 1.20, c + math.sin(a_) * r2, c - math.cos(a_) * r2], fill=tc, width=int(2.2 * SS))
        if size != "small":
            for lab, ang in (("0", -135), ("10", 135)):
                a_ = math.radians(ang)
                d.text((c + math.sin(a_) * R * 1.66, c - math.cos(a_) * R * 1.66 + 4 * SS), lab, font=font("b", max(11, R0 * 0.26) * SS), fill=tc, anchor="mm")
    img.alpha_composite(ov)
    return img.resize((S, S), Image.LANCZOS)


def render_knobs(style, out, only=None):
    for size, (r, frames) in LY.SIZES.items():
        S = LY.frame_px(size)
        for role in LY.ROLES:
            if only and f"{size}_{role}" not in only and "all" not in only:
                continue
            strip = Image.new("RGBA", (S, S * frames))
            for i in range(frames):
                strip.paste(knob_frame(style, size, role, i / (frames - 1)), (0, i * S))
            strip.save(os.path.join(out, f"knob_{size}_{role}.png"))
            print("knob", size, role, S, frames, S * frames, flush=True)


# ---- panel backgrounds ------------------------------------------------------------------------------------------------
def base_panel(style, sections, texts, footer=True):
    w, h = W * SS, H * SS; size = (w, h); shp = (h, w)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    T = LY.FRAME * SS
    dist_x = np.minimum(xx, w - 1 - xx); dist_y = np.minimum(yy, h - 1 - yy); din = np.minimum(dist_x, dist_y)
    cr = 14 * SS; cxm = np.clip(dist_x, 0, cr); cym = np.clip(dist_y, 0, cr)
    corner = (dist_x < cr) & (dist_y < cr); rr = np.hypot(cr - cxm, cr - cym); outside = corner & (rr > cr)
    din = np.where(corner, np.minimum(din, cr - rr), din)
    frame = din < T
    vert = dist_x < dist_y
    g_h = noise(shp, 90 * SS, 1, 1.0) + 0.5 * noise(shp, 30 * SS, 2, 1.0) + 0.25 * noise(shp, 6 * SS, 1, 1.0)
    g_v = noise(shp, 1, 90 * SS, 1.0) + 0.5 * noise(shp, 2, 30 * SS, 1.0) + 0.25 * noise(shp, 1, 6 * SS, 1.0)
    gr = np.where(vert, g_v, g_h)
    rings = 0.5 + 0.5 * np.sin(np.where(vert, xx, yy) / (5.5 * SS) + 2.2 * gr)
    wb = np.array([0.36, 0.19, 0.095]); wh = np.array([0.56, 0.33, 0.17])
    wal = (wb + (wh - wb) * (0.5 * rings + 0.12 * gr)[..., None]) * (1.0 + 0.07 * noise(shp, 3, 3, 1.0))[..., None]
    prof = np.where(din < 16 * SS, np.sin(smooth(din / (16 * SS)) * math.pi / 2), 1.0)
    prof = np.where(din > T - 13 * SS, 1.0 - 0.86 * smooth((din - (T - 13 * SS)) / (13 * SS)), prof)
    hm = np.where(frame, prof, 0.14) + np.where(frame, 0.012 * gr, 0)
    mit = frame & (np.abs(dist_x - dist_y) < 1.3 * SS) & (din > 2 * SS) & (din < T - 8 * SS)
    hm = np.where(mit, hm - 0.05, hm)
    alb = np.where(frame[..., None], wal, np.zeros((h, w, 3)))
    spk = np.where(frame, 0.95, 0.12); spp = np.where(frame, 46.0, 12.0)
    if style == "A":
        base = np.array([0.255, 0.268, 0.285]); tex = noise(shp, 60 * SS, 1, 0.9) * 0.25 + noise(shp, 6 * SS, 1, 0.5) * 0.25 + rng.normal(0, 0.06, shp)
        pan = np.ones((h, w, 3)) * base * (1.14 - 0.5 * (yy / h))[..., None]; bloom = 0.25; ambient = 0.80
    else:
        base = np.array([0.625, 0.61, 0.575]); tex = rng.normal(0, 0.10, shp) + noise(shp, 3, 3, 0.10)
        pan = np.ones((h, w, 3)) * base * (1.07 - 0.15 * (yy / h))[..., None]; pan += rng.normal(0, 0.010, (h, w, 1)); bloom = 0.14; ambient = 0.84
    glow = np.exp(-(((xx - 0.3 * w) / (0.6 * w)) ** 2 + ((yy + 0.15 * h) / (0.8 * h)) ** 2)); pan *= (0.92 + bloom * glow)[..., None]
    alb = np.where(frame[..., None], alb, pan); hm = np.where(frame, hm, hm + 0.012 * tex)
    # engraved sections, grooves, lettering
    sec = np.zeros(shp); grv = np.zeros(shp); grv2 = np.zeros(shp)
    for (x0, y0, x1, y1) in sections:
        sec = np.maximum(sec, rrect(x0, y0, x1, y1, 14, size)); grv = np.maximum(grv, rrect(x0, y0, x1, y1, 14, size, 2.5))
        grv2 = np.maximum(grv2, rrect(x0 - 8, y0 - 8, x1 + 8, y1 + 8, 18, size, 1.6))
    top = np.zeros(shp)
    hm = hm - 0.07 * blur(sec, 2) - 0.12 * blur(grv, 1) - 0.07 * blur(grv2, 1) - 0.09 * blur(top, 1)
    alb = alb * (1 - 0.18 * blur(grv, 1)[..., None]) * (1 - 0.10 * sec[..., None])
    tm = blur(text_mask(texts, size), 1)
    hm = hm - 0.05 * tm; alb = alb * (1 - 0.55 * tm[..., None])
    # wear: edge lightening along the grooves, scratches, smudges
    edge = blur(grv, 2) * 0.6 + blur(grv2, 2) * 0.4
    wear = np.clip(noise(shp, 5, 5, 1.0) * 0.7 + 0.2, 0, 1) * edge
    alb = np.where(frame[..., None], alb, np.clip(alb + 0.10 * wear[..., None], 0, 1))
    sm = np.clip(noise(shp, 70 * SS, 40 * SS, 1.0), -1, 1); alb = np.where(frame[..., None], alb, alb * (1 + 0.035 * sm[..., None]))
    img_s = Image.new("L", size, 0); ds = ImageDraw.Draw(img_s)
    for _ in range(46):
        x = rng.uniform(70, 1210) * SS; y = rng.uniform(70, 560) * SS; ln = rng.uniform(20, 130) * SS; a = rng.uniform(0, math.pi)
        ds.line([x, y, x + math.cos(a) * ln, y + math.sin(a) * ln], fill=int(rng.uniform(40, 120)), width=1)
    scr = np.asarray(img_s, float) / 255
    alb = np.where(frame[..., None], alb, np.clip(alb + 0.30 * scr[..., None] * (0.6 if style == "A" else 0.5), 0, 1))
    hm = np.where(frame, hm, hm - 0.01 * scr); spk = np.where(frame, spk, 0.10 + 0.25 * scr)
    img = shade(hm * 24 * SS / 2, alb, spk, spp, ambient=ambient, gain=0.42)
    img = np.where(frame[..., None], np.clip(img * (0.92 + 0.14 * np.exp(-((xx / w - 0.25) / 0.3) ** 2))[..., None], 0, 1), img)
    img *= (0.88 + 0.12 * (1 - np.clip((np.abs(xx / w - 0.5) * 2) ** 3, 0, 1)))[..., None]
    img = np.where(outside[..., None], 0.05, img)
    ps = blur(np.roll(np.roll(np.where(frame, 1.0, 0.0), 9 * SS, 0), 7 * SS, 1), 12 * SS)
    img = np.where(frame[..., None], img, img * (1 - 0.62 * ps[..., None]))
    return img


def finish(img, extra=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype("uint8")).convert("RGBA")
    if extra:
        extra(im)
    return im.resize((W, H), Image.LANCZOS).convert("RGB")


def ink_text(d, style, items):
    ink = INK[style][1] + (255,)
    for (x, y), s, px, anch in items:
        d.text((x * SS, y * SS), s, font=font("b", px * SS), fill=ink, anchor=anch)


def render_bgs(style, out):
    head = [((1176, 130), "AIRWINDOWS COLLECTIONS", 15, "rs")]
    for name, tx in (("controls", head), ("none", [((1176, 130), "AIRWINDOWS COLLECTIONS", 15, "rs")])):
        img = base_panel(style, [LY.SECTION], tx, footer=False)

        def extra(im, tx=tx, name=name):
            d = ImageDraw.Draw(im); ink_text(d, style, tx)
            if name == "none":
                d.text((640 * SS, 330 * SS), "NO CONTROLS", font=font("b", 46 * SS), fill=INK[style][1] + (255,), anchor="mm")
                d.text((640 * SS, 390 * SS), "fixed processing: see the MANUAL tab", font=font("r", 26 * SS), fill=INK[style][1] + (255,), anchor="mm")
        finish(img, extra).save(os.path.join(out, f"bg_{name}.png")); print("bg", name, flush=True)


def render_manual(style, out):
    texts = [((1176, 172), "MANUAL", 15, "rs"), ((1176, 130), "AIRWINDOWS COLLECTIONS", 15, "rs")]
    img = base_panel(style, [LY.SECTION], texts, footer=False)

    def extra(im):
        d = ImageDraw.Draw(im); ink_text(d, style, texts)
        lx, ly, lw, lh = LY.LEGEND_BOX
        d.text(((lx + 4) * SS, ly * SS), "KNOB COLOURS", font=font("b", 15 * SS), fill=INK[style][1] + (255,), anchor="lm")
        for i, (role, label) in enumerate(LY.ROLE_LABEL):
            cy = ly + 50 + i * 56
            rgb, a = ssl_knob(15 * SS, CAPS[style][role], math.radians(-45)); k = rgb.shape[0]
            kim = Image.fromarray((np.dstack([rgb, a]) * 255).astype("uint8"), "RGBA")
            im.alpha_composite(kim, (int((lx + 22) * SS - k / 2), int(cy * SS - k / 2)))
            d.text(((lx + 46) * SS, cy * SS), label, font=font("r", 17 * SS), fill=INK[style][1] + (255,), anchor="lm")
    finish(img, extra).save(os.path.join(out, "bg_manual.png")); print("bg manual", flush=True)


# ---- Q-Link overlay layers, category plates ---------------------------------------------------------------------------
def draw_badge(d, cx, cy, g, k):
    """One Q-Link badge (the Force knob number 1-8 in its column's colour) centred on cx, cy."""
    gc = tuple(int(255 * c) for c in LY.GROUP[g])
    d.ellipse([(cx - 12) * SS, (cy - 12) * SS, (cx + 12) * SS, (cy + 12) * SS], fill=(16, 16, 18, 235), outline=gc + (255,), width=int(2.4 * SS))
    d.text((cx * SS, cy * SS), str(k), font=font("b", 16 * SS), fill=gc + (255,), anchor="mm")


def render_qover(style, out):
    """Per control count: the Q-Link column brackets (one-row layouts), one full-panel image (badges are separate, see render_badges)."""
    for n in range(1, 15):
        rows, sz, ldy, vdy, bdy = LY.layout(n)
        im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        if len(rows) == 1:
            R = LY.SIZES[sz][0]; row = rows[0]; by = row[0][1] + bdy
            for gs in range(0, n, 4):
                seg = row[gs:gs + 4]; gc = tuple(int(255 * c) for c in LY.GROUP[(gs // 4) % 4])
                x0 = seg[0][0] - R * 1.2; x1 = seg[-1][0] + R * 1.2
                d.line([x0 * SS, by * SS, x1 * SS, by * SS], fill=gc + (230,), width=int(3 * SS))
                for xx in (x0, x1):
                    d.line([xx * SS, (by - 6) * SS, xx * SS, by * SS], fill=gc + (230,), width=int(3 * SS))
        im.resize((W, H), Image.LANCZOS).save(os.path.join(out, f"qover_{n}.png"))
    print("qover 1..14", flush=True)


def render_badges(style, out):
    """Q-Link badges, one per column colour and Force knob number (1-8). The image is 64 x 32 with the badge in its middle: the
    MPC Live III draws an image only when it is at least 64 px wide (smaller ones vanish, larger ones are cropped, not scaled)."""
    for g in range(4):
        for k in range(1, 9):
            im = Image.new("RGBA", (64 * SS, 32 * SS), (0, 0, 0, 0)); draw_badge(ImageDraw.Draw(im), 32, 16, g, k)
            im.resize((64, 32), Image.LANCZOS).save(os.path.join(out, f"badge_{g}_{k}.png"))
    print("badges", flush=True)


def slug(c):
    return "".join(ch for ch in c.lower() if ch.isalnum())


def render_cats(style, out, cats):
    for cat in cats:
        acc = LY.ACCENT.get(cat, (0.6, 0.6, 0.6)); ac = tuple(int(255 * c) for c in acc)
        pw, ph = 360, 36; im = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        label = "AW " + cat.upper(); f = font("b", 17 * SS); tw = d.textlength(label, font=f)
        d.text(((pw - 16) * SS, ph / 2 * SS), label, font=f, fill=INK[style][1] + (255,), anchor="rm")
        lx = (pw - 16) * SS - tw - 20 * SS
        glow = Image.new("RGBA", im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        gd.ellipse([lx - 12 * SS, (ph / 2 - 12) * SS, lx + 12 * SS, (ph / 2 + 12) * SS], fill=ac + (90,))
        im.alpha_composite(glow)
        d.ellipse([lx - 6 * SS, (ph / 2 - 6) * SS, lx + 6 * SS, (ph / 2 + 6) * SS], fill=ac + (255,), outline=(20, 20, 20, 255), width=SS)
        d.ellipse([lx - 3.5 * SS, (ph / 2 - 4.5) * SS, lx - 0.5 * SS, (ph / 2 - 1.5) * SS], fill=(255, 255, 255, 170))
        im.resize((pw, ph), Image.LANCZOS).save(os.path.join(out, f"cat_{slug(cat)}.png"))
    print("cats", len(cats), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="A", choices=["A", "C"]); ap.add_argument("--out", required=True)
    ap.add_argument("--fonts", default=os.path.join(HERE, "fonts")); ap.add_argument("--only", default="bg,manual,qover,badges,cats,knobs")
    ap.add_argument("--knobs", default="all", help="comma list like normal_red,small_step, or all")
    ap.add_argument("--vst", default=os.path.join(HERE, "..", "..", "vst"))
    a = ap.parse_args()
    FONTS["b"] = os.path.join(a.fonts, "TitilliumWeb-Bold.ttf"); FONTS["r"] = os.path.join(a.fonts, "TitilliumWeb-Regular.ttf")
    os.makedirs(a.out, exist_ok=True)
    only = set(a.only.split(","))
    cats = sorted({json.load(open(f))["category"] for f in glob.glob(os.path.join(a.vst, "*", "gen", "skin_models.json"))})
    if "bg" in only: render_bgs(a.style, a.out)
    if "manual" in only: render_manual(a.style, a.out)
    if "badges" in only: render_badges(a.style, a.out)
    if "qover" in only: render_qover(a.style, a.out)
    if "cats" in only: render_cats(a.style, a.out, cats)
    if "knobs" in only: render_knobs(a.style, a.out, set(a.knobs.split(",")))


if __name__ == "__main__":
    main()
