#!/usr/bin/env bash
# Build this category with mpc-vst-plugins' tools (MPC_VST, else a checkout next to this repo),
# then its skin (tools/gen_skin.py).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MPC_VST="${MPC_VST:-$HERE/../../../mpc-vst-plugins}"
"$MPC_VST/tools/build_port.sh" "$HERE/vst.json" "$@"
python3 "$HERE/../../tools/gen_skin.py" "$HERE"
