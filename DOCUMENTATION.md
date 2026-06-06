<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo_dark.png">
    <img src="assets/logo_light.png" alt="The Way Out" width="280">
  </picture>

<h1>Documentation</h1>

<p>
    <a href="README.md"><b>README</b></a> ·
    <b>Documentation</b> ·
    <a href="VERSIONING.md"><b>Versioning</b></a> ·
    <a href="CHANGELOG.md"><b>Changelog</b></a>
  </p>
</div>

---

This page is the architectural overview of The Way Out: how the game
loop, levels, characters, interactables, editor, save file, and the
self-updater fit together. Module names below refer to actual files in
the repository. For the level-file tile vocabulary and the editor key
bindings, see [`assets/levels/LEGEND.md`](assets/levels/LEGEND.md) — it
is the authoritative reference and this page links to it rather than
restating it.

## Contents

1. [Source layout](#1-source-layout)
2. [Game loop and states](#2-game-loop-and-states)
3. [Levels and maps](#3-levels-and-maps)
4. [Characters and combat](#4-characters-and-combat)
5. [Interactables and puzzles](#5-interactables-and-puzzles)
6. [Level editor](#6-level-editor)
7. [Save files](#7-save-files)
8. [Updater and packaging](#8-updater-and-packaging)
9. [Testing](#9-testing)

## 1. Source layout

```text
main.py              Entry point: pygame init, the game-state machine, the main loop
launcher.py          Frozen entry point baked into the .app — the ONLY frozen Python;
                     relocate-to-/Applications, seed the code tree, then self-update
menu.py              Title, settings, level, character, and pause menus
levels.py            Level parsing, the Camera, and LevelManager (runtime + win/lose)
level_catalog.py     Merges built-in (manifest.json) and custom levels into one list
units.py             Character base + 5 playables, Boss, Enemy, Projectile
interactables.py     Spikes, Lever, Gate, KeyItem, PressurePlate (procedural art)
static_objects.py    Tile / Prop sprites + procedural TileTextures (floor/wall fallback)
tiles.py             TileSpec REGISTRY — the one tile vocabulary the loader + editor read
tileset.py           Tileset asset loader (floor/wall tiles + furniture/decor art)
theme.py             Shared palette, font cache, draw primitives, animated menu scene
audio.py             Lazy mixer: SFX + per-level music (clone-safe, fully optional)
effects.py           Particle bursts + full-screen fades (game-feel polish)
loading_screen.py    Inter-level beat: title, tagline, character avatar, control hints
editor.py            In-game level editor (palette → canvas → .txt)
save.py              JSON progress + preferences at ~/.the-way-out/save.json
updater.py           Self-update engine — pulls the latest code into ~/.the-way-out/app/
settings.py          Screen, FPS, save/level paths, TILE_SIZE constants
version.py / VERSION  Runtime version string (VERSION is the single source of truth)

assets/              Sprites, audio, fonts, and level maps
  levels/            *.txt maps + manifest.json + LEGEND.md (tile vocabulary)
  tileset/           Floor/wall tiles + furniture/decoration art
  units/             Character + enemy sprite sheets
  audio/sfx,music/   Sound effects and per-level music beds
scripts/             gen_sfx.py (SFX), make_icon.py (.icns), render_logo.swift (logo)
tests/               pytest suite (headless — conftest wires dummy SDL drivers)
build_mac.sh         PyInstaller builder — arm64 .app
build_mac_intel.sh   PyInstaller builder — x86_64 .app
The Way Out.spec     PyInstaller spec
pyproject.toml       Pinned runtime/build/dev deps + the Ruff config
```

## 2. Game loop and states

`main.py` boots pygame fullscreen at the monitor's native resolution
(`settings.WIDTH/HEIGHT` is only the fallback), constructs one instance
of every menu plus the `LevelManager` and `LevelEditor`, then runs a
single `clock`-paced loop over a `game_state` string machine:

| State         | Screen                                                         |
| :------------ | :------------------------------------------------------------- |
| `menu`        | Animated title scene — the chosen character is playable on it  |
| `settings`    | Sound + music-volume preferences                              |
| `char_select` | Character picker with stat bars and the per-character ability  |
| `lvls`        | Level menu (built-in + custom), ✓ marks and best-time line     |
| `loading`     | Inter-level loading screen — title, tagline, avatar, hints     |
| _playing_     | A live level, driven entirely by `LevelManager`               |
| `paused`      | Frozen-world overlay — preserves every bit of level state      |
| `editor`      | The in-game level editor                                      |
| `updating`    | Threaded self-update status toast over the title              |

`return_state` records where a finished run goes back to — normally
`lvls`, but `editor` when the level was launched from the editor's
**Test** button. The loading screen is shown only on first entry into a
level; R-retry and pause-restart bypass it with a direct
`level_manager.load_level()`. The update flow runs on a worker thread
that writes into `update_state`; the loop polls it each frame and
renders an animated status, so the window never blocks on the network.
Background music is selected per state (`_BGM_FOR_STATE`); gameplay
music is owned by the level (its `manifest.json` `music` track).

## 3. Levels and maps

A level is a plain-text grid where each cell is one `TILE_SIZE` (64 px)
tile. There are two kinds, and adding either needs **no code changes**:

- **Built-in** — `.txt` files in `assets/levels/`, listed in
  `assets/levels/manifest.json` (`id`, `file`, `title`, `tagline`,
  optional `music` / per-level floor+wall override).
- **Custom** — anything the editor saves, landing in
  `~/.the-way-out/custom_levels/<name>.txt` and auto-discovered (no
  manifest entry; shown with a `CUSTOM` pill).

`level_catalog.py` is the single source of truth that merges both
lists. Rows may be **dense** (one char per cell) or **tokenised**
(space-separated, so a cell can carry a variant number like `T3`); a
row is tokenised the moment it contains a space. The tile vocabulary
lives once in `tiles.py` (`REGISTRY`) — both the loader and the editor
palette read it, so the map format, the registry, and the editor never
drift apart. `levels.py` dispatches each glyph at load time, builds the
sprite groups, and `LevelManager` owns the runtime: the `Camera`,
collision, combat, the win/lose transition, and the best-time write.

> Full tile table, row formats, trigger/gate pairing, and the
> floor/wall and audio conventions are in
> [`assets/levels/LEGEND.md`](assets/levels/LEGEND.md).

## 4. Characters and combat

Combat is 4-directional: you aim the way you face and fire a ranged
`Projectile`. `units.py` defines a `Character` base and five playable
subclasses, each with its own HP / speed / damage / fire-rate profile
and one **signature ability** on a cooldown, fired with **Shift**:

| Character | Ability   | Effect                                              |
| :-------- | :-------- | :-------------------------------------------------- |
| Wizard    | Slow      | Enemies, boss, and their shots run at 0.35× for 3 s |
| Shiggy    | Dash      | Short, i-framed burst dash                          |
| Penguin   | Shield    | Total damage immunity for 2.5 s                     |
| Elf       | Volley    | Doubled fire rate for 2 s                           |
| Wolf      | Sprint    | 1.5 s of peak movement speed (no i-frames)          |

Threats are the `Boss` (two-phase; its general identity — Mr. Green,
Mr. Orange, Gen. Frost, The Archer, Mr. Shadow — is chosen
deterministically from the level id, so a level always fights the same
boss, with mechanics unchanged) and roaming `Enemy` chasers that deal
contact damage but do **not** gate the exit. The exit opens once the
boss (if any) is dead and the key is held.

## 5. Interactables and puzzles

`interactables.py` holds the escape-room props, all drawn with cached
procedural art (clone-safe, no asset files required):

- **Spikes** — timed hazard cycling safe → warning → deadly.
- **Lever** — pulled with **E** within reach.
- **PressurePlate** — trips after ~0.25 s of standing on it.
- **Gate** — solid until its trigger fires; a *panel* is the set of
  4-connected gate cells.
- **KeyItem** — walked over to pick up; required before the exit opens.

Triggers (levers + plates) bind to gate panels either **by reading
order** (top-to-bottom, left-to-right) or by an **explicit pair id** —
a matching trailing digit `1`–`9` on a trigger and its gate. The two
modes mix freely in one level. See the pairing rules in
[`LEGEND.md`](assets/levels/LEGEND.md).

## 6. Level editor

`editor.py` (`LevelEditor`) is a pygame-native palette-to-canvas editor
that writes `.txt` files in the same tokenised format the runtime
loads, into `~/.the-way-out/custom_levels/`. It reads the same
`tiles.REGISTRY`, so the palette can never offer a tile the loader does
not understand. The palette is a hover-driven drawer that overlays the
canvas without reflowing it; **Load** reopens any saved custom map,
**Theme** picks one of five floor/wall presets saved alongside the map,
and **Test** (or F5) launches a play-test that returns to the canvas
when the run ends. Player start (`P`) and exit (`X`) are singletons.
The full key-binding table is in
[`LEGEND.md`](assets/levels/LEGEND.md#in-game-level-editor).

## 7. Save files

`save.py` keeps one JSON document at `~/.the-way-out/save.json`:

```json
{
  "completed": ["level_1"],        // beaten level ids
  "times":     {"level_1": 42.7},  // best clear time, seconds
  "settings":  {"sound": true}     // persisted preferences
}
```

Every public helper goes through one `_load` / `_write` pair, so a
write of one section never clobbers another. `_write` is atomic
(`tmp` + `fsync` + `os.replace`), so a process killed mid-write leaves
the previous save intact instead of truncating it to `{}`. Any I/O or
shape error degrades to "no save data" / "save skipped" — a weird
filesystem never crashes the game. Legacy saves that stored integer
level indices are migrated to string ids on read. This on-disk shape is
the save-file surface frozen by
[`VERSIONING.md` §3.1](VERSIONING.md#31-save-file-format).

## 8. Updater and packaging

The packaged macOS `.app` is only a thin launcher. `launcher.py` is the
**only** Python PyInstaller bakes into the bundle, and it never changes
after a build. On launch it relocates the app into `/Applications`
(dodging macOS App Translocation), seeds the real game code from the
bundle on first run, and then hands off to it. The actual game lives
*outside* the frozen bundle, in `~/.the-way-out/app/`, and is refreshed
by `updater.py` straight from GitHub's `main` branch (a `codeload` zip,
versioned by the commit sha in `app/.version`). TLS is pinned to
`certifi`'s CA bundle — the frozen build ships no system CA store — and
an `online()` probe to `1.1.1.1:53` distinguishes "no internet" from
"GitHub unreachable". `updater.py` is pure standard library on purpose
(it is itself part of the auto-updated payload) and only ever writes
inside `~/.the-way-out/app/`; the save file is a *sibling* of `app/`, so
an update can never wipe progress. `build_mac.sh` / `build_mac_intel.sh`
produce the arm64 / x86_64 `.app` via PyInstaller.

> This section describes the implementation. The release, support, and
> security contract those mechanics must honour is in
> [`VERSIONING.md`](VERSIONING.md).

## 9. Testing

`tests/` is a headless pytest suite — `conftest` wires the dummy SDL
video/audio drivers before `pygame.init()`, so it runs without a
display or audio device. It covers the level-parser helpers
(`_split_cells` / `_cell_variant` / `_pair_id`), the `PressurePlate`
charge/trip lifecycle, `Lever.use` single-shot behaviour, and the
`Character` attack + ability-cooldown bookkeeping. CI
(`.github/workflows/ci.yml`) runs on every push and PR: a `check` job
on Ubuntu (`ruff check`, `pytest`, and an `import main` smoke under the
dummy drivers) and a `build` job on macOS that runs `build_mac.sh` and
uploads `dist/TheWayOut-mac.zip` as a workflow artifact.

---

[← Prev: README](README.md) · [Next: Versioning →](VERSIONING.md)
