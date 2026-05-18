"""Tiny progress + preferences save file.

One JSON document at ``~/.the-way-out/save.json``::

    {
      "completed": ["level_1", ...],     # beaten level ids
      "times":     {"level_1": 42.7},    # best clear time, seconds
      "settings":  {"sound": true}       # persisted prefs
    }

Survives reclones, keeps no per-run state. The level menu reads
``completed``/``times`` for the ✓ marks and best-time line,
``LevelManager`` writes both when a run finishes, and the Settings
menu reads/writes ``settings``.

Every public function goes through one ``_load``/``_write`` pair so a
write of one section never clobbers another, and any I/O or shape
error degrades to "no save data" / "save skipped" — a weird FS never
crashes the game.

Legacy migration: older saves stored integer indices (``0/1/2``) in
``completed`` before the catalog refactor; those map to
``level_1/2/3`` on read so a returning player keeps their checkmarks.
"""

import json
import os

from settings import SAVE_DIR, SAVE_FILE

# How a legacy int index maps to a string id. Indices 0..2 were the
# only ones ever shipped, so a flat lookup is enough.
_LEGACY_INDEX_TO_ID = {0: "level_1", 1: "level_2", 2: "level_3"}


def _load():
    """The whole save document as a dict. Empty dict on any error or
    if the file holds something other than an object."""
    try:
        with open(SAVE_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(data):
    """Rewrite the whole file atomically. Silent no-op on FS errors so
    a write-protected home never crashes the player out of a victory
    screen. The tmp+rename keeps the previous file intact if the
    process is killed mid-write — without it, a partial JSON reads
    back as ``{}`` and silently wipes all progress."""
    try:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SAVE_FILE.with_name(SAVE_FILE.name + '.tmp')
        with open(tmp, 'w') as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, SAVE_FILE)
    except OSError as e:
        print(f"the-way-out: could not save progress ({e})")


# --- completion ---------------------------------------------------------

def _parse_completed(data):
    """Apply legacy int-index migration to ``data['completed']`` and
    return a set of string level ids."""
    out = set()
    for item in data.get('completed', []):
        if isinstance(item, str):
            out.add(item)
        elif isinstance(item, bool):
            continue  # bool is an int subclass — never a valid index
        elif isinstance(item, int) and item in _LEGACY_INDEX_TO_ID:
            out.add(_LEGACY_INDEX_TO_ID[item])
    return out


def load_completed():
    """Return a ``set`` of completed level ids (strings). Empty set on
    any error or missing file."""
    return _parse_completed(_load())


def mark_complete(level_id):
    """Add ``level_id`` to the completed set and rewrite the file,
    preserving ``times``/``settings``."""
    if not isinstance(level_id, str):
        return  # guard against accidental int passthrough
    data = _load()
    completed = _parse_completed(data)
    if level_id in completed:
        return
    completed.add(level_id)
    data['completed'] = sorted(completed)
    _write(data)


# --- best times ---------------------------------------------------------

def _parse_times(data):
    """Return a dict of valid level id → float seconds from
    ``data['times']``, dropping anything malformed so a hand-edited
    file can't crash the menu."""
    out = {}
    raw = data.get('times', {})
    if isinstance(raw, dict):
        for k, v in raw.items():
            if (isinstance(k, str) and isinstance(v, (int, float))
                    and not isinstance(v, bool) and v > 0):
                out[k] = float(v)
    return out


def load_times():
    """Map of level id → best clear time in seconds. Skips anything
    malformed so a hand-edited file can't crash the menu."""
    return _parse_times(_load())


def record_time(level_id, seconds):
    """Store ``seconds`` as the best time for ``level_id``, but only if
    it beats (or sets) the existing record."""
    if not isinstance(level_id, str) or seconds <= 0:
        return
    data = _load()
    times = _parse_times(data)
    best = times.get(level_id)
    if best is not None and best <= seconds:
        return
    times[level_id] = float(seconds)
    data['times'] = times
    _write(data)


# --- preferences --------------------------------------------------------

def load_settings():
    """Persisted preference dict (e.g. ``{"sound": True}``). Empty dict
    if unset or malformed."""
    raw = _load().get('settings', {})
    return raw if isinstance(raw, dict) else {}


def set_setting(key, value):
    """Set one preference key, preserving the rest of the document."""
    data = _load()
    settings = data.get('settings')
    if not isinstance(settings, dict):
        settings = {}
    settings[key] = value
    data['settings'] = settings
    _write(data)
