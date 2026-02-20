"""Maven artifact resolution and download helpers."""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


from chaquopy_stubgen._artifacts import DEFAULT_CACHE_DIR

log = logging.getLogger(__name__)


MAVEN_REPOSITORIES = [
    "https://dl.google.com/dl/android/maven2",  # Google Maven (androidx, com.android, ...)
    "https://repo1.maven.org/maven2",            # Maven Central
]
_DEFAULT_CACHE_DIR = DEFAULT_CACHE_DIR / "maven"


@dataclass(frozen=True)
class MavenCoordinate:
    """Parsed Maven coordinate in the form ``groupId:artifactId:version``."""

    group_id: str
    artifact_id: str
    version: str

    def __str__(self) -> str:
        return f"{self.group_id}:{self.artifact_id}:{self.version}"

    def _artifact_url(self, base: str) -> str:
        group_path = self.group_id.replace(".", "/")
        return f"{base}/{group_path}/{self.artifact_id}/{self.version}/{self.artifact_id}-{self.version}"


def parse_maven_coordinate(s: str) -> MavenCoordinate:
    """
    Parse a Maven coordinate string ``groupId:artifactId:version``.

    Raises ValueError if the string does not match the expected format.

    >>> parse_maven_coordinate("androidx.appcompat:appcompat:1.0.2")
    MavenCoordinate(group_id='androidx.appcompat', artifact_id='appcompat', version='1.0.2')
    >>> parse_maven_coordinate("invalid")
    Traceback (most recent call last):
        ...
    ValueError: Invalid Maven coordinate 'invalid'. Expected format: 'groupId:artifactId:version'.
    """
    parts = s.split(":")
    if len(parts) != 3 or not all(parts):
        raise ValueError(
            f"Invalid Maven coordinate {s!r}. "
            "Expected format: 'groupId:artifactId:version'."
        )
    return MavenCoordinate(group_id=parts[0], artifact_id=parts[1], version=parts[2])


def is_maven_coordinate(s: str) -> bool:
    """
    Return True if *s* looks like a Maven coordinate (``groupId:artifactId:version``).

    >>> is_maven_coordinate("androidx.appcompat:appcompat:1.0.2")
    True
    >>> is_maven_coordinate("libs/mylib.jar")
    False
    >>> is_maven_coordinate("a:b")
    False
    """
    parts = s.split(":")
    return len(parts) == 3 and all(parts)


def resolve_maven_artifact(
    coord: MavenCoordinate,
    cache_dir: Path | None = None,
    repositories: list[str] | None = None,
) -> Path:
    """
    Resolve a Maven artifact to a local file path, downloading it if necessary.

    Tries ``.aar`` first, then ``.jar``, against each repository in *repositories*
    in order (default: Google Maven, then Maven Central).  Downloads are cached
    under *cache_dir* (defaults to ``~/.cache/chaquopy-stubgen/maven``).

    Returns the path to the cached file.
    Raises FileNotFoundError if the artifact cannot be found in any repository.
    """
    if cache_dir is None:
        cache_dir = _DEFAULT_CACHE_DIR
    if repositories is None:
        repositories = MAVEN_REPOSITORIES

    for ext in (".aar", ".jar"):
        filename = f"{coord.artifact_id}-{coord.version}{ext}"
        local_path = (
            cache_dir
            / coord.group_id
            / coord.artifact_id
            / coord.version
            / filename
        )
        if local_path.exists():
            log.info(f"Using cached artifact: {local_path}")
            return local_path

        for base in repositories:
            url = coord._artifact_url(base) + ext
            try:
                log.info(f"Downloading {url}...")
                with urllib.request.urlopen(url) as response:
                    data: bytes = response.read()
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    log.debug(f"Not found at {url}")
                    continue
                raise

            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)
            log.info(f"Saved to {local_path}")
            return local_path

    raise FileNotFoundError(
        f"Maven artifact '{coord}' not found in any repository "
        f"(tried .aar and .jar in: {repositories})"
    )
