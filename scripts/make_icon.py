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
sys.path.insert(0, str(REPO))  # run from anywhere: find settings/theme
import settings  # noqa: E402
import theme  # noqa: E402

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

    # Warm glow centred on the canvas — the wordmark sits in the light.
    # Single soft layer, normal alpha blend (NOT additive — stacked ADDs
    # blow out to white).
    glow = _radial_gradient(
        CANVAS, CANVAS // 2, CANVAS // 2,
        inner_color=(255, 200, 110, 255),
        outer_color=(20, 8, 0, 0),
        inner_frac=0.0, outer_frac=0.55, power=1.7,
    )
    canvas.blit(glow, (0, 0))

    # Wordmark: lowercase "two" (short for The Way Out) in the game
    # font, rotated 90° clockwise so it reads top->bottom (t, w, o).
    # Each glyph is rendered, trimmed to its inked pixels (optical
    # centering — not the font's line box), rotated, then stacked with
    # explicit tracking. Separate glyphs + a real gap keep the letters
    # distinct when the icon is shrunk to ~32 px (font-kerned "two"
    # merges into a bar at that size) and match the spaced sketch.
    font = pygame.font.Font(str(REPO / settings.FONT), 600)
    glyphs = []
    for ch_ in "two":
        g = font.render(ch_, True, theme.TITLE_C)
        g = g.subsurface(g.get_bounding_rect()).copy()
        # -90 deg = clockwise in pygame: a glyph's left edge goes to the
        # top, so the row t,w,o stacks top->bottom. 90 deg multiples
        # rotate exactly (no blur).
        glyphs.append(pygame.transform.rotate(g, -90))

    gap = round(0.22 * sum(g.get_height() for g in glyphs) / len(glyphs))
    stack_w = max(g.get_width() for g in glyphs)
    stack_h = sum(g.get_height() for g in glyphs) + gap * (len(glyphs) - 1)
    mark = pygame.Surface((stack_w, stack_h), pygame.SRCALPHA)
    y = 0
    for g in glyphs:
        mark.blit(g, ((stack_w - g.get_width()) // 2, y))
        y += g.get_height() + gap

    # Fit inside the squircle-mask safe area: cap height, and width too
    # so a wide render can't overflow either edge.
    mw, mh = mark.get_size()
    scale = (CANVAS * 0.62) / mh
    if mw * scale > CANVAS * 0.5:
        scale = (CANVAS * 0.5) / mw
    mark = pygame.transform.smoothscale(
        mark, (max(1, round(mw * scale)), max(1, round(mh * scale))))
    center = (CANVAS // 2, CANVAS // 2)

    # Seating halo: a soft dark silhouette behind the cream so it keeps
    # contrast on the bright glow even shrunk to ~32 px. RGBA_MULT by
    # (0,0,0,90) zeros RGB and drops alpha to ~35% in one pass; the
    # 1.04x upscale + smoothscale softens it into a halo.
    halo = mark.copy()
    halo.fill((0, 0, 0, 90), special_flags=pygame.BLEND_RGBA_MULT)
    halo = pygame.transform.smoothscale(
        halo, (round(halo.get_width() * 1.04),
               round(halo.get_height() * 1.04)))
    canvas.blit(halo, halo.get_rect(center=center))
    canvas.blit(mark, mark.get_rect(center=center))

    # Vignette: corners fade to pure black, centre untouched.
    canvas.blit(_vignette(CANVAS), (0, 0))

    # Flatten onto an opaque surface — Apple icons must carry no alpha.
    out = pygame.Surface((CANVAS, CANVAS))
    out.fill((0, 0, 0))
    out.blit(canvas, (0, 0))

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(out, str(OUT_PNG))
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
