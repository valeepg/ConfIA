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


# --- cifrado reversible: los campos que hay que poder LEER --------------------- #
#
# El DNI se hashea porque solo hay que compararlo. El nombre del contacto y su teléfono no: el
# vendedor los tiene que leer. Esos van cifrados.


@pytest.fixture
def clave():
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


def test_lo_que_se_cifra_se_puede_leer_de_vuelta(clave):
    from app.personal_data import cifrar, descifrar

    original = "María Quispe Huamán"
    token = cifrar(original, clave=clave)
    assert descifrar(token, clave=clave) == original


def test_el_texto_cifrado_no_deja_ver_el_valor(clave):
    """Es la única propiedad que hace que valga la pena cifrar."""
    from app.personal_data import cifrar

    token = cifrar("María Quispe Huamán", clave=clave)
    assert "María" not in token
    assert "Quispe" not in token


def test_dos_veces_el_mismo_dato_da_dos_textos_distintos(clave):
    """Fernet es aleatorio a propósito: si el mismo nombre diera siempre el mismo texto, comparar dos
    documentos revelaría que son la misma persona. Las dos se descifran igual.

    Y de acá sale la consecuencia que hay que tener clara: **no se puede buscar por un campo
    cifrado**. Firestore no puede hacer `where` sobre esto.
    """
    from app.personal_data import cifrar, descifrar

    uno = cifrar("María Quispe", clave=clave)
    otro = cifrar("María Quispe", clave=clave)
    assert uno != otro
    assert descifrar(uno, clave=clave) == descifrar(otro, clave=clave) == "María Quispe"


def test_un_dato_manipulado_no_se_puede_leer(clave):
    """Fernet es autenticado: si alguien cambia el texto cifrado, falla en vez de devolver basura
    como si fuera un dato bueno.
    """
    from cryptography.fernet import InvalidToken

    from app.personal_data import cifrar, descifrar

    token = cifrar("99999999", clave=clave)
    manipulado = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(InvalidToken):
        descifrar(manipulado, clave=clave)


def test_con_la_clave_equivocada_no_se_puede_leer(clave):
    from cryptography.fernet import Fernet, InvalidToken

    from app.personal_data import cifrar, descifrar

    token = cifrar("un secreto", clave=clave)
    with pytest.raises(InvalidToken):
        descifrar(token, clave=Fernet.generate_key().decode())


def test_sin_clave_falla_en_vez_de_guardar_en_claro(clave):
    """Si falta la clave, guardar el valor en claro no es una opción: se falla."""
    from app.personal_data import SinClave, cifrar, descifrar

    with pytest.raises(SinClave):
        cifrar("algo", clave="")
    with pytest.raises(SinClave):
        descifrar("algo", clave="")


def test_rotar_la_clave_no_pierde_los_datos_ya_guardados(clave):
    """Este es el test que hace útil el cifrado en producción: al rotar se prueba la nueva y después
    las anteriores, así que lo viejo se sigue leyendo hasta re-cifrarlo.

    Sin esto, rotar la clave equivaldría a perder todos los teléfonos y nombres guardados.
    """
    from cryptography.fernet import Fernet

    from app.personal_data import cifrar, descifrar_con_rotacion

    vieja = clave
    nueva = Fernet.generate_key().decode()

    guardado_con_la_vieja = cifrar("987654321", clave=vieja)

    # se rota: la nueva se prueba primero, la vieja sigue estando para lo que ya estaba guardado
    assert descifrar_con_rotacion(guardado_con_la_vieja, claves=[nueva, vieja]) == "987654321"
    # y lo nuevo se cifra con la nueva, y solo la nueva lo puede leer
    lo_nuevo = cifrar("111222333", clave=nueva)
    assert descifrar_con_rotacion(lo_nuevo, claves=[nueva, vieja]) == "111222333"


def test_si_se_perdio_todas_las_claves_avisa(clave):
    """Un dato que no se puede descifrar es un dato perdido, y hay que decirlo con esas palabras."""
    from cryptography.fernet import Fernet

    from app.personal_data import cifrar, descifrar_con_rotacion

    guardado = cifrar("algo", clave=clave)
    with pytest.raises(ValueError, match="clave"):
        descifrar_con_rotacion(guardado, claves=[Fernet.generate_key().decode()])
