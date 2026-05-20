import pygame
from units import CHARACTER_INFO
import level_catalog
import save
import audio
import theme
from version import VERSION
# Palette, font cache and the shared title / back-hint / hover
# primitives. Bound to module-private aliases to match the internal
# naming used by the screens below.
from theme import (
    BG, INK, MUTED, ACCENT, TITLE_C, DONE_C, SEL_C, LINE_C,
    measure,
    draw_title as _draw_title,
    draw_back_hint as _draw_back_hint,
    hover_marker as _hover_marker)


class MainMenu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = theme.font(46)
        self.title_font = theme.font(78)
        self.small_font = theme.font(24)
        # Set by main.py's update flow; drawn as a toast under the
        # title. status_until is the wall-clock time (seconds, from
        # pygame.time.get_ticks) at which main.py should clear the
        # status — animated phases (the dots) set it to None to opt out
        # of the auto-dismiss, results set it to ~4 s out.
        self.status = ""
        self.status_until = None

        self.buttons = [
            {"text": "Levels", "rect": None, "action": "lvls"},
            {"text": "Editor", "rect": None, "action": "editor"},
            {"text": "Characters", "rect": None, "action": "chars"},
            {"text": "Settings", "rect": None, "action": "settings"},
            {"text": "Update", "rect": None, "action": "update"},
            {"text": "Quit", "rect": None, "action": "quit"}
        ]

        center_x = width // 2
        start_y = height // 2 - 100

        for i, btn in enumerate(self.buttons):
            rect = measure(self.font, btn["text"])
            rect.center = (center_x, start_y + i * 90)
            btn["rect"] = rect

        self.title_center_y = height // 2 - 210
        # Toast sits between title-bottom and first-button-top so it
        # cannot collide with QUIT or the tip line at any resolution.
        title_bottom = (self.title_center_y
                        + self.title_font.get_height() // 2)
        first_btn_top = self.buttons[0]["rect"].top
        self._toast_y = (title_bottom + first_btn_top) // 2

        # Ambient background: scrolling floor + wandering sprites +
        # vignette. Replaces the prior PixelDust on the title screen.
        self.scene = theme.MenuScene(width, height, seed=7)

        # Playable avatar overlay (AC-style loading screen). The
        # wandering MenuScene actors stay non-interactive — they have no
        # hitbox and aren't in any group, so the player walks through
        # them and shots can't hit them. Bounds are enforced by a
        # screen-rect clamp in update(); walls/targets are empty groups.
        self._character_classes = {
            key: cls for key, cls, _label, _tag in CHARACTER_INFO}
        self.world_obstacles = pygame.sprite.Group()
        self.projectile_targets = pygame.sprite.Group()
        self.projectile_group = pygame.sprite.Group()
        self.player = None
        self._spawn_player("c_wiz")

    def _spawn_player(self, key):
        cls = self._character_classes.get(key)
        if cls is None:
            return
        # Bottom-center, well clear of the title and buttons. The clamp
        # in update() keeps the player on screen no matter the spawn.
        spawn_x = self.width // 2
        spawn_y = self.height - 220
        self.player = cls(spawn_x, spawn_y, self.world_obstacles)
        # Center the sprite on the requested spawn point.
        self.player.rect.center = (spawn_x, spawn_y)
        self.player.pos.update(self.player.rect.topleft)
        self.player.hitbox.center = self.player.rect.center
        self.player.projectile_group = self.projectile_group
        self.player.projectile_targets = self.projectile_targets
        # Left mouse must stay reserved for clicking menu buttons.
        self.player.attack_mouse_enabled = False
        self.current_character_key = key

    def set_character(self, key):
        """Rebuild the menu avatar when CharacterMenu picks a new one."""
        if key == getattr(self, "current_character_key", None):
            return
        for shot in list(self.projectile_group):
            shot.kill()
        self._spawn_player(key)

    def update(self, dt):
        if self.player is None:
            return
        self.player.update(dt)
        self.projectile_group.update(dt)

        # Clamp the player to the screen rect. The level's wall-collide
        # path is unavailable here (no walls), so cap pos/rect/hitbox
        # together to keep the sprite, draw rect and shot-spawn point in
        # sync.
        rect = self.player.rect
        max_x = self.width - rect.width
        max_y = self.height - rect.height
        if self.player.pos.x < 0:
            self.player.pos.x = 0
        elif self.player.pos.x > max_x:
            self.player.pos.x = max_x
        if self.player.pos.y < 0:
            self.player.pos.y = 0
        elif self.player.pos.y > max_y:
            self.player.pos.y = max_y
        rect.topleft = (round(self.player.pos.x), round(self.player.pos.y))
        self.player.hitbox.center = rect.center

        # Prune shots that left the screen; Projectile.update would
        # eventually drop them via PROJECTILE_LIFETIME, but clearing
        # off-screen orbs early keeps the group tight.
        screen_rect = pygame.Rect(0, 0, self.width, self.height)
        for shot in list(self.projectile_group):
            if not screen_rect.colliderect(shot.rect):
                shot.kill()

    def set_status(self, text, ttl=4.0):
        """Set the toast text. ``ttl`` is seconds until main.py clears
        it; pass ``None`` for a status that should persist (animated
        phases overwrite themselves every frame instead)."""
        self.status = text
        if ttl is None:
            self.status_until = None
        else:
            self.status_until = pygame.time.get_ticks() / 1000.0 + ttl

    def clear_status(self):
        self.status = ""
        self.status_until = None

    def draw(self, screen):
        # No screen.fill(BG): MenuScene.draw immediately overdraws the
        # whole screen with 4 opaque slab blits, so the fill is dead
        # work (submenus keep theirs — PixelDust is sparse, does not
        # cover the screen).
        self.scene.draw(screen)

        # AC-style loading-screen overlay: shots under the player, both
        # above the scene and below the title/buttons so the UI stays
        # readable and clickable.
        self.projectile_group.draw(screen)
        if self.player is not None:
            screen.blit(self.player.image, self.player.rect)

        mouse_pos = pygame.mouse.get_pos()

        title = theme.text_surface(self.title_font, "THE WAY OUT", TITLE_C)
        screen.blit(title, title.get_rect(
            center=(self.width // 2, self.title_center_y)))

        if self.status:
            theme.draw_toast(
                screen, self.status, self.small_font,
                center_x=self.width // 2, center_y=self._toast_y)

        for btn in self.buttons:
            is_hovered = btn["rect"].collidepoint(mouse_pos)
            # Thin separator above the last item (Quit) to set it apart.
            if btn["action"] == "quit":
                ly = btn["rect"].top - 22
                pygame.draw.line(screen, LINE_C,
                                 (self.width // 2 - 90, ly),
                                 (self.width // 2 + 90, ly), 2)
            color = ACCENT if is_hovered else INK
            text_surf = theme.text_surface(self.font, btn["text"], color)
            screen.blit(text_surf, btn["rect"])
            if is_hovered:
                _hover_marker(screen, btn["rect"])

        d = theme.HINT_DOT
        tip = theme.text_surface(
            self.small_font,
            f"WASD/Arrows move + aim   {d}   Space shoot   {d}   "
            f"Shift ability   {d}   E use",
            MUTED)
        screen.blit(tip, tip.get_rect(
            center=(self.width // 2, self.height - 58)))

        if VERSION:
            ver = theme.text_surface(self.small_font, VERSION, MUTED)
            screen.blit(ver, ver.get_rect(
                bottomleft=(16, self.height - 12)))

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                if btn["rect"].collidepoint(mouse_pos):
                    audio.play("menu_confirm")
                    return btn["action"]
        return None


class SettingsMenu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = theme.font(46)
        self.title_font = theme.font(56)
        self.small_font = theme.font(24)
        # Persisted preference; main.py applies it to the audio module
        # at startup so it holds before Settings is ever opened.
        _prefs = save.load_settings()
        self.sound_on = _prefs.get("sound", True)
        # Five-step bed level (0 / 25 / 50 / 75 / 100 %) — coarse on
        # purpose so a click cycles through them clearly. Volume is
        # independent of the sound toggle: muting kills audio outright,
        # the slider sets the music level when audio is on.
        raw_vol = _prefs.get("music_vol", 1.0)
        self.music_vol = max(0.0, min(1.0,
            float(raw_vol) if isinstance(raw_vol, (int, float)) else 1.0))
        # Fullscreen vs. bordered window only — no resolution picker.
        # The game always boots fullscreen at the monitor's own size
        # (main.py); this toggle is session-only, never persisted.
        self.toggle_screen = True

        # Same idle motion as the title screen but quieter — a
        # different seed gives each submenu its own pattern.
        self.dust = theme.PixelDust(width, height, seed=11, count=35)

        self.update_buttons()

    def update_buttons(self):
        sound_text = f"Sound: {'ON' if self.sound_on else 'OFF'}"
        music_text = f"Music: {int(round(self.music_vol * 100))}/100"
        screen_text = (
            f"Screen: {'FULLSCREEN' if self.toggle_screen else 'BORDERED'}")

        self.buttons = [
            {"text": sound_text, "rect": None, "action": "toggle_sound"},
            {"text": music_text, "rect": None, "action": "cycle_music"},
            {"text": screen_text, "rect": None, "action": "toggle_fs_w"},
        ]

        center_x = self.width // 2
        start_y = self.height // 2 - 100

        for i, btn in enumerate(self.buttons):
            rect = measure(self.font, btn["text"])
            rect.center = (center_x, start_y + i * 100)
            btn["rect"] = rect

    def draw(self, screen):
        screen.fill(BG)
        self.dust.draw(screen)
        _draw_title(screen, self.title_font, "Settings", self.width)
        _draw_back_hint(screen, self.small_font)

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            is_hovered = btn["rect"].collidepoint(mouse_pos)
            color = ACCENT if is_hovered else INK
            screen.blit(theme.text_surface(
                self.font, btn["text"], color), btn["rect"])
            if is_hovered:
                _hover_marker(screen, btn["rect"])

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                if btn["rect"].collidepoint(mouse_pos):
                    if btn["action"] == "toggle_sound":
                        self.sound_on = not self.sound_on
                        audio.set_enabled(self.sound_on)
                        save.set_setting("sound", self.sound_on)
                        self.update_buttons()

                    elif btn["action"] == "cycle_music":
                        # Cycle 0 → 25 → 50 → 75 → 100 → 0. Snap any
                        # off-step saved value to the next step up.
                        steps = (0.0, 0.25, 0.5, 0.75, 1.0)
                        cur = round(self.music_vol * 4) / 4
                        idx = (steps.index(cur) + 1) % len(steps) \
                            if cur in steps else 0
                        self.music_vol = steps[idx]
                        audio.set_music_volume(self.music_vol)
                        save.set_setting("music_vol", self.music_vol)
                        self.update_buttons()

                    elif btn["action"] == "toggle_fs_w":
                        self.toggle_screen = not self.toggle_screen
                        pygame.display.toggle_fullscreen()
                        self.update_buttons()

                    audio.play("menu_confirm")
                    return btn["action"]
        return None


class LevelMenu:
    """Level select with completion checkmarks read from ``save.py``.

    Entries are rebuilt from ``level_catalog`` on every ``refresh()`` so:
      * freshly-beaten levels light up the next time you back to the menu
      * a custom level the player just saved in the editor appears
        without restarting the game

    Built-in levels are listed first (manifest order); user-built levels
    follow, visually marked as ``Custom``.
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = theme.font(46)
        self.title_font = theme.font(56)
        self.small_font = theme.font(24)
        self.tag_font = theme.font(22)
        self.best_font = theme.font(20)

        self.times = {}
        self.entries = []
        # Idle motion, kept thinner than the title because this screen
        # is text-dense (rows of titles, taglines and best times).
        self.dust = theme.PixelDust(width, height, seed=13, count=25)
        self.refresh()

    def _layout(self):
        """Stack entries vertically, auto-shrinking spacing when the
        catalog grows so custom levels still fit on screen."""
        if not self.entries:
            return
        count = len(self.entries)
        # 130 px per row up to 5 entries, then tighten so 10 still fit.
        gap = max(60, min(130, (self.height - 240) // max(count, 1)))
        center_x = self.width // 2
        start_y = self.height // 2 - (count - 1) * gap // 2
        for i, btn in enumerate(self.entries):
            rect = measure(self.font, btn["text"])
            rect.center = (center_x, start_y + i * gap)
            btn["rect"] = rect

    def refresh(self):
        """Rebuild entries from the catalog + reread completed ids and
        best times."""
        self.completed = save.load_completed()
        self.times = save.load_times()
        self.entries = []
        for entry in level_catalog.load_catalog():
            self.entries.append({
                "text": entry.title,
                "action": entry.id,
                "tagline": entry.tagline,
                "custom": entry.custom,
                "rect": None,
            })
        self._layout()

    def draw(self, screen):
        screen.fill(BG)
        self.dust.draw(screen)
        _draw_title(screen, self.title_font, "Levels", self.width)
        _draw_back_hint(screen, self.small_font)

        if not self.entries:
            empty = theme.text_surface(
                self.small_font,
                "No levels found — check assets/levels/manifest.json",
                MUTED)
            screen.blit(empty, empty.get_rect(
                center=(self.width // 2, self.height // 2)))
            return

        mouse_pos = pygame.mouse.get_pos()

        for btn in self.entries:
            is_hovered = btn["rect"].collidepoint(mouse_pos)
            is_done = btn["action"] in self.completed
            if is_hovered:
                color = ACCENT
            elif is_done:
                color = DONE_C
            else:
                color = INK
            text_surf = theme.text_surface(self.font, btn["text"], color)
            screen.blit(text_surf, btn["rect"])
            if is_hovered:
                _hover_marker(screen, btn["rect"])

            tag = btn["tagline"]
            if btn["custom"]:
                # No pill — a quiet prefix keeps the row flat.
                tag = f"custom | {tag}"
            tag_surf = theme.text_surface(
                self.tag_font, tag,
                MUTED if not is_done else theme.shade(DONE_C, -30))
            screen.blit(tag_surf, tag_surf.get_rect(
                center=(btn["rect"].centerx, btn["rect"].bottom + 16)))

            best = self.times.get(btn["action"])
            if best is not None:
                m, s = divmod(int(best), 60)
                # INK, not ACCENT: a persistent 20px label in the gold
                # accent is too low-contrast to read (same reason the
                # update status line uses INK).
                bt = theme.text_surface(
                    self.best_font, f"best  {m}:{s:02d}", INK)
                screen.blit(bt, bt.get_rect(
                    center=(btn["rect"].centerx, btn["rect"].bottom + 42)))

            if is_done:
                # Minimal check: a thin tick, no filled circle.
                tx = btn["rect"].left - 60
                ty = btn["rect"].centery
                pygame.draw.lines(screen, DONE_C, False, [
                    (tx - 9, ty),
                    (tx - 2, ty + 8),
                    (tx + 11, ty - 8)], 3)

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.entries:
                if btn["rect"] and btn["rect"].collidepoint(mouse_pos):
                    audio.play("menu_confirm")
                    return btn["action"]
        return None


class CharacterMenu:
    """Character select with the stat block of the currently-hovered
    (or, if none, currently-selected) character shown alongside."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.title_font = theme.font(56)
        self.card_font = theme.font(44)
        self.name_font = theme.font(46)
        self.small_font = theme.font(24)
        self.stat_font = theme.font(24)
        self.tagline_font = theme.font(22)

        # Build entries from the units catalogue.
        self.character = []
        for key, cls, label, tagline in CHARACTER_INFO:
            self.character.append({
                "text": label,
                "action": key,
                "tagline": tagline,
                "cls": cls,
                "rect": None,
            })

        # Left-align every name on a single vertical line so the column
        # doesn't zigzag with each name's width.
        self.name_x = width // 2 - 320
        start_y = height // 2 - 200

        for i, btn in enumerate(self.character):
            rect = measure(self.name_font, btn["text"])
            rect.midleft = (self.name_x, start_y + i * 100)
            btn["rect"] = rect

        # Two scaled idle-frame lists per character:
        #  * ``previews``: 220 px hero, used by the focused row only.
        #  * ``thumbs``:    64 px badge, drawn next to every row so the
        #                   whole list animates instead of standing
        #                   still everywhere except the focus.
        self.previews = {}
        self.thumbs = {}
        for key, cls, label, tagline in CHARACTER_INFO:
            self.previews[key] = self._load_idle_frames(cls, 220)
            self.thumbs[key] = self._load_idle_frames(cls, 72)

        # Idle motion — quieter than the title screen so it doesn't
        # compete with the stat block on the right.
        self.dust = theme.PixelDust(width, height, seed=17, count=30)

    def _load_idle_frames(self, cls, target_h):
        """Every idle frame, scaled to ``target_h`` px tall.

        Used twice per character: once for the focused-row hero
        preview, once for the per-row thumbnail so every figure in the
        list loops its idle instead of sitting on a static name.
        Returns ``None`` if the sheet is missing — callers skip the
        blit, and the row just shows the name."""
        try:
            sheet = pygame.image.load(
                f"assets/units/{cls.asset_folder}/D_Idle.png").convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None
        _, count = cls.SPRITE_SHEETS['idle_down']
        fw = sheet.get_width() // count
        fh = sheet.get_height()
        scale = target_h / fh
        size = (int(fw * scale), int(fh * scale))
        return [
            pygame.transform.scale(
                sheet.subsurface(pygame.Rect(i * fw, 0, fw, fh)), size)
            for i in range(count)
        ]

    def draw(self, screen, current_selected):
        screen.fill(BG)
        self.dust.draw(screen)
        _draw_title(screen, self.title_font, "Select Character", self.width)
        _draw_back_hint(screen, self.small_font)

        mouse_pos = pygame.mouse.get_pos()

        # Choose which character's stats to show: hovered first,
        # otherwise the current selection.
        focus = None
        for btn in self.character:
            if btn["rect"].collidepoint(mouse_pos):
                focus = btn
                break
        if focus is None:
            for btn in self.character:
                if btn["action"] == current_selected:
                    focus = btn
                    break

        ticks = pygame.time.get_ticks()
        for i, btn in enumerate(self.character):
            is_hovered = btn["rect"].collidepoint(mouse_pos)

            if btn["action"] == current_selected:
                color = SEL_C
            elif is_hovered:
                color = ACCENT
            else:
                color = INK

            text_surf = theme.text_surface(self.name_font, btn["text"], color)
            screen.blit(text_surf, btn["rect"])
            if is_hovered:
                _hover_marker(screen, btn["rect"])
            tag = theme.text_surface(
                self.tagline_font, btn["tagline"], MUTED)
            screen.blit(tag, tag.get_rect(
                topleft=(btn["rect"].left, btn["rect"].bottom + 4)))

            # Per-row idle thumbnail — every character animates. Skip
            # the focused row: it gets the bigger hero sprite drawn
            # below, and a duplicate thumb beside the name would compete
            # with the stat-card column.
            is_focus = focus is not None and btn["action"] == focus["action"]
            if not is_focus:
                thumbs = self.thumbs.get(btn["action"])
                if thumbs:
                    # Stagger frame index per row so they don't blink in
                    # sync. ~7 fps idle loop.
                    idx = (ticks // 140 + i * 2) % len(thumbs)
                    frame = thumbs[idx]
                    screen.blit(frame, frame.get_rect(
                        center=(self.name_x - 60, btn["rect"].centery)))

        if focus is not None:
            frames = self.previews.get(focus["action"])
            if frames:
                # ~7 fps idle loop, timed off the wall clock so this
                # screen doesn't need a dt plumbed in just for the sprite.
                frame = frames[(ticks // 140) % len(frames)]
                pcx = self.name_x - 170
                pcy = self.height // 2
                screen.blit(frame, frame.get_rect(center=(pcx, pcy)))
            self._draw_stat_card(screen, focus)

    def _draw_stat_card(self, screen, btn):
        cls = btn["cls"]
        # No box: a flat column with one thin separator under the name.
        card_w = 520
        cx = self.width // 2 + 360
        left = cx - card_w // 2
        top = self.height // 2 - 220

        name = theme.text_surface(self.card_font, btn["text"], TITLE_C)
        screen.blit(name, name.get_rect(center=(cx, top)))
        tag = theme.text_surface(self.tagline_font, btn["tagline"], MUTED)
        screen.blit(tag, tag.get_rect(center=(cx, top + 44)))
        pygame.draw.line(screen, LINE_C,
                         (left + 20, top + 78),
                         (left + card_w - 20, top + 78), 2)

        stats = [
            ("HP",        cls.max_hp, 200),
            ("SPEED",     cls.speed, 900),
            ("DAMAGE",    cls.attack_damage, 25),
            ("FIRE RATE", 1.0 / max(0.01, cls.attack_cooldown), 6.0),
        ]
        # Label column width from font metrics (codebase idiom — cf.
        # theme.draw_toast, MainMenu._toast_y) so the widest label
        # ("FIRE RATE") can't overrun a hardcoded 110 px column into
        # its bar. bar_right reproduces the old right edge
        # (left+130)+(card_w-170) so the value-number column is byte-
        # stable; the max(60, …) is a defensive floor (B10-class) that
        # never triggers with the current font/labels.
        label_w = max(self.stat_font.size(s)[0] for s, _, _ in stats)
        bar_right = left + card_w - 40
        bar_x = left + 20 + label_w + 18
        bar_w = max(60, bar_right - bar_x)
        bar_h = 10
        y = top + 130
        for label, val, vmax in stats:
            text = theme.text_surface(self.stat_font, label, MUTED)
            screen.blit(text, text.get_rect(midleft=(left + 20, y + 5)))
            ratio = max(0.05, min(1.0, val / vmax))
            theme.draw_bar(screen,
                           pygame.Rect(bar_x, y, bar_w, bar_h),
                           ratio, ACCENT, border=False)
            num = theme.text_surface(
                self.stat_font,
                f"{val:.1f}" if isinstance(val, float) else str(val),
                INK)
            screen.blit(num, num.get_rect(midleft=(bar_x + bar_w + 12, y + 5)))
            y += 56

        # Signature ability — a fifth line below the stat bars so the
        # differentiator reads before the character is picked.
        if getattr(cls, "ABILITY_NAME", ""):
            pygame.draw.line(screen, LINE_C,
                             (left + 20, y - 6),
                             (left + card_w - 20, y - 6), 2)
            y += 14
            name = theme.text_surface(
                self.stat_font, f"ABILITY  {cls.ABILITY_NAME}", TITLE_C)
            screen.blit(name, name.get_rect(midleft=(left + 20, y + 5)))
            y += 34
            desc = theme.text_surface(
                self.tagline_font, cls.ABILITY_DESC, MUTED)
            screen.blit(desc, desc.get_rect(midleft=(left + 20, y + 5)))

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.character:
                if btn["rect"].collidepoint(mouse_pos):
                    audio.play("menu_confirm")
                    return btn["action"]
        return None


class PauseMenu:
    """Translucent overlay over the live game.

    The level keeps its state — ``main.py`` simply stops calling
    ``LevelManager.update`` while paused, so the next Resume picks up
    exactly where you froze.
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = theme.font(50)
        self.title_font = theme.font(76)
        self.hint_font = theme.font(24)

        self.buttons = [
            {"text": "Resume",       "action": "resume"},
            {"text": "Restart Level", "action": "restart"},
            {"text": "Quit to Menu", "action": "quit"},
        ]

        cx = width // 2
        start_y = height // 2 - 30
        for i, btn in enumerate(self.buttons):
            rect = measure(self.font, btn["text"])
            rect.center = (cx, start_y + i * 110)
            btn["rect"] = rect

    def draw(self, screen):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*BG, 210))
        screen.blit(overlay, (0, 0))

        title = theme.text_surface(self.title_font, "PAUSED", TITLE_C)
        t_rect = title.get_rect(
            center=(self.width // 2, self.height // 2 - 200))
        screen.blit(title, t_rect)
        ly = t_rect.bottom + 16
        pygame.draw.line(screen, LINE_C,
                         (self.width // 2 - 150, ly),
                         (self.width // 2 + 150, ly), 2)

        mp = pygame.mouse.get_pos()
        for btn in self.buttons:
            hov = btn["rect"].collidepoint(mp)
            col = ACCENT if hov else INK
            screen.blit(theme.text_surface(
                self.font, btn["text"], col), btn["rect"])
            if hov:
                _hover_marker(screen, btn["rect"])

        hint = theme.text_surface(self.hint_font, "Esc to resume", MUTED)
        screen.blit(hint, hint.get_rect(
            center=(self.width // 2, self.height - 88)))

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = pygame.mouse.get_pos()
            for btn in self.buttons:
                if btn["rect"].collidepoint(mp):
                    audio.play("menu_confirm")
                    return btn["action"]
        return None
