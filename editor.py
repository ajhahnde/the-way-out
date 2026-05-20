"""In-game level editor.

A pygame-native palette → canvas editor that writes ``.txt`` files in
the same tokenised format the runtime loads. Output goes to
``~/.the-way-out/custom_levels/<name>.txt`` and is picked up by
:mod:`level_catalog` automatically, so a fresh level appears in the
level menu the next time it's opened.

Layout (anchored to the screen size, scales with it):

* **Canvas** on the left: scrolling grid, the level being authored.
* **Palette** on the right: a narrow strip of tile thumbnails grouped
  by category (terrain, special, hazard, enemy, prop). Click to select.
  A preview panel below the grid shows the selected tile at a large
  size; its < > buttons (or the mouse wheel) cycle the variant.
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

    # Palette layout. Cells are square thumbnails; the category headers
    # sit between them. CELL / CELL_GAP are sized so six columns fill
    # the narrow palette exactly: 6*CELL + 5*CELL_GAP == PALETTE_W - 2*PAD.
    # PALETTE_W is the expanded panel content width; PALETTE_GRIP_W is
    # the always-visible collapsed rail. Total panel width when the
    # drawer is expanded = PALETTE_GRIP_W + PALETTE_W.
    PALETTE_W = 330
    PALETTE_GRIP_W = 44
    PALETTE_PAD = 18
    CELL = 44
    CELL_GAP = 6

    # Hover-drawer animation seconds (linear). 0.14 ≈ 8 frames at 60 fps.
    PALETTE_ANIM_TIME = 0.14

    # Selected-tile preview panel: a large sprite plus the < > buttons
    # that step its variant.
    PREVIEW_SIZE = 64
    VARIANT_BTN = 30

    # Toolbar
    TOOLBAR_H = 110

    # Load-picker modal: one list row's height.
    PICKER_ROW_H = 56

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

        # Geometry — canvas fills everything left of the collapsed
        # palette rail and above the toolbar. The rail is the
        # always-visible portion of the drawer; the rest of the panel
        # slides in as an overlay over the canvas on hover, so the
        # canvas extent never reflows. palette_rect / _grip_rect are
        # placeholders here and get their real coordinates from
        # _layout_palette() once self._palette_anim is initialised.
        self.canvas_rect = pygame.Rect(
            0, 0,
            width - self.PALETTE_GRIP_W,
            height - self.TOOLBAR_H)
        self.toolbar_rect = pygame.Rect(
            0, height - self.TOOLBAR_H, width, self.TOOLBAR_H)
        self.palette_rect = pygame.Rect(0, 0, 0, 0)
        self._grip_rect = pygame.Rect(0, 0, 0, 0)

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
        self._variant_btn_rects = {}    # 'prev'/'next' -> pygame.Rect
        self._tile_thumb_cache = {}     # (char, variant, size) -> Surface

        # Hover-drawer state: 0.0 = collapsed rail, 1.0 = fully expanded.
        # _layout_palette() projects this onto _grip_rect / palette_rect
        # so the existing _build_palette_layout() math (B25) keeps
        # working unchanged regardless of where the drawer sits.
        self._palette_anim = 0.0
        self._palette_label_surf = None  # cached vertical letter stack
        self._palette_label_col = None   # last colour the cache was built for

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

        # Load picker (modal overlay listing saved custom maps). Closed
        # by default; opened from the toolbar's Load button.
        self.picker_open = False
        self.picker_entries = []
        self.picker_scroll = 0

        self.new_level()
        self._layout_palette()
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
        or loses control. Snapping the drawer closed at the same time
        means the user always lands on the collapsed rail when they
        come back, matching the "default smaller, hover to expand"
        intent of B27."""
        self._box_start = None
        self._box_erase = False
        self._mouse_buttons = [False, False, False]
        self._last_painted_cell = None
        self.picker_open = False
        self._palette_anim = 0.0
        self._layout_palette()

    # --- palette geometry (drawer) ------------------------------------

    def _layout_palette(self):
        """Place ``_grip_rect`` and ``palette_rect`` from ``_palette_anim``.

        ``canvas_rect`` is permanent — set once in ``__init__`` — and
        never reflows. The drawer slides in from the right: at anim=0
        ``palette_rect`` sits off-screen to the right of the grip, so
        no palette tile click can land while collapsed; at anim=1 the
        palette is flush with the screen's right edge, exactly where
        the fixed 330 px panel used to be."""
        panel_x = round(
            (self.width - self.PALETTE_GRIP_W)
            - self.PALETTE_W * self._palette_anim)
        h = self.height - self.TOOLBAR_H
        self._grip_rect = pygame.Rect(
            panel_x, 0, self.PALETTE_GRIP_W, h)
        self.palette_rect = pygame.Rect(
            panel_x + self.PALETTE_GRIP_W, 0, self.PALETTE_W, h)
        self._build_palette_layout()

    # --- frame ---------------------------------------------------------

    def update(self, dt):
        # Decay the toast message.
        if self.message_timer > 0:
            self.message_timer = max(0.0, self.message_timer - dt)
            if self.message_timer == 0:
                self.message = ""

        # Drawer hover-state animation. The drawer expands while the
        # cursor is over the rail or the panel body and contracts when
        # it leaves. Gated on no-buttons-held and no-active-box-drag
        # so a paint stroke aimed at the right edge of the canvas
        # doesn't open the drawer mid-gesture (which would then block
        # painting via the _screen_to_cell overlay guard).
        mx, my = pygame.mouse.get_pos()
        hot = (
            mx >= self._grip_rect.left
            and my < self.height - self.TOOLBAR_H
            and not any(self._mouse_buttons)
            and self._box_start is None
            and not self.editing_name
        )
        target = 1.0 if hot else 0.0
        if self._palette_anim != target:
            step = dt / self.PALETTE_ANIM_TIME
            if self._palette_anim < target:
                self._palette_anim = min(
                    target, self._palette_anim + step)
            else:
                self._palette_anim = max(
                    target, self._palette_anim - step)
            new_x = round(
                (self.width - self.PALETTE_GRIP_W)
                - self.PALETTE_W * self._palette_anim)
            if new_x != self._grip_rect.left:
                self._layout_palette()

        # Camera pan on held keys. Read pressed-state every frame so it
        # feels continuous (event-driven would tick once per repeat).
        pan_speed = TILE_SIZE * 12 * dt  # ~12 tiles/sec
        keys = pygame.key.get_pressed()
        if not self.editing_name and not self.picker_open:
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
        if self.picker_open:
            return self._handle_picker_input(event)

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
        # Drawer rail: pop open even if the hover signal is flaky
        # (touchpad scroll wheels, OS-level cursor warps). The rail is
        # the only mouse target while the drawer is collapsed, so a
        # click here is unambiguous intent to expand.
        if self._grip_rect.collidepoint(mx, my):
            self._palette_anim = 1.0
            self._layout_palette()
            return

        # Palette
        if self.palette_rect.collidepoint(mx, my):
            for rect, ch in self._palette_rects:
                if rect.collidepoint(mx, my):
                    self.selected_char = ch
                    # Reset variant when switching tiles so it can't go
                    # out of range silently.
                    self.selected_variant = 1
                    return
            # < > buttons under the preview panel step the variant the
            # same way the wheel does (_cycle_variant no-ops when the
            # selected tile has only one variant).
            if self._variant_btn_rects['prev'].collidepoint(mx, my):
                self._cycle_variant(-1)
            elif self._variant_btn_rects['next'].collidepoint(mx, my):
                self._cycle_variant(1)
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
                    elif name == 'load':
                        self._open_picker()
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
        # canvas_rect now extends under the expanded palette drawer
        # (B27), so reject any point sitting under the live overlay —
        # the user is targeting the palette, not a cell.
        if self._palette_anim > 0 and sx >= self._grip_rect.left:
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

    # --- load picker (modal) ------------------------------------------

    def _open_picker(self):
        """Open the modal Load picker over the canvas.

        Lists the player's saved custom maps only (built-in levels are
        deliberately excluded — the picker exists to *reopen what you
        saved*). ``_scan_custom`` is the same scan the level menu uses,
        so a map saved this session shows up without a restart."""
        self.picker_entries = level_catalog._scan_custom()
        self.picker_scroll = 0
        self.picker_open = True

    def _picker_panel(self):
        """Centred rect for the modal Load-picker panel."""
        w = min(560, self.width - 120)
        h = min(620, self.height - 160)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (self.width // 2, self.height // 2)
        return rect

    def _picker_list_rect(self):
        """Scrolling-list area inside the panel (below the title, above
        the footer hint). Rows are clipped to this rect."""
        panel = self._picker_panel()
        return pygame.Rect(panel.left, panel.top + 84,
                           panel.width, panel.height - 84 - 52)

    def _picker_visible_count(self):
        return max(1, self._picker_list_rect().height // self.PICKER_ROW_H)

    def _picker_rows(self):
        """``(rect, entry)`` for every list row, in catalog order.

        Rows are positioned absolutely against ``picker_scroll``; rows
        outside the list area simply fall outside ``_picker_list_rect``
        and the caller clips them. Shared by draw and input so hit-test
        and render never disagree."""
        lr = self._picker_list_rect()
        rows = []
        for i, entry in enumerate(self.picker_entries):
            y = lr.top + (i - self.picker_scroll) * self.PICKER_ROW_H
            rect = pygame.Rect(lr.left + 24, y,
                               lr.width - 48, self.PICKER_ROW_H)
            rows.append((rect, entry))
        return rows

    def _scroll_picker(self, delta):
        max_scroll = max(0, len(self.picker_entries)
                         - self._picker_visible_count())
        self.picker_scroll = max(
            0, min(self.picker_scroll + delta, max_scroll))

    def _handle_picker_input(self, event):
        """Drive the modal Load picker. Always returns ``None`` — the
        picker never leaves the editor or starts a test."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.picker_open = False
            return None

        if event.type == pygame.MOUSEWHEEL:
            if event.y:
                self._scroll_picker(-1 if event.y > 0 else 1)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:        # wheel up
                self._scroll_picker(-1)
                return None
            if event.button == 5:        # wheel down
                self._scroll_picker(1)
                return None
            if event.button != 1:
                return None
            if not self._picker_panel().collidepoint(event.pos):
                # Click off the panel dismisses the picker.
                self.picker_open = False
                return None
            list_rect = self._picker_list_rect()
            if list_rect.collidepoint(event.pos):
                for rect, entry in self._picker_rows():
                    if rect.collidepoint(event.pos):
                        self.open_level(entry)
                        self._flash(f"Loaded {entry.title}")
                        self.picker_open = False
                        break
        return None

    def _draw_picker(self, screen):
        """Modal overlay: a centred panel listing saved custom maps."""
        dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.BG, 210))
        screen.blit(dim, (0, 0))

        panel = self._picker_panel()
        pygame.draw.rect(screen, theme.shade(theme.BG, 6), panel,
                         border_radius=10)
        pygame.draw.rect(screen, theme.LINE_C, panel, 2, border_radius=10)

        title = self.font.render("LOAD MAP", True, theme.TITLE_C)
        screen.blit(title, title.get_rect(
            midtop=(panel.centerx, panel.top + 22)))

        list_rect = self._picker_list_rect()
        if not self.picker_entries:
            empty = self.label_font.render(
                "No custom maps yet — save one first", True, theme.MUTED)
            screen.blit(empty, empty.get_rect(center=list_rect.center))
        else:
            prev_clip = screen.get_clip()
            screen.set_clip(list_rect)
            mp = pygame.mouse.get_pos()
            for rect, entry in self._picker_rows():
                if (rect.bottom < list_rect.top
                        or rect.top > list_rect.bottom):
                    continue
                hov = (rect.collidepoint(mp)
                       and list_rect.collidepoint(mp))
                col = theme.ACCENT if hov else theme.INK
                name = self.head_font.render(entry.title, True, col)
                screen.blit(name, name.get_rect(
                    midleft=(rect.left + 16, rect.centery)))
            screen.set_clip(prev_clip)

        hint = self.hint_font.render(
            "Click a map to load   ·   Esc cancel", True, theme.MUTED)
        screen.blit(hint, hint.get_rect(
            midbottom=(panel.centerx, panel.bottom - 16)))

    # --- draw ---------------------------------------------------------

    def draw(self, screen):
        # Backdrop — canvas/palette/toolbar are shades derived from the
        # shared BG so the split stays one family, not three tuples.
        # The palette's own backdrop is drawn inside _draw_palette,
        # *after* _draw_canvas, so the expanded drawer cleanly overlays
        # the canvas instead of being painted over by it.
        screen.fill(theme.BG)
        pygame.draw.rect(screen, theme.shade(theme.BG, -6), self.canvas_rect)
        pygame.draw.rect(screen, theme.shade(theme.BG, -2), self.toolbar_rect)

        self._draw_canvas(screen)
        self._draw_palette(screen)
        self._draw_toolbar(screen)
        self._draw_message(screen)
        if self.picker_open:
            self._draw_picker(screen)

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
            y += cell + gap + 8

        # Selected-tile preview panel sits below the last category.
        self._palette_info_y = y + 6

        # Panel geometry: a PREVIEW_SIZE sprite centred in the panel,
        # flanked by the < > variant buttons. _draw_palette mirrors
        # these offsets for the cosmetic parts (name, separator, text).
        iy = self._palette_info_y
        ix = self.palette_rect.left + self.PALETTE_PAD
        pw = self.palette_rect.width - 2 * self.PALETTE_PAD
        sprite_top = iy + 56
        self._preview_sprite_pos = (
            ix + (pw - self.PREVIEW_SIZE) // 2, sprite_top)
        btn = self.VARIANT_BTN
        by = sprite_top + (self.PREVIEW_SIZE - btn) // 2
        self._variant_btn_rects = {
            'prev': pygame.Rect(ix + 8, by, btn, btn),
            'next': pygame.Rect(ix + pw - 8 - btn, by, btn, btn),
        }

    def _draw_palette(self, screen):
        # Rail (always visible) — the hover affordance + the only piece
        # of the drawer shown while it's collapsed.
        pygame.draw.rect(
            screen, theme.shade(theme.BG, 4), self._grip_rect)
        self._draw_palette_grip(screen)

        if self._palette_anim <= 0:
            return

        # Panel body backdrop — drawn after the canvas so the expanded
        # drawer cleanly overlays. The 10-shade matches the previous
        # fixed-panel tone from B25.
        pygame.draw.rect(
            screen, theme.shade(theme.BG, 10), self.palette_rect)

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

        # Selected-tile preview panel — name, a thin separator, a large
        # sprite flanked by the < > variant buttons, the variant counter,
        # then a short description. Same flat visual language as the
        # CharacterMenu stat block. The buttons step the variant like the
        # wheel; they grey out for single-variant tiles.
        spec = REGISTRY.get(self.selected_char)
        if spec is None:
            return
        ix = self.palette_rect.left + self.PALETTE_PAD
        iy = self._palette_info_y
        w = self.palette_rect.width - 2 * self.PALETTE_PAD
        card = pygame.Rect(ix, iy, w, 150)
        name = self.font.render(spec.label, True, theme.TITLE_C)
        screen.blit(name, (card.left + 16, card.top + 10))
        pygame.draw.line(screen, theme.LINE_C,
                         (card.left + 16, card.top + 48),
                         (card.right - 16, card.top + 48), 2)

        # Large sprite preview of the current selection + variant, on a
        # faint backplate so a dark tile still reads against the panel.
        sx, sy = self._preview_sprite_pos
        plate = pygame.Rect(sx, sy, self.PREVIEW_SIZE, self.PREVIEW_SIZE)
        pygame.draw.rect(screen, theme.shade(theme.BG, 6), plate,
                         border_radius=6)
        preview = self._thumbnail(self.selected_char, self.selected_variant,
                                  large=False, size=self.PREVIEW_SIZE)
        if preview is not None:
            screen.blit(preview, (sx, sy))

        # < > variant buttons — interactive only for multi-variant tiles.
        has_variants = spec.variant_count > 1
        for key, glyph in (('prev', "<"), ('next', ">")):
            rect = self._variant_btn_rects[key]
            hov = has_variants and rect.collidepoint(mp)
            col = (theme.ACCENT if hov
                   else theme.INK if has_variants
                   else theme.LINE_C)
            pygame.draw.rect(screen, col, rect, 2, border_radius=6)
            g = self.head_font.render(glyph, True, col)
            screen.blit(g, g.get_rect(center=rect.center))

        # Variant counter, centred under the sprite.
        vtext = (f"variant {self.selected_variant} / {spec.variant_count}"
                 if has_variants else "single variant")
        v = self.small_font.render(vtext, True, theme.MUTED)
        screen.blit(v, v.get_rect(
            midtop=(card.centerx, sy + self.PREVIEW_SIZE + 8)))

        # Short wrapped description below the panel.
        desc_lines = self._wrap(spec.description, card.width - 30,
                                self.small_font)
        desc_y = sy + self.PREVIEW_SIZE + 32
        for i, line in enumerate(desc_lines[:2]):
            s = self.small_font.render(line, True, theme.MUTED)
            screen.blit(s, (card.left + 16, desc_y + i * 18))

    def _draw_palette_grip(self, screen):
        """Draw the always-visible rail: a 32×32 thumbnail of the
        currently-selected tile, a vertical 'PALETTE' letter stack, and
        — while the drawer is expanded — an ACCENT stripe on the rail's
        left edge as a hover affordance."""
        mp = pygame.mouse.get_pos()
        hot = self._grip_rect.collidepoint(mp)

        # 32×32 selected-tile thumb at the top of the rail so the user
        # always sees what's currently selected even when the drawer is
        # closed. Cached via the regular _thumbnail path; size keys
        # share with the existing palette grid cache only when 32
        # happens to match CELL-12, which it does (44-12 == 32).
        thumb = self._thumbnail(
            self.selected_char, self.selected_variant,
            large=False, size=32)
        if thumb is not None:
            screen.blit(thumb, thumb.get_rect(
                midtop=(self._grip_rect.centerx,
                        self._grip_rect.top + 12)))

        # Vertical letter stack — one small_font letter per row,
        # centred horizontally. ACCENT tint while hovered, MUTED at
        # rest. The stack surface is cached and only rebuilt when the
        # colour flips, so the per-frame cost is one blit.
        col = theme.ACCENT if hot else theme.MUTED
        if (self._palette_label_surf is None
                or self._palette_label_col != col):
            self._palette_label_col = col
            letters = [theme.text_surface(self.small_font, ch, col)
                       for ch in "PALETTE"]
            line_h = self.small_font.get_height() + 2
            stack = pygame.Surface(
                (self._grip_rect.width, line_h * len(letters)),
                pygame.SRCALPHA)
            for i, s in enumerate(letters):
                stack.blit(s, s.get_rect(
                    midtop=(stack.get_width() // 2, i * line_h)))
            self._palette_label_surf = stack
        label = self._palette_label_surf
        screen.blit(label, label.get_rect(
            midtop=(self._grip_rect.centerx,
                    self._grip_rect.top + 56)))

        # Accent stripe on the rail's left edge while the drawer is
        # open — mirrors the toolbar button underline language.
        if self._palette_anim > 0:
            pygame.draw.line(
                screen, theme.ACCENT,
                (self._grip_rect.left, self._grip_rect.top + 4),
                (self._grip_rect.left, self._grip_rect.bottom - 4), 2)

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
            ('load',   "Load", 130, 'tool'),
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

    def _thumbnail(self, char, variant, large, size=None):
        """Cached preview surface for one tile.

        ``large=True`` returns a TILE_SIZE x TILE_SIZE image suitable
        for the canvas; ``large=False`` returns a thumbnail-sized image
        for the palette grid. An explicit ``size`` overrides both — the
        selected-tile preview panel uses it for a larger sprite."""
        if size is None:
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
