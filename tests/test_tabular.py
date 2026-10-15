"""Encoding handling for the SUSALUD sources.

Consulta A and Consulta G are published in latin-1 and Polars only reads UTF-8,
so a non-UTF-8 source is transcoded once. The transcoded copy is a cache: it must
live in the cache directory, never next to the source, which may be a read-only
mount or a tracked fixture directory.
"""

from pathlib import Path

from scraper.tabular import detect_encoding, normalize_encoding

LATIN1_BYTES = (
    '"ANHO";"MES";"PROCEDIMIENTO"\n"2026";"01";"Aplicación de ozonoterapia"\n'
).encode("latin-1")


def _latin1_source(tmp_path: Path) -> Path:
    source = tmp_path / "source" / "consulta.csv"
    source.parent.mkdir(parents=True)
    source.write_bytes(LATIN1_BYTES)
    return source


def test_detect_encoding_falls_back_to_latin1_on_an_accented_byte(tmp_path):
    assert detect_encoding(_latin1_source(tmp_path)) == "latin1"


def test_a_utf8_source_is_used_as_is(tmp_path):
    source = tmp_path / "utf8.csv"
    source.write_text('"A";"B"\n"1";"á"\n', encoding="utf-8")
    assert detect_encoding(source) == "utf8"
    assert normalize_encoding(source, cache_dir=tmp_path / "cache") == source


def test_normalize_encoding_caches_outside_the_source_directory(tmp_path):
    source = _latin1_source(tmp_path)
    cache_dir = tmp_path / "cache"

    transcoded = normalize_encoding(source, cache_dir=cache_dir)

    assert transcoded != source
    assert transcoded.parent == cache_dir
    assert transcoded.read_text(encoding="utf-8").endswith('"Aplicación de ozonoterapia"\n')
    # El directorio de origen queda intacto: nada de archivos derivados al lado.
    assert sorted(entry.name for entry in source.parent.iterdir()) == ["consulta.csv"]


def test_normalize_encoding_reuses_the_cached_transcode(tmp_path):
    source = _latin1_source(tmp_path)
    cache_dir = tmp_path / "cache"

    first = normalize_encoding(source, cache_dir=cache_dir)
    stamp = first.stat().st_mtime_ns
    second = normalize_encoding(source, cache_dir=cache_dir)

    assert second == first
    assert second.stat().st_mtime_ns == stamp  # no se reescribió


def test_normalize_encoding_does_not_mix_up_equal_file_names(tmp_path):
    """Two fixtures with the same name in different directories are different files."""
    first = tmp_path / "a" / "consulta.csv"
    second = tmp_path / "b" / "consulta.csv"
    for path, marker in ((first, "ozono"), (second, "oxigeno")):
        path.parent.mkdir(parents=True)
        path.write_bytes(f'"PROCEDIMIENTO"\n"{marker}"\n'.encode("latin-1"))

    cache_dir = tmp_path / "cache"
    transcoded_first = normalize_encoding(first, cache_dir=cache_dir)
    transcoded_second = normalize_encoding(second, cache_dir=cache_dir)

    assert transcoded_first != transcoded_second
    assert "ozono" in transcoded_first.read_text(encoding="utf-8")
    assert "oxigeno" in transcoded_second.read_text(encoding="utf-8")
