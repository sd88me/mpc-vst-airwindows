#!/usr/bin/env bash
# Run render_assets.py in a python container (numpy + Pillow):   tools/art/run.sh --style A --out build/art/A
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
docker run --rm -u "$(id -u):$(id -g)" -v "$ROOT":/w -w /w python:3.11-slim sh -c \
  "pip install -q --no-warn-script-location --target /tmp/p pillow numpy >/dev/null 2>&1; PYTHONPATH=/tmp/p python3 tools/art/render_assets.py \"\$@\"" sh "$@"
