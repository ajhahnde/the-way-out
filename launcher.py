"""Frozen entry-point for the packaged macOS app.

This is the *only* Python that PyInstaller bakes into ``The Way Out.app``.
It never changes after a build. Its whole job:

  1. make sure runnable game code exists in ``~/.the-way-out/app/``
     (pull the newest commit from GitHub, or fall back to the snapshot
     baked into the .app on a first run with no internet),
  2. hand control to that external ``app/main.py`` *inside this same
     frozen Python* so ``import pygame`` resolves from the bundle.

Imports only stdlib + ``updater`` (the bundled bootstrap copy) +
``pygame`` (only for the offline error screen). No new dependencies.
"""
import os
import runpy
import sys
import traceback

import updater   # bundled bootstrap copy — NOT re-implemented here


def _bundle_seed():
    """Folder PyInstaller unpacked the source snapshot into.

    ``--add-data "<seed>:_seed"`` puts it next to the frozen app; in a
    plain ``python launcher.py`` dev run there is no ``_seed`` and
    ``updater.seed_from`` simply returns False (the GitHub path covers
    dev)."""
    base = getattr(sys, "_MEIPASS",
                   os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "_seed")


def _log_crash(exc):
    """Persist a traceback so a failed launch is debuggable later."""
    try:
        updater.ROOT.mkdir(parents=True, exist_ok=True)
        with open(updater.ROOT / "last_error.log", "w") as fh:
            traceback.print_exception(
                type(exc), exc, exc.__traceback__, file=fh)
    except OSError:
        pass


def _error_screen(lines):
    """Tiny pygame window for the one case we can't recover from: very
    first launch with no code and no internet. Uses the game's pixel
    font baked into ``_seed`` so this screen matches the rest of the
    game; only falls back to the default font if the seed isn't
    unpacked. Best-effort; never raises."""
    try:
        import pygame
        pygame.init()
        sw, sh = 720, 360
        # set_icon must run BEFORE set_mode so macOS picks it up for the
        # actual window. Best-effort: the bundled seed may be missing.
        try:
            seed_icon = os.path.join(
                _bundle_seed(), "assets", "icon_1024.png")
            pygame.display.set_icon(pygame.image.load(seed_icon))
        except (pygame.error, FileNotFoundError, OSError):
            pass
        screen = pygame.display.set_mode((sw, sh))
        pygame.display.set_caption("The Way Out")
        # settings.FONT == "assets/gui/font/main_font.otf"; the frozen
        # launcher can't import settings, so reconstruct that path
        # under the bundled seed the same way _bundle_seed() does.
        seed_font = os.path.join(_bundle_seed(), "assets", "gui",
                                 "font", "main_font.otf")
        try:
            font = pygame.font.Font(seed_font, 30)
        except (OSError, pygame.error):
            font = pygame.font.Font(None, 30)  # seed missing → default
        clock = pygame.time.Clock()
        running = True
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                if (e.type == pygame.KEYDOWN
                        and e.key == pygame.K_ESCAPE):
                    running = False
                if (e.type == pygame.KEYDOWN
                        and e.key == pygame.K_q
                        and (e.mod & pygame.KMOD_META)):
                    running = False
            # Hand-synced copies of theme.BG / theme.INK — the frozen
            # launcher runs before the game's own modules are on the
            # path, so it can't import theme.py. Keep these two tuples
            # in sync with theme.py manually.
            screen.fill((18, 18, 24))
            for i, ln in enumerate(lines):
                surf = font.render(ln, True, (214, 216, 226))
                screen.blit(surf, surf.get_rect(
                    center=(sw // 2, 70 + i * 42)))
            pygame.display.flip()
            clock.tick(30)
        pygame.quit()
    except Exception:
        pass


def ensure_code():
    """Guarantee ``app/`` holds a runnable game. Order: try update →
    else recover from a crashed prior update → else seed from the baked
    snapshot → else whatever is already there. Any network/IO failure is
    swallowed: a stale-but-working install is always better than not
    starting."""
    try:
        if updater.should_check():
            loc, rem, available = updater.check()
            if available and rem is not None:
                updater.apply_update(expected_sha=rem)
    except Exception:
        pass                                  # offline/error → fallbacks
    if not updater.has_code():
        updater.recover_from_prev()           # crashed mid-rename → use prev
    if not updater.has_code():
        updater.seed_from(_bundle_seed())     # offline first-run snapshot
    return updater.has_code()


def main():
    if not ensure_code():
        _error_screen([
            "The Way Out",
            "",
            "Couldn't load the game.",
            "Please connect to the internet and open it once.",
            "After that it runs offline.",
            "",
            "(close this window to quit)",
        ])
        return 1

    app = str(updater.app_dir())
    os.chdir(app)                  # CRITICAL: game uses relative asset paths
    sys.path.insert(0, app)        # so app/main.py finds its sibling modules
    # The bootstrap updater has done its job. Drop it so the game's own
    # ``import updater`` loads app/updater.py — that way the in-game
    # "Update" button evolves with the repo instead of being pinned to
    # the frozen bootstrap copy.
    sys.modules.pop("updater", None)
    try:
        runpy.run_path(os.path.join(app, "main.py"), run_name="__main__")
        return 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0
    except BaseException as e:     # last line of defence — log & exit clean
        _log_crash(e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
