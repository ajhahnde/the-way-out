"""Sound effects + background music.

Clone-safe and entirely optional, the same way the tileset is: the
mixer is initialised **lazily** on the first ``play``/``play_music``,
every lookup degrades to a silent no-op when there is no audio device,
no ``assets/audio`` tree or just a single missing file (mirrors the
``tileset.tile`` try/except → None pattern), and importing this module
touches nothing — so the headless smoke tests keep working.

Asset layout — drop files in, no code change needed:

    assets/audio/sfx/<name>.wav      # or .ogg
    assets/audio/music/<name>.ogg    # or .wav / .mp3

``play("shoot")`` looks up ``assets/audio/sfx/shoot.wav``; a level's
manifest ``"music"`` value is just such a ``<name>`` under music/.
Symmetry with ``tileset``: callers pass *names*, not paths, so the
audio asset convention lives only here. The names the game already
triggers are listed in ``assets/levels/LEGEND.md``.
"""

import os

import pygame

# Flipped by the Settings menu (persisted via save.py). Read live by
# every play call, so toggling it silences playback immediately.
enabled = True

# Music level (0.0..1.0). Independent of ``enabled``: muting flips
# enabled, the volume slider is the bed level when sound is on.
# Reapplied to ``pygame.mixer.music`` on every track change so a switch
# never resets it back to 1.0.
music_volume = 1.0

_SFX_DIR = os.path.join("assets", "audio", "sfx")
_MUSIC_DIR = os.path.join("assets", "audio", "music")
_SFX_EXTS = (".wav", ".ogg")
_MUSIC_EXTS = (".ogg", ".wav", ".mp3")

# One knob for every music transition (track switch, stop, mute). ~700
# ms reads as musical without dragging. ``pygame.mixer.music`` is a
# single stream, so there is no true crossfade — we fade the old track
# out and fade the new one in (the simple, fine-here option from the
# Style.md notes). Reused by stop_music so muting fades too, not clicks.
MUSIC_FADE_MS = 700

_mixer_ok = None          # None = not tried yet, then True / False
_sounds = {}              # name -> Sound | None  (None = file absent)
_current_music = None     # name of the looping track, or None


def _ensure_mixer():
    """Init the mixer once. Stays False forever if there is no audio
    device, which turns everything here into a no-op."""
    global _mixer_ok
    if _mixer_ok is None:
        try:
            pygame.mixer.init()
            _mixer_ok = True
        except pygame.error:
            _mixer_ok = False
    return _mixer_ok


def _find(directory, name, exts):
    for ext in exts:
        path = os.path.join(directory, name + ext)
        if os.path.isfile(path):
            return path
    return None


def play(name):
    """Fire-and-forget one-shot SFX. Silent when disabled, when there
    is no device, or when ``assets/audio/sfx/<name>.*`` is missing."""
    if not enabled or not _ensure_mixer():
        return
    if name not in _sounds:
        path = _find(_SFX_DIR, name, _SFX_EXTS)
        try:
            _sounds[name] = pygame.mixer.Sound(path) if path else None
        except pygame.error:
            _sounds[name] = None
    snd = _sounds[name]
    if snd is not None:
        snd.play()


def play_music(name):
    """Loop ``assets/audio/music/<name>.*`` as background music.

    ``name is None`` (the level declares no track) stops the music.
    Re-requesting the track that is already playing is a no-op, so a
    level reload / retry doesn't restart the loop."""
    global _current_music
    if name is None:
        stop_music()
        return
    if not enabled or not _ensure_mixer():
        return
    if name == _current_music:
        return
    path = _find(_MUSIC_DIR, name, _MUSIC_EXTS)
    if path is None:
        stop_music()
        # Remember the request even though the file is absent: main.py
        # calls play_music every frame, and without this _current_music
        # stays None so the unchanged-name guard above never engages —
        # a missing track would re-stat the FS and re-fade every frame.
        _current_music = name
        return
    try:
        # Fade the outgoing track, then bring the new one up. Single
        # stream → not a true crossfade; the incoming fade_ms is what
        # kills the hard cut on a start↔menu↔game switch.
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(MUSIC_FADE_MS)
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(music_volume)
        pygame.mixer.music.play(-1, fade_ms=MUSIC_FADE_MS)
        _current_music = name
    except pygame.error:
        _current_music = None


def stop_music():
    global _current_music
    _current_music = None
    # Only touch the mixer if it actually came up — never spin it up
    # just to stop silence (keeps cold paths side-effect-free).
    if _mixer_ok:
        try:
            # Fade rather than stop() so a mute / leaving a level goes
            # quiet smoothly instead of clicking.
            pygame.mixer.music.fadeout(MUSIC_FADE_MS)
        except pygame.error:
            pass


def set_enabled(flag):
    """Settings hook. Muting also kills the music so the world goes
    quiet at once; SFX are short, they just stop being requested."""
    global enabled
    enabled = bool(flag)
    if not enabled:
        stop_music()


def set_music_volume(level):
    """Settings hook for the bed volume (0.0..1.0). Applied live so a
    slider tweak audibly changes the current track without waiting for
    the next track switch."""
    global music_volume
    music_volume = max(0.0, min(1.0, float(level)))
    if _mixer_ok:
        try:
            pygame.mixer.music.set_volume(music_volume)
        except pygame.error:
            pass
