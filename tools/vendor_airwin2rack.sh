#!/usr/bin/env bash
# Re-vendor the airwindows sources from baconpaul/airwin2rack into vendor/airwin2rack/.
#   tools/vendor_airwin2rack.sh [ref]     (ref: a branch, tag or commit; default main)
# Copies the consolidated effect sources (src/autogen_airwin, the base class, ModuleAdd.h for names/categories)
# and the per-effect manual (res/awpdoc), then records the commit in vendor/VENDORED.md. Nothing is patched in
# place: the category generator reads ModuleAdd.h, and tools/category_overrides.tsv fills in "Unclassified" ones.
# After running: tools/gen_categories.py, rebuild, and commit vendor/ with the new commit in the message.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
REF="${1:-main}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git clone -q --filter=blob:none https://github.com/baconpaul/airwin2rack.git "$TMP/a2r"
git -C "$TMP/a2r" checkout -q "$REF"
SHA="$(git -C "$TMP/a2r" rev-parse HEAD)"; DATE="$(git -C "$TMP/a2r" log -1 --format=%cs)"
OUT="$HERE/vendor/airwin2rack"
rm -rf "$OUT"; mkdir -p "$OUT/src" "$OUT/res"
cp "$TMP/a2r/LICENSE.md" "$OUT/"
cp "$TMP/a2r/src/airwin_consolidated_base.h" "$TMP/a2r/src/airwin_consolidated_base.cpp" "$TMP/a2r/src/ModuleAdd.h" "$OUT/src/"
cp -r "$TMP/a2r/src/autogen_airwin" "$OUT/src/"
rm -f "$OUT/src/autogen_airwin/CMakeLists.txt"
cp -r "$TMP/a2r/res/awpdoc" "$OUT/res/"
cat > "$HERE/vendor/VENDORED.md" <<MD
# Vendored: airwin2rack

- Upstream: https://github.com/baconpaul/airwin2rack (MIT; airwindows by Chris Johnson, MIT)
- Commit: \`$SHA\` ($DATE)
- Copied: \`LICENSE.md\`, \`src/airwin_consolidated_base.{h,cpp}\`, \`src/ModuleAdd.h\`, \`src/autogen_airwin/\` (minus its CMakeLists),
  \`res/awpdoc/\` (manual text per effect).
- Local changes: none. Update with \`tools/vendor_airwin2rack.sh [ref]\`.
MD
echo "vendored airwin2rack $SHA ($DATE): $(ls "$OUT/src/autogen_airwin" | grep -c 'Proc.cpp$') effects"
