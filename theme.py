"""Shared minimal/clean UI theme.

One palette, one font cache, and the handful of draw primitives every
screen uses — so ``menu.py`` / ``levels.py`` / ``editor.py`` all look
like the same game (flat dark background, generous whitespace,
restrained hover accent, thin separators instead of boxes).

Centralising this keeps exactly one copy of every RGB tuple and of the
title / back-hint / hover primitives, so the screens cannot drift apart.
"""

import random

import pygame
from settings import FONT

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

# One glyph for every "·" hint separator / bullet across the game.
HINT_DOT = "·"


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


# --- helpers ---------------------------------------------------------
def measure(font_, text):
    """Size a string for a layout-only placement that is never blitted."""
    return pygame.Rect((0, 0), font_.size(text))


def draw_title(screen, font_, text, width, y=96):
    """Screen title in caps with a thin centred underline."""
    surf = font_.render(text.upper(), True, TITLE_C)
    rect = surf.get_rect(center=(width // 2, y))
    screen.blit(surf, rect)
    ly = rect.bottom + 16
    pygame.draw.line(screen, LINE_C,
                     (width // 2 - 170, ly), (width // 2 + 170, ly), 2)


def draw_back_hint(screen, font_):
    surf = font_.render("ESC  BACK", True, MUTED)
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
