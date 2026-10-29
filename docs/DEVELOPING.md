# Developing: building, skinning and releasing the Airwindows collections

All of Chris Johnson's airwindows effects as native MPC OS VST2 effects, **one plugin per upstream category**
(AW Reverb, AW Filter, AW Consoles, ... 23 in all, 528 models). Status of each: [STATUS.md](STATUS.md).

In each plugin:
- **CONTROLS**: the model name sits between `<` `>` arrows at the top (or use the PRESET menu: every model is a preset, with its
  own default settings). That model's controls appear on a wood-framed console panel: SSL-style caps coloured by what a control
  does (red gain/drive, blue time/frequency, green tone, white mix), a printed scale, and Q-Link badges (the Force knob number,
  coloured by Q-Link column). A footer-less layout leaves the whole panel for controls; the category accent plate is top right.
  Each model keeps its own settings while you browse; projects save models by name.
- **MANUAL**: the model's airwindows documentation, the description of each control first, page by page (`<` page `>`), with a
  legend of the knob colours.
- Audio runs in float straight from the host (no 16-bit step), via mpc-vst-plugins' `process_float` engine path.

## Layout

| Controls | Panel |
|---|---|
| 0 | "No controls" panel (48 models, fixed processing) |
| 1-3 | large knobs, one row |
| 4-7 | one row of normal knobs |
| 8-14 | two rows of small knobs |
| more than 14 | extra CONTROLS pages of 14 (the planned `AW Console Strips` split takes the 8 models over 14) |

Stepped controls get a detent knob. Rules and geometry live in `tools/art/layout.py`.

## Build

```
tools/vendor_airwin2rack.sh [ref]   # pull airwin2rack (sources + manual) into vendor/, records the commit
tools/probe.sh                      # every model's real parameters (x86 build)
tools/gen_categories.py             # regenerate all categories; new models append to each models.lock
tools/art/run.sh --style A --out build/art/A      # skin artwork (Docker python + Pillow + numpy); style A graphite, C grey
MPC_VST=<mpc-vst-plugins checkout> $MPC_VST/tools/build_port.sh vst/<Category>/vst.json [armv7|aarch64]
tools/gen_skin.py vst/<Category> --style A         # the skin (add --no-qlink-overlay to drop the Q-Link badges)
tools/status.py                     # refresh docs/STATUS.md
```
`vst/<Category>/build.sh` does the build and the skin in one go. `process_float` needs the wrapper change from the
mpc-vst-plugins branch `wrapper-float-effect` (not yet merged).
`tools/category_overrides.tsv` (from charlesvestal/schwung-airwindows) classifies models upstream leaves "Unclassified".

## Install (device)

Into the Synths folder (`/sdcard/Synths`, `/nvme/Synths` on a Live III): the plugin folder
`<vendor> - VST - AW <Category>/` (the `.so`, `Plugin Skins/`, `version.xml`) and the shared `AW Skin/` art folder
side by side (each plugin's build holds only the images its skin uses, about 11-14 MB; several plugins' folders merge), then register the plugin in `MPC.settings` (mpc-vst-plugins SKILL).

**The skin folder name comes from the vendor string compiled into the `.so`** (vst.json `vendor`), not from the manufacturer in
`MPC.settings`: change the vendor and you must rebuild. Currently `Airwindows - VST - AW <Category>`.

## Skin artwork

All artwork is drawn here (`tools/art/render_assets.py`, original and procedural: a height map lit from the top left):
walnut frame with mitred corners, engraved sections, wear, knob filmstrips (48 frames, three sizes, six roles), Q-Link
layers, category plates, the manual's colour legend. Titillium Web (SIL OFL) is baked into the images. No third-party artwork.
MPC draws live text at about 0.64 of the label height, so text is sized by its visual px (`layout.MPC_K`).

## Preview offline

`tools/preview_skin.py vst/Reverb Galactic3 [tab] [out.png]` (needs Pillow).

## Known issues

- Wheel/Q-Link stepping of the 40-entry Model and Manual page selectors is too fine (a click moves 1% of the range): use the
  `<` `>` buttons or the PRESET menu. The Reverb host test reports 4 such checks as failed.
- Experimental native Q-Link column outlines (`AW_QLINK_NATIVE=1 tools/gen_skin.py ...`) are off by default and unverified on a
  Force or Live III (only checked on an MPC One upstream).
- The MPC Live III (aarch64) draws an Image component only when the PNG is at least 64 px wide: smaller ones vanish and larger
  ones are cropped, not scaled (device test, 2026-10-27). The Force draws any size. So the Q-Link badges are 64 x 32 images with
  the badge in the middle (`render_badges`). Keep every skin image at least 64 px wide.
- MPC delivers each touch on a momentary button twice, 80 to 140 ms apart. `src/engine.cpp` handles the step buttons itself with
  a 250 ms debounce: do not give them `step_of` in params.json (the wrapper would then step on both events). Re-run
  `tools/gen_categories.py` before a rebuild after changing the generator, or vst.json/params.json go stale.
- Whole-set builds are slow (QEMU); the aarch64 compile sometimes segfaults once: just run it again.

## Releasing (plan)

mpc-vst-plugins' catalog lets one repo host several plugins, told apart by each registry entry's `asset_pattern`
(`mmiroshnikov/mpc-airwindows` already lists 22 that way). Plan: one tag per release holding a zip per plugin and generation
(`AW-Reverb-1.0.0-mpc-armv7.zip`, `-aarch64.zip`, ...), one `catalog/plugins/aw-<category>.json` each. Every zip must be
self-contained, so each carries the art its skin uses (about 11-14 MB, 32-bit PNGs: quantising to 8-bit flattened the knob shadows and caps).

Credits: airwindows (Chris Johnson, MIT), airwin2rack (Paul Walker, MIT), skin artwork drawn here (assets/CREDITS.md),
category overrides from schwung-airwindows (MIT).
