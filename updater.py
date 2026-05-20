"""Self-update engine for The Way Out.

The packaged macOS app is only a thin launcher: the actual game code
lives *outside* the frozen bundle in ``~/.the-way-out/app/`` and is
refreshed straight from GitHub's ``main`` branch. That keeps the
"author pushes, player gets it" workflow without ever rebuilding the
.app.

Pure standard library on purpose — this module is itself part of the
auto-updated payload, so it can evolve, but it must never require a
``pip install`` on the player's machine.

Hard safety rule: this module only ever writes inside ``ROOT`` and
specifically swaps ``app/``. The save game lives at
``~/.the-way-out/save.json`` (a *sibling* of ``app/``) and is never
touched, so updating cannot wipe progress.
"""
import io
import json
import os
import shutil
import socket
import ssl
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = "ajhahnde/the-way-out"
BRANCH = "main"

ROOT = Path.home() / ".the-way-out"          # holds save.json + app/
APP_DIR = ROOT / "app"                        # the live game code
VERSION_FILE = APP_DIR / ".version"           # remote commit sha we ran
LAST_CHECK_FILE = ROOT / ".last_check"        # mtime = last successful check

_API_COMMIT = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"
_ZIP_BASE = f"https://codeload.github.com/{REPO}/zip"
_HEADERS = {"User-Agent": "the-way-out-updater"}   # GitHub API needs a UA


def _ssl_context():
    """TLS context that actually verifies on stock macOS installs.

    The packaged .app ships Python.framework but no CA bundle, so
    ``ssl.create_default_context()`` ends up with an empty trust store
    and every HTTPS call to GitHub fails CERTIFICATE_VERIFY_FAILED —
    which the urlopen callers below swallow as OSError, leaving the
    user looking at "Update server unreachable" on a working network.
    Pin the context to certifi's bundle when it's importable (it is in
    the frozen build via PyInstaller's --collect-all certifi); fall
    back to the platform default so dev runs with a system openssl
    (homebrew, Linux distros) keep working.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return ssl.create_default_context()


_SSL_CTX = _ssl_context()


def app_dir() -> Path:
    return APP_DIR


def has_code() -> bool:
    """True when ``app/`` actually contains a runnable game."""
    return (APP_DIR / "main.py").is_file()


def local_sha():
    """Commit sha we last installed, or None."""
    try:
        return (VERSION_FILE.read_text().strip() or None)
    except OSError:
        return None


def remote_sha(timeout: float = 6):
    """Latest commit sha on the branch, or None if offline/blocked."""
    try:
        req = urllib.request.Request(_API_COMMIT, headers=_HEADERS)
        with urllib.request.urlopen(
                req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.load(resp).get("sha")
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def online(timeout: float = 2) -> bool:
    """True when the machine actually has internet.

    Distinguishes "no network at all" from "GitHub unreachable / API
    rate-limited / slow link" — :func:`remote_sha` returns None for all
    of those, so the caller can't tell which from the sha alone.

    Probes 1.1.1.1:53 (Cloudflare DNS) with a raw TCP connect: no DNS
    lookup, no HTTP, not GitHub, so it stays up even when the GitHub
    API is throttling us. Best-effort; any failure means "offline".
    """
    for host in ("1.1.1.1", "8.8.8.8"):
        try:
            socket.create_connection((host, 53), timeout=timeout).close()
            return True
        except OSError:
            continue
    return False


def check(timeout: float = 6):
    """Return ``(local, remote, update_available)``.

    ``update_available`` is True when there is a reachable remote sha
    that differs from the local one, *or* when there is no local code
    yet (first run). When offline, ``remote`` is None and the result
    is False so the caller just runs whatever is already installed.
    """
    loc = local_sha()
    rem = remote_sha(timeout=timeout)
    if rem is None:
        return loc, None, False
    _mark_checked()
    available = (not has_code()) or (loc != rem)
    return loc, rem, available


def _mark_checked():
    """Record that we just successfully reached GitHub.

    Used by :func:`should_check` to throttle the cold-start network
    call. Best-effort: a write failure simply means the next launch
    will probe the network again.
    """
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
        LAST_CHECK_FILE.touch()
    except OSError:
        pass


def should_check(min_interval_s: float = 86400.0) -> bool:
    """True when a cold-start update probe is worth doing.

    First run (no installed code) always returns True. After that we
    skip the probe until ``min_interval_s`` has passed since the last
    successful one, so a slow/captive network doesn't pause every
    launch by up to the request timeout. The in-game Update action
    calls :func:`check` directly and bypasses this gate.
    """
    if not has_code():
        return True
    try:
        last = LAST_CHECK_FILE.stat().st_mtime
    except OSError:
        return True
    return (time.time() - last) >= min_interval_s


def _download_zip(ref: str, timeout: float) -> bytes:
    req = urllib.request.Request(f"{_ZIP_BASE}/{ref}", headers=_HEADERS)
    with urllib.request.urlopen(
            req, timeout=timeout, context=_SSL_CTX) as resp:
        return resp.read()


def apply_update(expected_sha=None, timeout: float = 90) -> bool:
    """Download the branch zip and atomically replace ``app/``.

    Returns True on success. On *any* failure the existing install is
    left untouched (download/extract happen in a temp area first). The
    previous version is kept as ``app.prev`` for manual rollback.
    """
    # Pin the download to expected_sha so the extracted code matches
    # the sha we write into .version. Without this, ``main`` can advance
    # between the commits API call in ``check()`` and the codeload fetch
    # here, leaving .version one commit behind the actual install.
    ref = expected_sha or f"refs/heads/{BRANCH}"
    try:
        blob = _download_zip(ref, timeout)
    except (urllib.error.URLError, OSError, TimeoutError):
        return False

    ROOT.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="twout-stage-", dir=ROOT))
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            zf.extractall(staging)
        # GitHub wraps everything in a single ``<repo>-<branch>/`` dir.
        roots = [p for p in staging.iterdir() if p.is_dir()]
        if len(roots) != 1 or not (roots[0] / "main.py").is_file():
            return False
        src = roots[0]
        if expected_sha:
            (src / ".version").write_text(expected_sha)

        new_dir = ROOT / "app.new"
        prev_dir = ROOT / "app.prev"
        if new_dir.exists():
            shutil.rmtree(new_dir, ignore_errors=True)
        # Same filesystem (under ROOT) → these renames are atomic.
        os.replace(src, new_dir)
        if prev_dir.exists():
            shutil.rmtree(prev_dir, ignore_errors=True)
        if APP_DIR.exists():
            os.replace(APP_DIR, prev_dir)
        os.replace(new_dir, APP_DIR)
        return True
    except (OSError, zipfile.BadZipFile, ValueError):
        return False
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def recover_from_prev() -> bool:
    """Move ``app.prev`` back into ``app/`` after a crashed update.

    Between the two renames in :func:`apply_update` the live ``app/``
    does not exist. If the process dies in that window, restoring
    ``app.prev`` here keeps the launcher from silently falling back to
    the (older) bundled seed. Returns True when a restore happened.
    """
    if has_code():
        return False
    prev_dir = ROOT / "app.prev"
    if not (prev_dir / "main.py").is_file():
        return False
    try:
        os.replace(prev_dir, APP_DIR)
        return True
    except OSError:
        return False


def seed_from(seed_dir, force: bool = False) -> bool:
    """Copy a bundled source snapshot into ``app/``.

    The launcher uses this so the very first launch works even with no
    internet. A no-op (returns True) if code already exists and
    ``force`` is False.
    """
    seed = Path(seed_dir)
    if not (seed / "main.py").is_file():
        return False
    if has_code() and not force:
        return True
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="twout-seed-", dir=ROOT))
    try:
        dst = tmp / "app"
        shutil.copytree(seed, dst)
        if APP_DIR.exists():
            shutil.rmtree(APP_DIR, ignore_errors=True)
        os.replace(dst, APP_DIR)
        return True
    except OSError:
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
