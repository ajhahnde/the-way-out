# CHANGELOG

## v0.5.0

Gives every playable character a distinct **signature ability** on a
cooldown, triggered with **Shift** — the combat differentiator for the
v1.0.0 cut. The universal dash is now Shiggy's alone.

### Gameplay

- Each character has one signature ability, fired with Shift on its
  own cooldown:
  - **Wizard — Slow:** bends time for every enemy, the boss and their
    in-flight shots for 3s, while the Wizard keeps moving and firing at
    full speed.
  - **Shiggy — Dash:** the short, i-framed burst dash every character
    shared before this release — now Shiggy's signature alone.
  - **Penguin — Shield:** total damage immunity for 2.5s.
  - **Elf — Volley:** doubled fire rate for 2s.
  - **Wolf — Sprint:** a 1.5s burst of peak movement speed (no
    i-frames, full steering — distinct from Shiggy's dash).
- The other four characters no longer have the dash; each is defined
  by its own ability instead.

### UI

- The HUD dash ring is now an ability ring: a per-character glyph,
  bright while the ability is active, a depleting arc on cooldown.
- Character select shows each character's ability — name and a
  one-line description — below the four stat bars.
- Control hints updated from "Shift dash" to "Shift ability".

### Fixes

- macOS system shortcuts (Cmd-Tab, Mission Control, Spaces) no longer
  steal focus mid-level. The keyboard is grabbed by the game while a
  level is live, so those combos reach the game instead of the OS; the
  grab is released in menus, pause and the level-end screen so the
  player can always tab away. The in-game Cmd-Q quit still works.

## v0.4.0

Adds the second new built-in level for the v1.0.0 cut: **Level 5 —
"The Sunken Archive"**, the largest map shipped to date and the first
with an optional side area.

### Content

- Level 5 "The Sunken Archive": a five-room library-ruin (~55×80) with
  a bookshelf-lined atrium (player spawn, lever 1), a two-spike-row
  crossing chamber (pressure plate past the trap), a vault antechamber
  holding the key and a second lever, a small enclosed reading-room
  vestibule reachable from the antechamber but not required to clear
  the level, and a boss arena with the exit. Three reading-order
  trigger/gate pairs chain the mandatory path: lever → plate → lever
  open the gates atrium → crossing → vault → boss arena. Loads via
  the existing generic glyph dispatch in `levels.py` — no code
  changes.

## v0.3.0

Adds the first new built-in level since v0.1: **Level 4 — "The
Foundry"**, lifting the campaign past the three-room demo line.

### Content

- Level 4 "The Foundry": a four-chamber forge map (~50×70) with a
  bellows-hall entry, a spike-gauntlet pressure-plate puzzle, a key
  vault, and a boss arena. Three reading-order trigger/gate pairs
  chain the chambers: a lever opens the gate from the bellows hall
  into the spike gauntlet; a pressure plate hidden past the southern
  spike row opens the gate into the key vault; a second lever in the
  vault opens the gate into the boss arena. Loads via the existing
  generic glyph dispatch in `levels.py` — no code changes.

## v0.2.15

A maintenance release. No gameplay, tools, or save-file format
changes; existing saves and custom levels load as-is.

### Fixes

- Update flow: in-game **UPDATE** now works on packaged macOS `.app`
  installs that have no system CA bundle (Intel Macs on stock
  Monterey, arm64 machines without homebrew openssl). The previous
  build silently fell back to Python's default verify paths, which
  point at a `cert.pem` that only the python.org installer creates —
  so HTTPS to `api.github.com` failed `CERTIFICATE_VERIFY_FAILED`,
  was swallowed as `OSError`, and the player saw **"Update server
  unreachable - try again later."** on a working network. The build
  now bundles `certifi`'s CA roots via PyInstaller's `--collect-all
  certifi`, and `updater.py` pins its TLS context to
  `certifi.where()` (with a system-default fallback so dev runs on a
  homebrew openssl or Linux distro keep working).

## v0.2.14

A maintenance release. No gameplay, tools, or save-file format
changes; existing saves and custom levels load as-is.

### Fixes

- Level editor: the hover-driven tile palette no longer slides open
  while the level filename is being edited inline. The hover test
  now ignores cursor presence over the drawer rail when
  `editing_name` is true, so typing past the right edge of the field
  does not accidentally pop the palette out from under the cursor.
- Update flow: on the packaged macOS `.app`, a post-update restart
  that can't resolve the bundle path now exits cleanly instead of
  falling through to `os.execv`. The `os.execv` path on a frozen
  darwin build could reproduce B28 ("two windows"); the new
  `SystemExit(0)` branch closes that hole. The user re-launches
  manually in the rare case the bundle path can't be derived (dev
  runs and `/Applications` installs are unaffected).

## v0.2.13

A maintenance release. No gameplay, tools, or save-file format changes;
existing saves and custom levels load as-is.

### Fixes

- Update flow: on the packaged macOS `.app`, clicking **UPDATE** in the
  main menu no longer leaves the old game window open next to the
  freshly launched one. The post-update restart now hands off via
  `/usr/bin/open -n` + `SystemExit(0)` (mirroring the existing
  `/Applications` relocation path in `launcher.py`) instead of
  `os.execv`'ing the bundle's bootloader — only the new instance
  survives. Dev runs (`python main.py` / `python launcher.py`) still
  restart via `os.execv` as before.

## v0.2.12

A level-editor polish release. No gameplay or save-file format
changes; existing saves and custom levels load as-is.

### Tools

- Level editor: the tile palette is now a hover-driven drawer. By
  default only a 44 px rail sits at the right edge — showing a
  thumbnail of the currently-selected tile and a vertical "PALETTE"
  label — so the canvas has the full width to work in. Move the
  cursor over the rail (or click it) and the drawer slides out to
  its full size with the tile grid, category headers, and the
  interactive `<` `>` variant preview added in v0.2.10. Move the
  cursor away and it slides back. The drawer never reflows the
  canvas: it overlays on top, so painting near the right edge
  stays unaffected. Esc / Test / window-focus loss always returns
  to the collapsed state.

## v0.2.11

Maintenance release. No gameplay, tools, or save-file format changes;
existing saves and custom levels load as-is.

### Repo

- Level editor: six source comments described the palette's
  variant-step buttons as `◄ ►`, but the buttons render — by design —
  as ASCII `<` `>` (the bundled pixel font has no arrow glyphs).
  Comments corrected to match the code; no runtime change.

## v0.2.10

A level-editor polish release. No gameplay or save-file format
changes; existing saves and custom levels load as-is.

### Tools

- Level editor: the tile palette is narrower, so the canvas has more
  room to work in. It also gains an interactive preview panel — the
  selected tile is drawn at a large size with `<` `>` buttons that
  step through its variants, so a tile and variant can be previewed
  before being painted. The mouse wheel still cycles variants too.

## v0.2.9

Maintenance release. No gameplay or save-file format changes.

### Repo

- README link points to the correct upstream (`eeco`, not `eecon`).
- `.gitignore` no longer tracks the local `.eeco/` workspace or the
  legacy `ajhahnde/` notes directory.

## v0.2.8

The packaged macOS app now installs itself into `/Applications`. No
save-file format changes; existing saves load as-is.

### App

- On launch, `The Way Out.app` copies itself into `/Applications`
  (replacing any older copy) and relaunches from there, then runs
  normally. This fixes macOS App Translocation: a quarantined copy
  opened from Downloads no longer runs from a random read-only path.
  If `/Applications` needs authentication the standard macOS password
  prompt is shown; if the copy can't be done for any reason the game
  still starts in place. Running an already-installed copy is a no-op.

## v0.2.7

A playable title screen, in the style of an Assassin's Creed loading
screen. No save-file format changes; existing saves load as-is.

### Title screen

- The main menu is now playable: your selected character spawns on
  the title screen and can be moved (WASD/Arrows), dashed (Shift) and
  fired (Space) while the menu buttons stay clickable. The camera does
  not move — the avatar is confined to the window.
- The wandering background figures are purely decorative ghosts: the
  player walks through them, projectiles pass through them, and they
  never attack or react.
- Left mouse no longer fires on the title screen so clicks only
  operate the menu buttons; in-game, left mouse still shoots as
  before.
- Picking a different character in the Characters menu immediately
  updates the avatar shown on the title screen.

## v0.2.6

A small polish release: two missing-glyph fixes in the UI and a
proper macOS Cmd+Q shortcut. No save-file format changes.

### UI

- Main-menu hint bar: replaced `&` and the three `·` separators with
  characters the bundled pixel font actually has glyphs for, so the
  bar now reads `WASD/Arrows move + aim | Space shoot | Shift dash |
  E use` instead of showing `?` boxes.
- Settings: the music level now reads `Music: 25/100` (etc.) — the
  previous `%` rendered as a `?` because the font has no percent
  glyph.

### Input

- Cmd+Q now quits the game instantly from every screen on macOS,
  matching standard system behaviour. Bare `Q` in the editor still
  toggles the paint/pick tool — it just ignores the keystroke when
  the Command key is held.

## v0.2.3

An icon-polish release. No save-file format changes; existing saves
load as-is.

### App

- App icon: the "two" wordmark is now set vertically the way Mandarin
  is written — each glyph upright, stacked top-to-bottom — instead of
  each letter rotated 90° onto its side. Regenerated by
  `scripts/make_icon.py` as the bundled macOS `.icns` and the runtime
  pygame window icon.

## v0.2.2

A polish release: a new app icon plus editor and input fixes. No
save-file format changes; existing saves load as-is.

### App

- New app icon: a typographic "two" wordmark — short for The Way Out —
  set in the game's own font and palette, replacing the wizard-in-a-
  doorway icon. Regenerated by `scripts/make_icon.py` as the bundled
  macOS `.icns` and the runtime pygame window icon.

### Tools

- Level editor: the toolbar **Test** button now launches a test
  session. It previously saved silently but never started the level —
  only the F5 shortcut worked.

### Gameplay

- Level-end input no longer leaks: Enter / Space / R on the win or
  fail screen of an editor-launched test is consumed, so it can't fall
  through into the editor and commit or extend a half-typed level name.

### Docs

- Release history moved from `RELEASE_NOTES.md` into this
  `CHANGELOG.md`; the former is removed.

## v0.2.1

A bug-fix patch. No save-file format changes; existing saves load
as-is.

### Fixes

- Audio: a missing music track is remembered so `play_music`'s
  unchanged-name guard engages, instead of re-statting the filesystem
  and re-fading the bed every frame.
- Levels: boss and enemy contact damage no longer applies during the
  level intro — no hits before the room is live.
- Editor: Esc on a finished editor-launched test is consumed, so it
  returns to the editor canvas instead of bouncing to the main menu.
- Units: a missing or renamed sprite sheet degrades to a visible
  magenta placeholder frame instead of crashing with `IndexError`.

## v0.2.0

A content and polish update. No save-file format changes; v0.1.0 saves
load as-is.

### Gameplay

- Boss roster: each level now picks one of five generals — Mr. Green,
  Mr. Orange, Gen. Frost, The Archer, Mr. Shadow — deterministically
  from the level id, so a given level always fights the same boss
  across restarts. Mechanics are unchanged; identity is conveyed by
  sprite and a subtle colour overlay.
- Boss UI updates: the health-bar label and objective text reflect the
  active general's name.

### UI

- New animated title scene: a slowly scrolling floor, a small crowd of
  idle characters wandering the screen, and a soft vignette — the
  static dust field has been retired for the main menu.
- Update status is now a toast under the title. Result messages
  auto-dismiss after a few seconds; pressing Esc to return to the
  title also clears any stale status.
- Character select animates every row, not just the focused one, with
  staggered idle frames so the list never feels static.
- The mouse cursor is hidden during active gameplay (combat is fully
  keyboard-driven) and visible everywhere else.

### App

- Custom app icon: a wizard standing in a glowing doorway, shipped as
  a macOS `.icns` bundled into the app and as the runtime pygame
  window icon. The icon is regenerated by `scripts/make_icon.py`.

### Internal

- `theme.py` gains a reusable `draw_toast` primitive and a
  `MenuScene` background, so future screens can opt into the same
  ambient look without re-implementing it.

## v0.1.0

Initial release.

### Gameplay

- Top-down pixel-art escape-room shooter with 4-directional aim,
  ranged combat, and a Shift dash with i-frames.
- Five playable characters with distinct HP, speed, damage, and
  fire-rate profiles: Wizard, Penguin, Elf, Shiggy, Wolf.
- Three hand-authored escape rooms with levers, pressure plates,
  gates, spike hazards, and a two-phase boss (Mr. Green).

### Tools

- In-game level editor for the text-based map format.
- Data-driven levels (`assets/levels/`, `manifest.json`) — new rooms
  require no code changes.

### App

- Self-updating macOS build; save data is stored outside the app
  bundle and is preserved across updates.
- Accurate connectivity detection: the updater distinguishes "no
  internet" from "update server unreachable / rate-limited".

### UI

- Shared theme across all screens (single palette and font set).
- Readable status and stat text; animated character-select preview.
