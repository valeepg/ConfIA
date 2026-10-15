"""Google Places as a source: the segment the registry cannot see.

Measured on 2026-10-14: RENIPRESS classifies establishments, not clinical specialties, so
one clinic out of 2,459 is filed as `MEDICINA FISICA`. Searching Google for the specialty
instead returned 93 physiotherapy clinics in the ten busiest Lima districts, and **not one
of them was in the registry-based list**. For the focused segment the search source is the
primary one and the registry is the enrichment.

Everything here is offline-testable: the provider call is the only network edge, and the
raw answers are cached per query so a credit is never spent twice on the same question.
"""

import json
from pathlib import Path

import httpx
import pytest

from scraper.places import (
    PLACES_ENDPOINT,
    PlaceRecord,
    derive_chains,
    fetch_segment,
    rating_band,
    reviews_band,
    search_places,
)

ANSWER = {
    "credits": 1,
    "places": [
        {
            "position": 1,
            "title": "Fisiathlon - San Isidro - Centro de Fisioterapia",
            "address": "Av. Las Begonias 475, San Isidro 15046",
            "latitude": -12.0936,
            "longitude": -77.0223,
            "rating": 5,
            "ratingCount": 10,
            "category": "Fisioterapeuta",
            "phoneNumber": "+51 987 654 321",
            "website": "https://fisiathlon.pe/",
            "cid": 123456789,
        },
        {
            "position": 2,
            "title": "Power Health: Fisioterapia y Rehabilitacion",
            "address": "Av. Arequipa 1234, Lima",
            "latitude": -12.08,
            "longitude": -77.03,
            "rating": 4.5,
            "ratingCount": 20,
            "cid": 987654321,
        },
    ],
}


def client_with(payload: dict, calls: list | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(json.loads(request.content))
        return httpx.Response(200, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_search_maps_a_place_into_a_record():
    with client_with(ANSWER) as client:
        records = search_places(client, "fisioterapia San Isidro Lima", api_key="clave")

    primero = records[0]
    assert isinstance(primero, PlaceRecord)
    assert primero.name == "Fisiathlon - San Isidro - Centro de Fisioterapia"
    assert primero.category == "Fisioterapeuta"
    assert primero.phone == "+51 987 654 321"
    assert primero.latitude == pytest.approx(-12.0936)
    assert primero.website == "https://fisiathlon.pe/"
    assert primero.rating == 5
    assert primero.rating_count == 10
    assert primero.cid == "123456789"


def test_search_keeps_the_query_that_surfaced_the_place():
    """A segment is reproducible from its queries, not from a file hash."""
    with client_with(ANSWER) as client:
        records = search_places(client, "fisioterapia Miraflores Lima", api_key="clave")
    assert {record.query for record in records} == {"fisioterapia Miraflores Lima"}


def test_search_asks_for_the_peruvian_locale_and_a_page_of_results():
    calls: list = []
    with client_with(ANSWER, calls) as client:
        search_places(client, "fisioterapia Lince Lima", api_key="clave", num=20)
    assert calls[0]["q"] == "fisioterapia Lince Lima"
    assert calls[0]["gl"] == "pe"
    assert calls[0]["hl"] == "es"
    assert calls[0]["num"] == 20


def test_search_tolerates_a_place_without_optional_fields():
    payload = {"places": [{"title": "Solo el nombre", "cid": 1}]}
    with client_with(payload) as client:
        registro = search_places(client, "q", api_key="clave")[0]
    assert registro.name == "Solo el nombre"
    assert registro.phone is None
    assert registro.rating is None
    assert registro.rating_count is None
    assert registro.website is None


def test_search_returns_nothing_when_there_are_no_results():
    with client_with({"places": []}) as client:
        assert search_places(client, "q", api_key="clave") == ()


@pytest.mark.parametrize(
    ("cuenta", "esperado"),
    [(None, "sin datos"), (0, "sin reseñas"), (5, "baja"), (50, "media"), (419, "alta")],
)
def test_reviews_band_buckets(cuenta, esperado):
    """Bands exist so the CRM can filter without recomputing thresholds."""
    assert reviews_band(cuenta) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(None, "sin datos"), (3.5, "baja"), (4.2, "buena"), (4.8, "alta")],
)
def test_rating_band_buckets(valor, esperado):
    assert rating_band(valor) == esperado


def test_chains_count_the_same_name_across_places():
    """Un nombre idéntico en dos fichas distintas son dos sedes de lo mismo."""
    registros = [
        PlaceRecord(cid="1", name="Artrauma", category="Fisioterapeuta", query="q"),
        PlaceRecord(cid="2", name="ARTRAUMA", category="Fisioterapeuta", query="q"),
        PlaceRecord(cid="3", name="Fisioterapia Miraflores", category="Fisioterapeuta", query="q"),
    ]
    cadenas = derive_chains(registros)
    assert cadenas["1"].brand == "artrauma"
    assert cadenas["1"].sites == 2
    assert cadenas["1"].evidence == "name"
    assert cadenas["3"].sites == 1
    assert cadenas["3"].brand is None


def test_the_same_phone_across_branches_is_a_chain():
    """Medido: `Centro Médico OSI` tiene ocho sedes en la hoja de llamados y todas publican
    `(01) 7390888`. La regla por nombre las perdía todas, porque cada sede lleva su distrito."""
    registros = [
        PlaceRecord(cid="1", name="Centro Medico OSI / La Molina", phone="(01) 7390888", query="q"),
        PlaceRecord(cid="2", name="Centro Medico OSI / Miraflores", phone="(01) 739-0888", query="q"),
        PlaceRecord(cid="3", name="Otra Clinica Suelta", phone="999888777", query="q"),
    ]
    cadenas = derive_chains(registros)
    assert cadenas["1"].evidence == "phone"
    assert cadenas["1"].sites == 2
    assert cadenas["1"].brand == "centro medico osi"  # el prefijo comun de las sedes
    assert cadenas["3"].sites == 1
    assert cadenas["3"].evidence is None


def test_a_shared_first_word_is_not_a_chain():
    """Medido: agrupar por la primera palabra dio `fisio` con 34 sedes, `san` con 24 y
    `dolor` con 14 — 385 de 829 lugares marcados como cadena, casi todos un artefacto."""
    registros = [
        PlaceRecord(cid="1", name="Fisio Centro San Isidro", query="q"),
        PlaceRecord(cid="2", name="Fisio Salud Miraflores", query="q"),
        PlaceRecord(cid="3", name="Fisiozoe Lima", query="q"),
    ]
    cadenas = derive_chains(registros)
    assert all(not cadenas[cid].is_chain for cid in ("1", "2", "3"))


def test_a_repeated_service_word_is_not_a_brand():
    """Medido: `terapia del dolor` se repite dos veces y no es una marca, es el servicio."""
    registros = [
        PlaceRecord(cid="1", name="Terapia del Dolor", query="q"),
        PlaceRecord(cid="2", name="TERAPIA DEL DOLOR", query="q"),
    ]
    assert derive_chains(registros)["1"].is_chain is False


def test_a_repeated_purely_generic_name_is_not_a_chain():
    """Medido: `medicina fisica y rehabilitacion` se repite tres veces y no es una marca:
    es un descriptor que clínicas sin relación comparten."""
    registros = [
        PlaceRecord(cid="1", name="Medicina Fisica y Rehabilitacion", query="q"),
        PlaceRecord(cid="2", name="MEDICINA FISICA Y REHABILITACION", query="q"),
    ]
    cadenas = derive_chains(registros)
    assert cadenas["1"].is_chain is False
    assert cadenas["1"].sites == 1


def test_fetch_segment_spends_each_query_once_thanks_to_the_cache(tmp_path):
    calls: list = []
    with client_with(ANSWER, calls) as client:
        primera = fetch_segment(
            client, ["fisioterapia San Isidro Lima"], api_key="clave", cache_dir=tmp_path
        )
        gastadas = len(calls)
        segunda = fetch_segment(
            client, ["fisioterapia San Isidro Lima"], api_key="clave", cache_dir=tmp_path
        )

    assert len(primera) == 2
    assert len(segunda) == 2
    assert len(calls) == gastadas  # la segunda corrida no volvio a preguntar
    assert (tmp_path / "fisioterapia-san-isidro-lima.json").exists()


def test_fetch_segment_deduplicates_the_same_place_across_queries(tmp_path):
    with client_with(ANSWER) as client:
        registros = fetch_segment(
            client,
            ["fisioterapia San Isidro Lima", "centro de rehabilitacion San Isidro"],
            api_key="clave",
            cache_dir=tmp_path,
        )
    cids = [registro.cid for registro in registros]
    assert len(cids) == len(set(cids)) == 2


def test_unanswered_queries_lists_the_ones_without_a_cached_answer(tmp_path):
    from scraper.places import cache_name, unanswered_queries

    (tmp_path / cache_name("respondio")).write_text("{\"places\": []}", encoding="utf-8")
    assert unanswered_queries(tmp_path, ["respondio", "nunca"]) == ["nunca"]


# --- resistencia a fallos del proveedor -------------------------------------- #
#
# Medido: un 500 de Serper tiró abajo una corrida de 275 consultas ya pagadas. Una corrida
# por lotes tiene que sobrevivir una respuesta mala, y un 401 no se arregla insistiendo.


def test_fetch_segment_retries_a_transient_server_error(tmp_path):
    respuestas = iter([httpx.Response(500), httpx.Response(200, json=ANSWER)])
    client = httpx.Client(transport=httpx.MockTransport(lambda request: next(respuestas)))
    registros = fetch_segment(
        client, ["q"], api_key="clave", cache_dir=tmp_path, sleep=lambda _: None
    )
    assert len(registros) == 2
    assert (tmp_path / "q.json").exists()


def test_a_query_that_never_answers_is_skipped_and_the_rest_continues(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if "rota" in str(request.content):
            return httpx.Response(503)
        return httpx.Response(200, json=ANSWER)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    registros = fetch_segment(
        client,
        ["rota", "buena"],
        api_key="clave",
        cache_dir=tmp_path,
        sleep=lambda _: None,
    )

    assert len(registros) == 2  # solo la que respondio
    assert not (tmp_path / "rota.json").exists()  # sin cache = nunca respondio
    assert (tmp_path / "buena.json").exists()


def test_a_credential_error_is_not_retried(tmp_path):
    llamadas: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas.append(1)
        return httpx.Response(401, json={"error": "clave invalida"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_segment(client, ["q"], api_key="mala", cache_dir=tmp_path, sleep=lambda _: None)
    assert len(llamadas) == 1
