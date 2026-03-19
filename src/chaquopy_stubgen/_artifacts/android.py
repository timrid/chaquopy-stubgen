"""Android platform JAR resolution and download helpers."""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from pathlib import Path


from chaquopy_stubgen._artifacts import DEFAULT_CACHE_DIR

log = logging.getLogger(__name__)

_ANDROID_PLATFORMS_BASE = (
    "https://raw.githubusercontent.com/Sable/android-platforms/master"
)
_DEFAULT_CACHE_DIR = DEFAULT_CACHE_DIR / "android"
_ANDROID_SHORTHAND_RE = re.compile(r"^android-(\d+)$", re.IGNORECASE)


def is_android_shorthand(s: str) -> bool:
    """
    Return True if *s* is an Android platform shorthand like ``android-35``.

    >>> is_android_shorthand("android-35")
    True
    >>> is_android_shorthand("android-36")
    True
    >>> is_android_shorthand("androidx.appcompat:appcompat:1.0.2")
    False
    >>> is_android_shorthand("mylib.jar")
    False
    """
    return bool(_ANDROID_SHORTHAND_RE.match(s))


def resolve_android_jar(api_level: str, cache_dir: Path | None = None) -> Path:
    """
    Resolve an Android platform JAR to a local file path, downloading it if necessary.

    *api_level* may be a bare number (``"35"``) or the full shorthand (``"android-35"``).
    Downloads are cached under *cache_dir*
    (defaults to ``~/.cache/chaquopy-stubgen/android``).

    Returns the path to the cached ``android.jar``.
    Raises FileNotFoundError if the requested API level is not available.
    """
    if cache_dir is None:
        cache_dir = _DEFAULT_CACHE_DIR

    # Normalise "android-35" → "35"
    api_level = api_level.lower().removeprefix("android-")

    local_path = cache_dir / f"android-{api_level}" / "android.jar"
    if local_path.exists():
        log.info(f"Using cached Android JAR: {local_path}")
        return local_path

    url = f"{_ANDROID_PLATFORMS_BASE}/android-{api_level}/android.jar"
    try:
        log.info(f"Downloading {url}...")
        with urllib.request.urlopen(url) as response:
            data: bytes = response.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FileNotFoundError(
                f"Android API level {api_level!r} not found at {url}."
            ) from e
        raise

    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(data)
    log.info(f"Saved to {local_path}")
    return local_path
