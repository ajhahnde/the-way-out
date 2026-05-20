"""Inter-level loading screen.

Sits between the level menu and gameplay so the player gets one focused
beat — title, tagline, character avatar, control hints — before the
room becomes interactive. Replaces the older in-level intro card that
used to draw over a live world.

Press-or-timeout: auto-advances after ``LOADING_SCREEN_DURATION`` or on
Enter / Space / left-click / Esc. ``main.py`` gates this screen inside
``_start_level``; R-retry and pause-restart bypass it deliberately so
death-heavy levels stay snappy.
"""

import pygame

import theme
from settings import LOADING_SCREEN_DURATION
from units import CHARACTER_INFO


def _asset_folder_for(character_id):
    """Map the menu's character id (e.g. ``"c_wiz"``) to its sprite-
    sheet folder name. Falls back to the Wizard's folder so a missing
    id renders something instead of crashing."""
    for cid, cls, _name, _tagline in CHARACTER_INFO:
        if cid == character_id:
            return cls.asset_folder
    return "wizard"


class LoadingScreen:
    """One-shot scene shown before a level loads."""

    AVATAR_SCALE = 3

    def __init__(self, width, height, level_entry, character_id):
        self.width = width
        self.height = height
        self.level_entry = level_entry
        self.timer = LOADING_SCREEN_DURATION
        self.skipped = False

        self._dust = theme.PixelDust(width, height, seed=41)
        self._title_font = theme.font(theme.FONT_TITLE)
        self._tagline_font = theme.font(theme.FONT_HEADING)
        self._hint_font = theme.font(theme.FONT_CAPTION)

        folder = _asset_folder_for(character_id)
        self._avatar_frames = theme._load_idle_frames(
            folder, self.AVATAR_SCALE)
        self._ticks_at_start = pygame.time.get_ticks()

    @property
    def done(self):
        return self.skipped or self.timer <= 0

    def update(self, dt):
        if self.timer > 0:
            self.timer = max(0.0, self.timer - dt)

    def handle_input(self, event):
        """Return True when the player skipped the screen. Esc is left
        alone so main.py's global Esc handler can route it (cancel back
        to the level menu, rather than advancing into the level)."""
        if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN, pygame.K_SPACE):
            self.skipped = True
            return True
        if (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1):
            self.skipped = True
            return True
        return False

    def draw(self, screen):
        screen.fill(theme.BG)
        self._dust.draw(screen)

        cx = self.width // 2
        title_y = self.height // 3 - 30
        title = (self.level_entry.title or "LEVEL").upper()
        t_surf = self._title_font.render(title, True, theme.TITLE_C)
        screen.blit(t_surf, t_surf.get_rect(center=(cx, title_y)))

        ly = t_surf.get_rect(center=(cx, title_y)).bottom + 16
        pygame.draw.line(screen, theme.LINE_C,
                         (cx - 170, ly), (cx + 170, ly), 2)

        tagline = self.level_entry.tagline or ""
        if tagline:
            s_surf = self._tagline_font.render(tagline, True, theme.MUTED)
            screen.blit(s_surf, s_surf.get_rect(center=(cx, ly + 50)))

        # Avatar: pick one idle frame; cycle slowly so it reads as alive
        # without distracting from the title.
        if self._avatar_frames:
            ticks = pygame.time.get_ticks() - self._ticks_at_start
            idx = (ticks // 200) % len(self._avatar_frames)
            frame = self._avatar_frames[idx]
            screen.blit(frame, frame.get_rect(
                center=(cx, self.height // 2 + 90)))

        d = theme.HINT_DOT
        hint = (f"WASD/Arrows move  {d}  Space shoot  {d}  "
                f"Shift ability  {d}  E use")
        h_surf = self._hint_font.render(hint, True, theme.MUTED)
        screen.blit(h_surf, h_surf.get_rect(
            center=(cx, self.height - 70)))

        skip_hint = self._hint_font.render(
            "Enter / Space / click to skip", True, theme.MUTED)
        screen.blit(skip_hint, skip_hint.get_rect(
            center=(cx, self.height - 36)))
