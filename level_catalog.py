"""Single source of truth for the level list.

Built-in levels come from ``assets/levels/manifest.json``. Custom levels
written by the in-game editor are discovered as ``*.txt`` files in
``~/.the-way-out/custom_levels/`` and appended at the end of the list.

Each level has a stable string id (``"level_1"`` for built-ins,
``"custom_<name>"`` for user-built). The id is what :mod:`save` records
as completed and what :meth:`LevelManager.load_level` takes — so adding
a built-in level or saving one in the editor needs no code changes
anywhere else.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import tileset
from settings import SAVE_DIR

CUSTOM_DIR = SAVE_DIR / "custom_levels"
MANIFEST_PATH = Path("assets/levels/manifest.json")


@dataclass(frozen=True)
class LevelEntry:
    """One playable level — built-in or user-built.

    ``id``     stable handle used by save.py and the level menu.
    ``file``   path (working-dir relative for built-ins, absolute for
               custom) to the level's .txt.
    ``title``  short header (e.g. "LEVEL 1").
    ``tagline`` one-liner under the title.
    ``custom`` True for editor-written levels; the level menu uses this
               to mark them visually so a player can tell them apart.
    ``music``  optional background-track name under
               ``assets/audio/music/`` (no extension); None = silent.
    ``floor_tile`` / ``wall_tile`` optional per-level tileset PNG names
               (under ``assets/tileset/tiles/``); None = the global
               ``tileset.FLOOR_TILE`` / ``WALL_TILE`` default.
    """
    id: str
    file: str
    title: str
    tagline: str
    custom: bool
    music: str | None = None
    floor_tile: str | None = None
    wall_tile: str | None = None


def _load_manifest():
    """Built-in levels from manifest.json. Empty list on any IO error so
    a missing/corrupt manifest never crashes the menu."""
    try:
        with open(MANIFEST_PATH) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    # Valid JSON that isn't the expected shape (top level not an object,
    # "levels" not a list, an entry not a dict) must also degrade to an
    # empty list, not raise — the docstring promises the menu never
    # crashes on a corrupt manifest, and AttributeError/TypeError from
    # the wrong shape aren't caught above.
    if not isinstance(data, dict):
        return []
    levels = data.get("levels", [])
    if not isinstance(levels, list):
        return []
    out = []
    for raw in levels:
        try:
            out.append(LevelEntry(
                id=raw["id"],
                file=os.path.join("assets/levels", raw["file"]),
                title=raw.get("title", raw["id"]),
                tagline=raw.get("tagline", ""),
                custom=False,
                music=raw.get("music"),
                floor_tile=raw.get("floor_tile"),
                wall_tile=raw.get("wall_tile")))
        except (KeyError, TypeError):
            continue
    return out


def read_custom_theme(txt_path):
    """Theme id from a custom map's ``<name>.json`` sidecar.

    Returns ``tileset.DEFAULT_THEME`` when there is no sidecar, it can't
    be read, or it isn't the expected shape — defensive in the same
    spirit as :func:`_load_manifest`, so a stray/corrupt sidecar never
    breaks the level list."""
    sidecar = Path(txt_path).with_suffix(".json")
    try:
        with open(sidecar) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return tileset.DEFAULT_THEME
    if not isinstance(data, dict):
        return tileset.DEFAULT_THEME
    theme_id = data.get("theme", tileset.DEFAULT_THEME)
    return theme_id if isinstance(theme_id, str) else tileset.DEFAULT_THEME


def _scan_custom():
    """Levels saved by the editor under ``~/.the-way-out/custom_levels/``.

    The file name (without extension) becomes the human-readable title
    and is also part of the id, so renaming a file = a "new" level for
    the save system. A map's visual theme comes from its ``<name>.json``
    sidecar (see :func:`read_custom_theme`); an un-themed map resolves to
    the default tiles and looks unchanged."""
    if not CUSTOM_DIR.exists():
        return []
    out = []
    for path in sorted(CUSTOM_DIR.glob("*.txt")):
        name = path.stem
        floor_tile, wall_tile = tileset.theme_tiles(read_custom_theme(path))
        out.append(LevelEntry(
            id=f"custom_{name}",
            file=str(path),
            title=name.replace("_", " ").title(),
            tagline="Custom",
            custom=True,
            music="default",
            floor_tile=floor_tile,
            wall_tile=wall_tile))
    return out


def load_catalog():
    """Return every playable level in display order:
    built-ins (manifest order) followed by custom levels (alphabetical)."""
    return _load_manifest() + _scan_custom()


def find(level_id):
    """Look up a level by id. Returns ``None`` if it's not in the
    catalog (e.g. user deleted a custom file)."""
    for entry in load_catalog():
        if entry.id == level_id:
            return entry
    return None


def ensure_custom_dir():
    """Make sure the custom-level directory exists; safe to call any
    time."""
    try:
        CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
