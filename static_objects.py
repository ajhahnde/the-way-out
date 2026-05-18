import pygame
from settings import TILE_SIZE

TS = TILE_SIZE


def _shade(color, d):
    """Lighten (d > 0) or darken (d < 0) a color, clamped to 0-255."""
    return tuple(max(0, min(255, c + d)) for c in color)


class TileTextures:
    """Lazily-built, cached 64x64 tile surfaces.

    One surface per kind is reused for every tile of that kind, so a
    4608x2944 level costs a handful of Surface allocations, not thousands.
    Built on first use (after the display exists).
    """

    WALL_BASE = (54, 52, 70)
    FLOOR_BASE = (32, 31, 44)

    _cache = {}

    @classmethod
    def _build_wall(cls):
        s = pygame.Surface((TS, TS)).convert()
        s.fill(cls.WALL_BASE)

        # Two-brick course with mortar lines for a dungeon-stone read.
        mortar = _shade(cls.WALL_BASE, -22)
        pygame.draw.line(s, mortar, (0, TS // 2), (TS, TS // 2), 3)
        pygame.draw.line(s, mortar, (TS // 2, 0), (TS // 2, TS // 2), 3)
        pygame.draw.line(s, mortar, (TS // 4, TS // 2), (TS // 4, TS), 3)
        pygame.draw.line(s, mortar, (3 * TS // 4, TS // 2), (3 * TS // 4, TS), 3)

        # Bevel: lit top/left, shadowed bottom/right -> blocks pop.
        hi = _shade(cls.WALL_BASE, 30)
        lo = _shade(cls.WALL_BASE, -34)
        pygame.draw.line(s, hi, (0, 0), (TS - 1, 0), 3)
        pygame.draw.line(s, hi, (0, 0), (0, TS - 1), 3)
        pygame.draw.line(s, lo, (0, TS - 1), (TS - 1, TS - 1), 3)
        pygame.draw.line(s, lo, (TS - 1, 0), (TS - 1, TS - 1), 3)
        return s

    @classmethod
    def _build_floor(cls, alt):
        base = cls.FLOOR_BASE if not alt else _shade(cls.FLOOR_BASE, 5)
        s = pygame.Surface((TS, TS)).convert()
        s.fill(base)
        pygame.draw.rect(s, _shade(base, -10), (0, 0, TS, TS), 1)
        pygame.draw.rect(s, _shade(base, 8), (4, 4, TS - 8, TS - 8), 1)
        return s

    @classmethod
    def get(cls, kind):
        if kind not in cls._cache:
            if kind == 'wall':
                cls._cache[kind] = cls._build_wall()
            elif kind == 'floor':
                cls._cache[kind] = cls._build_floor(False)
            elif kind == 'floor_alt':
                cls._cache[kind] = cls._build_floor(True)
            else:  # unknown -> magenta marker, easy to spot
                surf = pygame.Surface((TS, TS)).convert()
                surf.fill((120, 40, 120))
                cls._cache[kind] = surf
        return cls._cache[kind]


class StaticObject(pygame.sprite.Sprite):
    pass


class Tile(pygame.sprite.Sprite):
    """A static map cell.

    Walls go into the obstacle group for collision; the level pre-renders
    the look into one big surface, so every wall shares one cached image
    (no per-tile Surface allocation).
    """

    def __init__(self, pos, groups, sprite_type, surface=None):
        super().__init__(groups)
        self.sprite_type = sprite_type
        self.image = surface if surface is not None else TileTextures.get(
            sprite_type if sprite_type in ('wall', 'floor') else 'wall')
        self.rect = self.image.get_rect(topleft=pos)
        # Trim the vertical hitbox slightly so corners feel less sticky.
        self.hitbox = self.rect.inflate(0, -8)


class Prop(pygame.sprite.Sprite):
    """A tileset furniture/decoration object placed from the map.

    The art is bottom-anchored inside its tile (see ``tileset._fit``).
    ``solid`` props join the obstacle group so the player can't walk
    through them — their hitbox is just the lower footprint so you can
    still slip past the visual top. Decorations are draw-only.
    """

    def __init__(self, pos, image, solid=False, obstacle_group=None):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=pos)
        if solid:
            self.hitbox = self.rect.inflate(-10, -TILE_SIZE // 2)
            self.hitbox.bottom = self.rect.bottom - 4
            if obstacle_group is not None:
                obstacle_group.add(self)
        else:
            self.hitbox = self.rect.copy()
