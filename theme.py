"""Shared minimal/clean UI theme.

One palette, one font cache, and the handful of draw primitives every
screen uses — so ``menu.py`` / ``levels.py`` / ``editor.py`` all look
like the same game (flat dark background, generous whitespace,
restrained hover accent, thin separators instead of boxes).

Centralising this keeps exactly one copy of every RGB tuple and of the
title / back-hint / hover primitives, so the screens cannot drift apart.
"""

import os
import random

import pygame
from settings import FONT, TILE_SIZE

# --- palette ---------------------------------------------------------
BG      = (18, 18, 24)        # every screen fills this
INK     = (214, 216, 226)     # primary text
MUTED   = (120, 122, 138)     # captions, hints, secondary text
ACCENT  = (240, 208, 120)     # hover / focus / bar fill
TITLE_C = (245, 240, 215)     # screen + game title
DONE_C  = (140, 230, 170)     # completed level
SEL_C   = (120, 220, 150)     # active selection
LINE_C  = (52, 54, 66)        # separators, bar tracks
SUCCESS = (120, 220, 150)     # win / level complete
FAIL    = (220, 96, 96)       # lose / defeat / danger

# One glyph for every hint separator / bullet across the game. Kept
# to chars present in main_font.otf — "·" renders as the .notdef box.
HINT_DOT = "|"


def shade(color, delta):
    """A panel tint derived from another palette colour (used for the
    editor's canvas / palette / toolbar splits so they stay a family
    of ``BG`` instead of independent tuples)."""
    return tuple(max(0, min(255, c + delta)) for c in color)


# --- fonts -----------------------------------------------------------
# A small ladder of conventional sizes so screens don't drift wildly.
# Callers pass the raw px to ``font(N)``; the cache means the same N
# is one Font object, not one per frame. The ladder is documentation,
# not enforced — pick the closest tier when adding a new caller.
#
#   DISPLAY  ~ 96  (level intro 'big' text)
#   TITLE    = 72  (game / pause / end-screen title)
#   HEADING  = 44  (subscreen title)
#   BODY     = 28  (button label, HUD label)
#   CAPTION  = 22  (tag, hint, secondary line)
FONT_TITLE   = 72
FONT_HEADING = 44
FONT_BODY    = 28
FONT_CAPTION = 22

_font_cache = {}


def font(px):
    """Cached ``pygame.font.Font`` for the shared game font at ``px``."""
    f = _font_cache.get(px)
    if f is None:
        f = pygame.font.Font(FONT, px)
        _font_cache[px] = f
    return f


_text_cache = {}


def text_surface(font_, s, color):
    """Cached ``font_.render(s, True, color)`` for static UI labels.

    Every menu/title primitive re-renders the same constant strings
    each frame (only the hover *colour* toggles); the surface a fresh
    render produces is fully determined by ``(font, string, colour)``
    at the fixed ``True`` antialias, so memoise it. Keyed by
    ``id(font_)`` — safe because every Font is held in ``_font_cache``
    for the whole process and never GC'd, so an id can't be recycled.
    The key set is statically bounded the same way ``_font_cache`` is
    (a fixed label set × the fixed palette × the size ladder), so a
    plain dict needs no eviction. Blitting never mutates the source
    surface, so one shared copy is safe to blit every frame.

    Not named ``text`` so it cannot shadow the ``text`` parameter of
    ``draw_title`` / ``draw_toast`` when they call it.
    """
    key = (id(font_), s, color)
    surf = _text_cache.get(key)
    if surf is None:
        surf = font_.render(s, True, color)
        _text_cache[key] = surf
    return surf


# --- helpers ---------------------------------------------------------
def measure(font_, text):
    """Size a string for a layout-only placement that is never blitted."""
    return pygame.Rect((0, 0), font_.size(text))


def draw_title(screen, font_, text, width, y=96):
    """Screen title in caps with a thin centred underline."""
    surf = text_surface(font_, text.upper(), TITLE_C)
    rect = surf.get_rect(center=(width // 2, y))
    screen.blit(surf, rect)
    ly = rect.bottom + 16
    pygame.draw.line(screen, LINE_C,
                     (width // 2 - 170, ly), (width // 2 + 170, ly), 2)


def draw_back_hint(screen, font_):
    surf = text_surface(font_, "ESC  BACK", MUTED)
    screen.blit(surf, surf.get_rect(topleft=(48, 44)))


def hover_marker(screen, rect):
    """Small accent square left of a hovered list item — font-
    independent, so it works with the pixel font."""
    cy = rect.centery
    pygame.draw.rect(screen, ACCENT,
                     pygame.Rect(rect.left - 34, cy - 5, 10, 10))


def draw_bar(screen, rect, ratio, color, *, border=True):
    """Themed rectangular meter shared by every HUD/stat bar.

    The track is always ``LINE_C``; the fill colour is the caller's
    choice (``ACCENT`` for HP/dash, etc.). With ``border=True`` the bar
    gets the HUD's beveled backplate + rim; ``False`` is the flat
    inline version for compact lists like the character stat block."""
    ratio = max(0.0, min(1.0, ratio))
    if border:
        pygame.draw.rect(screen, shade(BG, -10),
                         rect.inflate(8, 8), border_radius=6)
    pygame.draw.rect(screen, LINE_C, rect,
                     border_radius=4 if border else 0)
    if ratio > 0:
        fill_rect = pygame.Rect(rect.left, rect.top,
                                int(rect.width * ratio), rect.height)
        pygame.draw.rect(screen, color, fill_rect,
                         border_radius=4 if border else 0)
    if border:
        pygame.draw.rect(screen, shade(BG, -6), rect, 2,
                         border_radius=4)


def draw_toast(screen, text, font_, *, center_x, center_y,
               fg=None, bg=None, border=None, pad_x=22, pad_y=10):
    """Draw a small rounded toast box centred at ``(center_x, center_y)``.

    Layout is computed from the font metrics so the toast can never
    collide with siblings at other resolutions. Returns the drawn
    ``pygame.Rect`` so the caller can place anything else relative to
    it. ``fg`` defaults to ``ACCENT`` (the toast is the only screen
    element using the gold accent for body text — short, high-priority,
    transient).
    """
    if fg is None:
        fg = ACCENT
    if bg is None:
        bg = shade(BG, +30)
    if border is None:
        border = LINE_C
    surf = text_surface(font_, text, fg)
    box = surf.get_rect()
    box.width += pad_x * 2
    box.height += pad_y * 2
    box.center = (center_x, center_y)
    pygame.draw.rect(screen, bg, box, border_radius=6)
    pygame.draw.rect(screen, border, box, 2, border_radius=6)
    screen.blit(surf, surf.get_rect(center=box.center))
    return box


def _load_idle_frames(folder, scale):
    """Split ``assets/units/<folder>/D_Idle.png`` into scaled frames.

    Standalone of ``Character.load_assets`` so the menu scene can draw
    ambient sprites without pulling the whole Character class (HP /
    dash / projectile machinery). Returns ``[]`` if the sheet is
    missing — caller skips the actor."""
    path = os.path.join("assets", "units", folder, "D_Idle.png")
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return []
    count = 4  # every unit sheet uses 4 idle frames (units.SPRITE_SHEETS)
    fw = sheet.get_width() // count
    fh = sheet.get_height()
    out = []
    for i in range(count):
        sub = sheet.subsurface(pygame.Rect(i * fw, 0, fw, fh))
        out.append(pygame.transform.scale(
            sub, (int(fw * scale), int(fh * scale))))
    return out


class _MenuActor:
    """Single wandering sprite used by :class:`MenuScene`.

    No collision, no AI — just a position, a velocity that reflects at
    screen edges, and an idle-loop frame index driven off the wall
    clock (with a per-actor phase so the crowd doesn't blink in sync).
    Right-facing frames are mirrored from left-facing at construction.
    """

    def __init__(self, frames, x, y, vx, vy, phase_ms):
        self._frames_l = [pygame.transform.flip(f, True, False)
                          for f in frames]
        self._frames_r = list(frames)
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.phase_ms = int(phase_ms)

    def update(self, dt, w, h):
        self.x += self.vx * dt
        self.y += self.vy * dt
        frame_w = self._frames_r[0].get_width()
        frame_h = self._frames_r[0].get_height()
        if self.x < frame_w * 0.5:
            self.x = frame_w * 0.5
            self.vx = abs(self.vx)
        elif self.x > w - frame_w * 0.5:
            self.x = w - frame_w * 0.5
            self.vx = -abs(self.vx)
        if self.y < frame_h * 0.5:
            self.y = frame_h * 0.5
            self.vy = abs(self.vy)
        elif self.y > h - frame_h * 0.5:
            self.y = h - frame_h * 0.5
            self.vy = -abs(self.vy)

    def draw(self, screen, ticks_ms):
        frames = self._frames_l if self.vx < 0 else self._frames_r
        idx = ((ticks_ms + self.phase_ms) // 160) % len(frames)
        frame = frames[idx]
        screen.blit(frame, frame.get_rect(center=(int(self.x), int(self.y))))


class MenuScene:
    """Ambient background for menu screens.

    * A scrolling floor: one tile pre-baked into a slab the size of the
      screen + one tile of overscan, blitted with a wrapped (ox, oy)
      offset so the scroll is one blit per frame (not a per-tile grid).
    * A handful of wandering character sprites (idle loop) that bounce
      off the screen edges — keeps the title alive without lockstep
      motion.
    * A dark vignette on top so menu text stays readable regardless of
      the underlying art.

    Cheap enough to throw on every menu screen, but :class:`MainMenu`
    is the primary user — submenus that need their stat card / list to
    read clearly should stay on the quieter :class:`PixelDust`.
    """

    # Diagonal scroll velocity (px/s) for the floor slab.
    SCROLL_VX = 18
    SCROLL_VY = 12
    # Vignette darkness — alpha over BG. Tuned so ACCENT-gold title text
    # still pops; raise toward 160 if a particular screen needs more.
    VIGNETTE_ALPHA = 110

    _FOLDERS = ("wizard", "penguin", "elf", "shiggy", "wolf", "mrgreen",
                "orange")

    def __init__(self, width, height, *, actor_count=6, seed=23,
                 floor_tile="Tile_42", actor_scale=2):
        self.width = width
        self.height = height
        self._rng = random.Random(seed)
        self._t0 = pygame.time.get_ticks()
        self._last_ms = self._t0
        self._slab = self._build_slab(floor_tile)
        self._vignette = self._build_vignette()
        self.actors = self._build_actors(actor_count, actor_scale)

    def _build_slab(self, floor_tile):
        """Pre-render one screen-plus-overscan slab of the floor tile.

        Falls back to a flat BG fill if the tile asset is missing — the
        scene still works (vignette + actors over a flat panel) instead
        of crashing on the title screen."""
        ts = TILE_SIZE
        cols = self.width // ts + 2
        rows = self.height // ts + 2
        slab = pygame.Surface((cols * ts, rows * ts))
        slab.fill(BG)
        path = os.path.join("assets", "tileset", "tiles",
                            floor_tile + ".png")
        try:
            raw = pygame.image.load(path).convert_alpha()
            tile_img = pygame.transform.scale(raw, (ts, ts))
        except (pygame.error, FileNotFoundError):
            return slab
        # Tone the tile down so it sits behind the UI rather than
        # competing with it: blit the tile, then a dark wash over the
        # whole slab.
        for r in range(rows):
            for c in range(cols):
                slab.blit(tile_img, (c * ts, r * ts))
        wash = pygame.Surface(slab.get_size(), pygame.SRCALPHA)
        wash.fill((*BG, 90))
        slab.blit(wash, (0, 0))
        return slab

    def _build_vignette(self):
        # Per-surface uniform alpha (SDL's fast blit path), pixel-
        # identical to a uniform (*BG, A) SRCALPHA blit: both resolve
        # to dst = BG·(A/255) + dst·(1 − A/255). A plain Surface +
        # set_alpha blits far cheaper than a full-screen per-pixel
        # SRCALPHA surface (the single heaviest menu op).
        v = pygame.Surface((self.width, self.height))
        v.fill(BG)
        v.set_alpha(self.VIGNETTE_ALPHA)
        return v

    def _build_actors(self, count, scale):
        actors = []
        folders = list(self._FOLDERS)
        self._rng.shuffle(folders)
        for i in range(count):
            folder = folders[i % len(folders)]
            frames = _load_idle_frames(folder, scale)
            if not frames:
                continue
            x = self._rng.uniform(80, self.width - 80)
            y = self._rng.uniform(80, self.height - 80)
            angle = self._rng.uniform(0, 6.2831853)
            speed = self._rng.uniform(30, 70)
            vx = speed * pygame.math.Vector2(1, 0).rotate_rad(angle).x
            vy = speed * pygame.math.Vector2(1, 0).rotate_rad(angle).y
            phase = self._rng.randint(0, 600)
            actors.append(_MenuActor(frames, x, y, vx, vy, phase))
        return actors

    def draw(self, screen):
        now = pygame.time.get_ticks()
        dt = min(0.1, (now - self._last_ms) / 1000.0)
        self._last_ms = now
        t = (now - self._t0) / 1000.0
        slab_w = self._slab.get_width()
        slab_h = self._slab.get_height()
        ox = int(t * self.SCROLL_VX) % slab_w
        oy = int(t * self.SCROLL_VY) % slab_h
        # Blit slab tiled with wrap: one base copy, then three offset
        # copies cover any gap from the modulo offset.
        screen.blit(self._slab, (-ox, -oy))
        screen.blit(self._slab, (slab_w - ox, -oy))
        screen.blit(self._slab, (-ox, slab_h - oy))
        screen.blit(self._slab, (slab_w - ox, slab_h - oy))
        for actor in self.actors:
            actor.update(dt, self.width, self.height)
            actor.draw(screen, now)
        screen.blit(self._vignette, (0, 0))


class PixelDust:
    """Slow upward-drifting pixel particles for idle backgrounds.

    Shared by every menu so they all carry the same motion: pass a
    different seed for a different particle layout, same look (three
    BG-derived tints, capped speed, deterministic layout per seed)."""

    def __init__(self, width, height, seed=7, count=60):
        self.width = width
        self.height = height
        self._rng = random.Random(seed)
        self._last_ms = None
        shades = [shade(BG, +20), shade(BG, +34), shade(BG, +52)]
        self.particles = []
        for _ in range(count):
            self.particles.append({
                "x": self._rng.uniform(0, width),
                "y": self._rng.uniform(0, height),
                "vy": self._rng.uniform(8, 26),
                "s": self._rng.choice((2, 2, 3, 4)),
                "c": self._rng.choice(shades),
            })

    def draw(self, screen):
        now = pygame.time.get_ticks()
        if self._last_ms is None:
            self._last_ms = now
        dt = min(0.1, (now - self._last_ms) / 1000.0)
        self._last_ms = now
        for p in self.particles:
            p["y"] -= p["vy"] * dt
            if p["y"] < -4:
                p["y"] = self.height + 4
                p["x"] = self._rng.uniform(0, self.width)
            pygame.draw.rect(screen, p["c"],
                             (int(p["x"]), int(p["y"]), p["s"], p["s"]))
