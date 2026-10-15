"""S6: the `prospect_mock.json` contract consumed by the other modules.

It is the boundary with the database module (RF-09) and the Kanban (RF-03):
`pipeline_stage` uses exactly the Kanban columns, so no translation layer is
needed between the scraper and the CRM dashboard.
"""

import pytest
from pydantic import ValidationError

from scraper.capacity import IpressCapacity
from scraper.contract import (
    PIPELINE_STAGES,
    TAG_NO_CAPACITY_DATA,
    Prospect,
    ProspectArchive,
    build_archive,
    build_prospect,
)
from scraper.procedures import OzoneTherapy
from scraper.renipress import Ipress
from scraper.scoring import score_prospect


def ipress(**overrides) -> Ipress:
    base = dict(
        ipress_code="00024663",
        name="CLINICA VERTEBRAL",
        institution="PRIVADO",
        classification="POLICLINICOS",
        establishment_type="ESTABLECIMIENTO DE SALUD SIN INTERNAMIENTO",
        department="LIMA",
        province="LIMA",
        district="SAN ISIDRO",
        ubigeo="150131",
        address="AV. JAVIER PRADO ESTE 1066",
        category="I-3",
        phone="984337558",
        schedule="8:00 - 20:00",
        status="ACTIVO",
    )
    base.update(overrides)
    return Ipress(**base)


def _prospect(**overrides):
    entity = ipress(**overrides)
    return build_prospect(
        entity,
        capacity=IpressCapacity(
            ipress_code=entity.ipress_code,
            legal_name="CLINICA VERTEBRAL SAC",
            period="2026-02",
            consulting_rooms=9,
            functional_consulting_rooms=8,
            beds=0,
            doctors_total=6,
            nurses=7,
            ambulances=1,
        ),
        ozone_therapy=OzoneTherapy(checked=False),
        score=score_prospect(entity, doctors_total=6, performs_ozone_therapy=False),
    )


def test_prospect_validates_and_starts_at_the_discovered_stage():
    prospect = _prospect()
    assert isinstance(prospect, Prospect)
    assert prospect.id == "00024663"
    assert prospect.pipeline_stage == "discovered"
    assert prospect.location.district == "SAN ISIDRO"
    assert prospect.contact.phone_valid is True
    assert prospect.capacity.doctors_total == 6
    assert PIPELINE_STAGES[0] == "discovered"


def test_prospect_without_capacity_source_does_not_invent_values():
    entity = ipress(ipress_code="00000000", name="SIN DATOS", phone="")
    prospect = build_prospect(
        entity,
        capacity=IpressCapacity(ipress_code="00000000"),
        ozone_therapy=OzoneTherapy(checked=False),
        score=score_prospect(entity, doctors_total=0, performs_ozone_therapy=False),
    )
    assert prospect.capacity.doctors_total == 0
    assert prospect.capacity.period is None
    assert prospect.legal_name is None
    assert prospect.ozone_therapy.checked is False
    assert prospect.contact.phone_valid is False


def test_prospect_rejects_an_unknown_pipeline_stage():
    payload = {**_prospect().model_dump(), "pipeline_stage": "casi_firmado"}
    with pytest.raises(ValidationError):
        Prospect(**payload)


def test_prospect_carries_the_coordinates_in_its_location():
    """RENIPRESS las llama NORTE y ESTE, pero son latitud y longitud."""
    entity = ipress(latitude=-12.0977, longitude=-77.0365)
    prospect = build_prospect(
        entity,
        capacity=IpressCapacity(ipress_code=entity.ipress_code),
        ozone_therapy=OzoneTherapy(checked=False),
        score=score_prospect(entity, doctors_total=None, performs_ozone_therapy=False),
    )
    assert prospect.location.coordinates is not None
    assert prospect.location.coordinates.latitude == pytest.approx(-12.0977)
    assert prospect.location.coordinates.longitude == pytest.approx(-77.0365)


def test_prospect_without_coordinates_says_null_and_not_zero():
    """(0,0) está en el océano frente a África: no es una ubicación plausible."""
    assert _prospect().location.coordinates is None


# --- el segmento que viene de la busqueda, no del padron ---------------------
#
# Medido: RENIPRESS clasifica establecimientos, no especialidades, así que las 93 clínicas
# de fisioterapia que devuelve Google en los 10 distritos top de Lima **no están en la lista
# del padrón**. Las dos fuentes conviven en el mismo contrato y se distinguen por `origin`.


def place_prospect(**overrides) -> Prospect:
    base = dict(
        id="places:123456789",
        origin="places",
        name="Fisiathlon - San Isidro",
        location={
            "department": "LIMA",
            "province": "LIMA",
            "district": "SAN ISIDRO",
            "coordinates": {"latitude": -12.0936, "longitude": -77.0223},
        },
        contact={"phone": "+51 987 654 321", "phone_valid": True, "address": "Av. Las Begonias 475"},
        google={
            "cid": "123456789",
            "query": "fisioterapia San Isidro Lima",
            "category": "Fisioterapeuta",
            "rating": 5.0,
            "rating_count": 10,
            "rating_band": "alta",
            "reviews_band": "baja",
            "website": "https://fisiathlon.pe/",
            "chain_brand": "fisiathlon",
            "chain_sites": 3,
        },
        tags=["physiotherapy-segment"],
    )
    base.update(overrides)
    return Prospect(**base)


def test_a_prospect_that_did_not_come_from_the_registry_says_so():
    prospect = place_prospect()
    assert prospect.origin == "places"
    assert prospect.institution is None
    assert prospect.classification is None
    assert prospect.location.ubigeo is None
    assert prospect.score is None  # el puntaje del padrón no aplica acá
    assert prospect.capacity.period is None
    assert prospect.ozone_therapy.checked is False
    assert prospect.pipeline_stage == "discovered"


def test_the_google_block_carries_what_the_registry_cannot_know():
    google = place_prospect().google
    assert google is not None
    assert google.category == "Fisioterapeuta"
    assert google.rating_band == "alta"
    assert google.reviews_band == "baja"
    assert google.website == "https://fisiathlon.pe/"
    assert google.chain_sites == 3


def test_a_registry_prospect_keeps_its_origin_and_has_no_google_block():
    prospect = _prospect()
    assert prospect.origin == "renipress"
    assert prospect.google is None
    assert prospect.score is not None


def test_an_archive_orders_scored_prospects_first_and_the_rest_by_id():
    """Dos orígenes en el mismo archivo: el puntaje del padrón ordena primero, y los del
    segmento, que no tienen puntaje, van después en orden estable.
    """
    con_puntaje = _prospect()
    sin_puntaje = place_prospect(id="places:2")
    otro_sin = place_prospect(id="places:1")
    archivo = build_archive([sin_puntaje, otro_sin, con_puntaje], sources=[], generated_at="x")
    assert [p.id for p in archivo.prospects] == ["00024663", "places:1", "places:2"]


def test_prospect_publishes_the_measured_weight_of_its_score():
    """The CRM must be able to tell a 100-point score over full evidence from a
    100-point score over three quarters of it."""
    entity = ipress()
    prospect = build_prospect(
        entity,
        capacity=IpressCapacity(ipress_code=entity.ipress_code),
        ozone_therapy=OzoneTherapy(checked=False),
        score=score_prospect(entity, doctors_total=None, performs_ozone_therapy=False),
    )
    assert prospect.capacity.period is None
    assert prospect.score.measured_weight == 70
    assert TAG_NO_CAPACITY_DATA in prospect.tags


def test_archive_is_ordered_by_score_and_is_stable():
    higher = _prospect(ipress_code="00000002", category="I-4", phone="999888777")
    lower = _prospect(ipress_code="00000001", phone="", address="")
    kwargs = dict(sources=[], generated_at="2026-01-01T00:00:00+00:00")

    archive = build_archive([lower, higher], **kwargs)

    assert isinstance(archive, ProspectArchive)
    assert archive.total == 2
    assert [p.id for p in archive.prospects] == ["00000002", "00000001"]
    assert archive.model_dump() == build_archive([lower, higher], **kwargs).model_dump()
