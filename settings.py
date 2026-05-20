from pathlib import Path

# Screen — the game boots fullscreen at the monitor's native size
# (queried via pygame in main.py). These are only the fallback used
# if that query fails; there is deliberately no resolution option.
WIDTH = 2560
HEIGHT = 1600
FPS = 60

# Colors
BLACK = (0, 0, 0)

# Player (base / Wizard) — individual characters override these in
# ``units.py`` to give Penguin/Elf/Shiggy/Wolf distinct feels.
PLAYER_SPEED = 600              # Pixel pro Sekunde
PLAYER_SCALE = 5

FONT = "assets/gui/font/main_font.otf"

TILE_SIZE = 64

# Collision box of the player, in pixels. Much smaller than the scaled
# sprite (which is mostly transparent padding) so movement through
# corridors feels right. Centered on the sprite.
PLAYER_HITBOX_SIZE = 56

# --- Combat ---
PLAYER_MAX_HP = 100
PLAYER_INVULN_TIME = 0.9        # seconds of i-frames after taking a hit
ATTACK_COOLDOWN = 0.35          # seconds between shots
PROJECTILE_DAMAGE = 10          # base damage; characters can override

PROJECTILE_SPEED = 950          # pixels per second
PROJECTILE_LIFETIME = 1.6       # seconds before it fizzles out
PROJECTILE_RADIUS = 12

# --- Dash ---
# Short burst on Shift: the player keeps full control of the direction
# but moves at ``PLAYER_SPEED * DASH_SPEED_MULT`` for ``DASH_DURATION``
# seconds, with i-frames the whole time. The cooldown starts at dash
# *end*, so spamming Shift doesn't shortcut it.
DASH_DURATION = 0.18
DASH_SPEED_MULT = 3.2
DASH_COOLDOWN = 1.2
DASH_INVULN_BONUS = 0.05        # extra i-frames after the dash itself ends

# --- Abilities ---
# Wizard's Slow ability scales the per-frame dt of every enemy, the
# boss and enemy projectiles by this factor while it is active; the
# Wizard himself and his own shots keep the raw dt. See levels.py.
SLOW_SCALE = 0.35

# Boss (Mr. Green) — slower than the player so it can be kited.
BOSS_SCALE = 9
BOSS_SPEED = 250
BOSS_MAX_HP = 220               # phase 2 keeps it onscreen longer
BOSS_HITBOX_SIZE = 150
BOSS_TOUCH_DAMAGE = 18

# Boss attack pattern (state machine in ``units.Boss``):
#   chase  -> windup -> dash    -> recover -> chase
#   chase  -> aim    -> shoot   -> recover -> chase   (phase 2 only)
# Phase 2 starts when boss HP drops below ``BOSS_PHASE2_HP_RATIO``.
BOSS_PHASE2_HP_RATIO = 0.5
BOSS_CHASE_TIME_MIN = 1.6
BOSS_CHASE_TIME_MAX = 2.6
BOSS_WINDUP_TIME = 0.55
BOSS_DASH_TIME = 0.45
BOSS_DASH_SPEED_MULT = 3.4
BOSS_RECOVER_TIME = 0.55
BOSS_AIM_TIME = 0.6
BOSS_SHOTS_PER_VOLLEY = 3       # phase 2: spread shot
BOSS_PROJECTILE_DAMAGE = 14
BOSS_PROJECTILE_SPEED = 720

# Hit feedback shared by every unit.
HIT_FLASH_TIME = 0.12

# --- Hazards / Puzzles ---
# Spike traps run on one shared clock so the rhythm is readable:
#   safe -> warning (telegraph) -> deadly -> safe ...
SPIKE_CYCLE = 3.0          # full period, seconds
SPIKE_DANGER_TIME = 1.1    # seconds fully extended (deadly)
SPIKE_WARN_TIME = 0.5      # telegraph before extending (still safe)
SPIKE_DAMAGE = 16

LEVER_REACH = 95           # px: how close the player must be to pull a lever

# Pressure plates auto-activate when the player's hitbox overlaps them.
# Once triggered they stay on (just like levers) and open the matching
# gate panel by reading order.
PLATE_TRIGGER_DELAY = 0.25  # player must stand on it for this long

# --- Persistence ---
# Completed level indices are stored as a JSON list under the user's
# home directory so the save survives a fresh clone.
SAVE_DIR = Path.home() / ".the-way-out"
SAVE_FILE = SAVE_DIR / "save.json"
