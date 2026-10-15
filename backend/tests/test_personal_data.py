"""El hash de identificadores personales: lo que tiene que garantizar y lo que no.

Lo que se prueba acá es sobre todo **lo que el hash no puede hacer**: no se puede revertir, no se
puede comparar en tiempo variable, y no funciona sin pimienta.
"""

import pytest

from app.personal_data import (
    SinPimienta,
    coincide,
    hash_identificador,
    normalizar,
)

PIMIENTA = "pimienta-de-prueba-no-usar-en-produccion"


def test_el_mismo_documento_da_el_mismo_hash_para_poder_buscarlo():
    """Si no fuera así, no se podría buscar una persona por su DNI."""
    uno = hash_identificador("12345678", campo="dni", pimienta=PIMIENTA)
    otro = hash_identificador("12345678", campo="dni", pimienta=PIMIENTA)
    assert uno == otro


def test_sin_pimienta_falla_en_vez_de_usar_una_por_defecto():
    """Una pimienta por defecto en el código es lo mismo que no tener pimienta.

    Y el error se descubre tarde: cuando ya hay datos guardados con ella.
    """
    with pytest.raises(SinPimienta):
        hash_identificador("12345678", campo="dni", pimienta="")


def test_cambiar_la_pimienta_cambia_todos_los_hashes():
    """Es lo que hace que la pimienta sirva: sin ella, un DNI de ocho dígitos se revierte con una
    tabla precalculada de 100 millones de valores."""
    con_una = hash_identificador("12345678", campo="dni", pimienta=PIMIENTA)
    con_otra = hash_identificador("12345678", campo="dni", pimienta="otra-pimienta")
    assert con_una != con_otra


def test_el_mismo_valor_en_dos_campos_da_hashes_distintos():
    """Separación de dominios: si el teléfono de alguien fuera '12345678', no puede dar el mismo
    hash que un DNI con ese número."""
    como_dni = hash_identificador("12345678", campo="dni", pimienta=PIMIENTA)
    como_telefono = hash_identificador("12345678", campo="telefono", pimienta=PIMIENTA)
    assert como_dni != como_telefono


def test_el_hash_no_contiene_el_valor_original():
    """Obvio, pero es la única propiedad que hace que valga la pena."""
    documento = "12345678"
    assert documento not in hash_identificador(documento, campo="dni", pimienta=PIMIENTA)


def test_las_formas_de_escribir_lo_mismo_dan_el_mismo_hash():
    """El dueño va a cargar el DNI como se lo dicten, no como lo normalizó nadie."""
    assert normalizar("12.345.678") == "12345678"
    assert normalizar(" 12 345 678 ") == "12345678"
    assert hash_identificador("12.345.678", campo="dni", pimienta=PIMIENTA) == hash_identificador(
        "12345678", campo="dni", pimienta=PIMIENTA
    )


def test_coincide_encuentra_el_documento_guardado():
    guardado = hash_identificador("12345678", campo="dni", pimienta=PIMIENTA)
    assert coincide("12.345.678", guardado, campo="dni", pimienta=PIMIENTA) is True
    assert coincide("87654321", guardado, campo="dni", pimienta=PIMIENTA) is False


def test_coincide_con_otra_pimienta_no_da_verdadero():
    """Una pimienta rotada sin re-hashear los datos no encuentra nada: es el costo de rotar, y hay
    que saberlo antes de rotar, no después."""
    guardado = hash_identificador("12345678", campo="dni", pimienta="pimienta-vieja")
    assert coincide("12345678", guardado, campo="dni", pimienta=PIMIENTA) is False
