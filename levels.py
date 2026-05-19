import math
import random
import zlib
from collections import deque

import pygame
from settings import (
    TILE_SIZE, BOSS_TOUCH_DAMAGE, PLAYER_INVULN_TIME,
    SPIKE_DAMAGE, LEVER_REACH, DASH_COOLDOWN,
)
from units import Wizard, Boss, BOSS_ROSTER, CHARACTER_INFO, ENEMY_INFO
from static_objects import Tile, TileTextures, Prop
from interactables import Spikes, Lever, Gate, KeyItem, PressurePlate
from tiles import PROP_CHARS
import tileset
import level_catalog
import save
import audio
import theme

# Boss state -> badge colour. One named set instead of inline tuples
# scattered through draw_boss_health (FAIL = imminent hit, ACCENT =
# ranged tell, INK = neutral).
_BOSS_BADGE = {
    'windup': ("!! WINDUP !!", theme.FAIL),
    'dash':   ("DASH",         theme.FAIL),
    'aim':    ("AIMING",       theme.ACCENT),
    'shoot':  ("FIRE",         theme.ACCENT),
    'chase':  ("PURSUIT",      theme.INK),
    'recover': ("stagger",     theme.MUTED),
}

# CHARACTERS comes from the units catalogue so adding a character is a
# one-liner in units.py.
CHARACTERS = {key: cls for key, cls, _label, _tagline in CHARACTER_INFO}
# Level token char -> enemy class (parallel to CHARACTERS).
ENEMIES = {char: cls for char, cls, _label in ENEMY_INFO}

# Built-in + custom levels come from ``level_catalog`` — the single
# source of truth for "what levels exist". The full LegendMD prop /
# letter table lives in :mod:`tiles` (``REGISTRY``); ``PROP_CHARS`` is
# the back-compat view used by the load_level switch below.


def _split_cells(line):
    """A map row is either dense — one character per cell, the legacy
    format — or whitespace-separated tokens, which lets a cell carry a
    variant (``T3``). A row with any internal spaces is tokenised."""
    parts = line.split()
    if len(parts) == 1 and parts[0] == line.strip():
        return list(parts[0])      # dense single-char cells (no variants)
    return parts                   # tokenised cells


def _cell_variant(cell):
    """Trailing digits of a token are the 1-based variant; default 1."""
    digits = cell[1:]
    return int(digits) if digits.isdigit() else 1


def _pair_id(cell):
    """Explicit trigger/gate pair id from a token's trailing digits
    (``L2``→2, ``G3``→3), or ``None`` when the token has no digit — in
    which case the legacy reading-order pairing is used.

    Distinct from :func:`_cell_variant` (which defaults to 1) because
    pairing must tell a bare ``L`` from an explicit ``L1``."""
    digits = cell[1:]
    return int(digits) if digits.isdigit() else None


class Camera:
    """Scrolls the world so the player stays centred, clamped to the
    level bounds so the view never leaves the map.

    Also owns the screen-shake offset: any system that wants a punch
    of feedback (player hit, boss death, ...) calls :meth:`shake` and
    the camera adds a decaying jitter to its effective offset.

    The follow is intentionally *not* 1:1. It models the camera used by
    well-regarded top-down action games (Zelda, Hyper Light Drifter,
    Death's Door): the view leads slightly toward the direction the
    player is moving so you see what you walk into, and the whole thing
    is eased with frame-rate-independent exponential smoothing so the
    camera trails softly instead of being glued to the sprite. It
    recenters when the player stands still. No dead zone — that is a
    platformer device and reads wrong for free 2D movement.
    """

    # Exponential smoothing rate (per second). Higher = snappier,
    # lower = floatier. ~6 reads as a soft trail without feeling sluggish.
    FOLLOW_SPEED = 6.0
    # How far the camera leads ahead of the player in the movement
    # direction, as a fraction of the screen size.
    LOOKAHEAD = 0.14

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.level_w = screen_w
        self.level_h = screen_h
        self.offset = pygame.math.Vector2(0, 0)
        self.shake_offset = pygame.math.Vector2(0, 0)
        self._shake_amount = 0.0
        self._shake_time = 0.0
        self._shake_total = 0.0

    def set_level_size(self, level_w, level_h):
        self.level_w = level_w
        self.level_h = level_h

    def follow(self, target, dt=None):
        # Lead the view toward where the player is heading so they see
        # what they walk into. When idle (direction == 0) the lead is
        # zero and the camera eases back to centred.
        lead_x = lead_y = 0.0
        d = getattr(target, "direction", None)
        if d is not None and d.magnitude() != 0:
            lead_x = d.x * self.screen_w * self.LOOKAHEAD
            lead_y = d.y * self.screen_h * self.LOOKAHEAD

        # Offset that centres the target, plus the lead.
        tx = target.rect.centerx - self.screen_w // 2 + lead_x
        ty = target.rect.centery - self.screen_h // 2 + lead_y

        if dt is None:
            # Level load / teleport: snap so we never start mid-pan.
            ox, oy = tx, ty
        else:
            # Ease toward that target. 1 - e^(-k·dt) is the same curve
            # regardless of frame rate, unlike a raw lerp factor which
            # speeds up / stutters when dt varies.
            t = 1.0 - math.exp(-self.FOLLOW_SPEED * dt)
            ox = self.offset.x + (tx - self.offset.x) * t
            oy = self.offset.y + (ty - self.offset.y) * t

        max_x = max(0, self.level_w - self.screen_w)
        max_y = max(0, self.level_h - self.screen_h)
        self.offset.x = max(0, min(ox, max_x))
        self.offset.y = max(0, min(oy, max_y))

    def shake(self, amount, duration):
        """Stack a shake event. Stronger / longer events take precedence
        over weaker ones still in flight."""
        if amount > self._shake_amount or duration > self._shake_time:
            self._shake_amount = max(self._shake_amount, amount)
            self._shake_time = max(self._shake_time, duration)
            self._shake_total = max(self._shake_total, self._shake_time)

    def update_shake(self, dt):
        if self._shake_time <= 0:
            self.shake_offset.update(0, 0)
            self._shake_amount = 0.0
            self._shake_total = 0.0
            return
        self._shake_time = max(0.0, self._shake_time - dt)
        # Linear decay over the full duration so the jolt rings out
        # rather than cutting off abruptly.
        decay = (self._shake_time / self._shake_total
                 if self._shake_total > 0 else 0)
        amp = self._shake_amount * decay
        # Random direction each tick — coherent noise would be nicer
        # but for short shakes pure random looks great.
        self.shake_offset.update(
            random.uniform(-amp, amp), random.uniform(-amp, amp))

    def world_to_screen(self, rect):
        return rect.move(
            -int(self.offset.x + self.shake_offset.x),
            -int(self.offset.y + self.shake_offset.y))


class LevelManager:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.display_surface = pygame.display.get_surface()

        # Walls live here for collision only; they are *not* drawn one by
        # one — the whole static map is baked into ``map_surface`` once.
        self.obstacle_sprites = pygame.sprite.Group()
        self.entities = pygame.sprite.Group()        # player + boss
        self.player_sprites = pygame.sprite.Group()  # just the player; boss aims here
        self.enemy_sprites = pygame.sprite.Group()
        self.projectile_sprites = pygame.sprite.Group()
        self.interactable_sprites = pygame.sprite.Group()  # spikes/levers/...

        self.camera = Camera(width, height)
        self.map_surface = None
        # Identity of the loaded level. ``level_id`` is the stable
        # string id from the catalog (used by save.py); ``level_title``
        # and ``level_tagline`` come from the same entry and drive the
        # intro card. None until a level is loaded.
        self.level_id = ""
        self.level_title = ""
        self.level_tagline = ""
        self.boss_name = ""
        self.boss_asset = None
        self.boss_tint = None

        self.player = None
        self.boss = None
        self.exit_rect = None
        self.completed = False
        self.failed = False
        self.time = 0.0
        self.intro_timer = 0.0
        self._saved = False

        # Escape-room state.
        self.spikes = []
        self.levers = []
        self.plates = []
        self.gates = []
        self.triggers = []      # ordered union of levers+plates for ID assignment
        self.props = []
        self.key_item = None
        self.needs_key = False
        self.has_key = False
        # Boss is spawned lazily: only once the player steps into the
        # final hall, so it can't be whittled down through a doorway.
        self.has_boss = False
        self.boss_defeated = False
        self.boss_spawn_pos = None
        self.arena_rect = None
        self._e_was_down = False

        # Damage-edge tracking for screen shake.
        self._last_player_hp = 0
        self._last_boss_hp = None

        self.title_font = theme.font(90)
        self.big_font = theme.font(110)
        self.hint_font = theme.font(36)
        self.label_font = theme.font(28)
        self.banner_font = theme.font(34)

        self._vignette = self._build_vignette()
        self._shadow_cache = {}

    # --- setup -------------------------------------------------------

    def _build_vignette(self):
        """Screen-sized darkened-edges overlay, built once."""
        vig = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        cx, cy = self.width / 2, self.height / 2
        max_d = (cx ** 2 + cy ** 2) ** 0.5
        step = 8  # coarse blocks; cheap and the gradient still reads
        vc = theme.shade(theme.BG, -12)  # one tint below the map floor
        for y in range(0, self.height, step):
            for x in range(0, self.width, step):
                d = (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / max_d
                a = int(150 * max(0.0, d - 0.55) / 0.45)
                if a > 0:
                    vig.fill((*vc, min(160, a)),
                             (x, y, step, step))
        return vig

    def _bake_map(self, grid, cols, rows, floor_tile, wall_tile):
        """Render background + every floor/wall cell into one big
        surface. Floor/wall use the named tileset PNGs (per-level
        override, else the ``tileset`` defaults); if a name is missing
        we fall back to the old procedural stone so a bad tile name
        never blanks the level."""
        level_w, level_h = cols * TILE_SIZE, rows * TILE_SIZE
        surf = pygame.Surface((level_w, level_h)).convert()

        # Base gradient so any gap reads as deep dungeon, not a void.
        top = theme.shade(theme.BG, -2)
        bot = theme.shade(theme.BG, -10)
        for y in range(rows):
            t = y / max(1, rows - 1)
            col = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
            surf.fill(col, (0, y * TILE_SIZE, level_w, TILE_SIZE))

        wall_img = tileset.tile(wall_tile)
        floor_img = tileset.tile(floor_tile)
        wall_tex = TileTextures.get('wall')
        floor_tex = TileTextures.get('floor')
        floor_alt = TileTextures.get('floor_alt')

        for r, row in enumerate(grid):
            for c, cell in enumerate(row):
                pos = (c * TILE_SIZE, r * TILE_SIZE)
                if cell[0] == 'W':
                    surf.blit(wall_img or wall_tex, pos)
                elif floor_img is not None:
                    surf.blit(floor_img, pos)
                else:
                    surf.blit(floor_alt if (r + c) % 2 else floor_tex, pos)
        return surf

    def load_level(self, entry_or_id, char_type="c_wiz"):
        """Load a level from a :class:`level_catalog.LevelEntry` or its
        id string. Returns True on success, False if the level could
        not be loaded (unknown id, missing or empty file) — the caller
        must not switch into the game state on a False return, since
        ``self.player`` stays None and ``update`` would then crash."""
        entry = (entry_or_id if hasattr(entry_or_id, 'file')
                 else level_catalog.find(entry_or_id))
        if entry is None:
            print(f"the-way-out: unknown level {entry_or_id!r}")
            return False

        self.obstacle_sprites.empty()
        self.entities.empty()
        self.player_sprites.empty()
        self.enemy_sprites.empty()
        self.projectile_sprites.empty()
        self.interactable_sprites.empty()
        self.player = None
        self.boss = None
        self.exit_rect = None
        self.completed = False
        self.failed = False
        self.time = 0.0
        self.intro_timer = 3.0
        self.level_id = entry.id
        self.level_title = entry.title
        self.level_tagline = entry.tagline
        self._saved = False

        self.spikes = []
        self.levers = []
        self.plates = []
        self.gates = []
        self.triggers = []
        self.props = []
        self.key_item = None
        self.needs_key = False
        self.has_key = False
        self.has_boss = False
        self.boss_defeated = False
        self.boss_spawn_pos = None
        self.arena_rect = None
        self._e_was_down = False
        self._last_boss_hp = None
        # Pick the general for this level deterministically from the
        # level id. zlib.crc32 (not Python's built-in hash) so the
        # choice is stable across game restarts, not just retries —
        # PYTHONHASHSEED randomises hash() per process.
        seed = zlib.crc32(entry.id.encode("utf-8"))
        self.boss_name, self.boss_asset, self.boss_tint = \
            BOSS_ROSTER[seed % len(BOSS_ROSTER)]

        try:
            with open(entry.file, 'r') as f:
                raw = [line.rstrip('\n') for line in f if line.strip()]
        except FileNotFoundError:
            print(f"Level file {entry.file} not found!")
            return False

        # An empty or all-whitespace file would make ``cols = max(...)``
        # below raise ValueError; bail the same way as a missing file so
        # a stray empty .txt in custom_levels can't crash the game.
        if not raw:
            print(f"Level file {entry.file} is empty!")
            return False

        # Each row is a list of cell tokens: a single char in legacy
        # dense rows, or a letter (+ optional variant digits) in spaced
        # rows. Short rows pad out with wall.
        grid = [_split_cells(line) for line in raw]
        rows = len(grid)
        cols = max(len(r) for r in grid)
        for row in grid:
            row.extend('W' * (cols - len(row)))

        level_w, level_h = cols * TILE_SIZE, rows * TILE_SIZE
        self.camera.set_level_size(level_w, level_h)
        # Per-level tileset override, else the global default.
        floor_tile = entry.floor_tile or tileset.FLOOR_TILE
        wall_tile = entry.wall_tile or tileset.WALL_TILE
        self.map_surface = self._bake_map(
            grid, cols, rows, floor_tile, wall_tile)

        player_pos = (TILE_SIZE, TILE_SIZE)
        gate_cells = []
        for r, row in enumerate(grid):
            for c, cell in enumerate(row):
                x, y = c * TILE_SIZE, r * TILE_SIZE
                ch = cell[0]
                if ch == 'W':
                    # Collision only — never individually drawn.
                    Tile((x, y), [self.obstacle_sprites], 'wall')
                elif ch == 'P':
                    player_pos = (x, y)
                elif ch == 'X':
                    self.exit_rect = pygame.Rect(
                        x, y, TILE_SIZE, TILE_SIZE)
                elif ch == 'B':
                    self.boss_spawn_pos = (x, y)
                    self.has_boss = True
                elif ch == 'S':
                    self.spikes.append(
                        Spikes((x, y), [self.interactable_sprites]))
                elif ch == 'L':
                    # gate_group filled in once all triggers are known;
                    # _pair_id is the explicit digit (or None = order).
                    lever = Lever(
                        (x, y), [self.interactable_sprites], None)
                    lever._pair_id = _pair_id(cell)
                    self.levers.append(lever)
                    self.triggers.append(lever)
                elif ch == 'Y':
                    plate = PressurePlate(
                        (x, y), [self.interactable_sprites], None)
                    plate._pair_id = _pair_id(cell)
                    self.plates.append(plate)
                    self.triggers.append(plate)
                elif ch == 'G':
                    gate_cells.append((r, c, _pair_id(cell)))
                elif ch == 'K':
                    self.key_item = KeyItem(
                        (x, y), [self.interactable_sprites])
                    self.needs_key = True
                elif ch in ENEMIES:
                    # Generic enemies spawn now (the boss alone stays
                    # lazy). target wired once the player exists.
                    enemy = ENEMIES[ch](x, y, self.obstacle_sprites)
                    self.enemy_sprites.add(enemy)
                    self.entities.add(enemy)
                elif ch in PROP_CHARS:
                    category = PROP_CHARS[ch]
                    solid = tileset.is_solid(category)
                    self.props.append(Prop(
                        (x, y),
                        tileset.sprite(category, _cell_variant(cell)),
                        solid,
                        self.obstacle_sprites if solid else None))

        # Flood-fill connected 'G' cells into gate panels. Panels and
        # triggers (levers + plates, in reading order) get matching
        # group ids — the i-th trigger opens the i-th panel. Author
        # them in the order you want paired.
        self._build_gates(gate_cells)
        # Triggers with an explicit digit pair by that digit
        # (namespaced so it can never collide with the reading-order
        # fallback); the rest keep the legacy sequential pairing, so a
        # level with no digits at all behaves exactly as before.
        seq = 0
        for trig in self.triggers:
            if trig._pair_id is None:
                trig.gate_group = ('seq', seq)
                seq += 1
            else:
                trig.gate_group = ('pair', trig._pair_id)

        player_class = CHARACTERS.get(char_type, Wizard)
        self.player = player_class(
            player_pos[0], player_pos[1], self.obstacle_sprites)
        self.entities.add(self.player)
        self.player_sprites.add(self.player)
        self.player.projectile_group = self.projectile_sprites
        self.player.projectile_targets = self.enemy_sprites
        # Only generic enemies are in the group now (boss is lazy).
        for enemy in self.enemy_sprites:
            enemy.target = self.player

        self._last_player_hp = self.player.hp

        if self.has_boss:
            self.arena_rect = self._compute_arena_rect(grid)

        self.camera.follow(self.player)
        # Per-level track (manifest "music" / "default" for custom);
        # play_music degrades to silence if the file is absent.
        audio.play_music(entry.music)
        return True

    def _build_gates(self, gate_cells):
        """Group adjacent gate cells (4-connectivity) into panels. A
        panel with an explicit digit on any of its cells (``G2``) pairs
        by that digit; panels with no digit fall back to reading order,
        so a level using no digits is grouped exactly as the legacy
        code did (the key is a tuple now, but ``_open_gates_for`` only
        ever compares for equality)."""
        pid_by_cell = {(r, c): pid for r, c, pid in gate_cells}
        coords = [(r, c) for r, c, _ in gate_cells]
        remaining = set(coords)
        panels = []
        for cell in coords:              # already in r,c reading order
            if cell not in remaining:
                continue
            comp, q = [], deque([cell])
            remaining.discard(cell)
            while q:
                r, c = q.popleft()
                comp.append((r, c))
                for nr, nc in ((r + 1, c), (r - 1, c),
                               (r, c + 1), (r, c - 1)):
                    if (nr, nc) in remaining:
                        remaining.discard((nr, nc))
                        q.append((nr, nc))
            panels.append(comp)

        seq = 0
        for comp in panels:
            digits = [pid_by_cell[cell] for cell in comp
                      if pid_by_cell[cell] is not None]
            if digits:
                group = ('pair', digits[0])
            else:
                group = ('seq', seq)
                seq += 1
            for r, c in comp:
                self.gates.append(Gate(
                    (c * TILE_SIZE, r * TILE_SIZE),
                    self.interactable_sprites, self.obstacle_sprites,
                    group))

    def _compute_arena_rect(self, grid):
        """Bounding box of the room containing the boss, found by
        flood-fill from the boss tile (walls *and* shut gates block it).
        Stepping into this box is what triggers the boss to spawn."""
        bx, by = self.boss_spawn_pos
        start = (by // TILE_SIZE, bx // TILE_SIZE)
        seen = {start}
        q = deque([start])
        while q:
            r, c = q.popleft()
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if (0 <= nr < len(grid) and 0 <= nc < len(grid[nr])
                        and (nr, nc) not in seen
                        and grid[nr][nc][0] not in ('W', 'G')):
                    seen.add((nr, nc))
                    q.append((nr, nc))
        cs = [c for _, c in seen]
        rs = [r for r, _ in seen]
        return pygame.Rect(
            min(cs) * TILE_SIZE, min(rs) * TILE_SIZE,
            (max(cs) - min(cs) + 1) * TILE_SIZE,
            (max(rs) - min(rs) + 1) * TILE_SIZE)

    # --- update ------------------------------------------------------

    def update(self, dt):
        self.time += dt
        if self.intro_timer > 0:
            self.intro_timer = max(0.0, self.intro_timer - dt)

        self.camera.update_shake(dt)

        if self.completed or self.failed:
            return

        self.entities.update(dt)
        self.projectile_sprites.update(dt)
        self.interactable_sprites.update(dt)
        self.camera.follow(self.player, dt)

        # Boss only materialises once you actually enter the final hall.
        if (self.has_boss and self.boss is None and not self.boss_defeated
                and self.arena_rect is not None
                and self.player.hitbox.colliderect(self.arena_rect)):
            bx, by = self.boss_spawn_pos
            self.boss = Boss(
                bx, by, self.obstacle_sprites, target=self.player,
                projectile_group=self.projectile_sprites,
                projectile_targets=self.player_sprites,
                display_name=self.boss_name,
                asset_folder=self.boss_asset,
                identity_tint=self.boss_tint)
            self.entities.add(self.boss)
            self.enemy_sprites.add(self.boss)
            self._last_boss_hp = self.boss.hp

        self._handle_levers()
        self._handle_plates(dt)
        self._handle_hazards()
        self._handle_key()

        if (self.boss is not None and self.boss.hp > 0
                and self.player.invuln_timer <= 0
                and self.boss.hitbox.colliderect(self.player.hitbox)):
            self.player.take_damage(BOSS_TOUCH_DAMAGE)
            self.player.invuln_timer = PLAYER_INVULN_TIME

        # Generic enemies: clear the dead, then apply contact damage.
        # The boss keeps its own separate touch/death path (above and
        # below) — the two are intentionally not merged.
        for en in [e for e in self.enemy_sprites if e is not self.boss]:
            if en.hp <= 0:
                en.kill()
                continue
            if (self.player.invuln_timer <= 0
                    and en.hitbox.colliderect(self.player.hitbox)):
                self.player.take_damage(en.touch_damage)
                self.player.invuln_timer = PLAYER_INVULN_TIME

        # Damage / death feedback — compare to last frame so spikes,
        # projectiles and contact damage all shake the camera uniformly.
        if (self.player is not None
                and self.player.hp < self._last_player_hp):
            self.camera.shake(5, 0.18)
        if self.player is not None:
            self._last_player_hp = self.player.hp

        if self.boss is not None:
            if (self._last_boss_hp is not None
                    and self.boss.hp < self._last_boss_hp):
                self.camera.shake(2, 0.08)
            self._last_boss_hp = self.boss.hp

        if self.boss is not None and self.boss.hp <= 0:
            self.camera.shake(12, 0.7)
            audio.play("boss_death")
            self.boss.kill()
            self.boss = None
            self.boss_defeated = True

        if self.player is not None and self.player.hp <= 0:
            self.camera.shake(8, 0.4)
            audio.stop_music()
            audio.play("player_death")
            self.failed = True
            return

        boss_clear = (not self.has_boss) or self.boss_defeated
        have_key = (not self.needs_key) or self.has_key
        if (self.exit_rect is not None and boss_clear and have_key
                and self.player is not None
                and self.player.hitbox.colliderect(self.exit_rect)):
            self.completed = True
            if not self._saved:
                save.mark_complete(self.level_id)
                save.record_time(self.level_id, self.time)
                audio.stop_music()
                audio.play("level_complete")
                self._saved = True

    def _handle_levers(self):
        """Edge-detected 'E' near a lever pulls it and opens its gate."""
        e_down = pygame.key.get_pressed()[pygame.K_e]
        pressed = e_down and not self._e_was_down
        self._e_was_down = e_down
        if not pressed:
            return
        pc = pygame.math.Vector2(self.player.hitbox.center)
        for lever in self.levers:
            if lever.activated:
                continue
            if pc.distance_to(lever.hitbox.center) <= LEVER_REACH:
                if lever.use():
                    self._open_gates_for(lever.gate_group)
                break

    def _handle_plates(self, dt):
        """Plates fire when the player has stood on them for the
        trigger delay; until then the charge bleeds off the moment the
        player steps off, so you can't sneak by with a quick brush."""
        for plate in self.plates:
            if plate.activated:
                continue
            if plate.hitbox.colliderect(self.player.hitbox):
                if plate.step_on(dt):
                    self._open_gates_for(plate.gate_group)
            else:
                plate.step_off()

    def _open_gates_for(self, group_id):
        for gate in self.gates:
            if gate.group_id == group_id:
                gate.open()

    def _handle_hazards(self):
        # No damage during the intro card — the player can't react yet.
        if self.intro_timer > 0 or self.player.invuln_timer > 0:
            return
        for sp in self.spikes:
            if sp.deadly and sp.hitbox.colliderect(self.player.hitbox):
                self.player.take_damage(SPIKE_DAMAGE)
                self.player.invuln_timer = PLAYER_INVULN_TIME
                break

    def _handle_key(self):
        if (self.key_item is not None
                and self.player.hitbox.colliderect(self.key_item.hitbox)):
            self.has_key = True
            self.key_item.kill()
            self.key_item = None

    # --- draw --------------------------------------------------------

    def _shadow(self, w):
        if w not in self._shadow_cache:
            s = pygame.Surface((w, w // 3), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (0, 0, 0, 90), s.get_rect())
            self._shadow_cache[w] = s
        return self._shadow_cache[w]

    def _blit_world(self, screen, image, rect):
        """Blit a world-space sprite at the camera offset, skipping it
        entirely when it is off screen."""
        r = self.camera.world_to_screen(rect)
        if (r.right < 0 or r.left > self.width
                or r.bottom < 0 or r.top > self.height):
            return None
        screen.blit(image, r)
        return r

    def _draw_interactables(self, screen):
        # Tileset furniture/decoration, then floor/wall props — all
        # drawn under the entities so the player walks visually on top
        # of spikes and in front of furniture.
        for pr in self.props:
            self._blit_world(screen, pr.image, pr.rect)
        for sp in self.spikes:
            self._blit_world(screen, sp.image, sp.rect)
        for plate in self.plates:
            self._blit_world(screen, plate.image, plate.rect)
        for gate in self.gates:
            self._blit_world(screen, gate.image, gate.rect)

        pc = pygame.math.Vector2(self.player.hitbox.center) \
            if self.player is not None else None
        for lever in self.levers:
            r = self._blit_world(screen, lever.image, lever.rect)
            if (r is not None and not lever.activated and pc is not None
                    and pc.distance_to(lever.hitbox.center) <= LEVER_REACH):
                self._draw_key_prompt(screen, r.centerx, r.top - 14, "E")

        if self.key_item is not None:
            bob = int(math.sin(self.key_item.t * 3.0) * 6)
            r = self.camera.world_to_screen(self.key_item.rect)
            r.y += bob
            if not (r.right < 0 or r.left > self.width):
                pulse = 0.5 + 0.5 * abs((self.time * 1.8) % 2 - 1)
                gr = int(TILE_SIZE * (0.5 + 0.25 * pulse))
                glow = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (250, 210, 90,
                                          int(60 + 70 * pulse)),
                                   (gr, gr), gr)
                screen.blit(glow, glow.get_rect(center=r.center))
                screen.blit(self.key_item.image, r)

    def _draw_key_prompt(self, screen, cx, cy, text):
        surf = self.label_font.render(text, True, theme.INK)
        box = surf.get_rect(center=(cx, cy)).inflate(20, 12)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((*theme.BG, 210))
        pygame.draw.rect(panel, theme.LINE_C,
                         panel.get_rect(), 2, border_radius=6)
        screen.blit(panel, box)
        screen.blit(surf, surf.get_rect(center=box.center))

    def _draw_world_sprite(self, screen, sprite):
        r = self.camera.world_to_screen(sprite.rect)
        sh = self._shadow(int(sprite.hitbox.width * 1.2))
        screen.blit(sh, sh.get_rect(
            center=(r.centerx, self.camera.world_to_screen(
                sprite.hitbox).bottom - 6)))
        screen.blit(sprite.image, r)

    def draw(self, screen):
        if self.map_surface is None:
            screen.fill(theme.BG)
            return

        sox = self.camera.offset.x + self.camera.shake_offset.x
        soy = self.camera.offset.y + self.camera.shake_offset.y
        screen.blit(self.map_surface, (0, 0),
                    (int(sox), int(soy), self.width, self.height))

        self._draw_interactables(screen)
        self._draw_exit(screen)

        # Y-sort so the player walks correctly in front of / behind the
        # boss and any overlap reads right.
        for sprite in sorted(self.entities, key=lambda s: s.hitbox.bottom):
            self._draw_world_sprite(screen, sprite)

        for proj in self.projectile_sprites:
            screen.blit(proj.image, self.camera.world_to_screen(proj.rect))

        screen.blit(self._vignette, (0, 0))

        if self.player is not None and not self.completed:
            self.draw_player_health(screen)
            self.draw_dash_meter(screen)
            if self.needs_key:
                self.draw_key_status(screen)
        if self.boss is not None:
            self.draw_boss_health(screen)
        self._draw_objective(screen)
        self._draw_intro(screen)

        if self.completed:
            self.draw_end_overlay(
                screen, "You found the way out!", theme.SUCCESS)
        elif self.failed:
            self.draw_end_overlay(
                screen, "You were defeated...", theme.FAIL)

    def _draw_exit(self, screen):
        if self.exit_rect is None:
            return
        r = self.camera.world_to_screen(self.exit_rect)
        if r.right < 0 or r.left > self.width:
            return

        open_ = (((not self.has_boss) or self.boss_defeated)
                 and ((not self.needs_key) or self.has_key))
        pulse = 0.5 + 0.5 * abs((self.time * 1.6) % 2 - 1)

        frame = theme.SUCCESS if open_ else theme.FAIL
        glow_c = theme.shade(frame, +10)

        # Soft glow halo around the doorway.
        gr = int(TILE_SIZE * (0.9 + 0.4 * pulse))
        glow = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*glow_c, int(70 + 80 * pulse)),
                           (gr, gr), gr)
        screen.blit(glow, glow.get_rect(center=r.center))

        # Door panel.
        pygame.draw.rect(screen, theme.shade(theme.BG, +6),
                         r.inflate(-6, -6), border_radius=6)
        pygame.draw.rect(screen, frame, r.inflate(-6, -6), 4,
                         border_radius=6)

        if open_:
            inner = r.inflate(-22, -18)
            a = int(120 + 110 * pulse)
            s = pygame.Surface(inner.size, pygame.SRCALPHA)
            s.fill((*glow_c, a))
            screen.blit(s, inner)
        else:
            for i in range(1, 4):  # bars -> "sealed"
                bx = r.left + i * r.width // 4
                pygame.draw.line(screen, frame,
                                 (bx, r.top + 10), (bx, r.bottom - 10), 5)

    # --- HUD ---------------------------------------------------------

    def _bar(self, screen, x, y, w, h, ratio, color):
        theme.draw_bar(screen, pygame.Rect(x, y, w, h), ratio, color)

    def draw_player_health(self, screen):
        w, h = 460, 34
        x, y = 40, self.height - h - 40
        self._bar(screen, x, y, w, h,
                  self.player.hp / self.player.max_hp, theme.ACCENT)
        label = self.label_font.render(
            f"HP  {int(self.player.hp)}/{self.player.max_hp}",
            True, theme.INK)
        screen.blit(label, (x, y - 36))

    def draw_dash_meter(self, screen):
        """Small ring next to the HP showing dash readiness. Filled
        ring = ready (Shift will fire); shrinking arc = cooldown left."""
        if self.player is None:
            return
        radius = 22
        cx = 40 + 460 + 36 + radius
        cy = self.height - 40 - 34 // 2 - 6
        ready = (self.player.dash_cooldown_timer == 0
                 and self.player.dash_timer == 0)
        # Backplate
        pygame.draw.circle(screen, theme.shade(theme.BG, -10),
                           (cx, cy), radius + 4)
        pygame.draw.circle(screen, theme.LINE_C, (cx, cy), radius)
        if ready:
            pygame.draw.circle(screen, theme.ACCENT, (cx, cy), radius - 4)
        else:
            ratio = 1.0 - (self.player.dash_cooldown_timer
                           / max(0.001, DASH_COOLDOWN))
            # Draw filled wedge from -pi/2 sweeping clockwise.
            ring = pygame.Surface((radius * 2 + 4, radius * 2 + 4),
                                  pygame.SRCALPHA)
            rc = (radius + 2, radius + 2)
            # Approximate wedge with a polygon for cheap rendering.
            pts = [rc]
            steps = max(2, int(36 * ratio))
            for i in range(steps + 1):
                ang = -math.pi / 2 + (2 * math.pi) * (i / 36)
                pts.append((rc[0] + math.cos(ang) * (radius - 4),
                            rc[1] + math.sin(ang) * (radius - 4)))
            if len(pts) >= 3:
                pygame.draw.polygon(ring, theme.MUTED, pts)
            screen.blit(ring, (cx - radius - 2, cy - radius - 2))
        pygame.draw.circle(screen, theme.shade(theme.BG, -6),
                           (cx, cy), radius, 2)
        # Glyph: lightning-style chevron
        col = theme.INK if ready else theme.MUTED
        pygame.draw.polygon(screen, col, [
            (cx - 6, cy - 9), (cx + 3, cy - 2),
            (cx - 1, cy - 1), (cx + 6, cy + 9),
            (cx - 3, cy + 2), (cx + 1, cy + 1),
        ])
        cap = self.label_font.render(
            "DASH" if ready else "...", True,
            theme.INK if ready else theme.MUTED)
        screen.blit(cap, (cx + radius + 14, cy - 14))

    def draw_key_status(self, screen):
        """Small chip by the HP bar: dim when the key is still out
        there, lit gold once it's in hand."""
        x, y = 40, self.height - 34 - 40 - 64
        got = self.has_key
        col = theme.ACCENT if got else theme.MUTED
        cx = x + 18
        pygame.draw.circle(screen, col, (cx, y + 14), 11)
        pygame.draw.circle(screen, theme.BG, (cx, y + 14), 5)
        pygame.draw.rect(screen, col, (cx - 4, y + 22, 8, 22))
        pygame.draw.rect(screen, col, (cx + 4, y + 34, 9, 5))
        label = self.label_font.render(
            "KEY" if got else "KEY  ?", True,
            theme.ACCENT if got else theme.MUTED)
        screen.blit(label, (x + 44, y + 8))

    def draw_boss_health(self, screen):
        w, h = 900, 40
        x = self.width // 2 - w // 2
        y = 56
        # Two-tone fill: phase-2 portion overlays in a brighter shade,
        # so you read at a glance how close you are to the next phase.
        ratio = self.boss.hp / self.boss.max_hp
        self._bar(screen, x, y, w, h, ratio, theme.ACCENT)
        # Phase divider line at 50%
        div_x = x + w // 2
        pygame.draw.line(screen, theme.LINE_C,
                         (div_x, y - 2), (div_x, y + h + 2), 2)
        # State badge — useful during dev, fun for the player too.
        state_text, badge_col = _BOSS_BADGE.get(
            self.boss.state, ("", theme.INK))
        if state_text:
            badge = self.label_font.render(state_text, True, badge_col)
            screen.blit(badge, badge.get_rect(
                center=(self.width // 2, y + h + 24)))
        label = self.label_font.render(
            self.boss_name.upper(), True, theme.INK)
        screen.blit(label, label.get_rect(center=(self.width // 2, y - 24)))

    def _draw_objective(self, screen):
        if self.completed or self.failed:
            return
        if self.boss is not None:
            text, color = f"Defeat {self.boss_name}!", theme.FAIL
        elif self.has_boss and not self.boss_defeated:
            if any(not lv.activated for lv in self.levers):
                text, color = ("Pull the levers — the way is sealed",
                               theme.ACCENT)
            elif any(not p.activated for p in self.plates):
                text, color = ("Step on the plates — the way is sealed",
                               theme.ACCENT)
            else:
                text, color = (f"{self.boss_name} guards the final hall",
                               theme.ACCENT)
        elif any(not p.activated for p in self.plates):
            text, color = ("Step on the pressure plates",
                           theme.ACCENT)
        elif self.needs_key and not self.has_key:
            text, color = ("Find the key to the way out",
                           theme.ACCENT)
        else:
            text, color = "The way out is open — escape!", theme.SUCCESS
        surf = self.banner_font.render(text, True, color)
        rect = surf.get_rect(center=(self.width // 2, self.height - 70))
        bg = rect.inflate(40, 20)
        panel = pygame.Surface(bg.size, pygame.SRCALPHA)
        panel.fill((*theme.BG, 150))
        screen.blit(panel, bg)
        screen.blit(surf, rect)

    def _draw_intro(self, screen):
        if self.intro_timer <= 0:
            return
        title = self.level_title or "LEVEL"
        sub = self.level_tagline
        # Fade out over the last second.
        alpha = int(255 * min(1.0, self.intro_timer))
        cx, cy = self.width // 2, self.height // 2 - 60

        t = self.big_font.render(title, True, theme.TITLE_C)
        t.set_alpha(alpha)
        screen.blit(t, t.get_rect(center=(cx, cy)))
        if sub:
            s = self.hint_font.render(sub, True, theme.MUTED)
            s.set_alpha(alpha)
            screen.blit(s, s.get_rect(center=(cx, cy + 90)))

        # Quick controls reminder during the first second
        if self.intro_timer > 2.0:
            d = theme.HINT_DOT
            hint = self.hint_font.render(
                f"WASD/Arrows to move & aim  {d}  Space to shoot  {d}  "
                f"Shift to dash  {d}  E to use",
                True, theme.MUTED)
            hint.set_alpha(alpha)
            screen.blit(hint, hint.get_rect(center=(cx, cy + 160)))

    def draw_end_overlay(self, screen, text, color):
        overlay = pygame.Surface(screen.get_size())
        overlay.set_alpha(210)
        overlay.fill(theme.BG)
        screen.blit(overlay, (0, 0))

        cx = screen.get_width() // 2
        cy = screen.get_height() // 2

        # Caps title + thin centred separator — same language as the
        # menu screens' theme.draw_title, but kept in the state colour
        # (SUCCESS / FAIL) and centred rather than pinned to the top.
        title = self.title_font.render(text.upper(), True, color)
        t_rect = title.get_rect(center=(cx, cy - 60))
        screen.blit(title, t_rect)
        ly = t_rect.bottom + 16
        pygame.draw.line(screen, theme.LINE_C,
                         (cx - 170, ly), (cx + 170, ly), 2)

        d = theme.HINT_DOT
        hint = self.hint_font.render(
            f"R retry   {d}   Enter or Esc back to menu",
            True, theme.MUTED)
        screen.blit(hint, hint.get_rect(center=(cx, cy + 50)))
