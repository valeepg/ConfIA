"""Downloads with a local cache and content provenance.

Extraction is only reproducible if every run records which bytes it read, so
each download reports the SHA-256 of the file that is actually on disk.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .config import USER_AGENT

CHUNK_SIZE = 1 << 20


@dataclass(frozen=True)
class Download:
    path: Path
    url: str
    sha256: str
    from_cache: bool
    last_modified: str | None = None
    size_bytes: int = 0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def newest_matching(directory: Path, pattern: str) -> Path | None:
    """The most recent local copy of a source, for when the catalogue stops publishing it.

    Measured on 14-10-2026: SUSALUD removed the health-resources package and the pipeline died on
    a 404 while a perfectly valid CSV sat in `data/raw/`. Falling back to it, and saying so out
    loud, is better than failing a run whose data is already on disk.

    The year in the file name wins over the modification time, because the newest *download* is
    not the newest *data*: a comparison run once left a 2025 file more recently written than the
    2026 one, and picking by time would have silently halved the coverage.
    """
    candidatos = list(Path(directory).glob(pattern))
    if not candidatos:
        return None

    def clave(path: Path) -> tuple[int, float]:
        anios = re.findall(r"(?:19|20)\d{2}", path.name)
        return (int(anios[-1]) if anios else 0, path.stat().st_mtime)

    return max(candidatos, key=clave)


def download(
    client: httpx.Client,
    url: str,
    destination: Path,
    *,
    force: bool = False,
) -> Download:
    """Download `url` to `destination`, reusing the local copy unless `force`."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not force:
        return Download(
            path=destination,
            url=url,
            sha256=file_sha256(destination),
            from_cache=True,
            size_bytes=destination.stat().st_size,
        )

    # Write to a temporary sibling and replace atomically, so an interrupted
    # download never leaves a truncated file that later looks like valid cache.
    temporary = destination.with_suffix(destination.suffix + ".part")
    with client.stream(
        "GET",
        url,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as response:
        response.raise_for_status()
        last_modified = response.headers.get("last-modified")
        with temporary.open("wb") as handle:
            for chunk in response.iter_bytes(CHUNK_SIZE):
                handle.write(chunk)
    temporary.replace(destination)

    return Download(
        path=destination,
        url=url,
        sha256=file_sha256(destination),
        from_cache=False,
        last_modified=last_modified,
        size_bytes=destination.stat().st_size,
    )
