"""Particle bursts and full-screen fades — game-feel polish.

Owned by :class:`levels.LevelManager`; emitters fire from the level's
event handlers (hit/death/ability) and the field is ticked + drawn each
frame. Particles live in world space and are clipped to the camera's
visible rect so off-screen bursts cost nothing to render.
"""

import random

import pygame


class Particle:
    """One short-lived sprite-less puff. Linear motion, decaying alpha.

    Kept tiny on purpose: the field can hold hundreds at once during a
    boss death, and every attribute access counts.
    """
    __slots__ = ("x", "y", "vx", "vy", "life", "life0", "color", "size",
                 "gravity", "drag")

    def __init__(self, x, y, vx, vy, life, color, size,
                 gravity=0.0, drag=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.life0 = life
        self.color = color
        self.size = size
        self.gravity = gravity
        self.drag = drag

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.gravity:
            self.vy += self.gravity * dt
        if self.drag:
            k = max(0.0, 1.0 - self.drag * dt)
            self.vx *= k
            self.vy *= k

    @property
    def alive(self):
        return self.life > 0


class ParticleField:
    """Pool of particles for one level run."""

    def __init__(self):
        self._items = []

    def clear(self):
        self._items.clear()

    def __len__(self):
        return len(self._items)

    def burst(self, x, y, count, color, *, speed=240, life=0.45,
              size=4, spread=1.0, size_jitter=2,
              gravity=0.0, drag=2.0):
        """Spawn ``count`` particles radiating from ``(x, y)``.

        ``spread`` is a 0..1 fraction of a full circle (1 = ring, 0.5 =
        cone-ish). ``drag`` decelerates them so the burst stops dead
        instead of drifting forever.
        """
        for _ in range(count):
            theta = random.random() * spread * 2 * 3.14159
            s = speed * (0.5 + random.random())
            vx = s * pygame.math.Vector2(1, 0).rotate_rad(theta).x
            vy = s * pygame.math.Vector2(1, 0).rotate_rad(theta).y
            sz = max(1, size + random.randint(-size_jitter, size_jitter))
            self._items.append(Particle(
                x, y, vx, vy,
                life * (0.7 + 0.6 * random.random()),
                color, sz, gravity, drag))

    def update(self, dt):
        if not self._items:
            return
        alive = []
        for p in self._items:
            p.update(dt)
            if p.alive:
                alive.append(p)
        self._items = alive

    def draw(self, screen, world_to_screen_offset, view_w, view_h):
        """Blit every alive particle, skipping any off the camera."""
        if not self._items:
            return
        ox, oy = world_to_screen_offset
        for p in self._items:
            sx = int(p.x - ox)
            sy = int(p.y - oy)
            if sx < -p.size or sx > view_w + p.size:
                continue
            if sy < -p.size or sy > view_h + p.size:
                continue
            a = max(0, min(255, int(255 * (p.life / p.life0))))
            r, g, b = p.color
            # Per-particle SRCALPHA surface so each fades independently;
            # cheap because particles are tiny (size ~2-8 px).
            d = p.size * 2
            surf = pygame.Surface((d, d), pygame.SRCALPHA)
            pygame.draw.circle(surf, (r, g, b, a), (p.size, p.size), p.size)
            screen.blit(surf, (sx - p.size, sy - p.size))


class FadeState:
    """Linear alpha overlay for level start / end transitions.

    Holds a single direction-and-duration pair: ``mode='in'`` starts at
    alpha=255 and decays to 0; ``mode='out'`` starts at 0 and rises to
    255. ``alpha()`` returns the current alpha to blit, or 0 when idle.
    """

    def __init__(self):
        self.mode = None     # 'in' | 'out' | None
        self.time = 0.0      # seconds remaining
        self.total = 0.0
        self.color = (0, 0, 0)

    def start_in(self, duration, color=(0, 0, 0)):
        self.mode = 'in'
        self.time = duration
        self.total = duration
        self.color = color

    def start_out(self, duration, color=(0, 0, 0)):
        self.mode = 'out'
        self.time = duration
        self.total = duration
        self.color = color

    def update(self, dt):
        if self.mode is None:
            return
        self.time = max(0.0, self.time - dt)
        if self.time == 0.0 and self.mode == 'in':
            self.mode = None

    def alpha(self):
        if self.mode is None or self.total <= 0:
            return 0
        ratio = self.time / self.total
        if self.mode == 'in':
            return int(255 * ratio)
        return int(255 * (1.0 - ratio))

    def draw(self, screen, view_w, view_h):
        a = self.alpha()
        if a <= 0:
            return
        overlay = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        overlay.fill((*self.color, a))
        screen.blit(overlay, (0, 0))
