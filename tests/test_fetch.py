"""Local download cache: the pipeline must not re-fetch 226 MB of Consulta G
when the file is already in `data/raw`.
"""

import hashlib
import os

import httpx

from scraper.fetch import Download, download, file_sha256, newest_matching


def test_file_sha256(tmp_path):
    path = tmp_path / "x.csv"
    path.write_bytes(b"hola")
    assert file_sha256(path) == hashlib.sha256(b"hola").hexdigest()


def test_download_writes_the_file_and_reports_its_hash(tmp_path):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, content=b"a;b\n1;2\n")

    destination = tmp_path / "raw" / "mini.csv"
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = download(client, "http://example.test/mini.csv", destination)

    assert isinstance(result, Download)
    assert result.from_cache is False
    assert destination.read_bytes() == b"a;b\n1;2\n"
    assert result.sha256 == hashlib.sha256(b"a;b\n1;2\n").hexdigest()
    assert calls == ["http://example.test/mini.csv"]


def test_download_reuses_the_local_copy_without_hitting_the_network(tmp_path):
    def handler(request):
        raise AssertionError("must not hit the network when the file already exists")

    destination = tmp_path / "mini.csv"
    destination.write_bytes(b"previous content")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = download(client, "http://example.test/mini.csv", destination)

    assert result.from_cache is True
    assert destination.read_bytes() == b"previous content"


def test_download_with_force_ignores_the_local_copy(tmp_path):
    def handler(request):
        return httpx.Response(200, content=b"nuevo")

    destination = tmp_path / "mini.csv"
    destination.write_bytes(b"viejo")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = download(client, "http://example.test/mini.csv", destination, force=True)

    assert result.from_cache is False
    assert destination.read_bytes() == b"nuevo"


def test_newest_matching_prefers_the_newest_year_over_the_newest_download(tmp_path):
    """Medido: una corrida de comparación dejó el archivo de 2025 más reciente en disco que el de
    2026, y elegir por fecha de descarga habría bajado la cobertura de capacidad a la mitad."""
    de_2026 = tmp_path / "ConsultaA_2026_v15.csv"
    de_2025 = tmp_path / "ConsultaA_2025_v22.csv"
    de_2026.write_text("2026", encoding="utf-8")
    de_2025.write_text("2025", encoding="utf-8")
    os.utime(de_2026, (1, 1))
    os.utime(de_2025, (999_999_999, 999_999_999))

    assert newest_matching(tmp_path, "ConsultaA_*.csv") == de_2026


def test_newest_matching_without_a_year_falls_back_to_the_modification_time(tmp_path):
    viejo = tmp_path / "ConsultaA_sin_anio.csv"
    nuevo = tmp_path / "ConsultaA_otro.csv"
    viejo.write_text("a", encoding="utf-8")
    nuevo.write_text("b", encoding="utf-8")
    os.utime(viejo, (1, 1))
    os.utime(nuevo, (999_999_999, 999_999_999))

    assert newest_matching(tmp_path, "ConsultaA_*.csv") == nuevo
