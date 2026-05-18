import random

import pygame

import audio
from settings import (
    PLAYER_SCALE, PLAYER_SPEED, PLAYER_HITBOX_SIZE,
    PLAYER_MAX_HP, ATTACK_COOLDOWN,
    PROJECTILE_SPEED, PROJECTILE_DAMAGE, PROJECTILE_LIFETIME,
    PROJECTILE_RADIUS,
    BOSS_SCALE, BOSS_SPEED, BOSS_MAX_HP, BOSS_HITBOX_SIZE,
    BOSS_PHASE2_HP_RATIO, BOSS_CHASE_TIME_MIN, BOSS_CHASE_TIME_MAX,
    BOSS_WINDUP_TIME, BOSS_DASH_TIME, BOSS_DASH_SPEED_MULT,
    BOSS_RECOVER_TIME, BOSS_AIM_TIME,
    BOSS_PROJECTILE_DAMAGE, BOSS_PROJECTILE_SPEED,
    DASH_DURATION, DASH_SPEED_MULT, DASH_COOLDOWN, DASH_INVULN_BONUS,
    HIT_FLASH_TIME,
)

# Unit vector for each facing direction (used as aim fallback when no
# explicit aim is set and for the boss's targeting).
FACING_VECTORS = {
    'down': (0, 1),
    'up': (0, -1),
    'left': (-1, 0),
    'right': (1, 0),
}


class Character(pygame.sprite.Sprite):
    """Base class for all units (player and AI).

    Subclasses set ``asset_folder`` plus, optionally, the tuning class
    attributes below; all loading, animation, movement, collision and
    health behaviour is shared. The player is keyboard-driven via
    ``get_input``; enemies override it with AI.
    """

    asset_folder = None

    # Tuning — overridable per subclass.
    scale = PLAYER_SCALE
    speed = PLAYER_SPEED
    hitbox_size = PLAYER_HITBOX_SIZE
    max_hp = PLAYER_MAX_HP
    attack_damage = PROJECTILE_DAMAGE
    attack_cooldown = ATTACK_COOLDOWN

    # name -> frame count in the sprite sheet
    SPRITE_SHEETS = {
        'idle_down': ('D_Idle', 4),
        'walk_down': ('D_Walk', 6),
        'idle_up': ('U_Idle', 4),
        'walk_up': ('U_Walk', 6),
        'idle_left': ('S_Idle', 4),
        'walk_left': ('S_Walk', 6),
    }

    def __init__(self, x, y, obstacle_sprites=None):
        super().__init__()
        if self.asset_folder is None:
            raise ValueError(
                f"{type(self).__name__} must define an 'asset_folder'")

        self.facing = 'down'
        self.load_assets()

        self.status = 'idle_down'
        self.frame_index = 0
        self.animation_speed = 10

        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=(x, y))

        # Smaller collision box, centered on the sprite. Walls are
        # checked against this, not the (mostly transparent) image rect.
        self.hitbox = self.rect.inflate(
            self.hitbox_size - self.rect.width,
            self.hitbox_size - self.rect.height)

        # Sprites this unit cannot walk through. None -> no collision.
        self.obstacle_sprites = obstacle_sprites

        self.pos = pygame.math.Vector2(x, y)
        self.direction = pygame.math.Vector2()

        # Health / combat
        self.hp = self.max_hp
        self.invuln_timer = 0.0
        self.attack_timer = 0.0
        self.hit_flash_timer = 0.0
        # Boss telegraphs are driven by ``tint_color``: an (r,g,b,a) tuple
        # the base ``animate`` will additively overlay onto this frame's
        # opaque pixels (so transparent padding stays transparent).
        self.tint_color = None

        # Dash state — the player gets a Shift burst with i-frames and
        # a cooldown; enemies don't dash through this path (Boss has its
        # own state-machine dash).
        self.dash_timer = 0.0          # seconds remaining of active dash
        self.dash_cooldown_timer = 0.0  # seconds until dash can be used
        self.speed_mult = 1.0           # >1 during dash
        self._dash_dir = pygame.math.Vector2()

        # Set by the level for the player only; enemies leave these None
        # unless the level wires them up (boss phase 2 needs them too).
        self.projectile_group = None
        self.projectile_targets = None

    def load_assets(self):
        path = f"assets/units/{self.asset_folder}/"

        def import_frames(name, frame_count):
            img_path = f"{path}{name}.png"
            try:
                sheet = pygame.image.load(img_path).convert_alpha()
            except (pygame.error, FileNotFoundError):
                print(f"{img_path} not found.")
                return []  # crash safety

            frames = []
            width = sheet.get_width() // frame_count
            height = sheet.get_height()

            for i in range(frame_count):
                rect = pygame.Rect(i * width, 0, width, height)
                surf = sheet.subsurface(rect)
                scaled = pygame.transform.scale(
                    surf, (width * self.scale, height * self.scale))
                frames.append(scaled)
            return frames

        self.animations = {
            status: import_frames(name, count)
            for status, (name, count) in self.SPRITE_SHEETS.items()
        }

        # Right-facing frames are mirrored left-facing frames.
        self.animations['idle_right'] = [
            pygame.transform.flip(img, True, False)
            for img in self.animations['idle_left']
        ]
        self.animations['walk_right'] = [
            pygame.transform.flip(img, True, False)
            for img in self.animations['walk_left']
        ]

    # --- input / movement -------------------------------------------

    def get_status(self):
        if self.direction.magnitude() != 0:
            if abs(self.direction.x) > abs(self.direction.y):
                self.facing = 'right' if self.direction.x > 0 else 'left'
            else:
                self.facing = 'down' if self.direction.y > 0 else 'up'
            self.status = f'walk_{self.facing}'
        else:
            self.status = f'idle_{self.facing}'

    def get_input(self):
        # Belt-and-braces for the focus-loss hitch: while the window is
        # unfocused SDL keeps reporting the last-held keys, so treat
        # "unfocused" as "no input" even if the pause event raced us.
        if not pygame.key.get_focused():
            self.direction.update(0, 0)
            return
        keys = pygame.key.get_pressed()
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        down = keys[pygame.K_DOWN] or keys[pygame.K_s]
        up = keys[pygame.K_UP] or keys[pygame.K_w]
        self.direction.x = int(right) - int(left)
        self.direction.y = int(down) - int(up)

        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

    def move(self, dt):
        speed = self.speed * self.speed_mult

        # Move and resolve collisions one axis at a time so the unit
        # slides along walls instead of getting stuck on them.
        self.pos.x += self.direction.x * speed * dt
        self.rect.x = round(self.pos.x)
        self.hitbox.centerx = self.rect.centerx
        self.collide('horizontal')

        self.pos.y += self.direction.y * speed * dt
        self.rect.y = round(self.pos.y)
        self.hitbox.centery = self.rect.centery
        self.collide('vertical')

    def collide(self, direction):
        if self.obstacle_sprites is None:
            return

        for sprite in self.obstacle_sprites:
            if not sprite.hitbox.colliderect(self.hitbox):
                continue

            if direction == 'horizontal':
                if self.direction.x > 0:        # moving right
                    self.hitbox.right = sprite.hitbox.left
                elif self.direction.x < 0:      # moving left
                    self.hitbox.left = sprite.hitbox.right
                self.rect.centerx = self.hitbox.centerx
                self.pos.x = self.rect.x
            else:
                if self.direction.y > 0:        # moving down
                    self.hitbox.bottom = sprite.hitbox.top
                elif self.direction.y < 0:      # moving up
                    self.hitbox.top = sprite.hitbox.bottom
                self.rect.centery = self.hitbox.centery
                self.pos.y = self.rect.y

    def _toward_target(self, min_len=0):
        """Unit vector from this unit to ``self.target`` (set by the AI
        subclasses — Boss/Enemy), or zero when closer than
        ``min_len``."""
        to = (pygame.math.Vector2(self.target.hitbox.center)
              - pygame.math.Vector2(self.hitbox.center))
        if to.length() > max(1, min_len):
            return to.normalize()
        return pygame.math.Vector2(0, 0)

    # --- damage / feedback ------------------------------------------

    def take_damage(self, amount):
        """Subtract HP. Each hit always lands (no i-frames here).

        Contact-spam protection for the player lives in the level, which
        gates repeated hits with ``invuln_timer`` — projectiles, by
        contrast, should damage the boss on every shot.
        """
        if self.hp <= 0:
            return False
        self.hp = max(0, self.hp - amount)
        # White flash on hit so the damage reads instantly even on the
        # boss's huge sprite.
        self.hit_flash_timer = HIT_FLASH_TIME
        audio.play("hit")
        return True

    # --- combat -----------------------------------------------------

    def handle_attack(self, dt):
        """Player only: fire a projectile in the facing direction on
        Space or left-click.

        Aim follows the way the character is looking (the 4 facings) —
        there is deliberately no free mouse aim; the cursor doesn't
        steer shots.
        """
        if self.projectile_group is None:
            return

        self.attack_timer = max(0.0, self.attack_timer - dt)

        keys = pygame.key.get_pressed()
        mouse_left = pygame.mouse.get_pressed()[0]
        if (keys[pygame.K_SPACE] or mouse_left) and self.attack_timer <= 0:
            aim = pygame.math.Vector2(*FACING_VECTORS[self.facing])
            spawn = pygame.math.Vector2(self.hitbox.center)
            spawn += aim * (self.hitbox_size / 2 + 8)
            Projectile(
                spawn, aim,
                self.obstacle_sprites, self.projectile_targets,
                [self.projectile_group],
                damage=self.attack_damage)
            audio.play("shoot")
            self.attack_timer = self.attack_cooldown

    def handle_dash(self, dt):
        """Shift triggers a short, i-framed speed burst.

        Direction is locked at dash start (current input dir, falling
        back to facing) so a panic dash always commits somewhere
        sensible. Only the player goes through this — the Boss has its
        own dash state.
        """
        # Tick timers first. Cooldown only counts once the dash itself
        # has ended.
        if self.dash_timer > 0:
            self.dash_timer = max(0.0, self.dash_timer - dt)
            if self.dash_timer == 0:
                self.speed_mult = 1.0
                self.dash_cooldown_timer = DASH_COOLDOWN
                # A whisker of i-frames after landing helps you cross
                # contact-damage windows with frame-perfect dashes.
                self.invuln_timer = max(self.invuln_timer,
                                        DASH_INVULN_BONUS)
            else:
                # Lock direction during dash so mid-burst input can't
                # change course.
                self.direction.update(self._dash_dir)
        elif self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer = max(
                0.0, self.dash_cooldown_timer - dt)

        if self.projectile_group is None:
            return  # only the player dashes via input

        keys = pygame.key.get_pressed()
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if (shift and self.dash_timer == 0
                and self.dash_cooldown_timer == 0):
            d = self.direction if self.direction.magnitude() != 0 \
                else pygame.math.Vector2(*FACING_VECTORS[self.facing])
            self._dash_dir = d.normalize()
            self.direction.update(self._dash_dir)
            self.dash_timer = DASH_DURATION
            self.speed_mult = DASH_SPEED_MULT
            self.invuln_timer = max(self.invuln_timer, DASH_DURATION)
            audio.play("dash")

    # --- animation / tick -------------------------------------------

    def _apply_overlay(self, frame, color_rgba):
        """Additive RGB overlay that respects the sprite's alpha mask.

        ``BLEND_RGB_ADD`` adds the overlay's RGB to opaque destination
        pixels without touching the destination alpha, so a hit flash on
        a transparent-padded sprite stays a flash on the *character* and
        doesn't fill the bounding box with white.
        """
        if frame.get_flags() & pygame.SRCALPHA == 0:
            frame = frame.copy()
        else:
            frame = frame.copy()
        intensity = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
        intensity.fill(color_rgba)
        frame.blit(intensity, (0, 0),
                   special_flags=pygame.BLEND_RGB_ADD)
        return frame

    def animate(self, dt):
        current_animation = self.animations[self.status]

        if not current_animation:
            return

        self.frame_index += self.animation_speed * dt
        self.frame_index %= len(current_animation)
        frame = current_animation[int(self.frame_index)]

        # Flicker while invulnerable so hits read clearly.
        if self.invuln_timer > 0 and int(self.invuln_timer * 20) % 2 == 0:
            frame = frame.copy()
            frame.set_alpha(90)
        # Boss telegraph tint (red windup / gold aim) — applied before
        # the brighter hit flash so a hit during windup still pops.
        if self.tint_color is not None:
            frame = self._apply_overlay(frame, self.tint_color)
        if self.hit_flash_timer > 0:
            v = int(180 * (self.hit_flash_timer / HIT_FLASH_TIME))
            frame = self._apply_overlay(frame, (v, v, v, 255))
        self.image = frame

    def update(self, dt):
        if self.invuln_timer > 0:
            self.invuln_timer -= dt
        if self.hit_flash_timer > 0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)

        self.get_input()
        self.handle_dash(dt)
        self.get_status()
        self.move(dt)
        self.animate(dt)
        self.handle_attack(dt)


# --- player-character variants -----------------------------------------
# Each character is mechanically distinct (not just a skin).
# The blurbs in CHARACTER_INFO are what the menu shows; keep them in
# sync if you tune the numbers.

class Wizard(Character):
    """Balanced reference character."""
    asset_folder = "wizard"
    # defaults: HP 100, spd 600, cd 0.35, dmg 10


class Penguin(Character):
    """Tank — slower but takes more punishment and hits a bit harder."""
    asset_folder = "penguin"
    max_hp = 140
    speed = 480
    attack_damage = 12
    attack_cooldown = 0.45


class Elf(Character):
    """Archer — rapid-fire, lower damage per shot, fragile."""
    asset_folder = "elf"
    max_hp = 90
    speed = 580
    attack_damage = 7
    attack_cooldown = 0.20


class Shiggy(Character):
    """Glass cannon — biggest hit, smallest health pool."""
    asset_folder = "shiggy"
    max_hp = 70
    speed = 620
    attack_damage = 20
    attack_cooldown = 0.40


class Wolf(Character):
    """Scout — very fast, modest combat stats."""
    asset_folder = "wolf"
    max_hp = 85
    speed = 760
    attack_damage = 9
    attack_cooldown = 0.40


# Catalogue used by the character menu to display stats and by
# levels.py to instantiate the chosen class. Order = menu order.
CHARACTER_INFO = [
    ("c_wiz",  Wizard,  "Wizard",  "Balanced"),
    ("c_peng", Penguin, "Penguin", "Tank"),
    ("c_elf",  Elf,     "Elf",     "Rapid-fire"),
    ("c_shig", Shiggy,  "Shiggy",  "Glass cannon"),
    ("c_wolf", Wolf,    "Wolf",    "Speedster"),
]


# --- boss --------------------------------------------------------------

class Boss(Character):
    """AI enemy with a small state-machine fighting style.

    Phase 1 (HP above ``BOSS_PHASE2_HP_RATIO``): chase, then telegraphed
    dash attack. Phase 2 (below): also fires a 3-shot spread between
    chases. Each new state picks itself the moment the previous timer
    runs out, so the rhythm is readable and you can dodge by pattern.
    """

    asset_folder = "mrgreen"
    scale = BOSS_SCALE
    speed = BOSS_SPEED
    hitbox_size = BOSS_HITBOX_SIZE
    max_hp = BOSS_MAX_HP

    def __init__(self, x, y, obstacle_sprites=None, target=None,
                 projectile_group=None, projectile_targets=None):
        super().__init__(x, y, obstacle_sprites)
        self.target = target
        # The level wires these so phase 2 can spawn boss projectiles
        # that hurt only the player (not other enemies / the boss itself).
        self.projectile_group = projectile_group
        self.projectile_targets = projectile_targets

        self.state = 'chase'
        self.state_timer = random.uniform(
            BOSS_CHASE_TIME_MIN, BOSS_CHASE_TIME_MAX)
        self.dash_dir = pygame.math.Vector2(0, 1)

    def get_input(self):
        if self.target is None or self.target.hp <= 0 or self.hp <= 0:
            self.direction.update(0, 0)
            return

        if self.state == 'chase':
            self.direction = self._toward_target(min_len=6)
        elif self.state == 'dash':
            self.direction.update(self.dash_dir)
        else:  # windup / aim / recover / shoot — hold still
            self.direction.update(0, 0)

    def handle_attack(self, dt):
        # Boss doesn't fire via input; ranged volleys are scheduled by
        # the state machine in :meth:`update`.
        return

    def handle_dash(self, dt):
        # Boss dash is a state, not a button — skip the player path.
        return

    def _in_phase2(self):
        return self.hp <= self.max_hp * BOSS_PHASE2_HP_RATIO

    def _enter(self, state):
        self.state = state
        if state == 'chase':
            self.state_timer = random.uniform(
                BOSS_CHASE_TIME_MIN, BOSS_CHASE_TIME_MAX)
            self.speed_mult = 1.0
        elif state == 'windup':
            # Lock in the dash direction at the *start* of the windup so
            # the player has the full telegraph to read it.
            self.dash_dir = self._toward_target()
            if self.dash_dir.length() == 0:
                self.dash_dir.update(0, 1)
            self.state_timer = BOSS_WINDUP_TIME
            self.speed_mult = 0.0
        elif state == 'dash':
            self.state_timer = BOSS_DASH_TIME
            self.speed_mult = BOSS_DASH_SPEED_MULT
        elif state == 'recover':
            self.state_timer = BOSS_RECOVER_TIME
            self.speed_mult = 0.0
        elif state == 'aim':
            self.state_timer = BOSS_AIM_TIME
            self.speed_mult = 0.0
        elif state == 'shoot':
            # Shoot has zero duration: we fire on the next FSM tick and
            # immediately transition to recover.
            self.state_timer = 0.0
            self.speed_mult = 0.0

    def _fire_volley(self):
        """3-shot spread aimed at the player. Reuses :class:`Projectile`."""
        if (self.target is None or self.projectile_group is None
                or self.projectile_targets is None):
            return
        base = self._toward_target()
        if base.length() == 0:
            return
        spawn = pygame.math.Vector2(self.hitbox.center)
        for deg in (-12, 0, 12):
            v = base.rotate(deg)
            Projectile(
                spawn + v * (self.hitbox_size / 2 + 12), v,
                self.obstacle_sprites, self.projectile_targets,
                [self.projectile_group],
                damage=BOSS_PROJECTILE_DAMAGE,
                speed=BOSS_PROJECTILE_SPEED,
                color=(255, 130, 70))

    def _update_tint(self):
        """Red ramp during windup, gold ramp during aim — the colour
        cue tells the player which attack is coming."""
        if self.state == 'windup':
            ramp = 1.0 - (self.state_timer / BOSS_WINDUP_TIME)
            ramp = max(0.0, min(1.0, ramp))
            self.tint_color = (140, 30, 30, int(40 + 80 * ramp))
        elif self.state == 'aim':
            ramp = 1.0 - (self.state_timer / BOSS_AIM_TIME)
            ramp = max(0.0, min(1.0, ramp))
            self.tint_color = (140, 110, 30, int(40 + 80 * ramp))
        else:
            self.tint_color = None

    def update(self, dt):
        # Tick the FSM first so this frame's direction / speed reflect
        # the current state.
        if self.hp > 0 and self.target is not None and self.target.hp > 0:
            self.state_timer = max(0.0, self.state_timer - dt)
            if self.state_timer == 0.0:
                self._advance_state()
        self._update_tint()

        if self.invuln_timer > 0:
            self.invuln_timer -= dt
        if self.hit_flash_timer > 0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)

        self.get_input()
        self.get_status()
        prev = self.rect.topleft
        self.move(dt)

        # A dash that slammed into a wall ends early — scraping along
        # the wall for the rest of the dash feels broken.
        if self.state == 'dash' and self.rect.topleft == prev:
            self._enter('recover')

        self.animate(dt)
        # Boss has no handle_attack — see _fire_volley instead.

    def _advance_state(self):
        """Pick the next state. The boss alternates chase with one of
        its attacks; phase 2 unlocks ranged volleys."""
        if self.state == 'chase':
            # In phase 2, ~50% of the attacks are ranged volleys.
            if self._in_phase2() and random.random() < 0.5:
                self._enter('aim')
            else:
                self._enter('windup')
        elif self.state == 'windup':
            self._enter('dash')
        elif self.state == 'dash':
            self._enter('recover')
        elif self.state == 'recover':
            self._enter('chase')
        elif self.state == 'aim':
            self._enter('shoot')
        elif self.state == 'shoot':
            self._fire_volley()
            self._enter('recover')


# --- enemies -----------------------------------------------------------
# Generic placeable threats (a token char in the level text), as
# opposed to the single scripted Boss. Adding one is a class + a line
# in ENEMY_INFO + a sprite folder; tiles.REGISTRY and the editor
# palette pick it up from ENEMY_INFO automatically.

class Enemy(Character):
    """Plain chaser: walks straight at the player and relies on contact
    damage (applied by the level, like the boss touch).

    No FSM, no ranged attack, no dash — unlike :class:`Boss` it can be
    dropped anywhere and spawns immediately rather than lazily, and it
    does **not** gate the exit (only the boss/key do)."""

    scale = 6
    speed = 300
    max_hp = 45
    hitbox_size = 70
    touch_damage = 12

    def __init__(self, x, y, obstacle_sprites=None, target=None):
        super().__init__(x, y, obstacle_sprites)
        self.target = target

    def get_input(self):
        if self.target is None or self.target.hp <= 0 or self.hp <= 0:
            self.direction.update(0, 0)
            return
        self.direction = self._toward_target(min_len=4)

    def handle_attack(self, dt):
        return  # contact-only

    def handle_dash(self, dt):
        return  # no dash


class Orange(Enemy):
    """The orange blob — the basic roaming enemy."""
    asset_folder = "orange"


# Catalogue parallel to CHARACTER_INFO: (level token char, class,
# label). One line here + a sprite folder = a new placeable enemy.
ENEMY_INFO = [
    ("N", Orange, "Chaser"),
]


# --- projectile --------------------------------------------------------

class Projectile(pygame.sprite.Sprite):
    """A simple orb that flies straight, hurts its targets and dies on walls.

    The colour and speed can be customised so the boss's volley reads
    visually different from the player's shots.
    """

    def __init__(self, pos, direction, obstacle_sprites, targets, groups,
                 damage=PROJECTILE_DAMAGE, color=(120, 230, 255),
                 speed=PROJECTILE_SPEED):
        super().__init__(groups)
        self.obstacle_sprites = obstacle_sprites
        self.targets = targets
        self.damage = damage
        self.speed = speed

        r = PROJECTILE_RADIUS
        size = (r + 4) * 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        # Soft outer halo.
        for i in range(3):
            pygame.draw.circle(
                self.image, (*color, 70 - i * 20),
                (size // 2, size // 2), r + 3 - i)
        pygame.draw.circle(self.image, color,
                           (size // 2, size // 2), r)
        pygame.draw.circle(self.image, (255, 255, 255),
                           (size // 2, size // 2), r // 2)
        self.rect = self.image.get_rect(center=(int(pos.x), int(pos.y)))
        # Smaller hitbox than the visual halo so glancing shots feel fair.
        self.hitbox = self.rect.inflate(-8, -8)

        self.pos = pygame.math.Vector2(pos)
        self.direction = pygame.math.Vector2(direction)
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()
        self.life = PROJECTILE_LIFETIME

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return

        # Substep so a fast shot can't tunnel a thin wall or a small
        # target in one tick: the per-tick move at 950 px/s under the
        # dt cap can exceed two projectile hitboxes.
        distance = self.speed * dt
        max_step = max(1.0, min(self.hitbox.width, self.hitbox.height) * 0.5)
        steps = 1 if distance <= max_step else int(distance / max_step) + 1
        step_vec = self.direction * (distance / steps)

        for _ in range(steps):
            self.pos += step_vec
            self.rect.center = (round(self.pos.x), round(self.pos.y))
            self.hitbox.center = self.rect.center

            # Targets first: a shot at an enemy pressed flush against a
            # wall is still credited before the wall kills the orb.
            if self.targets is not None:
                for target in self.targets:
                    if target.hitbox.colliderect(self.hitbox):
                        # Honour i-frames so a single tick of overlap
                        # from a spread shot can't burn the player's
                        # whole bar.
                        if getattr(target, 'invuln_timer', 0) > 0:
                            continue
                        target.take_damage(self.damage)
                        self.kill()
                        return

            if self.obstacle_sprites is not None:
                for wall in self.obstacle_sprites:
                    if wall.hitbox.colliderect(self.hitbox):
                        self.kill()
                        return
