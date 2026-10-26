#!/usr/bin/env python3
"""Generate one MPC plugin per airwindows category from the vendored airwin2rack sources.

    tools/gen_categories.py [category ...]      (default: every category; names as upstream spells them, e.g. Reverb)

Needs build/probe/models_probe.jsonl (tools/probe.sh: every model's real parameter names, defaults and steps).
Per category, into vst/<Slug>/:
    vst.json, params.json, build.sh        the port, built with mpc-vst-plugins' tools/build_port.sh
    models.lock                            the model order (committed): a new upstream model is appended, never inserted,
                                           so a saved project's model index stays put
    gen/models.cpp, gen/docs.cpp           the model table and the manual pages compiled into the plugin
and after the build, tools/gen_skin.py writes the skin into vst/<Slug>/build/skin/.
Model factories (one file per model, shared by every category) go to src/gen/fac/.
"""
import json
import os
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import models as M  # noqa: E402

VENDOR = "Airwindows"
DOC_WRAP = 110         # characters per manual line (a 1220 px readout, Titillium at MPC height 30: about 20 css px)
PAGE_SLOTS = 14        # knobs per control page (a two-row rack layout)
UIDS = "uid_lock.json"


def probe():
    path = os.path.join(ROOT, "build", "probe", "models_probe.jsonl")
    if not os.path.exists(path):
        sys.exit("no %s: run tools/probe.sh first" % path)
    return {j["name"]: j for j in map(json.loads, open(path))}


def ascii_text(t):
    t = (t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
         .replace("\u2026", "...").replace("\u2013", "-").replace("\u2014", " - ").replace("\u00a0", " "))
    return t.encode("ascii", "ignore").decode()


def manual(name):
    p = os.path.join(M.VENDOR, "res", "awpdoc", name + ".txt")
    return ascii_text(open(p, encoding="utf-8", errors="replace").read()) if os.path.exists(p) else ""


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def control_text(pname, body):
    """The manual's own sentences about one control: those naming it (or its first five letters, for the
    abbreviated names airwindows uses, e.g. Brightns)."""
    words = re.findall(r"[A-Za-z0-9]+", pname)
    if not words:
        return ""
    pats = [r"\W*".join(map(re.escape, words))]
    if len(words) == 1 and len(words[0]) >= 5:
        pats.append(re.escape(words[0][:5]) + r"\w*")
    rx = re.compile(r"\b(?:%s)\b" % "|".join(pats), re.I)
    out = []
    for s in sentences(" ".join(body)):
        if rx.search(s) and s not in out:
            out.append(s)
        if len(" ".join(out)) > 200 or len(out) >= 2:
            break
    return " ".join(out)


def doc_lines(model, params):
    """A model's manual as wrapped lines: what it is, each control, then the full text."""
    text = manual(model["name"])
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    title = ascii_text(model["what"])
    if paras and paras[0].startswith("#"):
        title = paras.pop(0).lstrip("# ").strip()
    body = [re.sub(r"\s+", " ", p) for p in paras]
    w = lambda t, ind="": textwrap.wrap(t, DOC_WRAP, initial_indent=ind, subsequent_indent="    " if ind else "") or [""]
    lines = w(title or model["name"]) + [""]
    if params:
        lines.append("CONTROLS")
        for p in params:
            d = control_text(p["name"], body)
            lines += w("%s%s" % (p["name"], (": " + d) if d else ""), "- ")
        lines.append("")
    if body:
        lines.append("ABOUT")
        for p in body:
            lines += w(p) + [""]
    else:
        lines.append("(No manual page upstream yet for %s.)" % model["name"])
    while lines and not lines[-1]:
        lines.pop()
    return lines


def c_str(t):
    return '"%s"' % t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def stepped(p):
    return 2 <= len(p["steps"]) <= 12


def locked_order(slug, names_now):
    """Upstream order for a new category; afterwards the committed order, new models appended."""
    path = os.path.join(ROOT, "vst", slug, "models.lock")
    if os.path.exists(path):
        old = [l.strip() for l in open(path) if l.strip()]
        order = [n for n in old if n in names_now] + [n for n in names_now if n not in old]
    else:
        order = list(names_now)
    open(path, "w").write("\n".join(order) + "\n")
    return order


def uid_for(slug):
    path = os.path.join(ROOT, "vst", UIDS)
    d = json.load(open(path)) if os.path.exists(path) else {}
    if slug not in d:
        used = set(d.values())
        cand = ("a" + slug[:3]) if len(slug) >= 3 else ("aw" + slug.ljust(2, "x"))
        i = 0
        while cand in used:
            cand = "a" + slug[:2] + "0123456789"[i]
            i += 1
        d[slug] = cand
        json.dump(d, open(path, "w"), indent=1, sort_keys=True)
    return d[slug]


def params_for(names, slots):
    ps = [{"key": "model", "name": "Model", "options": names, "default": 0, "refresh_display": True, "type": "stepper"}]
    for i in range(1, slots + 1):
        ps.append({"key": "p%d" % i, "name": "P%d" % i, "min": 0, "max": 1, "default": 0.5,
                   "dynamic_name": True, "dynamic_display": True})
    ps.append({"key": "man_page", "name": "Manual Page", "min": 0, "max": 39, "default": 0, "display": "int",
               "refresh_display": True})
    ps.append({"key": "man_info", "name": "Manual", "min": 0, "max": 0, "default": 0, "display": "string", "type": "readout"})
    ps.append({"key": "info", "name": "About", "min": 0, "max": 0, "default": 0, "display": "string", "type": "readout"})
    for i in range(1, 13):
        ps.append({"key": "m%d" % i, "name": "Line %d" % i, "min": 0, "max": 0, "default": 0, "display": "string",
                   "type": "readout"})
    # touch buttons for the skin: a momentary press steps the model / manual page (handled, debounced, by src/engine.cpp)
    for key, name, target, d in (("model_prev", "<", "model", -1), ("model_next", ">", "model", 1),
                                 ("page_prev", "<", "man_page", -1), ("page_next", ">", "man_page", 1)):
        ps.append({"key": key, "name": name, "momentary": True, "refresh_display": True})
    return ps


def gen_category(cat, ms, pr):
    slug = M.slug(cat)
    d = os.path.join(ROOT, "vst", slug)
    os.makedirs(os.path.join(d, "gen"), exist_ok=True)
    by = {m["name"]: m for m in ms}
    order = locked_order(slug, [m["name"] for m in ms])
    ms = [by[n] for n in order]
    slots = max(1, max(len(pr[m["name"]]["params"]) for m in ms))
    name = "AW %s" % cat

    open(os.path.join(d, "gen", "models.cpp"), "w").write(M.table_cpp(ms))
    docs = ["// Generated by tools/gen_categories.py from the vendored airwin2rack manual (res/awpdoc): do not edit.",
            "extern const char *const AW_DOCS[] = {"]
    for m in ms:
        docs.append("    %s," % c_str("\n".join(doc_lines(m, pr[m["name"]]["params"]))))
    docs += ["};", "extern const char *const AW_WHAT[] = {"]
    docs += ["    %s," % c_str(ascii_text(m["what"])) for m in ms]
    docs.append("};")
    open(os.path.join(d, "gen", "docs.cpp"), "w").write("\n".join(docs) + "\n")

    json.dump({"name": name, "params": params_for(order, slots)}, open(os.path.join(d, "params.json"), "w"), indent=1)
    # one MPC PRESET-menu entry per model: pick the model, then that model's own defaults (model first, as the engine needs)
    presets = []
    for m in ms:
        v = {"model": m["name"]}
        ps = pr[m["name"]]["params"]
        for i in range(slots):
            v["p%d" % (i + 1)] = round(ps[i]["default"], 6) if i < len(ps) else 0.5
        presets.append({"name": m["name"], "values": v})
    json.dump({"presets": presets}, open(os.path.join(d, "presets.json"), "w"), indent=1)
    srcs = ["src/engine.cpp", "vst/%s/gen/models.cpp" % slug, "vst/%s/gen/docs.cpp" % slug,
            "vendor/airwin2rack/src/airwin_consolidated_base.cpp"]
    srcs += ["src/gen/fac/%s.cpp" % m["name"] for m in ms]
    srcs += ["vendor/airwin2rack/src/" + s for s in M.sources(ms)]
    cfg = {
        "name": name, "vendor": VENDOR, "uid": uid_for(slug), "version": 1000,
        "so": "aw_%s.so" % slug.lower(), "params": "params.json", "effect": True, "custom_skin": True, "presets": "presets.json",
        "cc": False, "targets": ["armv7", "aarch64"],
        "defines": {"PARAM_TEXT_MAX": 128},
        "build": {"root": "../..", "sources": srcs,
                  "cflags": ["-std=gnu++17", "-Isrc", "-Ivendor/airwin2rack/src", "-w", "-O2", "-DAW_SLOTS=%d" % slots],
                  "libs": ["-lm"], "cflags_arm": ["-mfpu=neon"]},
    }
    json.dump(cfg, open(os.path.join(d, "vst.json"), "w"), indent=1)
    sh = os.path.join(d, "build.sh")
    open(sh, "w").write(
        "#!/usr/bin/env bash\n# Build this category with mpc-vst-plugins' tools (MPC_VST, else a checkout next to this repo),\n"
        "# then its skin (tools/gen_skin.py).\nset -euo pipefail\nHERE=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
        "MPC_VST=\"${MPC_VST:-$HERE/../../../mpc-vst-plugins}\"\n"
        "\"$MPC_VST/tools/build_port.sh\" \"$HERE/vst.json\" \"$@\"\n"
        "python3 \"$HERE/../../tools/gen_skin.py\" \"$HERE\"\n")
    os.chmod(sh, 0o755)
    # what the skin generator needs: per model its controls and which are stepped
    json.dump({"category": cat, "name": name, "vendor": VENDOR, "slots": slots,
               "models": [{"name": m["name"],
                           "params": [{"name": p["name"], "stepped": stepped(p)} for p in pr[m["name"]]["params"]]}
                          for m in ms]},
              open(os.path.join(d, "gen", "skin_models.json"), "w"), indent=1)
    return slug, len(ms), slots


def main():
    pr = probe()
    allm = M.models()
    fac = os.path.join(ROOT, "src", "gen", "fac")
    os.makedirs(fac, exist_ok=True)
    for m in allm:
        open(os.path.join(fac, m["name"] + ".cpp"), "w").write(M.factory_cpp(m["name"]))
    cats = {}
    for m in allm:
        cats.setdefault(m["category"], []).append(m)
    want = sys.argv[1:] or sorted(cats)
    for c in want:
        if c not in cats:
            sys.exit("no category %r (have: %s)" % (c, ", ".join(sorted(cats))))
        slug, n, slots = gen_category(c, cats[c], pr)
        print("%-12s -> vst/%s: %d models, %d control slots" % (c, slug, n, slots))


if __name__ == "__main__":
    main()
