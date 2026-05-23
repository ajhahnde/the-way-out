<div align="center">

<h1>The Way Out</h1>

<h3>A top-down pixel-art escape-room shooter.</h3>

<p>
    <a href="https://github.com/ajhahnde/the-way-out/actions/workflows/ci.yml"><img src="https://github.com/ajhahnde/the-way-out/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
    <img src="https://img.shields.io/badge/version-v1.0.4-blue" alt="Version">
    <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License">
    <img src="https://img.shields.io/badge/python-3.12+-orange" alt="Python 3.12+">
    <img src="https://img.shields.io/badge/target-macOS-lightgrey" alt="macOS">
  </p>

<p>
    <b>README</b> ·
    <a href="VERSIONING.md"><b>Versioning</b></a> ·
    <a href="CHANGELOG.md"><b>Changelog</b></a>
  </p>

</div>

---

<p align="center">
  <img src="assets/screenshot.png" alt="The Way Out — character select" width="780">
</p>

Pick a character, fight your way through locked rooms, work the levers
and pressure plates, and find the way out.

The Way Out's main purpose is to test and develop
[eeco](https://github.com/ajhahnde/eeco).

## Play

```bash
pip install pygame
python main.py
```

## Controls

| Input         | Action             |
| ------------- | ------------------ |
| WASD / Arrows | Move & aim (4-way) |
| Space         | Shoot              |
| Shift         | Dash               |
| E             | Use / interact     |
| Esc           | Pause / back       |

## Characters

Five playable characters, each with its own HP, speed, damage and
fire-rate profile: the balanced Wizard, the Penguin tank, the rapid-fire
Elf, the glass-cannon Shiggy, and the speedster Wolf.

## Levels

Three hand-authored escape rooms. Levels are plain text maps under
`assets/levels/` (see `LEGEND.md` for the tile vocabulary) plus a
`manifest.json`, so new rooms can be added without touching code. An
in-game editor (`editor.py`) edits them live.

## Project layout

| Path                                                          | Purpose                                  |
| ------------------------------------------------------------- | ---------------------------------------- |
| `main.py`                                                   | Entry point & game loop                  |
| `menu.py`                                                   | Title, settings, character & level menus |
| `levels.py`                                                 | Level loading & runtime                  |
| `units.py`                                                  | Player & enemy logic                     |
| `interactables.py` / `static_objects.py` / `tileset.py` | World objects                            |
| `editor.py`                                                 | In-game level editor                     |
| `theme.py`                                                  | Shared palette & UI helpers              |
| `audio.py`                                                  | Music & SFX                              |
| `assets/`                                                   | Sprites, audio, fonts, level maps        |

## Build (macOS)

```bash
./build_mac.sh        # arm64 .app
./build_mac_intel.sh  # x86_64 .app
```

The app self-updates from this repository on launch via `updater.py`;
save data lives outside the app bundle and is never touched by updates.

## Versioning

Semantic versioning (`vMAJOR.MINOR.PATCH`); each release is a single
annotated git tag. See [`CHANGELOG.md`](CHANGELOG.md) for the history.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

## See also

- [FlashOS](https://github.com/ajhahnde/FlashOS) — AArch64 bare-metal kernel for the Raspberry Pi 4 Model B.
- [eeco](https://github.com/ajhahnde/eeco) — self-maintaining workflow ecosystem + no-AI-spend knowledge layer.

---

[Next: Versioning →](VERSIONING.md)
