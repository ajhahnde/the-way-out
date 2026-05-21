import os
import subprocess
import sys
import threading

import pygame

import audio
import level_catalog
from editor import LevelEditor
from levels import LevelManager
from loading_screen import LoadingScreen
from menu import CharacterMenu, LevelMenu, MainMenu, PauseMenu, SettingsMenu
from settings import FPS, HEIGHT, WIDTH

# Setup & Initalisation
pygame.init()
# set_icon must happen BEFORE set_mode for the icon to take effect on
# the actual macOS window (not just the Dock).
try:
    pygame.display.set_icon(
        pygame.image.load(os.path.join("assets", "icon_1024.png")))
except (pygame.error, FileNotFoundError, OSError):
    pass
# Always boot fullscreen at the monitor's own resolution — there is no
# in-game resolution picker. settings.WIDTH/HEIGHT is only the fallback
# if the desktop size can't be read.
_desktop = pygame.display.get_desktop_sizes()
SCREEN_W, SCREEN_H = (_desktop[0] if _desktop and _desktop[0][0] > 0
                      else (WIDTH, HEIGHT))
screen = pygame.display.set_mode(
    (SCREEN_W, SCREEN_H),
    pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.SCALED)
pygame.display.set_caption("The Way Out")
clock = pygame.time.Clock()

main_menu = MainMenu(SCREEN_W, SCREEN_H)
settings_menu = SettingsMenu(SCREEN_W, SCREEN_H)
level_menu = LevelMenu(SCREEN_W, SCREEN_H)
character_menu = CharacterMenu(SCREEN_W, SCREEN_H)
pause_menu = PauseMenu(SCREEN_W, SCREEN_H)
level_manager = LevelManager(SCREEN_W, SCREEN_H)
editor = LevelEditor(SCREEN_W, SCREEN_H)

# Apply the persisted sound + music-volume preferences before any
# level can start. Volume goes through audio.set_music_volume so the
# value is stored even though the mixer is still cold (it'll re-apply
# on the first play_music).
audio.set_enabled(settings_menu.sound_on)
audio.set_music_volume(settings_menu.music_vol)

# Background-music bed per screen. The start screen gets its own track;
# every submenu (and the editor) shares a lighter "menu" bed; gameplay
# music is owned by levels.py (the level's manifest "music"), so "game"
# is intentionally absent here. "paused" is absent too — the level's
# track keeps playing under the overlay. audio.play_music no-ops when
# the name is unchanged, so submenu↔submenu navigation never re-fades
# the bed, and missing track files just stay silent.
_BGM_FOR_STATE = {
    "menu": "title",
    "updating": "title",
    "settings": "menu",
    "char_select": "menu",
    "lvls": "menu",
    "loading": "menu",
    "editor": "menu",
}

# Game state machine. ``paused`` is a frozen-world overlay; it preserves
# every bit of level_manager state so Resume picks up mid-frame.
# ``return_state`` remembers where to go when a game/run ends — normally
# "lvls" (level menu), but "editor" when the level was launched via the
# editor's Test button so the user lands back in the canvas.
game_state = "menu"
return_state = "lvls"
current_character = "c_wiz"

# Loading screen is shown only on first entry into a level (level menu
# or editor Test); R-retry and pause-restart deliberately bypass it via
# their direct level_manager.load_level() calls. The pending_* fields
# stash the (level_id, return_to) pair until the screen finishes.
loading_screen = None
pending_level_id = None
pending_return_to = "lvls"

# Threaded update flow. The worker writes into update_state; the main
# loop polls each frame and renders an animated status. phase is what
# the worker is doing right now ("checking" / "updating"); result is set
# exactly once when the worker is done.
update_state = {"phase": None, "result": None}
update_anim_t = 0.0
_UPDATE_PHASE_TEXT = {
    "checking": "Checking for updates",
    "updating": "Updating",
}
_UPDATE_RESULT_TEXT = {
    "uptodate": "Already up to date.",
    "offline": "No internet - try again later.",
    "unreachable": "Update server unreachable - try again later.",
    "failed": "Update failed - try again later.",
    "error": "Update error - try again later.",
}


def _run_update():
    """Worker thread: drive check + apply_update without blocking the
    event loop. Dict writes are GIL-atomic, which is enough for the
    one-writer / one-reader hand-off here."""
    try:
        import updater
        update_state["phase"] = "checking"
        _loc, rem, avail = updater.check()
        if rem is None:
            # rem is None for "no net" AND "GitHub down / rate-limited /
            # slow". Probe real connectivity so we don't tell a user with
            # working internet that they have none.
            update_state["result"] = (
                "offline" if not updater.online() else "unreachable")
            return
        if not avail:
            update_state["result"] = "uptodate"
            return
        update_state["phase"] = "updating"
        if updater.apply_update(expected_sha=rem):
            update_state["result"] = "done"
        else:
            update_state["result"] = "failed"
    except Exception:
        update_state["result"] = "error"


def _start_level(level_id, return_to="lvls"):
    """Push to the loading screen for ``level_id``; the actual load
    happens when the screen finishes (see ``_finish_loading``).
    ``return_to`` is what we'll switch to when the level ends."""
    global game_state, loading_screen, pending_level_id, pending_return_to
    entry = level_catalog.find(level_id)
    if entry is None:
        # Unknown id — route to wherever this launch came from, mirroring
        # the failure branch _finish_loading uses below.
        if return_to == "editor":
            editor.reset_pointer_state()
            game_state = "editor"
        else:
            _to_level_menu()
        return
    loading_screen = LoadingScreen(
        SCREEN_W, SCREEN_H, entry, current_character)
    pending_level_id = level_id
    pending_return_to = return_to
    game_state = "loading"


def _finish_loading():
    """Run the deferred ``load_level`` and hand off to the game state.
    Bad/empty/missing level files route back to the launch origin —
    same B17/B19/B20 "editor Test returns to editor" contract."""
    global game_state, return_state, loading_screen, pending_level_id
    level_id = pending_level_id
    return_to = pending_return_to
    loading_screen = None
    pending_level_id = None
    if not level_manager.load_level(level_id, current_character):
        if return_to == "editor":
            editor.reset_pointer_state()
            game_state = "editor"
        else:
            _to_level_menu()
        return
    game_state = "game"
    return_state = return_to


def _to_level_menu():
    """Bail to the level select — always refreshes so a freshly beaten
    level lights up immediately and any new custom level appears."""
    global game_state
    level_menu.refresh()
    game_state = "lvls"


def _leave_game():
    """End the run and route back to whatever opened the level."""
    global game_state
    if return_state == "editor":
        editor.reset_pointer_state()
        game_state = "editor"
    else:
        _to_level_menu()


if __name__ == "__main__":
    running = True
    while running:
        # Clamp dt so a hitch (focus loss, level load, the update HTTP
        # call, an OS stall) can't teleport the player or fast-forward
        # timers. Cap at ~3 frames; below that the sim stays frame-fair.
        dt = min(clock.tick(FPS) / 1000.0, 3.0 / FPS)

        # Events -----------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Cmd+Q (macOS): quit immediately from any state. Handled
            # here before per-state delegation so the editor's bare-Q
            # tool toggle (editor.py) can't consume it on the way out.
            if (event.type == pygame.KEYDOWN
                    and event.key == pygame.K_q
                    and (event.mod & pygame.KMOD_META)):
                running = False
                continue

            # Losing focus while fullscreen (Cmd-Tab, Mission Control,
            # a notification) makes SDL freeze key state: get_pressed()
            # keeps reporting the last-held key, so the player would run
            # on forever. Auto-pause live gameplay; the user resumes
            # from the pause menu with a clean input state.
            if event.type in (pygame.WINDOWFOCUSLOST,
                              pygame.WINDOWMINIMIZED):
                if (game_state == "game"
                        and not (level_manager.completed
                                 or level_manager.failed)):
                    game_state = "paused"
                # Same SDL freeze hits the editor: a held mouse button
                # can get stuck down, so a mid-Shift-drag would later
                # commit a stray box-fill. Drop the editor's transient
                # pointer state.
                elif game_state == "editor":
                    editor.reset_pointer_state()

            # Esc is shared by every menu / overlay state — handle it
            # here so the routing stays in one place. ``editor``
            # swallows its own Esc via handle_input so the user can quit
            # while typing a filename without nuking the session.
            if (event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE):
                if game_state in ("lvls", "settings", "char_select"):
                    # Returning to the title screen — drop any stale
                    # update toast so it doesn't reappear long after the
                    # user has moved on.
                    main_menu.clear_status()
                    game_state = "menu"
                elif game_state == "loading":
                    # Cancel the pending level launch and bail back to
                    # the origin (level menu, or editor if the editor's
                    # Test button kicked this off).
                    loading_screen = None
                    pending_level_id = None
                    if pending_return_to == "editor":
                        editor.reset_pointer_state()
                        game_state = "editor"
                    else:
                        _to_level_menu()
                elif game_state == "paused":
                    game_state = "game"
                elif game_state == "game":
                    if level_manager.completed or level_manager.failed:
                        _leave_game()
                        # Esc is consumed here. Without this, when the
                        # level was launched from the editor's Test
                        # button (return_state == "editor")
                        # _leave_game() switches to "editor" and the
                        # *same* Esc then falls through to
                        # editor.handle_input below, which reads it as
                        # "back" and bounces the user past the editor to
                        # the main menu instead of the editor canvas.
                        continue
                    else:
                        game_state = "paused"

            # In a finished level: R retries, Enter/Space bails out.
            if (game_state == "game"
                    and (level_manager.completed
                         or level_manager.failed)
                    and event.type == pygame.KEYDOWN):
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    _leave_game()
                    # Same reasoning as the Esc-finished branch above:
                    # consume the key so it can't also drive
                    # editor.handle_input on a return_state == "editor"
                    # session (Enter would commit a half-typed level
                    # name, R would append 'r' to it).
                    continue
                elif event.key == pygame.K_r:
                    if not level_manager.load_level(
                            level_manager.level_id, current_character):
                        _leave_game()
                        continue

            # Main menu
            if game_state == "menu":
                action = main_menu.handle_input(event)
                if action == "lvls":
                    main_menu.clear_status()
                    _to_level_menu()
                elif action == "editor":
                    main_menu.clear_status()
                    editor.reset_pointer_state()
                    game_state = "editor"
                elif action == "settings":
                    main_menu.clear_status()
                    game_state = "settings"
                elif action == "chars":
                    main_menu.clear_status()
                    game_state = "char_select"
                elif action == "update":
                    # Hand the work off to a thread so the event loop
                    # can keep pumping (no macOS beachball) and animate
                    # the status. The main loop polls update_state each
                    # frame.
                    update_state["phase"] = "checking"
                    update_state["result"] = None
                    update_anim_t = 0.0
                    main_menu.clear_status()
                    threading.Thread(
                        target=_run_update, daemon=True).start()
                    game_state = "updating"
                elif action == "quit":
                    running = False

            # Editor — Esc returns to menu; Test (F5 or button)
            # requests a play session that lands back here when it ends.
            elif game_state == "editor":
                action = editor.handle_input(event)
                if action == "back":
                    game_state = "menu"
                elif action == "test":
                    level_menu.refresh()  # so the new custom shows later
                    _start_level(editor.test_level_id,
                                 return_to="editor")
                    editor.request_test = False

            # Settings
            elif game_state == "settings":
                action = settings_menu.handle_input(event)
                if action == "back":
                    game_state = "menu"

            # Charakter select
            elif game_state == "char_select":
                action = character_menu.handle_input(event)
                if action:
                    current_character = action
                    main_menu.set_character(current_character)
                    game_state = "menu"

            # Levels select — action is the chosen level id (catalog).
            elif game_state == "lvls":
                action = level_menu.handle_input(event)
                if action:
                    _start_level(action)

            # Loading screen — Enter / Space / Esc / click skip ahead.
            # The screen also auto-advances on its own timer in the draw
            # block.
            elif game_state == "loading":
                if loading_screen is not None:
                    loading_screen.handle_input(event)

            # Pause overlay
            elif game_state == "paused":
                action = pause_menu.handle_input(event)
                if action == "resume":
                    game_state = "game"
                elif action == "restart":
                    if level_manager.load_level(
                            level_manager.level_id, current_character):
                        game_state = "game"
                    else:
                        _leave_game()
                elif action == "quit":
                    _leave_game()

        # BGM follows the state machine. Game/paused are deliberately
        # absent: levels.py owns the in-level track via the manifest,
        # and pause should not swap the bed (the level's music keeps
        # playing under the overlay). audio.play_music guards same-name
        # calls, so this is a no-op when the screen didn't change.
        _bgm = _BGM_FOR_STATE.get(game_state)
        if _bgm is not None:
            audio.play_music(_bgm)

        # Mouse cursor: hidden during live gameplay (combat is keyboard
        # + 4-way facing — no aim cursor); visible everywhere else,
        # including the keyboard-driven level-end screen so the player
        # can still see the cursor land in pause/menu/editor cleanly.
        in_active_game = (game_state == "game"
                          and not level_manager.completed
                          and not level_manager.failed)
        pygame.mouse.set_visible(not in_active_game)

        # Keyboard grab while a level is live: SDL routes macOS system
        # shortcuts (Cmd-Tab, Mission Control, Spaces) to the game
        # instead of the OS, so they can't yank focus mid-fight.
        # Released in menus, pause and the level-end screen so the
        # player can always tab away; the game's own Cmd-Q handler
        # still fires (the combo reaches the app, which quits cleanly).
        pygame.event.set_keyboard_grab(in_active_game)

        # Auto-dismiss the main-menu status toast once its TTL elapses
        # so a stale "Already up to date." doesn't sit on screen
        # forever.
        if (main_menu.status_until is not None
                and pygame.time.get_ticks() / 1000.0
                > main_menu.status_until):
            main_menu.clear_status()

        # Draw & Update ----------------------------------------------
        if game_state == "menu":
            main_menu.update(dt)
            main_menu.draw(screen)
        elif game_state == "updating":
            update_anim_t += dt
            result = update_state["result"]
            main_menu.update(dt)
            if result == "done":
                main_menu.set_status("Updated - restarting...",
                                     ttl=None)
                main_menu.draw(screen)
                pygame.display.flip()
                pygame.time.delay(900)
                pygame.quit()
                # On a PyInstaller --windowed macOS bundle, os.execv
                # re-execs the bootloader from inside its Python child
                # while the parent bootloader keeps its NSApplication
                # alive — net result: two windows. `open -n` +
                # SystemExit hands off cleanly via LaunchServices so
                # only the new instance survives. Mirrors
                # launcher._relocate_to_applications().
                bundle = None
                if (getattr(sys, "frozen", False)
                        and sys.platform == "darwin"):
                    contents_macos = os.path.dirname(
                        os.path.realpath(sys.executable))
                    candidate = os.path.dirname(
                        os.path.dirname(contents_macos))
                    if (candidate.endswith(".app")
                            and os.path.isdir(candidate)):
                        bundle = candidate
                if bundle is not None:
                    subprocess.Popen(["/usr/bin/open", "-n", bundle])
                    raise SystemExit(0)
                if (getattr(sys, "frozen", False)
                        and sys.platform == "darwin"):
                    # Bundle path unresolvable on a frozen darwin build
                    # — os.execv here would reproduce B28 (two windows).
                    # Exit cleanly; the user re-launches manually.
                    raise SystemExit(0)
                if getattr(sys, "frozen", False):
                    os.execv(sys.executable, [sys.executable])
                else:
                    os.execv(sys.executable,
                             [sys.executable, os.path.abspath(__file__)])
            elif result is not None:
                main_menu.set_status(_UPDATE_RESULT_TEXT.get(
                    result, "Update failed - try again later."))
                game_state = "menu"
                main_menu.draw(screen)
            else:
                phase = update_state["phase"] or "checking"
                dots = "." * (1 + int(update_anim_t * 2) % 3)
                main_menu.set_status(
                    f"{_UPDATE_PHASE_TEXT.get(phase, 'Updating')}{dots}",
                    ttl=None)
                main_menu.draw(screen)
        elif game_state == "settings":
            settings_menu.draw(screen)
        elif game_state == "char_select":
            character_menu.draw(screen, current_character)
        elif game_state == "lvls":
            level_menu.draw(screen)
        elif game_state == "loading":
            if loading_screen is not None:
                loading_screen.update(dt)
                loading_screen.draw(screen)
                if loading_screen.done:
                    # Finalise the deferred load; next frame draws the
                    # level.
                    _finish_loading()
        elif game_state == "editor":
            editor.update(dt)
            editor.draw(screen)
        elif game_state == "game":
            level_manager.update(dt)
            level_manager.draw(screen)
        elif game_state == "paused":
            # Render the frozen world, then the pause overlay on top.
            level_manager.draw(screen)
            pause_menu.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()
