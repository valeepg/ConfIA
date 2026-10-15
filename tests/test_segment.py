"""The focused segment, assembled from the search source into the same contract.

Why it exists: the registry files establishments, not specialties. Of 2,459 registry
prospects exactly one is filed as `MEDICINA FISICA`, and of the 93 physiotherapy clinics
Google returns for the ten busiest Lima districts, none is in that list. The segment the
business wants to focus on therefore has to be asked for by name, and the result has to live
in the same archive as the registry prospects or the CRM needs two code paths.

Everything except the provider call is pure and tested here.
"""

from pathlib import Path

import pytest

from scraper.contract import ProspectArchive
from scraper.places import Chain, PlaceRecord
from scraper.segment import (
    SEGMENT_TAG,
    build_queries,
    build_segment_prospect,
    top_districts,
)

RECORD = PlaceRecord(
    cid="1585704026956535642",
    name="Fisiathlon - San Isidro - Centro de Fisioterapia",
    category="Fisioterapeuta",
    phone="+51 987 654 321",
    address="Av. Las Begonias 475, San Isidro 15046",
    latitude=-12.0936,
    longitude=-77.0223,
    website="https://fisiathlon.pe/",
    rating=4.8,
    rating_count=419,
    position=1,
    query="fisioterapia San Isidro Lima",
)


def place(**overrides) -> PlaceRecord:
    from dataclasses import replace

    return replace(RECORD, **overrides)


def prospect_for(record: PlaceRecord, chain: Chain | None = None):
    return build_segment_prospect(
        record,
        chain or Chain(brand=None, sites=1),
        district="SAN ISIDRO",
        department="LIMA",
    )


# --- las consultas ---------------------------------------------------------- #


def test_build_queries_covers_every_district_and_specialty():
    consultas = build_queries(["SAN ISIDRO", "MIRAFLORES"], department="LIMA")
    assert len(consultas) == 2 * len(build_queries(["SAN ISIDRO"], department="LIMA"))
    assert all(consulta.department == "LIMA" for consulta in consultas)
    assert {consulta.district for consulta in consultas} == {"SAN ISIDRO", "MIRAFLORES"}
    assert all(consulta.district.title() in consulta.text for consulta in consultas)


def test_build_queries_disambiguates_the_district_with_its_department():
    """`SAN ISIDRO` is a district in Lima and a town elsewhere, so the department is asked."""
    consulta = build_queries(["SAN ISIDRO"], department="LIMA")[0]
    assert consulta.text.endswith("San Isidro Lima")


def test_build_queries_does_not_repeat_the_department_for_its_own_district():
    consulta = build_queries(["LIMA"], department="LIMA")[0]
    assert not consulta.text.endswith("Lima Lima")


# --- el prospecto ----------------------------------------------------------- #


def test_a_place_becomes_a_prospect_that_says_it_came_from_search():
    prospect = prospect_for(place())
    assert prospect.origin == "places"
    assert prospect.id == "places:1585704026956535642"
    assert prospect.name.startswith("Fisiathlon")
    assert prospect.institution is None
    assert prospect.category is None
    assert prospect.score is None
    assert prospect.pipeline_stage == "discovered"


def test_the_segment_prospect_keeps_the_phone_the_coordinates_and_the_bands():
    prospect = prospect_for(place())
    assert prospect.contact.phone == "+51 987 654 321"
    assert prospect.contact.phone_valid is True
    assert prospect.location.district == "SAN ISIDRO"
    assert prospect.location.coordinates.latitude == pytest.approx(-12.0936)
    assert prospect.google.category == "Fisioterapeuta"
    assert prospect.google.reviews_band == "alta"
    assert prospect.google.rating_band == "alta"


def test_a_chain_gets_a_tag_so_it_can_be_filtered():
    con_cadena = prospect_for(place(), Chain(brand="fisiathlon", sites=3))
    assert "chain" in con_cadena.tags
    suelta = prospect_for(place(name="Fisioterapia Miraflores"), Chain(brand=None, sites=1))
    assert "chain" not in suelta.tags
    assert SEGMENT_TAG in suelta.tags


def test_a_place_without_a_website_is_tagged_so_it_can_be_filtered():
    assert "no-website" in prospect_for(place(website=None)).tags
    assert "no-website" not in prospect_for(place()).tags


def test_a_place_without_coordinates_leaves_them_null_instead_of_guessing():
    prospect = prospect_for(place(latitude=None, longitude=None))
    assert prospect.location.coordinates is None


# --- el tag tiene que significar "es del segmento", no "lo encontro la consulta" --- #
#
# Medido sobre 180 consultas reales: las cinco especialidades tambien devuelven
# `Servicio de salud mental` (10), `Hospital` (22) y `Medico` (18). Taggear todo lo que
# devuelve la consulta haria que el filtro del CRM mienta.


def test_a_physiotherapy_category_is_tagged_as_the_segment():
    for categoria in (
        "Fisioterapeuta",
        "Clinica de fisioterapia",
        "Centro de rehabilitacion fisica",
        "Clinica del dolor",
        "Quiropráctico",
    ):
        assert SEGMENT_TAG in prospect_for(place(category=categoria)).tags, categoria


def test_a_category_outside_the_segment_is_not_tagged_but_is_not_hidden():
    raro = prospect_for(place(category="Servicio de salud mental"))
    assert SEGMENT_TAG not in raro.tags
    assert raro.google.category == "Servicio de salud mental"  # visible, no escondido
    assert raro.tags == [] or "no-website" in raro.tags


def test_a_place_without_a_category_is_not_claimed_as_the_segment():
    """Sin categoria no hay evidencia de que sea del segmento."""
    assert SEGMENT_TAG not in prospect_for(place(category=None)).tags


def test_the_archive_of_the_segment_validates():
    archive = ProspectArchive(
        generated_at="2026-10-14T00:00:00+00:00",
        sources=[],
        total=2,
        prospects=[prospect_for(place()), prospect_for(place(cid="99", name="Otra"))],
    )
    assert archive.total == 2
    assert {p.origin for p in archive.prospects} == {"places"}


# --- el orden de los distritos ---------------------------------------------- #


def test_top_districts_ranks_by_how_many_prospects_each_one_holds():
    contenido = {
        "generated_at": "x",
        "sources": [],
        "total": 3,
        "prospects": [
            {"id": "a", "name": "A", "location": {"department": "LIMA", "province": "LIMA", "district": "MIRAFLORES", "ubigeo": "1"}},
            {"id": "b", "name": "B", "location": {"department": "LIMA", "province": "LIMA", "district": "MIRAFLORES", "ubigeo": "2"}},
            {"id": "c", "name": "C", "location": {"department": "LIMA", "province": "LIMA", "district": "LINCE", "ubigeo": "3"}},
            {"id": "d", "name": "D", "location": {"department": "AREQUIPA", "province": "AREQUIPA", "district": "YANAHUARA", "ubigeo": "4"}},
        ],
    }
    archive = ProspectArchive.model_validate(contenido)
    assert top_districts(archive.prospects, department="LIMA", limit=10) == ["MIRAFLORES", "LINCE"]
    assert top_districts(archive.prospects, department="LIMA", limit=1) == ["MIRAFLORES"]
    assert top_districts(archive.prospects, department="AREQUIPA") == ["YANAHUARA"]
