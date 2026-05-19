"""Runtime version string. Reads VERSION (sibling text file) once on
import. Bump VERSION in the release commit; updater + bundled seed
both ship the file as-is, so this works in dev and the packaged .app."""
from pathlib import Path


def _read():
    try:
        return (Path(__file__).resolve().parent
                / "VERSION").read_text().strip()
    except OSError:
        return ""


VERSION = _read()
