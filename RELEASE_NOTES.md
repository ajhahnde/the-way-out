# Release Notes

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
