import pytest
from pydantic import ValidationError

from app.confia_product_catalog import (
    DEFAULT_PRODUCT_LINE_KEY,
    PRODUCT_LINES,
    UnknownProductLineError,
    resolve_product_line,
)
from app.schemas import DossierInput


def test_resolves_by_specialty_keyword_with_accents_ignored():
    line, match = resolve_product_line("Reumatología")
    assert line.key == "ozonobaric_ahtm"
    assert match == "specialty"


def test_traumatology_and_pain_map_to_ozonette():
    for specialty in ("Traumatología y Quemados", "Medicina del Dolor", "Rehabilitación y Deporte"):
        line, match = resolve_product_line(specialty)
        assert line.key == "ozonette_infiltracion", specialty
        assert match == "specialty"


def test_unmatched_specialty_falls_back_to_default_without_error():
    line, match = resolve_product_line("Pediatría")
    assert line.key == DEFAULT_PRODUCT_LINE_KEY
    assert match == "default"


def test_explicit_product_line_wins_over_specialty():
    line, match = resolve_product_line("Traumatología", "ozonobaric_ahtm")
    assert line.key == "ozonobaric_ahtm"
    assert match == "explicit"


def test_unknown_explicit_product_line_is_rejected():
    with pytest.raises(UnknownProductLineError):
        resolve_product_line("Traumatología", "no_existe")


def test_catalog_is_immutable():
    with pytest.raises(TypeError):
        PRODUCT_LINES["nuevo"] = PRODUCT_LINES[DEFAULT_PRODUCT_LINE_KEY]

    line = PRODUCT_LINES["ozonette_infiltracion"]
    with pytest.raises(ValidationError):
        line.regulatory.registry_number = "ALTERADO"


def test_every_line_has_all_regulatory_fields_filled():
    for line in PRODUCT_LINES.values():
        for value in line.regulatory.model_dump().values():
            assert value.strip(), line.key


def test_standard_registry_is_the_equipment_catalog_one():
    assert PRODUCT_LINES["ozonette_infiltracion"].regulatory.registry_number == "DM-14820-E"


def test_dossier_input_no_longer_requires_regulatory_data():
    payload = DossierInput(
        name="Clínica Nueva",
        district="Miraflores",
        specialty="Pediatría",
        director_medico="Dr. Pérez",
        doctor_specialty="Pediatría",
        score=40,
        ai_suggestion="Contacto inicial",
    )
    assert payload.product_line is None
    assert payload.lead_id is None
    assert not hasattr(payload, "validated_regulatory_data")
