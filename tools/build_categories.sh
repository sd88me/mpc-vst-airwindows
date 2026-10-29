#!/usr/bin/env bash
# Build collection plugins for both devices, retrying the QEMU compiler crash (cc1plus segfaults now and then).
#   MPC_VST=<mpc-vst-plugins checkout with the process_float wrapper change> tools/build_categories.sh Tape Distortion ...
# Slugs are the vst/<Slug> folder names. Each build takes 10 to 45 minutes; run it in the background and read its log.
# params.lock is deleted first: the lock is only a guard for released parameter order (GEN_VST_RELOCK=1 does not reach the Docker run).
set -u
cd "$(dirname "$0")/.."
: "${MPC_VST:?set MPC_VST to the mpc-vst-plugins checkout}"
python3 tools/gen_categories.py >/dev/null
for c in "$@"; do
  so=$(python3 -c "import json;print(json.load(open('vst/$c/vst.json'))['so'])")
  rm -f "vst/$c/params.lock"
  for t in armv7 aarch64; do
    d=vst/$c/build; [ $t = aarch64 ] && d=$d/aarch64
    for try in 1 2 3 4 5 6; do rm -f "$d/$so"; "$MPC_VST/tools/build_port.sh" "vst/$c/vst.json" $t && [ -f "$d/$so" ] && break; done
    echo "FINISHED $c $t $(ls -l "$d/$so" 2>&1)"
  done
done
echo ALLDONE
