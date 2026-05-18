"""Escape-room props: spike traps, levers, gates, the key and plates.

All visuals are procedural (one cached surface set per class, like
``static_objects.TileTextures``) so the game stays clone-safe and costs
only a handful of Surface allocations no matter how many props a level
has. Every prop is a normal ``Sprite`` with ``image``/``rect``/``hitbox``
so the level can blit and collision-test it like any other sprite.
"""

import pygame
from settings import (
    TILE_SIZE, SPIKE_CYCLE, SPIKE_DANGER_TIME, SPIKE_WARN_TIME,
    PLATE_TRIGGER_DELAY,
)

TS = TILE_SIZE

# Shared state cues for the escape-room props. The lever uses both;
# the plate's "off" state is intentionally a quiet grey (the plate is
# *inactive*, not *dangerous*), so only ON_COL is shared with it.
ON_COL  = (90, 220, 130)
OFF_COL = (205, 90, 90)


class Spikes(pygame.sprite.Sprite):
    """Floor trap on a shared clock: safe -> warning -> deadly -> safe.

    Every spike is created with the same phase, so the whole field
    pulses together and the player can learn the rhythm. It only hurts
    while fully extended; the warning frame telegraphs that so timing a
    crossing is fair rather than a coin flip.
    """

    _imgs = None

    def __init__(self, pos, groups, phase=0.0):
        super().__init__(groups)
        self._build_images()
        self.t = phase
        self.image = self._imgs['down']
        self.rect = self.image.get_rect(topleft=pos)
        # Inset so you can stand on the very edge of a tile unharmed.
        self.hitbox = self.rect.inflate(-16, -16)
        self.deadly = False

    @classmethod
    def _build_images(cls):
        if cls._imgs is not None:
            return

        def base():
            s = pygame.Surface((TS, TS), pygame.SRCALPHA)
            pygame.draw.rect(s, (26, 24, 32), (3, 3, TS - 6, TS - 6),
                             border_radius=4)
            pygame.draw.rect(s, (12, 11, 16), (3, 3, TS - 6, TS - 6), 2,
                             border_radius=4)
            for ox in range(2):
                for oy in range(2):
                    cx, cy = TS // 4 + ox * TS // 2, TS // 4 + oy * TS // 2
                    pygame.draw.circle(s, (8, 8, 12), (cx, cy), 5)
            return s

        def teeth(color, h):
            s = base()
            for ox in range(2):
                for oy in range(2):
                    cx, cy = TS // 4 + ox * TS // 2, TS // 4 + oy * TS // 2
                    pygame.draw.polygon(s, color, [
                        (cx - 7, cy + 6), (cx + 7, cy + 6), (cx, cy - h)])
                    pygame.draw.line(s, (255, 255, 255),
                                     (cx - 2, cy - h + 4), (cx, cy - h), 2)
            return s

        cls._imgs = {
            'down': base(),
            'warn': teeth((148, 96, 74), 9),
            'up': teeth((214, 82, 70), 18),
        }

    def update(self, dt):
        self.t = (self.t + dt) % SPIKE_CYCLE
        danger_start = SPIKE_CYCLE - SPIKE_DANGER_TIME
        warn_start = danger_start - SPIKE_WARN_TIME
        if self.t >= danger_start:
            self.image, self.deadly = self._imgs['up'], True
        elif self.t >= warn_start:
            self.image, self.deadly = self._imgs['warn'], False
        else:
            self.image, self.deadly = self._imgs['down'], False


class Lever(pygame.sprite.Sprite):
    """Pull-once switch. ``use()`` flips it and the level opens every
    gate whose ``group_id`` matches this lever's ``gate_group``."""

    _imgs = None

    def __init__(self, pos, groups, gate_group):
        super().__init__(groups)
        self._build_images()
        self.gate_group = gate_group
        self.activated = False
        self.image = self._imgs[False]
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.copy()

    @classmethod
    def _build_images(cls):
        if cls._imgs is not None:
            return

        def make(on):
            s = pygame.Surface((TS, TS), pygame.SRCALPHA)
            plate = pygame.Rect(TS // 4, TS // 6, TS // 2, TS * 2 // 3)
            pygame.draw.rect(s, (42, 40, 52), plate, border_radius=6)
            pygame.draw.rect(s, (16, 15, 22), plate, 2, border_radius=6)
            pivot = (TS // 2, TS * 2 // 3)
            knob = (TS * 2 // 3, TS // 3) if on else (TS // 3, TS // 3)
            col = ON_COL if on else OFF_COL
            pygame.draw.line(s, (18, 17, 24), pivot, knob, 8)
            pygame.draw.line(s, (158, 158, 168), pivot, knob, 4)
            pygame.draw.circle(s, col, knob, 9)
            pygame.draw.circle(s, (235, 235, 240), knob, 9, 2)
            pygame.draw.circle(s, (20, 19, 26), pivot, 5)
            return s

        cls._imgs = {False: make(False), True: make(True)}

    def use(self):
        if self.activated:
            return False
        self.activated = True
        self.image = self._imgs[True]
        return True


class Gate(pygame.sprite.Sprite):
    """One cell of a (possibly multi-cell) gate.

    While shut it sits in the obstacle group for collision and draws as
    a barred door. Its lever calls :meth:`open`, which pulls it out of
    the obstacle group (collision gone) and swaps to the open frame.
    """

    _imgs = None

    def __init__(self, pos, draw_group, obstacle_group, group_id):
        super().__init__(draw_group)
        self._build_images()
        self.group_id = group_id
        self.obstacle_group = obstacle_group
        obstacle_group.add(self)
        self.opened = False
        self.image = self._imgs[False]
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -8)

    @classmethod
    def _build_images(cls):
        if cls._imgs is not None:
            return

        shut = pygame.Surface((TS, TS), pygame.SRCALPHA)
        shut.fill((28, 26, 34))
        pygame.draw.rect(shut, (72, 68, 88), (0, 0, TS, TS), 3)
        for i in range(1, 4):
            x = i * TS // 4
            pygame.draw.line(shut, (122, 118, 142), (x, 4), (x, TS - 4), 6)
            pygame.draw.line(shut, (58, 56, 72), (x + 2, 4), (x + 2, TS - 4), 2)
        for y in (TS // 3, 2 * TS // 3):
            pygame.draw.line(shut, (98, 94, 114), (4, y), (TS - 4, y), 4)

        opened = pygame.Surface((TS, TS), pygame.SRCALPHA)
        pygame.draw.rect(opened, (60, 58, 74), (0, 0, TS, 6))
        pygame.draw.rect(opened, (60, 58, 74), (0, TS - 6, TS, 6))
        for x in (5, TS - 11):  # bars retracted into the side jambs
            pygame.draw.rect(opened, (92, 88, 108), (x, 6, 6, TS - 12))

        cls._imgs = {False: shut, True: opened}

    def open(self):
        if self.opened:
            return
        self.opened = True
        self.obstacle_group.remove(self)
        self.image = self._imgs[True]


class KeyItem(pygame.sprite.Sprite):
    """The key to the way out. Walking over it picks it up; the level
    bobs/glows it when drawing."""

    _img = None

    def __init__(self, pos, groups):
        super().__init__(groups)
        self._build_image()
        self.image = self._img
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(-10, -10)
        self.t = 0.0

    @classmethod
    def _build_image(cls):
        if cls._img is not None:
            return
        s = pygame.Surface((TS, TS), pygame.SRCALPHA)
        c, cx = (245, 205, 70), TS // 2
        pygame.draw.circle(s, c, (cx, TS // 2 - 9), 12)
        pygame.draw.circle(s, (58, 48, 16), (cx, TS // 2 - 9), 5)
        pygame.draw.rect(s, c, (cx - 4, TS // 2 - 2, 8, 26))
        pygame.draw.rect(s, c, (cx + 4, TS // 2 + 12, 10, 6))
        pygame.draw.rect(s, c, (cx + 4, TS // 2 + 20, 8, 5))
        cls._img = s

    def update(self, dt):
        self.t += dt


class PressurePlate(pygame.sprite.Sprite):
    """Floor plate that opens its paired gate when the player stands on
    it long enough.

    Levers need a button press (E) within reach; plates need only your
    weight — but you have to commit to standing on them for a heartbeat
    so a stray cross-the-room doesn't trip them by accident. Once
    triggered the plate stays down for the rest of the run, matching
    the one-shot feel of levers, and the level pairs them to gates by
    reading order exactly like levers.
    """

    _imgs = None

    def __init__(self, pos, groups, gate_group):
        super().__init__(groups)
        self._build_images()
        self.gate_group = gate_group
        self.activated = False
        self.charge = 0.0           # seconds player has stood on it
        self.image = self._imgs[False]
        self.rect = self.image.get_rect(topleft=pos)
        # Trigger area covers most of the cell but not the very edges
        # so brushing past doesn't count.
        self.hitbox = self.rect.inflate(-12, -12)

    @classmethod
    def _build_images(cls):
        if cls._imgs is not None:
            return

        def make(on):
            s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            # Sunken stone base
            base = pygame.Rect(6, 6, TILE_SIZE - 12, TILE_SIZE - 12)
            pygame.draw.rect(s, (38, 36, 50), base, border_radius=8)
            pygame.draw.rect(s, (14, 13, 20), base, 3, border_radius=8)
            # Plate top — pressed lower & lit green when activated
            inset = base.inflate(-10, -14)
            if on:
                inset.y += 4
                plate_col = ON_COL
                rim_col = (40, 110, 70)
            else:
                plate_col = (78, 76, 92)
                rim_col = (28, 26, 36)
            pygame.draw.rect(s, plate_col, inset, border_radius=6)
            pygame.draw.rect(s, rim_col, inset, 2, border_radius=6)
            # Rune mark on top — lit when on
            cx, cy = TILE_SIZE // 2, TILE_SIZE // 2
            mark_col = (235, 250, 215) if on else (110, 108, 120)
            pygame.draw.circle(s, mark_col, (cx, cy), 6, 2)
            pygame.draw.line(s, mark_col, (cx - 8, cy), (cx + 8, cy), 2)
            return s

        cls._imgs = {False: make(False), True: make(True)}

    def step_on(self, dt):
        """Called by the level while the player overlaps this plate.

        Returns True the moment the plate trips (so the level can open
        the gate exactly once)."""
        if self.activated:
            return False
        self.charge += dt
        if self.charge >= PLATE_TRIGGER_DELAY:
            self.activated = True
            self.image = self._imgs[True]
            return True
        return False

    def step_off(self):
        """Reset the charge if the player walks off before tripping."""
        if not self.activated:
            self.charge = 0.0
