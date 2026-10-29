# Handoff: continuing the Airwindows collections

For another Claude session (or person) taking this over. Read `README.md` (what it is), `docs/DEVELOPING.md` (how it is built),
`docs/STATUS.md` (per-collection state) and this file (how to carry on and what to watch for). Written 2026-10-30.

## State

- Repo: https://github.com/sd88me/mpc-vst-airwindows (public, `main`). Local checkout `/home/sam/mpc-vst-airwin2rack`. MIT.
- **11 of 24 collections are built, installed on both devices and released:** Tape, Distortion, Saturation, Dynamics, Filter, Reverb,
  Ambience, Consoles, Console Strips, Utility, Effects (329 of 528 models). Each has hand-written manual summaries
  (`docs/summaries/<Category>.json`).
- **Release v0.1.0** is published as a *pre-release* with 22 zips (11 plugins, armv7 and aarch64). Catalog PR
  https://github.com/sd88me/mpc-vst-plugins/pull/627 adds the 11 entries (`Airwindows Collection: <Category>`); the user merges it
  (`gh pr merge` is blocked for the agent).
- **13 collections not started (199 models):** Brightness 26, Dithers 23, XYZ Filters 24, LoFi 21, Subtlety 20, Amp Sims 18,
  Tone Color 17, Stereo 12, Bass 10, Biquads 9, Clipping 9, Noise 9, Unclassified 1. The user's stated order so far:
  Utility and Effects (done), then Brightness; the rest is yours to propose.
- Open before the release can be called stable: run each zip's own `install.sh` on both devices, `tools/test_port.sh` host tests on the
  collections added since Reverb, `tools/bench.sh` CPU per plugin, and decide whether parameter positions are frozen (they are not:
  `params.lock` is deleted before builds, so a regenerated layout can break saved projects).

## The pipeline for one category (the user's rule: write its summaries when you build it)

1. **Summaries.** Dump every model's manual and control names, then write `docs/summaries/<Slug>.json`
   (see "Summary format"). Run `tools/gen_categories.py`: it folds them into `vst/<Slug>/gen/docs.cpp` and warns if a summary was written for
   a different manual.
2. **Build** both targets: `MPC_VST=<mpc-vst-plugins checkout with the process_float wrapper change> tools/build_categories.sh <Slug>...`
   in the background (10 to 45 min per target under QEMU; a `cc1plus` segfault is normal, the script retries). It prints `FINISHED ...` and
   `ALLDONE`; check that each `.so` exists. On the author's machine the checkout is `/home/sam/aw-src/mvp-float`.
3. **Stage** for a device: `tools/stage_device.py --arch armv7 -o f.tar <Slug>...` (Force) and `--arch aarch64 -o l.tar ...` (Live III).
   Both use the graphite skin (Style A): the user decided every device gets it.
4. **Ask the user before restarting MPC**, then copy the tar to the device and run its `install.sh` (usage in `tools/stage_device.py`). It
   stops MPC, backs up `MPC.settings` to `MPC.settings.bak-aw-<time>`, copies the skins, art and `.so`, registers new plugins and starts MPC.
5. The user checks it on the device. Then `docs/status.json` (device facts), `tools/status.py`, and the README table
   (regenerate the rows; there is no script for it yet, see how the commits did it), commit, push.
6. **Release** (when the user asks): per plugin `tools/gen_skin.py vst/<Slug> --style A --self-contained`, then
   `release.py` and `catalog_check.py` from mpc-vst-plugins; recipe in `docs/DEVELOPING.md`. Add zips to the release with
   `gh release upload`. New catalog entries go in a PR to mpc-vst-plugins from a worktree off `origin/main`.

## Summary format

`docs/summaries/<Slug>.json`: `{ "<Model>": { "what": one line, "sound": 1-2 sentences, "use": 1-2 sentences, "controls": { "<param name>": "short line" }, "src": hash } }`.
`src` is `gen_categories.manual_hash(model)`; stamp it after writing:
`import tools/gen_categories as G; G.manual_hash(name)`. Rules the user liked:

- Written from the original manual in `vendor/airwin2rack/res/awpdoc/<Model>.txt` plus the real control names (`vst/<Slug>/gen/skin_models.json`).
  Do not invent behaviour. Where the manual is thin, say less. A model with no upstream manual gets either no entry (it keeps the
  "No manual page upstream" text) or a short one written from control names, which says so.
- Control keys must be the upstream parameter names exactly (including quirks such as `Highpas`, `x`, `Elevnth`).
- Keep lines short: the MANUAL page is 12 lines of about 110 characters, paged.
- Flag guesses to the user afterwards (past ones: MultiBandDistortion `H Mtrx`, Righteous4 `BtDepth`, ConsoleH `More`/`CrossFd`, C5Raw `Center`).

## Things that bit us (all verified on devices)

- **The skin binds by parameter index; the skin and the `.so` must be installed together.** Changing slot counts reshuffles params.
- **The skin folder is found by the vendor string compiled into the `.so`** (`vendor` in vst.json = `Airwindows`), not by `MPC.settings`.
- **MPC rewrites `MPC.settings` multi-line.** A registration entry written on one line comes back wrapped. Test for existing entries by
  grepping the `.so` file name, not the `name=` attribute (the stage script does); otherwise you add duplicates.
- **Stale `params.json`/`vst.json`:** after changing the generator, run `tools/gen_categories.py` before a build. The step buttons must not
  carry `step_of` (the wrapper would step on both of MPC's two touch events; `src/engine.cpp` debounces 250 ms itself).
- **Live III image rule:** the aarch64 UI draws an image only when it is at least 64 px wide, and crops rather than scales. The Q-Link badges
  are 64x64 images for that reason. Keep every skin image at least 64 px wide. The Force draws any size.
- **`GEN_VST_RELOCK=1` does not reach the Docker run;** delete `vst/<Slug>/params.lock` instead (`build_categories.sh` does).
- **The Console Strips plugin uses a slot map** (`AW_SLOT_MAP` in each `models.cpp`): skin slot k is not upstream parameter k. The offline preview
  (`tools/preview_skin.py`) applies it; older notes about "mismatched names" in previews no longer apply.
- Whole-set builds are slow; do not launch more than one `build_port.sh` at a time.
- The offline preview shows the real artwork only (no live text). Screenshots in the README are renders, not device photos.

## Devices (ask the user for the current addresses: they are DHCP and change)

| | Force | MPC Live III |
|---|---|---|
| CPU target | `armv7` | `aarch64` |
| Synths folder | `/sdcard/Synths` | `/nvme/Synths` |
| `MPC.settings` | `/media/az01-internal/Settings/MPC/MPC.settings` | `/data/Settings/MPC/MPC.settings` |
| Shell | root over ssh, BusyBox (no `timeout`, no `unzip`) | root over ssh |

Restart is `systemctl stop|start acvs` (the stage script does it). SSH to the Live III is refused for a while after a restart or when
the device sleeps; the user brings it back. "can't preserve ownership" warnings when copying to `/nvme` are harmless. The Force's MCP
screen tool reaches only the Force. The Live III's screen is readable over its remote addin's HTTP `/screen.png`; do not send touches
through it unless asked.

## Standing rules from the user

- Ask before restarting MPC on either device; back up `MPC.settings` first; stage files then move into place.
- Only kill your own processes (`ps -eo pid,args | grep "[x]yz"`, then `kill <pid>`); never `pkill -f` with a pattern that could match your own shell.
- `/home/sam/mpc-vst-plugins` is shared with another session: never `git commit -a` there; use a worktree off `origin/main`.
  `gh pr merge` is blocked: open the PR and let the user merge. Summarise review comments to the user before posting them.
- Never commit Akai's stock skin JSON/PNGs (our artwork is original). Keep repos free of private IPs and serials.
- Commit trailers: `Co-Authored-By: <model> <noreply@anthropic.com>` and the session line; PR bodies end with the Claude Code line.
- Use they/them for people whose pronouns you do not know.
- Credit: @Locrian (MockbaMod) for the TUI skin method is in the README and `docs/DEVELOPING.md`.

## Not done / ideas

- Real device screenshots for the README (the user was asked; renders are used meanwhile).
- `process_float` wrapper change as its own PR to mpc-vst-plugins (the branch `wrapper-float-effect`; builds here use a checkout that has it).
- A script for the README status table (rows are generated by an inline snippet today).
- Rename the installed plugins to "Airwindows Collection: <Category>" if the user wants the names to match the catalog (plugin name, skin
  folder, registrations and rebuilds on both devices).
