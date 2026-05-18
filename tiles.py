"""The level tile vocabulary — one source of truth.

Every character that can appear in a level's ``.txt`` has a
:class:`TileSpec` here. ``levels.py`` reads it for prop dispatch at load
time, and ``editor.py`` reads the same registry to build its palette.
So adding a new tile is one entry here (and at most one branch in
``load_level``), never a triple-edit across files.

Category vocabulary used by the editor's palette grouping:

* ``terrain`` — wall, floor: structural cells
* ``special`` — player spawn, exit: singletons the level needs exactly
  one of
* ``hazard``  — spikes, levers, plates, gates, key: escape-room
  interactables
* ``enemy``   — boss (and any future enemies)
* ``prop``    — tileset furniture/decor (with variants)
"""

from dataclasses import dataclass
from typing import Optional

import tileset
from units import ENEMY_INFO


@dataclass(frozen=True)
class TileSpec:
    """Metadata for one map character.

    ``tileset_category`` is non-``None`` when the tile draws from the
    art tileset — ``solid`` and ``variant_count`` then mirror
    ``tileset.CATEGORIES``. Otherwise the runtime renders the tile
    procedurally (walls, spikes, levers, ...).
    """
    char: str
    label: str
    category: str
    description: str
    solid: bool = False
    variant_count: int = 1
    tileset_category: Optional[str] = None


# Prop letters → tileset category. The only duplication left between
# this module and ``tileset.CATEGORIES``; everything else (variant count,
# solid flag) is read from tileset at registry build time.
_PROP_MAPPING = {
    'T': ('torch',    "Torch"),
    'C': ('chair',    "Chair"),
    'A': ('table',    "Table"),
    'E': ('shelf',    "Bookshelf"),
    'D': ('decor',    "Bookshelf decor"),
    'O': ('box',      "Box / crate"),
    'R': ('rubble',   "Rubble"),
    'M': ('misc',     "Misc clutter"),
    'Z': ('door',     "Door"),
    'J': ('trapdoor', "Trapdoor"),
    'H': ('chest',    "Chest"),
    'F': ('fire',     "Fire"),
}


def _build_registry():
    reg = {}

    # --- terrain --------------------------------------------------------
    reg['W'] = TileSpec(
        'W', "Wall", 'terrain', "Solid wall, blocks movement",
        solid=True)
    reg['.'] = TileSpec(
        '.', "Floor", 'terrain', "Walkable cell (default)")

    # --- special (singletons) -------------------------------------------
    reg['P'] = TileSpec(
        'P', "Player start", 'special',
        "Where the chosen character spawns. Use exactly one.")
    reg['X'] = TileSpec(
        'X', "Exit", 'special',
        "The way out — opens after boss/key conditions are met.")

    # --- hazards / puzzles ----------------------------------------------
    reg['S'] = TileSpec(
        'S', "Spikes", 'hazard',
        "Timed trap (safe → warning → deadly cycle).")
    # L/Y/G carry an optional pair id in their trailing digit. The
    # variant_count is what the editor wheel cycles: 1 = pair by
    # reading order (writes a bare token), 2..9 = explicitly pair the
    # trigger with the gate of the same number.
    reg['L'] = TileSpec(
        'L', "Lever", 'hazard',
        "Pull with E. Wheel: 1 = pair by order, 2-9 = pair with the "
        "gate of that number.",
        variant_count=9)
    reg['Y'] = TileSpec(
        'Y', "Pressure plate", 'hazard',
        "Stand on ~0.25 s. Wheel: 1 = pair by order, 2-9 = pair with "
        "the gate of that number.",
        variant_count=9)
    reg['G'] = TileSpec(
        'G', "Gate", 'hazard',
        "Solid until its trigger fires; adjacent G = one panel. Wheel: "
        "1 = pair by order, 2-9 = pair id.",
        solid=True, variant_count=9)
    reg['K'] = TileSpec(
        'K', "Key", 'hazard',
        "Walk over to pick up; required before the exit opens.")

    # --- enemies --------------------------------------------------------
    reg['B'] = TileSpec(
        'B', "Boss (Mr. Green)", 'enemy',
        "Spawns lazily the first time the player enters its arena.")
    # Generic enemies are derived from units.ENEMY_INFO so adding one
    # there makes it appear in the editor palette automatically.
    for ch, _cls, label in ENEMY_INFO:
        reg[ch] = TileSpec(
            ch, label, 'enemy',
            "Roaming enemy — chases the player and deals contact "
            "damage. Spawns at once; does not block the exit.")

    # --- tileset props --------------------------------------------------
    for ch, (cat, label) in _PROP_MAPPING.items():
        meta = tileset.CATEGORIES.get(cat)
        if meta is None:
            continue
        _folder, _pattern, count, solid = meta
        reg[ch] = TileSpec(
            ch, label, 'prop',
            f"{label} ({count} variant{'s' if count > 1 else ''}).",
            solid=solid, variant_count=count, tileset_category=cat)

    return reg


REGISTRY = _build_registry()

# Palette category order used by the editor. REGISTRY insertion order
# is preserved within each category (CPython dicts are ordered).
PALETTE_CATEGORIES = ('terrain', 'special', 'hazard', 'enemy', 'prop')

# Back-compat shim for ``levels.py``: char -> tileset category, for the
# prop branch of the level-loading switch. Derived so editing REGISTRY
# is the only place to add a prop letter.
PROP_CHARS = {ch: spec.tileset_category
              for ch, spec in REGISTRY.items()
              if spec.tileset_category is not None}


def chars_for(category):
    """All characters in one palette category, in REGISTRY order."""
    return [ch for ch, spec in REGISTRY.items() if spec.category == category]
