"""Synthesised placeholder SFX for the v1.0.0 cut.

Pure stdlib — no numpy, no scipy, no third-party audio libs — so this
script runs anywhere the game's .venv can run. Each sound is a short
chiptune-style waveform written as a 16-bit mono PCM WAV into
``assets/audio/sfx/``. The audio.py loader looks up sounds by name
(`audio.play("shoot")` → `assets/audio/sfx/shoot.wav`); the names below
match every existing call site plus the ones wired in v0.9.0.

The SFX are intentionally chiptune-thin — the meme-flavoured pass that
the design notes call out is a post-v1.0 polish slot; these are the
"every action has feedback" baseline.

Re-run via ``./.venv/bin/python scripts/gen_sfx.py``. Idempotent: each
call rewrites the WAVs to disk so a tuning tweak ships by running the
script and committing the changed assets.
"""

import math
import os
import random
import struct
import wave

SAMPLE_RATE = 44100
SFX_DIR = os.path.join("assets", "audio", "sfx")

# Equal-temperament pitches in Hz. Just the notes I reach for in the
# arpeggios below — adding more is one line of math.
PITCH = {
    "A3": 220.0, "C4": 261.63, "D4": 293.66, "E4": 329.63,
    "F4": 349.23, "G4": 392.0, "A4": 440.0, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "G5": 783.99,
    "A5": 880.0, "C6": 1046.5, "E6": 1318.51, "G6": 1567.98,
}


def _frames(seconds):
    return int(SAMPLE_RATE * seconds)


def _envelope(n, attack=0.01, release=0.05, sustain=1.0):
    """Linear AR envelope; sustain is held between attack and release."""
    a = max(1, int(SAMPLE_RATE * attack))
    r = max(1, int(SAMPLE_RATE * release))
    out = [0.0] * n
    for i in range(n):
        if i < a:
            out[i] = (i / a) * sustain
        elif i > n - r:
            out[i] = max(0.0, ((n - i) / r)) * sustain
        else:
            out[i] = sustain
    return out


def _sine(freq, n, phase=0.0):
    w = 2 * math.pi * freq / SAMPLE_RATE
    return [math.sin(w * i + phase) for i in range(n)]


def _square(freq, n, duty=0.5):
    period = SAMPLE_RATE / freq
    return [1.0 if (i % period) / period < duty else -1.0 for i in range(n)]


def _triangle(freq, n):
    period = SAMPLE_RATE / freq
    out = []
    for i in range(n):
        t = (i % period) / period
        out.append(4 * abs(t - 0.5) - 1)
    return out


def _noise(n, rng):
    return [rng.uniform(-1.0, 1.0) for _ in range(n)]


def _sweep(f0, f1, n, wave_fn=_square):
    """Linear pitch sweep from f0 to f1 over n samples."""
    out = [0.0] * n
    phase = 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * (i / max(1, n - 1))
        phase += 2 * math.pi * f / SAMPLE_RATE
        if wave_fn is _square:
            out[i] = 1.0 if math.sin(phase) > 0 else -1.0
        elif wave_fn is _triangle:
            out[i] = (2 / math.pi) * math.asin(math.sin(phase))
        else:
            out[i] = math.sin(phase)
    return out


def _mix(*tracks):
    """Sum equal-length tracks, clip to [-1, 1]."""
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    peak = max((abs(v) for v in out), default=1.0)
    if peak > 1.0:
        out = [v / peak for v in out]
    return out


def _concat(*chunks):
    out = []
    for c in chunks:
        out.extend(c)
    return out


def _apply(samples, env):
    n = min(len(samples), len(env))
    return [samples[i] * env[i] for i in range(n)]


def _write(name, samples, gain=0.6):
    """Write a 16-bit mono WAV at the project's sample rate."""
    path = os.path.join(SFX_DIR, name + ".wav")
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        peak = max((abs(v) for v in samples), default=1.0)
        norm = gain / max(0.01, peak)
        frames = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(v * norm * 32767))))
            for v in samples)
        f.writeframes(frames)


# --- Individual SFX ---------------------------------------------------

def sfx_shoot(rng):
    """Short downward laser chirp + a click body."""
    n = _frames(0.10)
    body = _sweep(900, 280, n, _square)
    env = _envelope(n, 0.005, 0.06)
    return _apply(body, env)


def sfx_hit(rng):
    """Generic taken-hit thud: low square + noise burst."""
    n = _frames(0.09)
    thud = _square(160, n)
    grit = _noise(n, rng)
    sig = [0.7 * thud[i] + 0.4 * grit[i] for i in range(n)]
    env = _envelope(n, 0.003, 0.07)
    return _apply(sig, env)


def sfx_boss_hit(rng):
    """Heavier hit: lower pitch, longer tail."""
    n = _frames(0.18)
    thud = _square(110, n)
    grit = _noise(n, rng)
    sig = [0.8 * thud[i] + 0.5 * grit[i] for i in range(n)]
    env = _envelope(n, 0.005, 0.14)
    return _apply(sig, env)


def sfx_enemy_death(rng):
    """Pitched-down noise burst — the air going out."""
    n = _frames(0.22)
    sweep = _sweep(620, 110, n, _square)
    grit = _noise(n, rng)
    sig = [0.6 * sweep[i] + 0.4 * grit[i] for i in range(n)]
    env = _envelope(n, 0.005, 0.18)
    return _apply(sig, env)


def sfx_boss_death(rng):
    """Big descending sweep + grit, double-layered for weight."""
    n = _frames(0.85)
    s1 = _sweep(520, 60, n, _square)
    s2 = _sweep(310, 40, n, _triangle)
    grit = _noise(n, rng)
    sig = [0.6 * s1[i] + 0.5 * s2[i] + 0.35 * grit[i] for i in range(n)]
    env = _envelope(n, 0.01, 0.6)
    return _apply(sig, env)


def sfx_player_death(rng):
    """Sad descending three-note motif (E4 → C4 → A3)."""
    parts = []
    for note in ("E4", "C4", "A3"):
        n = _frames(0.18)
        sig = _triangle(PITCH[note], n)
        env = _envelope(n, 0.01, 0.12)
        parts.append(_apply(sig, env))
    return _concat(*parts)


def sfx_level_complete(rng):
    """Major arpeggio C5 E5 G5 C6 — the win chime."""
    parts = []
    for note in ("C5", "E5", "G5", "C6"):
        n = _frames(0.14)
        sig = _triangle(PITCH[note], n)
        env = _envelope(n, 0.005, 0.10)
        parts.append(_apply(sig, env))
    n = _frames(0.36)
    tail = _triangle(PITCH["C6"], n)
    parts.append(_apply(tail, _envelope(n, 0.005, 0.30)))
    return _concat(*parts)


def sfx_slow(rng):
    """Wizard slow — descending vibrato chord, time-warp feel."""
    n = _frames(0.55)
    a = _sweep(PITCH["G4"], PITCH["C4"], n, _triangle)
    b = _sweep(PITCH["E5"], PITCH["A4"], n, _triangle)
    sig = [0.7 * a[i] + 0.5 * b[i] for i in range(n)]
    env = _envelope(n, 0.04, 0.30)
    return _apply(sig, env)


def sfx_shield(rng):
    """Penguin shield — rising glass shimmer."""
    n = _frames(0.32)
    shimmer = _sweep(PITCH["A4"], PITCH["E6"], n, _triangle)
    chime = _triangle(PITCH["C5"], n)
    sig = [0.6 * shimmer[i] + 0.4 * chime[i] for i in range(n)]
    env = _envelope(n, 0.02, 0.22)
    return _apply(sig, env)


def sfx_volley(rng):
    """Elf volley — rapid double-tap chirp."""
    parts = []
    for f in (880, 1320):
        n = _frames(0.07)
        sig = _sweep(f, f * 1.6, n, _square)
        env = _envelope(n, 0.005, 0.05)
        parts.append(_apply(sig, env))
        parts.append([0.0] * _frames(0.02))
    return _concat(*parts)


def sfx_dash(rng):
    """Shiggy dash — quick whoosh."""
    n = _frames(0.18)
    sig = _sweep(180, 90, n, _triangle)
    grit = _noise(n, rng)
    mixed = [0.6 * sig[i] + 0.35 * grit[i] for i in range(n)]
    env = _envelope(n, 0.005, 0.14)
    return _apply(mixed, env)


def sfx_sprint(rng):
    """Wolf sprint — short rising whoosh that sustains."""
    n = _frames(0.35)
    sig = _sweep(140, 320, n, _triangle)
    grit = _noise(n, rng)
    mixed = [0.55 * sig[i] + 0.3 * grit[i] for i in range(n)]
    env = _envelope(n, 0.04, 0.20)
    return _apply(mixed, env)


def sfx_lever_click(rng):
    """Lever pull — two-click clack (engage + settle)."""
    parts = []
    for f in (640, 480):
        n = _frames(0.04)
        sig = _square(f, n)
        env = _envelope(n, 0.001, 0.03)
        parts.append(_apply(sig, env))
        parts.append([0.0] * _frames(0.03))
    return _concat(*parts)


def sfx_plate_press(rng):
    """Pressure plate — low compressed clunk."""
    n = _frames(0.12)
    sig = _square(110, n)
    grit = _noise(n, rng)
    mixed = [0.6 * sig[i] + 0.3 * grit[i] for i in range(n)]
    env = _envelope(n, 0.002, 0.10)
    return _apply(mixed, env)


def sfx_gate_open(rng):
    """Gate retracting — slow rising chord."""
    n = _frames(0.45)
    a = _sweep(PITCH["C4"], PITCH["G4"], n, _triangle)
    b = _sweep(PITCH["E4"], PITCH["B4"], n, _triangle)
    grit = _noise(_frames(0.45), rng)
    sig = [0.55 * a[i] + 0.4 * b[i] + 0.2 * grit[i] for i in range(n)]
    env = _envelope(n, 0.04, 0.30)
    return _apply(sig, env)


def sfx_key_pickup(rng):
    """Key pickup — bright two-tone chime (C5 → G5)."""
    parts = []
    for note in ("C5", "G5"):
        n = _frames(0.10)
        sig = _triangle(PITCH[note], n)
        env = _envelope(n, 0.003, 0.08)
        parts.append(_apply(sig, env))
    return _concat(*parts)


def sfx_menu_select(rng):
    """Menu navigation blip — single thin tick."""
    n = _frames(0.05)
    sig = _square(880, n)
    env = _envelope(n, 0.001, 0.04)
    return _apply(sig, env)


def sfx_menu_confirm(rng):
    """Menu confirm — short rising blip (G5 → C6)."""
    parts = []
    for note in ("G5", "C6"):
        n = _frames(0.06)
        sig = _square(PITCH[note], n)
        env = _envelope(n, 0.002, 0.05)
        parts.append(_apply(sig, env))
    return _concat(*parts)


SFX = {
    "shoot": (sfx_shoot, 0.45),
    "hit": (sfx_hit, 0.55),
    "boss_hit": (sfx_boss_hit, 0.60),
    "enemy_death": (sfx_enemy_death, 0.55),
    "boss_death": (sfx_boss_death, 0.70),
    "player_death": (sfx_player_death, 0.50),
    "level_complete": (sfx_level_complete, 0.55),
    "slow": (sfx_slow, 0.55),
    "shield": (sfx_shield, 0.55),
    "volley": (sfx_volley, 0.55),
    "dash": (sfx_dash, 0.55),
    "sprint": (sfx_sprint, 0.55),
    "lever_click": (sfx_lever_click, 0.50),
    "plate_press": (sfx_plate_press, 0.55),
    "gate_open": (sfx_gate_open, 0.55),
    "key_pickup": (sfx_key_pickup, 0.55),
    "menu_select": (sfx_menu_select, 0.40),
    "menu_confirm": (sfx_menu_confirm, 0.45),
}


def main():
    os.makedirs(SFX_DIR, exist_ok=True)
    rng = random.Random(0xCAFE)   # deterministic — rerun gives same bytes
    for name, (fn, gain) in SFX.items():
        samples = fn(rng)
        _write(name, samples, gain=gain)
        path = os.path.join(SFX_DIR, name + ".wav")
        print(f"  wrote {path}  ({len(samples)} samples, "
              f"{len(samples) / SAMPLE_RATE:.2f}s)")


if __name__ == "__main__":
    main()
