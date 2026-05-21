"""Headless pygame for the whole suite.

Force the dummy SDL drivers before ``pygame`` is imported anywhere else
in the suite, then ``pygame.init()`` once so sprite constructors that
build Surfaces work without a display server. The CI runner has no
monitor and no audio device.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Tests import game modules by their bare name (``import units`` etc.) —
# the repo root holds them, so make it importable when pytest is invoked
# from anywhere.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pygame  # noqa: E402

pygame.init()
# Create a tiny offscreen Surface so any ``convert_alpha`` call inside
# sprite asset loaders has a valid video context.
pygame.display.set_mode((1, 1))
