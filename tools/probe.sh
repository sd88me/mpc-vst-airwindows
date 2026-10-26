#!/usr/bin/env bash
# Build tools/introspect.cpp on this (x86) host with every vendored model and write build/probe/models_probe.jsonl:
# each model's real parameter names, defaults and stepped values, the input of tools/gen_categories.py.
# Run after tools/vendor_airwin2rack.sh. Needs g++ and make; takes a minute or two on 16 cores.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
B="$ROOT/build/probe"
mkdir -p "$B/fac"
python3 - "$ROOT" "$B" <<'PY'
import os, sys
sys.path.insert(0, os.path.join(sys.argv[1], "tools"))
import models
b = sys.argv[2]
ms = models.models()
open(os.path.join(b, "all_models.cpp"), "w").write(models.table_cpp(ms))
for m in ms:
    open(os.path.join(b, "fac", m["name"] + ".cpp"), "w").write(models.factory_cpp(m["name"]))
open(os.path.join(b, "srcs.txt"), "w").write("\n".join(models.sources(ms)))
PY
cat > "$B/Makefile" <<'MK'
V=../../vendor/airwin2rack/src
SRCS=$(shell cat srcs.txt)
FACS=$(wildcard fac/*.cpp)
OBJS=$(patsubst %.cpp,o/%.o,$(SRCS)) $(patsubst fac/%.cpp,o/fac/%.o,$(FACS)) o/base.o o/all_models.o o/introspect.o
CXXFLAGS=-O1 -std=c++17 -w -I$(V) -I../../src
introspect: $(OBJS)
	$(CXX) -o $@ $^
o/%.o: $(V)/%.cpp
	@mkdir -p $(dir $@); $(CXX) $(CXXFLAGS) -c $< -o $@
o/fac/%.o: fac/%.cpp
	@mkdir -p o/fac; $(CXX) $(CXXFLAGS) -c $< -o $@
o/base.o: $(V)/airwin_consolidated_base.cpp
	@mkdir -p o; $(CXX) $(CXXFLAGS) -c $< -o $@
o/all_models.o: all_models.cpp
	@mkdir -p o; $(CXX) $(CXXFLAGS) -c $< -o $@
o/introspect.o: ../../tools/introspect.cpp
	@mkdir -p o; $(CXX) $(CXXFLAGS) -c $< -o $@
MK
make -C "$B" -s -j"$(nproc)"
"$B/introspect" > "$B/models_probe.jsonl"
echo "probed $(wc -l < "$B/models_probe.jsonl") models -> build/probe/models_probe.jsonl"
