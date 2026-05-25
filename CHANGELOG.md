<div align="center">

<h1>Changelog</h1>

<p>
    <a href="README.md"><b>README</b></a> ·
    <a href="VERSIONING.md"><b>Versioning</b></a> ·
    <b>Changelog</b>
  </p>

</div>

---

## v1.0.5

Visual identity update. Adds a new responsive project logo in the
Orbitron font, supporting both light and dark modes via a standard
`<picture>` element in the README. Ships with a Swift script to
reproducibly regenerate the assets. No gameplay, save-file, or
build-tooling changes.

### Project

- **Responsive Logo.** The README now features a high-fidelity
  Orbitron logo that automatically switches between a black version
  (light mode) and a white version (dark mode).
- **`scripts/render_logo.swift`** — new Swift script using `AppKit` to
  render the project title into pixel-perfect PNG assets. Ensures the
  visual identity can be regenerated or modified without external
  design tools.
- **README Header Update.** Replaced the `<h1>` title with the new
  responsive logo block.

## v1.0.4

Formal versioning policy at the repository root, wired into the
tracked-doc nav-bar between README and Changelog. No gameplay,
save-file, build-tooling, or updater-protocol changes.

### Project

- **`VERSIONING.md`** — formal versioning policy at the repository
  root. Adapts SemVer 2.0.0 for a game with a save file: **MAJOR** =
  save-format incompatibility or in-game updater protocol break;
  **MINOR** = new content (level, character, mechanic) with
  forward-migrated saves; **PATCH** = bug fix / balance / perf with no
  save-touch. Defines the single supported stream (Latest Stable; no
  Maintenance tier), the forward-only save-migration policy with the
  unknown-schema refuse-to-corrupt guarantee, the yank procedure (the
  in-game updater MUST revert to the previous stable within 24 hours
  of a yank), the 30-day pre-MAJOR announcement window, and the
  TLS-only updater + SHA256-verified artefacts that constitute the
  game's security surface.

## v1.0.3

Visual harmonisation slice of the cross-project fingerprint pass.
Brings the-way-out's tracked-doc layout in line with FlashOS — the
README and CHANGELOG now ship a centred HTML title block (page title +
doc nav-bar), a `---` divider before the prose, and a bottom
Prev/Next navigation, identical in shape to FlashOS's per-page
template. No gameplay, save-file, or build-tooling changes.

### Project

- **README header restructure.** Title, tagline, badge row, and
  doc-nav bar now sit inside a centred `<div align="center">` block,
  followed by `---` divider, then the content. Same layout
  FlashOS uses on each of its tracked pages.
- **CHANGELOG nav header.** This file now opens with a matching
  centred title block (`Changelog` H1 + README · Changelog nav-bar).
- **Bottom Prev/Next navigation** on README (`Next: Changelog →`) and
  this file (`← Prev: README · Back to start (README) ↺`), modelled
  on the per-doc footer in FlashOS.

## v1.0.2

Cross-project fingerprint pass. Harmonises the README surface with its
sibling repos (eeco, FlashOS) so the three portfolio projects read as
one body of work. No gameplay, save-file, or build-tooling changes —
existing saves and custom levels load as-is.

### Project

- **README badge row** — adopts the canonical 5-badge fingerprint
  modelled on FlashOS: CI · Version · License · Python · target. Same
  ordering and same `shields.io` colour vocabulary the other two repos
  now share. The Coverage badge is deliberately omitted — codecov is
  not wired into the-way-out yet; it will join the row when coverage
  reporting lands as a separate slice.
- **`## See also` section** — new section at the foot of the README
  cross-links [FlashOS](https://github.com/ajhahnde/FlashOS) and
  [eeco](https://github.com/ajhahnde/eeco). Mirrors the matching
  section both sibling repos added in the same fingerprint pass.
- **Stale version line removed.** The standalone `**Version:** v1.0.1`
  line below the title is superseded by the new badge row; the badge
  is now the single source of the displayed version. Reduces
  maintenance to one location.

## v1.0.1

Repo-hygiene release. No gameplay or save-file changes; existing saves
and custom levels load as-is. Brings the project's tooling in line with
its sibling repos (eeco, FlashOS) so it can be forked, built and
contributed to without the operator in the loop.

### Project

- **LICENSE** — Apache 2.0. The repo had no license until now, which
  meant the source was legally all-rights-reserved and nobody could
  fork it. Matches the licence both sibling repos already use.
- **`pyproject.toml`** — pins the runtime (`pygame==2.6.1`), the build
  toolchain (`pyinstaller==6.20.0`, `certifi==2026.5.20`) and the dev
  tools (`ruff==0.15.14`, `pytest==9.0.3`) so a fresh clone resolves to
  the same versions that produced the v1.0.0 .app. Carries the project's
  Ruff config (E/F/I/UP/B, 79-col, py312) — `.ruff_cache/` existed in
  the tree but the config was missing, so contributors couldn't format
  identically.
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — two jobs on
  every push and PR. `check` (ubuntu): `ruff check`, `pytest`, and a
  headless `import main` smoke under the dummy SDL drivers. `build`
  (macos): runs `build_mac.sh` and uploads
  `dist/TheWayOut-mac.zip` as a workflow artifact.
- **Test suite** (`tests/`, 26 tests) — first ever. Covers the level
  parser helpers (`_split_cells` / `_cell_variant` / `_pair_id`), the
  `PressurePlate` charge/trip lifecycle, `Lever.use` single-shot, and
  the `Character` attack + ability cooldown bookkeeping. Headless via a
  conftest that wires the dummy SDL drivers before `pygame.init()`.

### Fixed

- `main.py` now wraps the game loop in `if __name__ == "__main__":`,
  so `import main` is safe in tests and CI. Without this the loop ran
  at module import and the smoke test would have hung forever.
- README's version line said `v0.2.2` (stale from v1.0.0); now `v1.0.1`.

## v1.0.0

The first real release. Bundles the v0.3.0 → v0.10.0 cuts into one
banner: two new built-in levels, a per-character signature ability for
each playable, a full editor-as-UGC loop (Load picker + theme picker +
riddle/interactable palette), a game-feel pass (hit-pause + particles
+ fades), 18 new sound effects across every gameplay and menu event,
and an inter-level loading screen. No save-file format changes;
existing saves and custom levels load as-is.

### Content

- Two new built-in levels lift the campaign from three rooms to five.
  - **Level 4 "The Foundry"** — a four-chamber forge map: bellows
    hall, spike-gauntlet pressure plate, key vault, boss arena.
    Three reading-order trigger/gate pairs chain the chambers.
  - **Level 5 "The Sunken Archive"** — a five-room library ruin
    with a bookshelf-lined atrium, a two-spike-row crossing, a
    vault antechamber, an optional reading-room side area, and a
    boss arena. The campaign's first off-path room.

### Gameplay

- Each playable character now has one signature active ability on
  its own cooldown, fired with **Shift**:
  - **Wizard — Slow:** time bends to 0.35× for every enemy, the
    boss and their in-flight shots for 3s. The Wizard moves and
    fires at full speed.
  - **Shiggy — Dash:** the short, i-framed burst dash that used to
    be universal, now Shiggy's alone.
  - **Penguin — Shield:** total damage immunity for 2.5s.
  - **Elf — Volley:** doubled fire rate for 2s.
  - **Wolf — Sprint:** a 1.5s burst of peak movement speed with no
    i-frames — distinct from Shiggy's short dash.
- The four other characters no longer have the dash; each is defined
  by its own ability instead.
- Brief hit-pause on impactful events (player hit, boss hit, boss
  death, player death) so every meaningful strike reads.

### UI

- The HUD dash ring is now an ability ring: a per-character glyph,
  bright while the ability is active, a depleting arc on cooldown.
- Character select shows each character's ability — name and a
  one-line description — below the four stat bars.
- Particle bursts on hits, deaths and ability activations. Player
  hits are red, regular hits are white, boss death sprays gold with
  a white core, and each character's signature ability blooms in
  its own colour (Wizard violet, Penguin ice blue, Elf leaf green,
  Shiggy warm dust, Wolf white).
- Levels fade in on start and fade out on completion / death.
- New inter-level loading screen shows the level title, tagline,
  your character, and the control hints. Auto-advances after a few
  seconds or press Enter / Space / left-click to skip; Esc cancels
  back to the level menu (or the editor, if launched from Test).
  Retries (R) and pause-restart bypass it.

### Audio

- 18 new sound effects across the board: player and enemy hits,
  enemy and boss death, the boss's own hit, all five signature
  abilities (Wizard slow, Penguin shield, Elf volley, Shiggy dash,
  Wolf sprint), shoot, level complete, player death, lever click,
  gate open, pressure plate, key pickup, and a menu confirmation
  beep. The Settings **Sound** toggle silences both music and
  effects.

### Editor

- New **Load** button reopens any custom map you saved — click a
  row to load it back onto the canvas and keep editing.
- New **Theme** button picks one of five floor/wall presets —
  **Keep**, **Foundry**, **Cellar**, **Archive**, **Frost** — each
  shown with tile swatches so you see the look before choosing.
  The chosen theme is saved alongside the map and the level renders
  with it everywhere. Maps saved before v0.7.0 keep the original
  look.
- The riddle/interactable palette exposes every interactable
  (spikes, levers, pressure plates, gates, keys) with scroll-wheel
  pair-id selection so chained puzzles can be authored cleanly.

### Input

- macOS system shortcuts (Cmd-Tab, Mission Control, Spaces) no
  longer steal focus mid-level. The keyboard is grabbed by the
  game while a level is live and released in menus, pause and the
  level-end screen. The in-game Cmd-Q quit still works.

### Tools

- New `scripts/gen_sfx.py` deterministically (re)generates all 18
  SFX WAV files using only stdlib `wave` + `math`, so a tuning
  tweak ships by running the script and committing the changed
  assets. Output lives under `assets/audio/sfx/`.

## v0.10.0

Adds an inter-level loading screen between the level menu and play —
one focused beat showing the level title, tagline, your character, and
the controls before the room becomes interactive.

### UI

- New loading screen between the level menu and play. Shows the
  level's title and tagline, an idle frame of your selected character,
  and a control hint bar. Auto-advances after a few seconds, or press
  Enter / Space / left-click to skip. Esc cancels back to the level
  menu (or the editor, if launched from Test).
- Retries are snappy: pressing R after a death, or Restart from the
  pause menu, reloads the room directly without the loading screen.
- The previous in-level title card that overlaid the live world is
  gone — the loading screen now carries the title surface, and the
  fade-in covers the visual handoff into the room. Contact damage is
  still suspended during the fade so the player can't be hit before
  they can react.

## v0.9.0

Hits, abilities, doors and pickups now have sound. Adds 18
synthesised chiptune-style sound effects covering every gameplay
event and every menu confirmation, plus the missing call sites for
the level's interactables.

### Audio

- New sound effects across the board: player and enemy hits, enemy
  and boss death, the boss's own hit, all five character signature
  abilities (Wizard slow, Penguin shield, Elf volley, Shiggy dash,
  Wolf sprint), shoot, level complete and player death.
- Levers, gates, pressure plates and the key now make sound when you
  use them.
- Menu confirmations beep when you click a button. The Settings
  **Sound** toggle silences both music and effects.

### Tools

- New `scripts/gen_sfx.py` deterministically (re)generates all 18 SFX
  WAV files using only stdlib `wave` + `math`, so a tuning tweak ships
  by running the script and committing the changed assets. Output
  lives under `assets/audio/sfx/`.

## v0.8.0

Combat now reads — every hit registers. Adds game-feel polish across
the level: brief hit-pause on impactful events, particle bursts on
hits / deaths / abilities, and a fade between level start and end.

### Gameplay

- Brief hit-pause on impactful events: the screen freezes for a few
  frames when the player takes damage, when the boss is hit, when the
  boss dies, and when the player dies. The pause is short enough to
  read as a snap, not a hang, and the camera + transition keep moving
  through it.

### UI

- Particle bursts on hits, kills, ability activations, and boss death.
  Player hits are red, regular hits are white, boss death sprays gold
  with a white core, and each character's signature ability blooms in
  its own colour (Wizard violet, Penguin ice blue, Elf leaf green,
  Shiggy warm dust, Wolf white).
- Levels fade in on start and fade out on completion / death-to-retry
  so transitions read as a deliberate cut.

## v0.7.0

Lets you give each custom map its own **visual theme** in the level
editor — until now every player-built map used the same floor and wall
tiles.

### Editor

- New **Theme** button in the editor toolbar. It opens a picker with
  five floor/wall presets — **Keep**, **Foundry**, **Cellar**,
  **Archive**, **Frost** — each shown with tile swatches so you see the
  look before choosing. The button itself shows the current theme.
- The chosen theme is saved alongside the map and the level renders
  with it, in the editor's Test run and in the level menu. Press Esc or
  click outside to dismiss the picker.
- Maps saved before this release keep the original look.

## v0.6.0

Lets the level editor **reopen a custom map you saved**, closing the
loop on the editor as a community-UGC feature — until now a saved map
could be played but never edited again.

### Editor

- New **Load** button in the editor toolbar. It opens a picker listing
  every custom map you have saved; click one to load it onto the canvas
  and keep editing. Press Esc or click outside to dismiss.
- The picker scrolls (mouse wheel) when you have more saved maps than
  fit on screen, and shows a hint when you have none yet.

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

---

[← Prev: Versioning](VERSIONING.md) · [Back to start (README) ↺](README.md)
