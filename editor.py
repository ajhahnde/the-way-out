"""In-game level editor.

A pygame-native palette → canvas editor that writes ``.txt`` files in
the same tokenised format the runtime loads. Output goes to
``~/.the-way-out/custom_levels/<name>.txt`` and is picked up by
:mod:`level_catalog` automatically, so a fresh level appears in the
level menu the next time it's opened.

Layout (anchored to the screen size, scales with it):

* **Canvas** on the left: scrolling grid, the level being authored.
* **Palette** on the right: tile thumbnails grouped by category
  (terrain, special, hazard, enemy, prop). Click to select; the wheel
  cycles the variant for prop tiles.
* **Toolbar** at the bottom: file name (click to rename), grid size,
  Save / Test / Clear buttons.

Controls (also displayed in the toolbar/hint):

* LMB / RMB:           place selected tile / clear to floor
* Shift + LMB/RMB drag: box-fill / box-erase a rectangle
* Q (or Pick):         eyedropper — next canvas click adopts that cell
* Border:              re-wall the outer ring
* Mouse wheel:         cycle variant on the selected tile
* WASD / arrows:       pan camera
* Esc:                 back to main menu
* F5 (or Test):        save + launch the level
* Ctrl+S (or Save):    save only

The editor is intentionally one self-contained file. It reuses
``tiles.REGISTRY`` for what tiles exist and ``tileset.sprite`` /
``interactables`` images for the canvas previews — so a new tile added
to the registry shows up automatically in the palette.
"""

import re
from pathlib import Path

import pygame

from settings import TILE_SIZE
from interactables import Spikes, Lever, Gate, KeyItem, PressurePlate
from static_objects import TileTextures
from tiles import REGISTRY, PALETTE_CATEGORIES, chars_for
import level_catalog
import tileset
import theme


# Used both as a directory and as the legal-filename charset.
SAFE_NAME = re.compile(r"[^a-zA-Z0-9_\-]+")
MAX_NAME = 32


def sanitize(name):
    """Squash any non-portable characters out of a filename stem,
    collapse runs of underscores, trim, and clamp length so the user
    can paste anything weird and still get something writable."""
    cleaned = SAFE_NAME.sub("_", name).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)[:MAX_NAME]
    return cleaned or "untitled"


class LevelEditor:
    """The editor surface + state. One instance lives for the whole
    session; ``new_level`` / ``open_level`` reset the grid."""

    # Palette layout. Cells are rendered as square thumbnails with a
    # 6 px gap; the category headers sit between them.
    PALETTE_W = 480
    PALETTE_PAD = 18
    CELL = 56
    CELL_GAP = 8

    # Toolbar
    TOOLBAR_H = 110

    # Default grid for a fresh level (with auto-walled border)
    DEFAULT_COLS = 30
    DEFAULT_ROWS = 20

    # --- lifecycle -----------------------------------------------------

    def __init__(self, width, height):
        self.width = width
        self.height = height

        # Fonts
        self.font = theme.font(36)
        self.label_font = theme.font(22)
        self.small_font = theme.font(18)
        self.hint_font = theme.font(20)
        self.head_font = theme.font(26)

        # Geometry — canvas fills everything left of the palette and
        # above the toolbar.
        self.palette_rect = pygame.Rect(
            width - self.PALETTE_W, 0,
            self.PALETTE_W, height - self.TOOLBAR_H)
        self.canvas_rect = pygame.Rect(
            0, 0, width - self.PALETTE_W, height - self.TOOLBAR_H)
        self.toolbar_rect = pygame.Rect(
            0, height - self.TOOLBAR_H, width, self.TOOLBAR_H)

        # State that resets per-level
        self.grid = []
        self.cols = 0
        self.rows = 0
        self.name = "my_level"
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.message = ""
        self.message_timer = 0.0

        # Palette / selection
        self.selected_char = 'W'
        self.selected_variant = 1
        self._palette_rects = []        # list of (pygame.Rect, char)
        self._tile_thumb_cache = {}     # (char, variant) -> Surface

        # Toolbar / buttons
        self._toolbar_rects = {}        # name -> pygame.Rect
        self._name_rect = pygame.Rect(0, 0, 0, 0)
        self.editing_name = False

        # Drag-painting: while LMB or RMB is held, every frame where
        # the mouse is on a new cell paints/erases.
        self._mouse_buttons = [False, False, False]  # left, middle, right
        self._last_painted_cell = None

        # 'paint' (default) or 'pick' (eyedropper, toggled with Q).
        self.tool = 'paint'
        # Shift+drag box fill/erase: anchor cell while the drag is live.
        self._box_start = None
        self._box_erase = False

        # ``request_test`` flips True when the user hits F5/Test; main
        # reads & clears it to switch into the game state.
        self.request_test = False
        self.test_level_id = None

        self.new_level()
        self._build_palette_layout()
        self._build_toolbar_layout()

    def new_level(self, cols=None, rows=None, name=None):
        """Reset the grid to the requested size (or default) with a
        wall border and a single 'P' near the top-left so the level is
        legal-ish out of the box."""
        if cols is not None:
            self.cols = cols
        else:
            self.cols = self.DEFAULT_COLS
        if rows is not None:
            self.rows = rows
        else:
            self.rows = self.DEFAULT_ROWS
        if name is not None:
            self.name = sanitize(name)
        self.grid = [['.' for _ in range(self.cols)]
                     for _ in range(self.rows)]
        self._wall_border()
        # Helpful defaults so a smashed save still loads.
        if self.rows > 2 and self.cols > 2:
            self.grid[1][1] = 'P'
            self.grid[self.rows - 2][self.cols - 2] = 'X'
        self.cam_x = 0.0
        self.cam_y = 0.0

    def open_level(self, entry):
        """Load an existing level file into the editor. Used to tweak
        a built-in level or continue work on a custom one."""
        try:
            with open(entry.file, 'r') as f:
                lines = [l.rstrip('\n') for l in f if l.strip()]
        except (FileNotFoundError, OSError) as e:
            self._flash(f"Could not open {entry.file}: {e}")
            return

        grid = []
        for line in lines:
            # Reuse the runtime parser so dense and tokenised rows
            # round-trip identically.
            if ' ' in line:
                grid.append(line.split())
            else:
                grid.append(list(line))
        if not grid:
            self._flash("Empty level — starting blank instead")
            self.new_level()
            return

        cols = max(len(r) for r in grid)
        for row in grid:
            row.extend('W' * (cols - len(row)))
        self.rows = len(grid)
        self.cols = cols
        self.grid = grid
        # Default name = file stem; user can rename before saving.
        self.name = sanitize(Path(entry.file).stem)
        self.cam_x = 0.0
        self.cam_y = 0.0

    def reset_pointer_state(self):
        """Drop any in-flight drag / box / held-button state.

        The editor instance lives for the whole session, so a Shift-drag
        box that was interrupted mid-gesture (Esc to menu, Test, window
        focus loss) would otherwise keep ``_box_start`` / a stuck
        ``_mouse_buttons`` entry set and commit a spurious box-fill on
        the next visit. ``main`` calls this whenever the editor (re)gains
        or loses control."""
        self._box_start = None
        self._box_erase = False
        self._mouse_buttons = [False, False, False]
        self._last_painted_cell = None

    # --- frame ---------------------------------------------------------

    def update(self, dt):
        # Decay the toast message.
        if self.message_timer > 0:
            self.message_timer = max(0.0, self.message_timer - dt)
            if self.message_timer == 0:
                self.message = ""

        # Camera pan on held keys. Read pressed-state every frame so it
        # feels continuous (event-driven would tick once per repeat).
        pan_speed = TILE_SIZE * 12 * dt  # ~12 tiles/sec
        keys = pygame.key.get_pressed()
        if not self.editing_name:
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self.cam_x -= pan_speed
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                self.cam_x += pan_speed
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self.cam_y -= pan_speed
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.cam_y += pan_speed
        self._clamp_camera()

        # Drag-paint: if a button is still held, keep applying while
        # the cursor crosses cells. Suppressed during a Shift box-drag
        # and while the eyedropper is active (those are click-only).
        if ((self._mouse_buttons[0] or self._mouse_buttons[2])
                and self._box_start is None and self.tool == 'paint'):
            mx, my = pygame.mouse.get_pos()
            if self.canvas_rect.collidepoint(mx, my):
                cell = self._screen_to_cell(mx, my)
                if cell is not None and cell != self._last_painted_cell:
                    self._paint_cell(cell, erase=self._mouse_buttons[2])

    def _clamp_camera(self):
        max_x = max(0, self.cols * TILE_SIZE - self.canvas_rect.width)
        max_y = max(0, self.rows * TILE_SIZE - self.canvas_rect.height)
        self.cam_x = max(0, min(self.cam_x, max_x))
        self.cam_y = max(0, min(self.cam_y, max_y))

    # --- input ---------------------------------------------------------

    def handle_input(self, event):
        """Return ``'back'`` to leave the editor, ``'test'`` to enter
        game state with the currently-saved level, or ``None``."""
        if event.type == pygame.KEYDOWN:
            if self.editing_name:
                if event.key == pygame.K_RETURN:
                    self.editing_name = False
                    self.name = sanitize(self.name) or "untitled"
                elif event.key == pygame.K_ESCAPE:
                    # Cancel the rename. Re-sanitize so backspacing the
                    # name down to empty can't leave self.name == "".
                    self.editing_name = False
                    self.name = sanitize(self.name)
                elif event.key == pygame.K_BACKSPACE:
                    self.name = self.name[:-1]
                else:
                    ch = event.unicode
                    if ch and (ch.isalnum() or ch in "_-") and len(self.name) < MAX_NAME:
                        self.name += ch
                return None

            if event.key == pygame.K_ESCAPE:
                return 'back'
            if event.key == pygame.K_F5:
                return self._do_test()
            if event.key == pygame.K_s and (pygame.key.get_mods()
                                            & pygame.KMOD_CTRL):
                self._do_save()
                return None
            if event.key == pygame.K_q and not (
                    pygame.key.get_mods() & pygame.KMOD_META):
                self.tool = 'pick' if self.tool == 'paint' else 'paint'
                return None

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
            if event.button == 1:
                self._mouse_buttons[0] = True
                if shift and self.canvas_rect.collidepoint(mx, my):
                    cell = self._screen_to_cell(mx, my)
                    if cell is not None:
                        self._box_start = cell
                        self._box_erase = False
                        return None
                result = self._click_left(mx, my)
                if result is not None:
                    return result
            elif event.button == 3:
                self._mouse_buttons[2] = True
                if shift and self.canvas_rect.collidepoint(mx, my):
                    cell = self._screen_to_cell(mx, my)
                    if cell is not None:
                        self._box_start = cell
                        self._box_erase = True
                        return None
                if self.canvas_rect.collidepoint(mx, my):
                    cell = self._screen_to_cell(mx, my)
                    if cell is not None:
                        self._paint_cell(cell, erase=True)
            elif event.button == 4:    # wheel up
                self._cycle_variant(1)
            elif event.button == 5:    # wheel down
                self._cycle_variant(-1)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self._mouse_buttons[0] = False
                self._last_painted_cell = None
                if self._box_start is not None and not self._box_erase:
                    end = self._screen_to_cell(*event.pos) \
                        or self._box_start
                    self._commit_box(end, erase=False)
            elif event.button == 3:
                self._mouse_buttons[2] = False
                self._last_painted_cell = None
                if self._box_start is not None and self._box_erase:
                    end = self._screen_to_cell(*event.pos) \
                        or self._box_start
                    self._commit_box(end, erase=True)

        elif event.type == pygame.MOUSEWHEEL:
            # Some platforms emit MOUSEWHEEL instead of buttons 4/5.
            if event.y:
                self._cycle_variant(1 if event.y > 0 else -1)
        return None

    def _click_left(self, mx, my):
        # Palette
        if self.palette_rect.collidepoint(mx, my):
            for rect, ch in self._palette_rects:
                if rect.collidepoint(mx, my):
                    self.selected_char = ch
                    # Reset variant when switching tiles so it can't go
                    # out of range silently.
                    self.selected_variant = 1
                    return
            return

        # Toolbar
        if self.toolbar_rect.collidepoint(mx, my):
            if self._name_rect.collidepoint(mx, my):
                self.editing_name = True
                return
            for name, rect in self._toolbar_rects.items():
                if rect.collidepoint(mx, my):
                    if name == 'save':
                        self._do_save()
                    elif name == 'test':
                        # Propagate 'test' out so handle_input can
                        # return it to main — without this the
                        # toolbar Test button silently saves but
                        # never launches a test session (F5 worked
                        # because it returned _do_test() directly).
                        return self._do_test()
                    elif name == 'clear':
                        self.new_level(self.cols, self.rows, self.name)
                        self._flash("Cleared")
                    elif name == 'border':
                        self._wall_border()
                        self._flash("Border walled")
                    elif name == 'pick':
                        self.tool = ('pick' if self.tool == 'paint'
                                     else 'paint')
                    elif name == 'grow_w':
                        self._resize(self.cols + 2, self.rows)
                    elif name == 'shrink_w':
                        self._resize(max(6, self.cols - 2), self.rows)
                    elif name == 'grow_h':
                        self._resize(self.cols, self.rows + 2)
                    elif name == 'shrink_h':
                        self._resize(self.cols, max(6, self.rows - 2))
                    return
            return

        # Canvas
        if self.canvas_rect.collidepoint(mx, my):
            cell = self._screen_to_cell(mx, my)
            if cell is None:
                return
            if self.tool == 'pick':
                self._pick_cell(cell)
            else:
                self._paint_cell(cell, erase=False)

    def _cycle_variant(self, delta):
        spec = REGISTRY.get(self.selected_char)
        if spec is None or spec.variant_count <= 1:
            return
        self.selected_variant = (
            (self.selected_variant - 1 + delta) % spec.variant_count) + 1

    # --- grid editing --------------------------------------------------

    def _screen_to_cell(self, sx, sy):
        if not self.canvas_rect.collidepoint(sx, sy):
            return None
        # int() to match _cell_to_screen and the canvas draw loop
        # (both use int(self.cam_*)); a float cam here would shift the
        # hit-test off the drawn grid by the sub-pixel camera fraction.
        wx = sx - self.canvas_rect.left + int(self.cam_x)
        wy = sy - self.canvas_rect.top + int(self.cam_y)
        c = int(wx // TILE_SIZE)
        r = int(wy // TILE_SIZE)
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return (r, c)
        return None

    def _cell_to_screen(self, r, c):
        return (self.canvas_rect.left + c * TILE_SIZE - int(self.cam_x),
                self.canvas_rect.top + r * TILE_SIZE - int(self.cam_y))

    def _paint_cell(self, cell, erase=False):
        r, c = cell
        if erase:
            self.grid[r][c] = '.'
        else:
            spec = REGISTRY.get(self.selected_char)
            # Singleton enforcement: P and X must be unique.
            if spec is not None and spec.category == 'special':
                self._clear_char(spec.char)
            self.grid[r][c] = self._selected_token()
        self._last_painted_cell = cell

    def _clear_char(self, ch):
        """Remove every existing occurrence of ``ch`` from the grid.
        Used for singleton tiles (P, X) so painting another puts the
        spawn where the user pointed instead of leaving two."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] and self.grid[r][c][0] == ch:
                    self.grid[r][c] = '.'

    def _wall_border(self):
        """Set the whole outer ring to wall. Shared by ``new_level``
        and the toolbar Border button."""
        for r in range(self.rows):
            self.grid[r][0] = 'W'
            self.grid[r][self.cols - 1] = 'W'
        for c in range(self.cols):
            self.grid[0][c] = 'W'
            self.grid[self.rows - 1][c] = 'W'

    def _selected_token(self):
        """The token string the current selection writes — letter plus
        a variant suffix only when it has a non-default variant (keeps
        saved files readable)."""
        spec = REGISTRY.get(self.selected_char)
        if (spec is not None and spec.variant_count > 1
                and self.selected_variant > 1):
            return f"{spec.char}{self.selected_variant}"
        return self.selected_char

    def _pick_cell(self, cell):
        """Eyedropper: load the token under the cursor into the
        selection, then drop back to paint so the next click draws."""
        r, c = cell
        tok = self.grid[r][c] or '.'
        ch = tok[0]
        if ch not in REGISTRY:
            ch = '.'
        self.selected_char = ch
        spec = REGISTRY.get(ch)
        v = _token_variant(tok)
        self.selected_variant = (
            v if spec is not None and 1 <= v <= spec.variant_count
            else 1)
        self.tool = 'paint'

    def _commit_box(self, end_cell, erase):
        """Fill (or erase) the rectangle spanned by the Shift-drag.
        Singleton specials (P/X) can't sensibly tile a box, so they
        fall back to a single placement at the release cell."""
        (r0, c0), (r1, c1) = self._box_start, end_cell
        self._box_start = None
        spec = REGISTRY.get(self.selected_char)
        if (not erase and spec is not None
                and spec.category == 'special'):
            self._paint_cell(end_cell, erase=False)
            return
        token = '.' if erase else self._selected_token()
        for r in range(min(r0, r1), max(r0, r1) + 1):
            for c in range(min(c0, c1), max(c0, c1) + 1):
                self.grid[r][c] = token

    def _resize(self, new_cols, new_rows):
        """Grow / shrink the grid, keeping existing content in place.
        New cells default to floor; the new outer border becomes wall
        only if it's the very edge."""
        new_grid = [['.' for _ in range(new_cols)] for _ in range(new_rows)]
        for r in range(min(self.rows, new_rows)):
            for c in range(min(self.cols, new_cols)):
                new_grid[r][c] = self.grid[r][c]
        # Re-wall border row/cols at the new edges.
        for r in range(new_rows):
            if new_grid[r][0] == '.':
                new_grid[r][0] = 'W'
            if new_grid[r][new_cols - 1] == '.':
                new_grid[r][new_cols - 1] = 'W'
        for c in range(new_cols):
            if new_grid[0][c] == '.':
                new_grid[0][c] = 'W'
            if new_grid[new_rows - 1][c] == '.':
                new_grid[new_rows - 1][c] = 'W'
        self.rows = new_rows
        self.cols = new_cols
        self.grid = new_grid
        self._clamp_camera()

    # --- save / load / test --------------------------------------------

    def _validate(self):
        """Return a list of warnings (empty if everything is fine).
        Only blocks 'no player start' — anything else is a soft warn so
        the user can experiment freely."""
        warnings = []
        flat = [tok for row in self.grid for tok in row]
        chars = [t[0] if t else '.' for t in flat]
        if 'P' not in chars:
            warnings.append("No 'P' player start — level won't be playable")
        if 'X' not in chars:
            warnings.append("No 'X' exit — player can't escape")
        triggers = sum(c in ('L', 'Y') for c in chars)
        # G *cells* are counted, but multiple adjacent G are one panel
        # at runtime. Cheap approximation: count G runs as panels.
        gate_runs = 0
        prev = None
        for c in chars:
            if c == 'G' and prev != 'G':
                gate_runs += 1
            prev = c
        if triggers and gate_runs and triggers != gate_runs:
            warnings.append(
                f"{triggers} trigger(s) but ~{gate_runs} gate panel(s) — "
                "pairings may be off")
        return warnings

    def _do_save(self):
        # Last line of defence: every entry path *should* keep self.name
        # safe, but sanitize at the write boundary too so an empty name
        # can never produce a ".txt" dot-file / "custom_" id.
        self.name = sanitize(self.name)
        warnings = self._validate()
        level_catalog.ensure_custom_dir()
        path = level_catalog.CUSTOM_DIR / f"{self.name}.txt"
        try:
            with open(path, 'w') as f:
                for row in self.grid:
                    f.write(' '.join(row) + '\n')
        except OSError as e:
            self._flash(f"Save failed: {e}")
            return False
        if warnings:
            self._flash(f"Saved with warnings: {warnings[0]}")
        else:
            self._flash(f"Saved → {path.name}")
        return True

    def _do_test(self):
        if not self._do_save():
            return None
        # Custom-level id matches the convention in level_catalog.
        self.test_level_id = f"custom_{self.name}"
        self.request_test = True
        return 'test'

    def _flash(self, msg, secs=2.6):
        self.message = msg
        self.message_timer = secs

    # --- draw ---------------------------------------------------------

    def draw(self, screen):
        # Backdrop — canvas/palette/toolbar are shades derived from the
        # shared BG so the split stays one family, not three tuples.
        screen.fill(theme.BG)
        pygame.draw.rect(screen, theme.shade(theme.BG, -6), self.canvas_rect)
        pygame.draw.rect(screen, theme.shade(theme.BG, 10), self.palette_rect)
        pygame.draw.rect(screen, theme.shade(theme.BG, -2), self.toolbar_rect)

        self._draw_canvas(screen)
        self._draw_palette(screen)
        self._draw_toolbar(screen)
        self._draw_message(screen)

    # ----- canvas -----------------------------------------------------

    def _draw_canvas(self, screen):
        # Clip to the canvas area so tiles drawn past the panel boundary
        # don't bleed into the palette.
        prev_clip = screen.get_clip()
        screen.set_clip(self.canvas_rect)

        # Tiles. Only the visible window costs anything — we skip every
        # row/col outside the camera.
        cw = self.canvas_rect.width
        ch = self.canvas_rect.height
        first_col = max(0, int(self.cam_x) // TILE_SIZE)
        first_row = max(0, int(self.cam_y) // TILE_SIZE)
        last_col = min(self.cols - 1,
                       (int(self.cam_x) + cw) // TILE_SIZE)
        last_row = min(self.rows - 1,
                       (int(self.cam_y) + ch) // TILE_SIZE)

        floor_img = tileset.tile(tileset.FLOOR_TILE)
        wall_img = tileset.tile(tileset.WALL_TILE)
        floor_tex = TileTextures.get('floor')
        wall_tex = TileTextures.get('wall')

        for r in range(first_row, last_row + 1):
            for c in range(first_col, last_col + 1):
                sx, sy = self._cell_to_screen(r, c)
                # Floor underneath everything.
                screen.blit(floor_img or floor_tex, (sx, sy))
                token = self.grid[r][c]
                if not token or token == '.':
                    continue
                ch_ = token[0]
                if ch_ == 'W':
                    screen.blit(wall_img or wall_tex, (sx, sy))
                else:
                    img = self._thumbnail(ch_, _token_variant(token),
                                          large=True)
                    if img is not None:
                        screen.blit(img, (sx, sy))

        # Grid lines (subtle) — a touch above the canvas shade.
        grid_col = theme.shade(theme.BG, 22)
        for c in range(first_col, last_col + 2):
            x = self.canvas_rect.left + c * TILE_SIZE - int(self.cam_x)
            pygame.draw.line(screen, grid_col,
                             (x, self.canvas_rect.top),
                             (x, self.canvas_rect.bottom), 1)
        for r in range(first_row, last_row + 2):
            y = self.canvas_rect.top + r * TILE_SIZE - int(self.cam_y)
            pygame.draw.line(screen, grid_col,
                             (self.canvas_rect.left, y),
                             (self.canvas_rect.right, y), 1)

        # Cursor preview — eyedropper shows just a cyan box (no ghost,
        # since picking doesn't place the current selection).
        mx, my = pygame.mouse.get_pos()
        cell = self._screen_to_cell(mx, my)
        if cell is not None and not self.editing_name:
            r, c = cell
            sx, sy = self._cell_to_screen(r, c)
            if self.tool == 'pick':
                pygame.draw.rect(screen, theme.ACCENT,
                                 (sx, sy, TILE_SIZE, TILE_SIZE), 3)
            else:
                preview = self._thumbnail(self.selected_char,
                                          self.selected_variant,
                                          large=True)
                if preview is not None:
                    ghost = preview.copy()
                    ghost.set_alpha(160)
                    screen.blit(ghost, (sx, sy))
                pygame.draw.rect(screen, theme.ACCENT,
                                 (sx, sy, TILE_SIZE, TILE_SIZE), 2)

        # Box fill/erase marquee while a Shift-drag is live.
        if self._box_start is not None:
            r0, c0 = self._box_start
            r1, c1 = self._screen_to_cell(mx, my) or self._box_start
            x0, y0 = self._cell_to_screen(min(r0, r1), min(c0, c1))
            w = (abs(c1 - c0) + 1) * TILE_SIZE
            h = (abs(r1 - r0) + 1) * TILE_SIZE
            tint = theme.FAIL if self._box_erase else theme.ACCENT
            ov = pygame.Surface((w, h), pygame.SRCALPHA)
            ov.fill((*tint, 45))
            screen.blit(ov, (x0, y0))
            pygame.draw.rect(screen, tint, (x0, y0, w, h), 2)

        screen.set_clip(prev_clip)

    # ----- palette ----------------------------------------------------

    def _build_palette_layout(self):
        """Compute click rects for every palette tile + remember the
        category headers' y-positions (used for drawing)."""
        self._palette_rects = []
        self._palette_headers = []  # (y, label)

        x0 = self.palette_rect.left + self.PALETTE_PAD
        y = self.palette_rect.top + 90  # leave room for "PALETTE" title
        max_x = self.palette_rect.right - self.PALETTE_PAD
        cell = self.CELL
        gap = self.CELL_GAP

        for category in PALETTE_CATEGORIES:
            chars = chars_for(category)
            if not chars:
                continue
            self._palette_headers.append((y, category.upper()))
            y += 32
            x = x0
            for ch in chars:
                if x + cell > max_x:
                    x = x0
                    y += cell + gap
                rect = pygame.Rect(x, y, cell, cell)
                self._palette_rects.append((rect, ch))
                x += cell + gap
            y += cell + gap + 14

        # Selection info card sits below the last category.
        self._palette_info_y = y + 6

    def _draw_palette(self, screen):
        # Title
        title = self.font.render("PALETTE", True, theme.TITLE_C)
        screen.blit(title, title.get_rect(
            midtop=(self.palette_rect.centerx,
                    self.palette_rect.top + 24)))

        # Headers
        for y, label in self._palette_headers:
            h = self.head_font.render(label, True, theme.MUTED)
            screen.blit(h, (self.palette_rect.left + self.PALETTE_PAD, y))
            pygame.draw.line(
                screen, theme.LINE_C,
                (self.palette_rect.left + self.PALETTE_PAD + 120, y + 12),
                (self.palette_rect.right - self.PALETTE_PAD, y + 12), 1)

        # Tile thumbnails
        mp = pygame.mouse.get_pos()
        for rect, ch in self._palette_rects:
            is_sel = (ch == self.selected_char)
            is_hov = rect.collidepoint(mp)
            # Backplate
            bp_color = (theme.shade(theme.BG, 28) if is_sel
                        else theme.shade(theme.BG, 16) if is_hov
                        else theme.shade(theme.BG, 6))
            pygame.draw.rect(screen, bp_color, rect, border_radius=6)
            # Tile preview — the thumb for char's variant 1
            img = self._thumbnail(ch, 1, large=False)
            if img is not None:
                screen.blit(img, img.get_rect(center=rect.center))
            # Letter overlay (top-left)
            letter = self.small_font.render(ch, True, theme.INK)
            screen.blit(letter, (rect.left + 4, rect.top + 2))
            # Border
            border = (theme.ACCENT if is_sel
                      else theme.MUTED if is_hov
                      else theme.LINE_C)
            pygame.draw.rect(screen, border, rect, 2, border_radius=6)

        # Selected-tile info card
        spec = REGISTRY.get(self.selected_char)
        if spec is None:
            return
        ix = self.palette_rect.left + self.PALETTE_PAD
        iy = self._palette_info_y
        w = self.palette_rect.width - 2 * self.PALETTE_PAD
        # Flat spec block — no bordered box. Same language as the
        # CharacterMenu stat block: name, one thin separator, then
        # quiet detail text.
        card = pygame.Rect(ix, iy, w, 130)
        name = self.font.render(spec.label, True, theme.TITLE_C)
        screen.blit(name, (card.left + 16, card.top + 10))
        pygame.draw.line(screen, theme.LINE_C,
                         (card.left + 16, card.top + 48),
                         (card.right - 16, card.top + 48), 2)
        if spec.variant_count > 1:
            v = self.label_font.render(
                f"variant {self.selected_variant} / {spec.variant_count}  "
                f"(scroll to cycle)", True, theme.MUTED)
            screen.blit(v, (card.left + 16, card.top + 58))
        # Wrap the description manually (cheap word-wrap)
        desc_lines = self._wrap(spec.description, card.width - 30,
                                self.small_font)
        for i, line in enumerate(desc_lines[:3]):
            s = self.small_font.render(line, True, theme.MUTED)
            screen.blit(s, (card.left + 16, card.top + 84 + i * 18))

    def _wrap(self, text, max_w, font):
        words = text.split()
        lines, cur = [], []
        for w in words:
            cur.append(w)
            if font.size(' '.join(cur))[0] > max_w:
                cur.pop()
                if cur:
                    lines.append(' '.join(cur))
                cur = [w]
        if cur:
            lines.append(' '.join(cur))
        return lines

    # ----- toolbar ----------------------------------------------------

    def _build_toolbar_layout(self):
        # Button rects are positioned right-anchored; the filename and
        # size info take the left side.
        h = self.toolbar_rect.height
        y = self.toolbar_rect.top
        # Filename area (top-left)
        self._name_rect = pygame.Rect(
            24, y + 16, 460, 44)
        # Buttons stacked horizontally, anchored to the right. Flat
        # text-only buttons share the menu/list language — no coloured
        # chips. Destructive intent ('clear') is signalled by FAIL on
        # hover; the eyedropper ('pick') latches to ACCENT while armed.
        spec = [
            ('pick',   "Pick (Q)", 160, 'tool'),
            ('border', "Border", 140, 'tool'),
            ('clear',  "Clear", 130, 'danger'),
            ('test',   "Test (F5)", 180, 'tool'),
            ('save',   "Save (Ctrl+S)", 220, 'tool'),
        ]
        right = self.toolbar_rect.right - 20
        self._toolbar_rects = {}
        for name, label, width, kind in reversed(spec):
            rect = pygame.Rect(right - width, y + 18, width, h - 36)
            self._toolbar_rects[name] = rect
            right -= width + 12
        self._toolbar_button_meta = {n: (l, k) for n, l, _w, k in spec}

        # Size +/- arrows (smaller, in the middle of the toolbar)
        mid_x = self._name_rect.right + 30
        my = y + 22
        for i, key in enumerate(['shrink_w', 'grow_w']):
            self._toolbar_rects[key] = pygame.Rect(
                mid_x + i * 38, my, 32, 32)
        for i, key in enumerate(['shrink_h', 'grow_h']):
            self._toolbar_rects[key] = pygame.Rect(
                mid_x + 90 + i * 38, my, 32, 32)
        self._toolbar_button_meta.update({
            'shrink_w': ("-W", 'tool'),
            'grow_w':   ("+W", 'tool'),
            'shrink_h': ("-H", 'tool'),
            'grow_h':   ("+H", 'tool'),
        })

    def _draw_toolbar(self, screen):
        # Filename "input"
        col = (theme.shade(theme.BG, 18) if self.editing_name
               else theme.shade(theme.BG, 8))
        pygame.draw.rect(screen, col, self._name_rect, border_radius=6)
        pygame.draw.rect(screen, theme.LINE_C,
                         self._name_rect, 2, border_radius=6)
        label = self.small_font.render(
            "FILE", True, theme.MUTED)
        screen.blit(label, (self._name_rect.left + 12,
                            self._name_rect.top - 18))
        cursor = "_" if (self.editing_name and
                         (pygame.time.get_ticks() // 400) % 2 == 0) else ""
        name_surf = self.label_font.render(
            f"{self.name}{cursor}.txt", True, theme.INK)
        screen.blit(name_surf, name_surf.get_rect(
            midleft=(self._name_rect.left + 16,
                     self._name_rect.centery)))

        # Grid size readout
        size = self.label_font.render(
            f"{self.cols} × {self.rows}", True, theme.MUTED)
        screen.blit(size, (self._name_rect.right + 200,
                           self.toolbar_rect.top + 28))

        # Buttons — flat text + thin underline. Hover or active state
        # lights the text/underline ACCENT; destructive 'clear' goes
        # FAIL on hover only.
        mp = pygame.mouse.get_pos()
        for name, rect in self._toolbar_rects.items():
            text, kind = self._toolbar_button_meta[name]
            active = (name == 'pick' and self.tool == 'pick')
            hov = rect.collidepoint(mp)
            if active:
                text_col = theme.ACCENT
            elif hov:
                text_col = theme.FAIL if kind == 'danger' else theme.ACCENT
            else:
                text_col = theme.INK
            t = self.label_font.render(text, True, text_col)
            screen.blit(t, t.get_rect(center=rect.center))
            if hov or active:
                pygame.draw.line(screen, text_col,
                                 (rect.left + 12, rect.bottom - 6),
                                 (rect.right - 12, rect.bottom - 6), 2)

        # Bottom-line hint
        d = theme.HINT_DOT
        hint = self.hint_font.render(
            f"LMB place {d} RMB clear {d} Shift+drag box {d} Q pick {d} "
            f"Wheel variant {d} WASD pan {d} Esc back {d} F5 test",
            True, theme.MUTED)
        screen.blit(hint, hint.get_rect(
            midbottom=(self.toolbar_rect.centerx,
                       self.toolbar_rect.bottom - 6)))

    def _draw_message(self, screen):
        if not self.message:
            return
        s = self.label_font.render(self.message, True, theme.INK)
        pad = s.get_rect().inflate(28, 14)
        pad.center = (self.canvas_rect.centerx,
                      self.toolbar_rect.top - 40)
        bg = pygame.Surface(pad.size, pygame.SRCALPHA)
        bg.fill((*theme.BG, 220))
        screen.blit(bg, pad)
        pygame.draw.rect(screen, theme.LINE_C, pad, 2, border_radius=8)
        screen.blit(s, s.get_rect(center=pad.center))

    # --- thumbnail rendering ------------------------------------------

    def _thumbnail(self, char, variant, large):
        """Cached preview surface for one tile.

        ``large=True`` returns a TILE_SIZE x TILE_SIZE image suitable
        for the canvas; ``large=False`` returns a thumbnail-sized image
        for the palette grid."""
        size = TILE_SIZE if large else self.CELL - 12
        key = (char, variant, size)
        if key in self._tile_thumb_cache:
            return self._tile_thumb_cache[key]
        surf = self._build_thumbnail(char, variant, size)
        self._tile_thumb_cache[key] = surf
        return surf

    def _build_thumbnail(self, char, variant, size):
        spec = REGISTRY.get(char)
        if spec is None:
            return None

        # Prop tiles draw straight from the tileset.
        if spec.tileset_category is not None:
            base = tileset.sprite(spec.tileset_category, variant)
            return _scale_surface(base, size)

        # Procedural / built-in tiles — fall through by character.
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        if char == 'W':
            wall = (tileset.tile(tileset.WALL_TILE)
                    or TileTextures.get('wall'))
            surf.blit(wall, (0, 0))
        elif char == '.':
            floor = (tileset.tile(tileset.FLOOR_TILE)
                     or TileTextures.get('floor'))
            surf.blit(floor, (0, 0))
        elif char == 'P':
            _draw_marker(surf, theme.SUCCESS, "P")
        elif char == 'X':
            _draw_exit_marker(surf)
        elif spec.category == 'enemy':
            _draw_marker(surf, theme.FAIL, char)
        elif char == 'S':
            Spikes._build_images()
            surf.blit(Spikes._imgs['up'], (0, 0))
        elif char == 'L':
            Lever._build_images()
            surf.blit(Lever._imgs[False], (0, 0))
        elif char == 'Y':
            PressurePlate._build_images()
            surf.blit(PressurePlate._imgs[False], (0, 0))
        elif char == 'G':
            Gate._build_images()
            surf.blit(Gate._imgs[False], (0, 0))
        elif char == 'K':
            KeyItem._build_image()
            surf.blit(KeyItem._img, (0, 0))
        else:
            # Last-resort marker for an unknown tile char — keep a loud
            # magenta so it visibly screams "missing art" in the editor.
            _draw_marker(surf, (180, 60, 180), char)
        return _scale_surface(surf, size)


# --- module helpers --------------------------------------------------------

def _token_variant(token):
    """Same logic as ``levels._cell_variant`` — duplicated here to keep
    editor.py importable without dragging the level runtime along."""
    digits = token[1:]
    return int(digits) if digits.isdigit() else 1


def _scale_surface(surf, size):
    if size == TILE_SIZE:
        return surf
    return pygame.transform.smoothscale(surf, (size, size))


def _draw_marker(surf, color, letter):
    """Generic 'this tile has no art' marker — circle + bold letter."""
    cx = cy = TILE_SIZE // 2
    pygame.draw.circle(surf, color, (cx, cy), TILE_SIZE // 2 - 6)
    pygame.draw.circle(surf, theme.BG,
                       (cx, cy), TILE_SIZE // 2 - 6, 3)
    f = theme.font(32)
    s = f.render(letter, True, theme.BG)
    surf.blit(s, s.get_rect(center=(cx, cy)))


def _draw_exit_marker(surf):
    """Door-shaped silhouette so the exit reads as something to head
    toward, not a generic marker."""
    rect = pygame.Rect(8, 6, TILE_SIZE - 16, TILE_SIZE - 12)
    pygame.draw.rect(surf, theme.shade(theme.BG, +6), rect, border_radius=4)
    pygame.draw.rect(surf, theme.SUCCESS, rect, 3, border_radius=4)
    inner = rect.inflate(-14, -10)
    pygame.draw.rect(surf, theme.shade(theme.SUCCESS, -30), inner)
