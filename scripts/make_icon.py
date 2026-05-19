"""Generate the macOS app icon (1024x1024 PNG + .icns).

Composites the existing wizard and big-door sprites onto a black canvas
with a soft vignette and a warm light pool under the door — the visual
shorthand for "the way out". Pixel-art scaling is nearest-neighbour
(``pygame.transform.scale``), no smoothing.

Run from the repo root:

    .venv/bin/python scripts/make_icon.py

Outputs:
    assets/icon_1024.png   master PNG (used at runtime by set_icon)
    assets/icon.icns       macOS bundle icon (used by PyInstaller --icon)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "assets"
OUT_PNG = ASSETS / "icon_1024.png"
OUT_ICNS = ASSETS / "icon.icns"

CANVAS = 1024
DOOR_SHEET = ASSETS / "tileset" / "interactables" / "BigDoor_D.png"
WIZARD_SHEET = ASSETS / "units" / "wizard" / "D_Idle.png"


def _first_frame(sheet: pygame.Surface) -> pygame.Surface:
    """Slice the first square frame off a horizontal sprite sheet."""
    w, h = sheet.get_size()
    return sheet.subsurface(pygame.Rect(0, 0, h, h)).copy()


def _radial_gradient(
    size: int,
    cx: int, cy: int,
    inner_color: tuple[int, int, int, int],
    outer_color: tuple[int, int, int, int],
    inner_frac: float = 0.0,
    outer_frac: float = 1.0,
    power: float = 1.0,
    seed_size: int = 96,
) -> pygame.Surface:
    """Smooth radial gradient. Built per-pixel on a small seed surface,
    then smoothscaled up — avoids the banding that draw.circle produces
    on an SRCALPHA target (which replaces alpha rather than blending)."""
    seed = pygame.Surface((seed_size, seed_size), pygame.SRCALPHA)
    scx = cx * seed_size / size
    scy = cy * seed_size / size
    max_r = ((max(scx, seed_size - scx)) ** 2
             + (max(scy, seed_size - scy)) ** 2) ** 0.5
    ir, ig, ib, ia = inner_color
    or_, og, ob, oa = outer_color
    for y in range(seed_size):
        for x in range(seed_size):
            r = ((x - scx) ** 2 + (y - scy) ** 2) ** 0.5 / max_r
            if r <= inner_frac:
                t = 0.0
            elif r >= outer_frac:
                t = 1.0
            else:
                t = ((r - inner_frac) / (outer_frac - inner_frac)) ** power
            seed.set_at((x, y), (
                int(ir + (or_ - ir) * t),
                int(ig + (og - ig) * t),
                int(ib + (ob - ib) * t),
                int(ia + (oa - ia) * t),
            ))
    return pygame.transform.smoothscale(seed, (size, size))


def _vignette(size: int) -> pygame.Surface:
    """Black overlay: transparent at centre, opaque near corners."""
    return _radial_gradient(
        size, size // 2, size // 2,
        inner_color=(0, 0, 0, 0),
        outer_color=(0, 0, 0, 235),
        inner_frac=0.30, outer_frac=1.0, power=1.6,
    )


def _integer_scale(surf: pygame.Surface, factor: int) -> pygame.Surface:
    w, h = surf.get_size()
    return pygame.transform.scale(surf, (w * factor, h * factor))


def build_icon() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))  # dummy driver still needs this for convert_alpha

    # Pure-black backdrop ("Schwarz mit Vignette"). The vignette layer
    # at the end darkens corners; the glow layer brightens the centre.
    canvas = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    canvas.fill((0, 0, 0, 255))

    # Warm glow behind the door — single soft layer with normal alpha
    # blending (NOT additive — stacked ADDs blow out to white).
    glow = _radial_gradient(
        CANVAS, CANVAS // 2, 540,
        inner_color=(255, 200, 110, 255),
        outer_color=(20, 8, 0, 0),
        inner_frac=0.0, outer_frac=0.55, power=1.7,
    )
    canvas.blit(glow, (0, 0))

    # Door (36x36 frame x22 = 792 px), rotated 90° so it reads as an
    # upright doorway rather than a top-down floor tile.
    door_sheet = pygame.image.load(str(DOOR_SHEET)).convert_alpha()
    door = _first_frame(door_sheet)
    door = pygame.transform.rotate(door, 90)
    door = _integer_scale(door, 22)
    dw, dh = door.get_size()
    door_x = CANVAS // 2 - dw // 2
    door_y = 90
    canvas.blit(door, (door_x, door_y))

    # Warm floor pool right at the door threshold — small additive
    # accent so the wizard reads as standing in the doorway's light.
    pool = _radial_gradient(
        CANVAS, CANVAS // 2, 920,
        inner_color=(255, 215, 140, 120),
        outer_color=(255, 160, 60, 0),
        inner_frac=0.0, outer_frac=0.25, power=1.4,
    )
    canvas.blit(pool, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # Wizard (32x32 frame x18 = 576 px) in front of the door.
    wiz_sheet = pygame.image.load(str(WIZARD_SHEET)).convert_alpha()
    wiz = _first_frame(wiz_sheet)
    wiz = _integer_scale(wiz, 18)
    ww, wh = wiz.get_size()
    canvas.blit(wiz, (CANVAS // 2 - ww // 2, 940 - wh))

    # Vignette: corners fade to pure black, centre untouched.
    canvas.blit(_vignette(CANVAS), (0, 0))

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(canvas, str(OUT_PNG))
    print(f"wrote {OUT_PNG.relative_to(REPO)}")


def build_icns() -> None:
    """Convert the master PNG to .icns via macOS-native sips + iconutil."""
    if sys.platform != "darwin":
        print("skipping .icns (not macOS)")
        return
    if not shutil.which("sips") or not shutil.which("iconutil"):
        print("skipping .icns (sips/iconutil missing)")
        return

    iconset = ASSETS / "icon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir()

    # Apple's required iconset entries.
    entries = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    for size, name in entries:
        subprocess.run(
            ["sips", "-z", str(size), str(size),
             str(OUT_PNG), "--out", str(iconset / name)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(OUT_ICNS)],
        check=True)
    shutil.rmtree(iconset)
    print(f"wrote {OUT_ICNS.relative_to(REPO)}")


if __name__ == "__main__":
    build_icon()
    build_icns()
