#!/usr/bin/env python3
"""Stage built collection plugins for a device: one tar holding the skins (style A), the shared artwork, the .so files for one
architecture and an install.sh that registers them in MPC.settings.

    tools/stage_device.py --arch armv7|aarch64 [-o stage.tar] Tape Distortion ...      (vst/<Slug> names)

Then, once the user has agreed to an MPC restart (the script stops and starts MPC), on the device as root:
    scp stage.tar root@<device>:/tmp/aw.tar
    ssh root@<device> 'mkdir -p /tmp/aw && tar xf /tmp/aw.tar -C /tmp/aw && sh /tmp/aw/install.sh <Synths dir> <MPC.settings>'
Synths dir: /sdcard/Synths on a Force, /nvme/Synths on a Live III. MPC.settings: see docs/HANDOFF.md.
Needs the plugins already built (vst/<Slug>/build[/aarch64]/<so>). Plugins already registered (any layout of the entry) are not added twice.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INSTALL = r'''set -e
DIR="$1"; S="$2"
[ -d "$DIR" ] && [ -f "$S" ] || { echo "usage: sh install.sh <Synths dir> <MPC.settings>"; exit 1; }
cd "$(dirname "$0")"
systemctl stop acvs; sleep 2
cp "$S" "$S.bak-aw-$(date +%Y%m%d%H%M)"
mkdir -p "$DIR/AW Skin"; cp -r "AW Skin/." "$DIR/AW Skin/"
for d in Airwindows*; do rm -rf "$DIR/$d"; cp -r "$d" "$DIR/$d"; done
cp "$S" "$S.new"
while IFS='|' read -r so line; do
  if grep -q "$so\"" "$S.new"; then echo "already registered: $so"; continue; fi
  echo "$line" | sed "s#@SYNTHS@#$DIR#" > /tmp/aw.entry
  awk -v f=/tmp/aw.entry '/<\/KNOWNPLUGINS>/ && !d {while((getline l < f)>0) print l; d=1} {print}' "$S.new" > "$S.new2"
  mv "$S.new2" "$S.new"; echo "registered: $so"
done < entries.txt
mv "$S.new" "$S"
systemctl start acvs; sleep 3; systemctl is-active acvs
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arch", required=True, choices=["armv7", "aarch64"])
    ap.add_argument("-o", "--out", default="stage.tar")
    ap.add_argument("slugs", nargs="+")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, "AW Skin"))
    entries = []
    for slug in a.slugs:
        port = os.path.join(ROOT, "vst", slug)
        cfg = json.load(open(os.path.join(port, "vst.json")))
        name, so = cfg["name"], cfg["so"]
        b = os.path.join(port, "build") + ("/aarch64" if a.arch == "aarch64" else "")
        if not os.path.exists(os.path.join(b, so)):
            sys.exit("%s: not built for %s (%s)" % (slug, a.arch, os.path.join(b, so)))
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_skin.py"), port, "--style", "A"], check=True, stdout=subprocess.DEVNULL)
        skin = os.path.join(port, "build", "skin")
        for f in os.listdir(os.path.join(skin, "AW Skin")):
            shutil.copy2(os.path.join(skin, "AW Skin", f), os.path.join(tmp, "AW Skin"))
        folder = "%s - VST - %s" % (cfg["vendor"], name)
        shutil.copytree(os.path.join(skin, folder), os.path.join(tmp, folder))
        shutil.copy2(os.path.join(b, so), os.path.join(tmp, folder, so))
        uid = cfg["uid"].encode().hex()
        entries.append("%s|      <PLUGIN name=\"%s\" descriptiveName=\"%s\" format=\"VST\" category=\"Effect\" manufacturer=\"%s\" version=\"1.0\" "
                       "file=\"@SYNTHS@/%s/%s\" uid=\"%s\" isInstrument=\"0\" fileTime=\"0\" infoUpdateTime=\"0\" numInputs=\"2\" numOutputs=\"2\" isShell=\"0\"/>"
                       % (so, name, name, cfg["vendor"], folder, so, uid))
        print("staged %s (%s)" % (name, a.arch))
    open(os.path.join(tmp, "entries.txt"), "w").write("\n".join(entries) + "\n")
    open(os.path.join(tmp, "install.sh"), "w", newline="\n").write(INSTALL)
    with tarfile.open(a.out, "w") as t:
        t.add(tmp, arcname=".")
    shutil.rmtree(tmp)
    print("wrote %s (%.1f MB)" % (a.out, os.path.getsize(a.out) / 1e6))


if __name__ == "__main__":
    main()
