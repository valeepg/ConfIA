"""La hoja de llamados: el único artefacto que convierte datos en una llamada.

El orden y las exclusiones son el punto: si la lista incluye clínicas sin teléfono o ajenas al
segmento, el vendedor pierde el tiempo y deja de confiar en la lista.
"""

from pathlib import Path

import pytest

from scraper.callsheet import DEFAULT_LIMIT, build_call_sheet, rank_for_calling, write_call_sheet
from scraper.contract import Prospect, ProspectArchive
from scraper.segment import SEGMENT_TAG


def place(**overrides) -> Prospect:
    base = dict(
        id="places:1",
        origin="places",
        name="Artrauma",
        location={"department": "LIMA", "district": "LIMA"},
        contact={"phone": "993 923 680", "phone_valid": True},
        google={
            "cid": "1",
            "query": "q",
            "category": "Fisioterapeuta",
            "rating": 4.8,
            "rating_count": 553,
        },
        tags=[SEGMENT_TAG],
    )
    base.update(overrides)
    return Prospect(**base)


def archive(*prospects: Prospect) -> ProspectArchive:
    return ProspectArchive(
        generated_at="2026-10-14T00:00:00+00:00",
        sources=[],
        total=len(prospects),
        prospects=list(prospects),
    )


def test_a_clinic_without_a_phone_is_not_worth_calling():
    sin_telefono = place(id="places:2", contact={"phone": "", "phone_valid": False})
    assert [p.id for p in rank_for_calling([sin_telefono, place()])] == ["places:1"]


def test_a_clinic_outside_the_segment_is_left_out_by_default():
    fuera = place(id="places:3", tags=[])
    assert [p.id for p in rank_for_calling([fuera, place()])] == ["places:1"]
    assert len(rank_for_calling([fuera, place()], only_segment=False)) == 2


def test_more_patient_activity_goes_first():
    """Las reseñas son el mejor indicador disponible de que la clínica atiende gente."""
    pocas = place(id="pocas", name="Pocas", google={"cid": "a", "query": "q", "rating": 5.0, "rating_count": 10})
    muchas = place(id="muchas", name="Muchas", google={"cid": "b", "query": "q", "rating": 4.0, "rating_count": 900})
    assert [p.id for p in rank_for_calling([pocas, muchas])] == ["muchas", "pocas"]


def test_with_the_same_activity_the_better_rating_goes_first():
    buena = place(id="buena", name="Buena", google={"cid": "a", "query": "q", "rating": 4.9, "rating_count": 100})
    floja = place(id="floja", name="Floja", google={"cid": "b", "query": "q", "rating": 3.1, "rating_count": 100})
    assert [p.id for p in rank_for_calling([floja, buena])] == ["buena", "floja"]


def test_a_clinic_without_google_data_still_has_an_order():
    sin_datos = place(id="sin", name="Sin datos", google=None)
    con_datos = place(id="con", name="Con datos")
    assert [p.id for p in rank_for_calling([sin_datos, con_datos])] == ["con", "sin"]


def test_the_limit_is_respected():
    filas = [place(id=f"p{i}", name=f"Clinica {i}") for i in range(10)]
    assert len(rank_for_calling(filas, limit=3)) == 3


def test_the_sheet_carries_the_ranking_rule_and_the_rows():
    hoja = build_call_sheet(archive(place()))
    assert "Hoja de llamados" in hoja
    assert "Cómo se ordenó" in hoja
    assert "Artrauma" in hoja
    assert "993 923 680" in hoja
    assert "553" in hoja


def test_the_sheet_says_what_the_data_is_not():
    """El dueño tiene que saber que estas clínicas no están en el padrón y de dónde salen."""
    hoja = build_call_sheet(archive(place()))
    assert "no están en el padrón" in hoja or "está en el padrón" in hoja
    assert "actividad de pacientes, no intención de compra" in hoja
    assert "restricción de caché" in hoja
    assert "este módulo no envía" in hoja


def test_the_sheet_states_how_many_it_shows_out_of_how_many():
    contenido = archive(*[place(id=f"p{i}", name=f"C{i}") for i in range(5)])
    hoja = build_call_sheet(contenido, limit=2)
    assert "mostrando **2**" in hoja
    assert "de 5 prospectos" in hoja


def test_the_default_limit_is_a_reasonable_worklist():
    assert 10 <= DEFAULT_LIMIT <= 50


def test_write_call_sheet_creates_the_file(tmp_path):
    destino = write_call_sheet(archive(place()), tmp_path / "hoja.md", limit=1)
    assert destino.exists()
    assert "Artrauma" in destino.read_text(encoding="utf-8")


def test_a_pipe_in_a_name_does_not_break_the_table():
    hoja = build_call_sheet(archive(place(name="Clinica | Rara")))
    fila = next(line for line in hoja.splitlines() if "Rara" in line)
    assert fila.count("|") == 10  # 9 columnas + los bordes, sin romper la tabla
