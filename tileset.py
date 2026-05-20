"""Tileset asset loader.

Every floor/wall tile and every furniture/decoration object the level
text files can place comes from ``assets/tileset/`` through here. The
art is tiny pixel-art (16x16 tiles, sub-tile props); this module scales
each piece up to one ``TILE_SIZE`` cell, caches the result, and hands
back a ready-to-blit surface. One surface per (category, variant) is
reused for every placement, mirroring the cheap-allocation approach in
``static_objects.TileTextures``.

Built lazily on first use, so it is safe to import before the pygame
display exists (the actual loads happen during ``load_level``).
"""

import os

import pygame

from settings import TILE_SIZE

TS = TILE_SIZE
_BASE = os.path.join("assets", "tileset")

# --- baked floor / wall layer -------------------------------------------
# Which Tile_XX.png the level's baked map surface uses. These are the
# only two values to tweak to restyle the dungeon floor/walls. To see
# the choices, open assets/tileset/tiles/ (or the full sheet at
# assets/tileset/Tileset.png / Palette.png) and put the file's number
# here. If a name fails to load the level falls back to the old
# procedural stone look automatically, so a bad value is harmless.
FLOOR_TILE = "Tile_42"
WALL_TILE = "Tile_03"

# --- map themes ---------------------------------------------------------
# Named floor/wall presets the editor's theme picker offers per custom
# map. Each is (id, display name, floor Tile_XX, wall Tile_XX). The id is
# what gets written to the map's sidecar JSON; ``"keep"`` reuses the
# global FLOOR_TILE/WALL_TILE above so an un-themed map looks unchanged.
# A bad tile name is harmless — ``tile`` returns None and the level
# falls back to the procedural stone look.
DEFAULT_THEME = "keep"
THEMES = [
    ("keep",    "Keep",    FLOOR_TILE, WALL_TILE),
    ("foundry", "Foundry", "Tile_53", "Tile_34"),
    ("cellar",  "Cellar",  "Tile_30", "Tile_15"),
    ("archive", "Archive", "Tile_44", "Tile_05"),
    ("frost",   "Frost",   "Tile_48", "Tile_07"),
]


def theme_tiles(theme_id):
    """``(floor_tile, wall_tile)`` for a theme id, falling back to
    ``DEFAULT_THEME`` for an unknown or missing id."""
    for tid, _name, floor, wall in THEMES:
        if tid == theme_id:
            return floor, wall
    for tid, _name, floor, wall in THEMES:
        if tid == DEFAULT_THEME:
            return floor, wall
    return FLOOR_TILE, WALL_TILE


# --- placeable objects --------------------------------------------------
# map letter -> (folder under assets/tileset, filename pattern with
# "{n}" for the variant, variant count, solid?). ``solid`` props join
# the obstacle group (you can't walk through them); the rest are pure
# decoration drawn under the player. The letter -> category mapping
# lives in levels.py (PROP_CHARS); keep the two in sync with LEGEND.md.
CATEGORIES = {
    "torch":    ("static_objects/torches",        "{n}.png",        8,  False),
    "chair":    ("static_objects/chairs",         "{n}.png",        14, False),
    "table":    ("static_objects/tables",         "{n}.png",        8,  True),
    "shelf":    ("static_objects/bookshelf",      "{n}.png",        12, True),
    "decor":    ("static_objects/bookshelf_decor", "{n}.png",       40, False),
    "box":      ("static_objects/boxes",          "{n}.png",        16, True),
    "rubble":   ("static_objects/blockage",       "{n}.png",        8,  True),
    "misc":     ("static_objects/other",          "{n}.png",        44, False),
    "door":     ("static_objects/doors",          "{n}.png",        4,  True),
    "trapdoor": ("static_objects/trapdoors",      "{n}.png",        6,  False),
    "chest":    ("interactables",                 "Chest{n}_S.png", 2,  True),
    "fire":     ("interactables",                 "Fire1.png",      1,  False),
}

_cache = {}


def _placeholder():
    """Magenta block for a missing/unknown asset — loud on purpose."""
    if "__ph__" not in _cache:
        s = pygame.Surface((TS, TS), pygame.SRCALPHA)
        s.fill((180, 40, 160))
        pygame.draw.rect(s, (0, 0, 0), s.get_rect(), 2)
        _cache["__ph__"] = s
    return _cache["__ph__"]


def _fit(surf):
    """Scale a small pixel-art sprite up to sit in one tile, keeping
    aspect ratio (nearest-neighbour, anchored bottom-centre so the
    object visually rests on the floor)."""
    w, h = surf.get_size()
    scale = TS / max(w, h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    img = pygame.transform.scale(surf, (nw, nh))
    cell = pygame.Surface((TS, TS), pygame.SRCALPHA)
    cell.blit(img, ((TS - nw) // 2, TS - nh))
    return cell


def tile(name):
    """A floor/wall tile scaled to exactly one cell, or None if the
    named PNG is missing (caller then uses the procedural fallback)."""
    key = ("tile", name)
    if key not in _cache:
        path = os.path.join(_BASE, "tiles", name + ".png")
        try:
            s = pygame.image.load(path).convert_alpha()
            _cache[key] = pygame.transform.scale(s, (TS, TS))
        except (pygame.error, FileNotFoundError):
            _cache[key] = None
    return _cache[key]


def is_solid(category):
    cat = CATEGORIES.get(category)
    return bool(cat and cat[3])


def variant_count(category):
    cat = CATEGORIES.get(category)
    return cat[2] if cat else 0


def sprite(category, variant=1):
    """One tile-sized surface for ``category``/``variant`` (1-based).

    Out-of-range or non-numeric variants clamp to 1. Unknown category
    or a missing file yields the magenta placeholder."""
    cat = CATEGORIES.get(category)
    if cat is None:
        return _placeholder()
    sub, pattern, count, _solid = cat

    n = variant if isinstance(variant, int) and 1 <= variant <= count else 1
    key = (category, n)
    if key in _cache:
        return _cache[key]

    path = os.path.join(_BASE, sub, pattern.format(n=n))
    try:
        raw = pygame.image.load(path).convert_alpha()
        if category == "fire":
            # Fire1.png is a horizontal animation strip; the first
            # square frame is enough for a static torch-fire decoration.
            h = raw.get_height()
            raw = raw.subsurface((0, 0, h, h)).copy()
        img = _fit(raw)
    except (pygame.error, FileNotFoundError, ValueError):
        img = _placeholder()

    _cache[key] = img
    return img
