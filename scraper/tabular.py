"""Shared CSV helpers for the SUSALUD open data sources.

All three sources are `;`-separated and quote fields with `"`, which is not
cosmetic: 270 RENIPRESS rows quote a phone like `3515111; 3515116`, and reading
the file without `quote_char` makes them overflow the header and shift every
following column. Consulta A and Consulta G are published in latin-1 and
RENIPRESS in UTF-8; Polars only reads UTF-8, so a non-UTF-8 source is transcoded
once and cached in the cache directory.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import polars as pl

from .config import CACHE_DIR

# A UTF-8 sequence can be truncated by the sample boundary; drop a few trailing
# bytes before validating so a valid file is never misdetected as latin-1.
_ENCODING_SAMPLE_BYTES = 1 << 16
_ENCODING_TAIL_GUARD = 4
_UTF8_BOM = b"\xef\xbb\xbf"
_COPY_CHUNK = 1 << 20
_CACHE_SUFFIX = ".utf8"

ENCODING_UTF8 = "utf8"
ENCODING_LATIN1 = "latin1"


def detect_encoding(path: Path) -> str:
    """Return `latin1` only when the sample is not valid UTF-8."""
    with Path(path).open("rb") as handle:
        sample = handle.read(_ENCODING_SAMPLE_BYTES)
    if sample.startswith(_UTF8_BOM):
        sample = sample[len(_UTF8_BOM) :]
    try:
        sample[:-_ENCODING_TAIL_GUARD].decode("utf-8")
    except UnicodeDecodeError:
        return ENCODING_LATIN1
    return ENCODING_UTF8


def _cache_path(source: Path, cache_dir: Path) -> Path:
    """Key the cache by name *and* location: two sources may share a file name."""
    key = hashlib.blake2b(str(source.resolve()).encode("utf-8"), digest_size=4).hexdigest()
    return cache_dir / f"{source.name}.{key}{_CACHE_SUFFIX}"


def normalize_encoding(path: Path, *, cache_dir: Path | None = None) -> Path:
    """Return a path Polars can read as UTF-8, transcoding and caching if needed.

    The transcoding streams line by line, so a 200 MB source never lands in
    memory twice. The BOM is left to Polars, which strips it on read.
    """
    path = Path(path)
    if detect_encoding(path) != ENCODING_LATIN1:
        return path

    cache_dir = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    target = _cache_path(path, cache_dir)
    if target.exists() and target.stat().st_mtime_ns >= path.stat().st_mtime_ns:
        return target

    cache_dir.mkdir(parents=True, exist_ok=True)
    with path.open(encoding=ENCODING_LATIN1, newline="") as source, target.open(
        "w", encoding="utf-8", newline=""
    ) as sink:
        shutil.copyfileobj(source, sink, _COPY_CHUNK)
    return target


def normalize_columns(frame: pl.DataFrame | pl.LazyFrame) -> pl.DataFrame | pl.LazyFrame:
    """Strip the BOM, surrounding spaces and uppercase the source column names."""
    renamed = {
        name: name.strip().lstrip("\ufeff").upper() for name in frame.collect_schema().names()
    }
    return frame.rename(renamed)


def read_source_csv(path: Path, *, lazy: bool = False, cache_dir: Path | None = None):
    """Read one SUSALUD CSV with the encoding and quoting its publisher uses."""
    path = normalize_encoding(Path(path), cache_dir=cache_dir)
    reader = pl.scan_csv if lazy else pl.read_csv
    frame = reader(
        path,
        separator=";",
        quote_char='"',
        encoding="utf8",
        infer_schema_length=0,
    )
    return normalize_columns(frame)


def parse_int(value: object) -> int:
    """Parse a source integer, returning 0 for blanks and unparseable values."""
    if value is None:
        return 0
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
