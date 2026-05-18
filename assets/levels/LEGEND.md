# Level file legend

Levels are plain-text grids. Each cell is one tile (`64 px`). The map
is padded with wall on the right, so rows don't have to be the same
length — but keeping them aligned makes editing sane.

## Where levels live

There are two kinds of level and you never have to touch code to add
one:

* **Built-in** — `.txt` files in `assets/levels/`, listed in
  `assets/levels/manifest.json`. To add one: drop the file in, add an
  entry to the manifest (`id`, `file`, `title`, `tagline`, and the
  optional `music` track name — see Audio). It appears in the level
  menu on next launch. No Python edits.
* **Custom** — anything saved by the in-game **Editor** lands in
  `~/.the-way-out/custom_levels/<name>.txt` and is auto-discovered (no
  manifest entry needed). These show a `CUSTOM` pill in the level menu.

`level_catalog.py` is the single source of truth that merges both;
`tiles.py` (`REGISTRY`) is the single source of truth for the tile
vocabulary below — the editor palette and the level loader both read
it, so this table, the registry and the editor never drift apart.

## In-game Level Editor

Main menu → **Editor**. Build a level visually and play-test it
instantly.

| Action               | Bind                                  |
|----------------------|---------------------------------------|
| Place selected tile  | Left mouse (hold to drag-paint)       |
| Clear to floor       | Right mouse (hold to drag-erase)      |
| Box fill / box erase | Shift + drag left / right mouse       |
| Eyedropper           | `Q` or **Pick**, then click a cell    |
| Wall the outer ring  | **Border** button                     |
| Select a tile        | Click it in the right-hand palette    |
| Cycle prop variant   | Mouse wheel                           |
| Pan the canvas       | WASD / Arrow keys                     |
| Grow / shrink grid   | `+W/-W` `+H/-H` buttons in the toolbar|
| Rename file          | Click the FILE box, type, Enter       |
| Save                 | Ctrl+S or the **Save** button         |
| Save & play-test     | F5 or the **Test** button             |
| Back to menu         | Esc                                   |

`P` (player start) and `X` (exit) are singletons — placing a new one
removes the old. Save warns (but never blocks) if there's no `P`/`X`
or if trigger/gate counts look mismatched, so you can iterate freely.
Test launches with the character last picked in **Characters** and
returns you to the editor when the run ends.

## Row formats

There are two ways to write a row; you can mix formats between rows in
the same file.

1. **Dense** (legacy) — one character per cell, no spaces:

   ```
   WWWWWWWW
   W..P...W
   WWWWWWWW
   ```

   Quick to write, but **cannot use variants** (every cell is the
   default look of its object).

2. **Spaced / tokenised** — cells separated by spaces, so a cell can
   carry a *variant number*:

   ```
   W  W  W  W  W  W
   W  .  T3 .  A1 W
   W  W  W  W  W  W
   ```

   A token is a letter optionally followed by digits. `T3` = torch
   variant 3, `A1` = table variant 1, `M40` = misc decor 40. A bare
   letter (`T`) or any dense cell uses variant 1. Out-of-range numbers
   clamp back to 1.

A row counts as tokenised the moment it contains a space; otherwise
it's read dense. Recommended: use the spaced format for new levels
(see `level_2.txt` for a full example).

## Core gameplay tiles

These drive the escape-room logic and use the game's own built-in
artwork (not the tileset). No tileset variants — but `L`/`Y`/`G` take
an optional pairing digit (see Trigger ↔ gate pairing below).

| Char | Meaning            | Notes                                                        |
|------|--------------------|--------------------------------------------------------------|
| `W`  | Wall               | Solid. Drawn from the tileset floor/wall art (see below).    |
| `.`  | Floor              | Empty walkable cell. Any unrecognised char is also floor.    |
| `P`  | Player start       | Where the chosen character spawns. Use exactly one.          |
| `X`  | Exit / way out     | Opens once the boss is dead (if any) and the key is held.    |
| `B`  | Boss (Mr. Green)   | Spawns lazily when the player first enters the boss room.    |
| `N`  | Enemy (chaser)     | Roaming threat; chases the player, contact damage. Spawns at once. Does **not** gate the exit. |
| `S`  | Spikes             | Timed hazard (safe → warning → deadly loop).                 |
| `L`  | Lever              | Pull with **E**. Pairs by order, or `L2`…`L9` to a gate.     |
| `Y`  | Pressure plate     | Stand on ~0.25 s. Pairs by order, or `Y2`…`Y9` to a gate.    |
| `G`  | Gate               | Solid until its trigger fires. Adjacent `G` = one panel.     |
| `K`  | Key                | Walk over to pick up; required before the exit opens.        |

Trigger ↔ gate pairing has two modes you can mix freely in one level:

* **By reading order (default).** Levers and pressure plates form one
  combined list in top-to-bottom, left-to-right order; the *i*-th
  un-numbered trigger opens the *i*-th un-numbered gate panel. Author
  a mixed sequence (plate, lever, plate, …) and rely on order alone —
  this is the original behaviour and needs no digits.
* **Explicit pair id.** Give a trigger and its gate the same trailing
  digit — `L2` opens the panel containing `G2`, `Y3` ↔ `G3`, etc.
  (1–9). Numbered pairs are matched by their number regardless of
  order and never interfere with the order-based pairing of the
  un-numbered ones, so complex rooms stay unambiguous. Put the digit
  on at least one cell of a multi-cell gate panel.

A panel is the set of 4-connected `G` cells; gates that touch are one
panel. In the **editor**, the mouse wheel on `L`/`Y`/`G` sets this
number: leave it at 1 to pair by order, or set 2–9 to pair a trigger
with the gate of the same number (the editor can't emit “1”, which is
fine — 1 just means “by order”).

## Tileset objects

Real tileset artwork. **Solid** objects block movement (you can't walk
through them); the rest are pure decoration drawn under the player.
The variant range is the count of images in that folder under
`assets/tileset/`.

| Char | Object             | Solid | Variants | Source folder                       |
|------|--------------------|-------|----------|-------------------------------------|
| `T`  | Torch              | no    | 1–8      | `static_objects/torches`            |
| `C`  | Chair              | no    | 1–14     | `static_objects/chairs`             |
| `A`  | Table              | yes   | 1–8      | `static_objects/tables`             |
| `E`  | Bookshelf          | yes   | 1–12     | `static_objects/bookshelf`          |
| `D`  | Bookshelf decor    | no    | 1–40     | `static_objects/bookshelf_decor`    |
| `O`  | Box / crate        | yes   | 1–16     | `static_objects/boxes`              |
| `R`  | Rubble / blockage  | yes   | 1–8      | `static_objects/blockage`           |
| `M`  | Misc clutter       | no    | 1–44     | `static_objects/other`              |
| `Z`  | Door (prop)        | yes   | 1–4      | `static_objects/doors`              |
| `J`  | Trapdoor           | no    | 1–6      | `static_objects/trapdoors`          |
| `H`  | Chest              | yes   | 1–2      | `interactables/Chest{n}_S.png`      |
| `F`  | Fire               | no    | 1        | `interactables/Fire1.png`           |

A missing or unknown asset is drawn as a loud magenta block so it's
easy to spot. An unknown *letter* is just treated as floor.

## Controls (for level testing)

| Action            | Bind                          |
|-------------------|-------------------------------|
| Move & aim        | WASD / Arrow keys             |
| Shoot             | Space or **left mouse**       |
| Aim               | The way you're facing (4-dir) |
| Dash              | Shift (~0.18 s, i-frames)     |
| Use lever         | E within reach                |
| Pause             | Esc (in level)                |
| Retry (after end) | R                             |
| Back to menu      | Esc (after end) / Enter / Space |

## Floor / wall look

The baked floor and wall come from two tiles in
`assets/tileset/tiles/`, set near the top of `tileset.py`:

```python
FLOOR_TILE = "Tile_42"
WALL_TILE  = "Tile_03"
```

To restyle the dungeon, browse `assets/tileset/tiles/` (or the full
sheet `assets/tileset/Tileset.png` / `Palette.png`), pick a tile, and
put its file name here. If the name can't be loaded the level quietly
falls back to the original procedural stone, so a wrong value never
breaks anything.

**Per level:** a built-in `manifest.json` entry may override the look
just for that level with `"floor_tile"` / `"wall_tile"` (same tile
names, e.g. `"floor_tile": "Tile_18"`). Either key is optional and
falls back to the global default above; an unknown name still
degrades to procedural stone. Custom (editor-built) levels always use
the global default. Note: the **editor canvas preview** also always
draws the global default floor/wall — a per-level override only shows
when you actually play the level, not while editing it.

## Audio

Sound is **entirely optional and clone-safe** — the game runs silent
if no audio files are present. Just drop files in; no code changes.

Layout (the only convention):

```
assets/audio/sfx/<name>.wav      (or .ogg)
assets/audio/music/<name>.ogg    (or .wav / .mp3)
```

Sound effects the game already triggers (create the matching file to
hear it):

| File name (`assets/audio/sfx/…`) | Plays when                         |
|----------------------------------|------------------------------------|
| `shoot`                          | the player fires a projectile      |
| `hit`                            | any unit takes damage              |
| `dash`                           | the player dashes (Shift)          |
| `boss_death`                     | Mr. Green is defeated              |
| `player_death`                   | the player dies (run failed)       |
| `level_complete`                 | the player reaches the exit        |

Adding a new SFX is just a new file plus one `audio.play("name")` call
at the trigger site.

**Background music** is per level. In a `manifest.json` entry add
`"music": "<name>"` to loop `assets/audio/music/<name>.*` for that
level (omit it for silence). Custom (editor-built) levels look for
`assets/audio/music/default.*`. Music stops on win/lose; a level
reload/retry keeps the same track playing without a restart.

Audio files are read **once per session** (like the tileset), so add
them before launching. The **Settings → Sound** toggle mutes/unmutes
everything and is remembered across launches (stored in
`~/.the-way-out/save.json`).

## Minimal example

```
W W W W W W
W P . T3 . W
W . A1 . . W
W . . . . X
W W W W W W
```

Player spawns top-left, a torch (variant 3) and a solid table
(variant 1) decorate the room, exit on the right.
