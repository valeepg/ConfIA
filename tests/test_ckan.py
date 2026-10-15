"""S1: download URLs are resolved through the SUSALUD CKAN API.

Business rule: the published filename is never hardcoded
(`RENIPRESS_2026_v7.csv` is renamed every time SUSALUD republishes).
The current resource is picked by (year, period).
"""

import json
from pathlib import Path

import httpx
import pytest

from scraper.ckan import (
    DatasetUnavailable,
    NoResourcesError,
    Resource,
    list_resources,
    pick_resource,
    resolve_resource,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _package(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_list_resources_ignores_the_xlsx_data_dictionary():
    resources = list_resources(_package("package_renipress.json"))
    assert [r.url for r in resources] == [
        "http://example.test/sites/default/files/RENIPRESS_2026_v7.csv"
    ]


def test_list_resources_parses_year_and_period_from_the_resource_name():
    by_url = {r.url: (r.year, r.period) for r in list_resources(_package("package_recursos.json"))}
    assert by_url["http://example.test/ConsultaG_2019_II_v1.csv"] == (2019, 2)
    assert by_url["http://example.test/ConsultaG_2025_IV_v3.csv"] == (2025, 4)
    assert by_url["http://example.test/ConsultaG_2026_07_v2.csv"] == (2026, 7)
    assert by_url["http://example.test/ConsultaG_2026_08_v1.csv"] == (2026, 8)


def test_pick_resource_takes_the_most_recent_year_and_period():
    resource = pick_resource(list_resources(_package("package_recursos.json")))
    assert isinstance(resource, Resource)
    assert resource.url == "http://example.test/ConsultaG_2026_08_v1.csv"


def test_pick_resource_accepts_an_explicit_year_or_period():
    resources = list_resources(_package("package_recursos.json"))
    assert pick_resource(resources, year=2025).url == "http://example.test/ConsultaG_2025_IV_v3.csv"
    assert pick_resource(resources, period=2).url == "http://example.test/ConsultaG_2019_II_v1.csv"


def test_pick_resource_without_candidates_fails_with_a_clear_message():
    package = {
        "result": {
            "name": "x",
            "resources": [{"name": "Diccionario", "format": "xlsx", "url": "u"}],
        }
    }
    with pytest.raises(NoResourcesError, match="csv"):
        pick_resource(list_resources(package))


# --- el catalogo de SUSALUD cambia de nombres --------------------------------- #
#
# Medido el 14-10-2026: SUSALUD retiro el paquete historico de recursos de salud y el
# identificador que este proyecto usaba paso a responder 404, con el dato todavia publicado
# bajo otro nombre y el CSV ya descargado en disco.


def test_resolve_resource_tries_the_other_identifiers_when_one_is_gone():
    llamadas: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        llamadas.append(url)
        if "consulta-recursos-de-salud-por-ipress" in url:
            return httpx.Response(404)
        return httpx.Response(200, json=_package("package_recursos.json"))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        recurso = resolve_resource(client, "capacity")

    assert recurso.url.endswith(".csv")
    assert len(llamadas) == 2  # el que fallo y el que resolvio
    assert "2018" in llamadas[1]


def test_resolve_resource_names_every_identifier_it_tried():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DatasetUnavailable, match="consulta-recursos-de-salud-por-ipress"):
            resolve_resource(client, "capacity")


def test_resolve_resource_can_be_limited_to_the_current_identifier():
    """El que tiene copia local no quiere que le ofrezcan un dataset de otro año.

    Medido: el identificador alternativo de 2018 sí existe, así que el fallback lo usó y la
    cobertura de capacidad cayó de 248 prospectos a 33 sin decir nada.
    """
    llamadas: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas.append(str(request.url))
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DatasetUnavailable):
            resolve_resource(client, "capacity", include_alternatives=False)

    assert len(llamadas) == 1  # solo el identificador principal
