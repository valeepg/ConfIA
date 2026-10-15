"""Protección de datos personales antes de que toquen Firestore.

Qué hace este módulo y qué no:

- **Identificadores que solo hay que comparar** (el DNI, un número de documento): se guardan
  **hasheados**, con una pimienta que vive en Secret Manager. Irreversibles: si se filtra la base,
  no se puede volver al DNI. Y siguen sirviendo para buscar, porque el mismo DNI con la misma
  pimienta da el mismo hash.
- **Datos que una persona tiene que leer** (el nombre del contacto con el que habla el vendedor):
  esos **no** se pueden hashear, porque hay que mostrarlos. Van cifrados de forma reversible, y eso
  está especificado pero **no implementado acá** (necesita una dependencia de cifrado y decidir por
  dónde se escribe; ver `docs/datos-personales.md` §4).

Por qué la pimienta no está en el código ni en la base:

Un hash sin pimienta se rompe con una tabla precalculada: los DNI peruanos son ocho dígitos, o sea
100 millones de valores, y eso se recorre en minutos. Con pimienta, el atacante necesita además el
secreto. Por eso la pimienta va en **Secret Manager**, con un permiso **separado** del de Firestore:
tener acceso de lectura a la base no alcanza para probar un DNI.

Y por eso tampoco se cifra en el navegador: una clave que se usa en la página viaja al navegador, o
sea que está en la máquina de cualquiera que abra las herramientas de desarrollo. El dato personal
se escribe **desde el backend**, que es el único que tiene la pimienta.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Final

# Separación de dominios: la misma pimienta se usa para el DNI y para el teléfono, pero el prefijo
# hace que el hash de un DNI no pueda confundirse con el de un teléfono del mismo valor. Sin esto,
# dos campos distintos con el mismo string dan el mismo hash y eso filtra información.
PREFIJO: Final = "confia2:personal:v1:"

SECRETO_PIMIENTA: Final = "PERSONAL_DATA_PEPPER"

# La clave del cifrado reversible va en su propio secreto, **separada de la pimienta**: se rotan por
# motivos distintos y con costos distintos. Rotar la pimienta rompe las busquedas; rotar esta clave no
# rompe nada si se guarda la anterior (ver `descifrar_con_rotacion`).
SECRETO_CLAVE: Final = "PERSONAL_DATA_KEY"


class SinPimienta(RuntimeError):
    """Se pidió un hash y no hay pimienta configurada.

    Se falla en vez de usar una por defecto: una pimienta por defecto en el código es lo mismo que
    no tener pimienta, y el error se descubre tarde, cuando ya hay datos guardados con ella.
    """


class SinClave(RuntimeError):
    """Se pidió cifrar o descifrar y no hay clave configurada."""


def hash_identificador(valor: str, *, campo: str, pimienta: str) -> str:
    """Hash irreversible de un identificador, para comparar sin poder volver al valor.

    `campo` (por ejemplo `dni` o `telefono`), se incluye en el hash para que el mismo valor en dos
    campos distintos no produzca el mismo resultado.
    """
    if not pimienta:
        raise SinPimienta(
            f"falta la pimienta ({SECRETO_PIMIENTA} en Secret Manager): sin ella el hash de un DNI de "
            "ocho dígitos se revierte con una tabla precalculada"
        )
    material = f"{PREFIJO}{campo}:{normalizar(valor)}".encode()
    return hmac.new(pimienta.encode(), material, hashlib.sha256).hexdigest()


def coincide(valor: str, esperado: str, *, campo: str, pimienta: str) -> bool:
    """Compara un valor con un hash guardado, en tiempo constante.

    `hmac.compare_digest` y no `==`: comparar dos strings con `==` corta en el primer byte distinto,
    y ese tiempo distinto alcanza para adivinar el hash byte por byte.
    """
    return hmac.compare_digest(hash_identificador(valor, campo=campo, pimienta=pimienta), esperado)


def normalizar(valor: str) -> str:
    """Quita espacios y guiones para que '12.345.678' y '12345678' sean el mismo documento."""
    return "".join(caracter for caracter in str(valor) if caracter.isalnum()).lower()


def pimienta_del_entorno() -> str:
    """La pimienta, del entorno. Falla si no está, en vez de inventar una."""
    return os.getenv(SECRETO_PIMIENTA, "")


def pimienta_del_secret_manager(
    *, proyecto: str, nombre: str = SECRETO_PIMIENTA, version: str = "latest"
) -> str:
    """Lee la pimienta de Secret Manager.

    Es una función y no una constante a propósito: el módulo se puede importar y probar sin la
    librería de Secret Manager ni credenciales, y el que la necesite la pide una vez y la pasa.

    **No la cachees en una variable global de larga vida**: rotar la pimienta tiene que obligar a
    volver a leerla, o la rotación no sirve de nada.
    """
    return _leer_secreto(proyecto=proyecto, nombre=nombre, version=version)


def _leer_secreto(*, proyecto: str, nombre: str, version: str = "latest") -> str:
    from google.cloud import secretmanager  # import perezoso: solo si se usa

    cliente = secretmanager.SecretManagerServiceClient()
    ruta = f"projects/{proyecto}/secrets/{nombre}/versions/{version}"
    return cliente.access_secret_version(name=ruta).payload.data.decode()


# ── Cifrado reversible: los campos que hay que poder LEER ────────────────────────────────────────
#
# El DNI se hashea porque solo hay que compararlo. El **nombre del contacto y su teléfono** no: el
# vendedor los tiene que leer para hablar con la persona. Esos van cifrados y se descifran al leerlos.
#
# Fernet (AES-CBC + HMAC, de la librería `cryptography`) y no "cifrado propio": un cifrado propio
# casi siempre sale mal de una forma que no se nota hasta que alguien lo rompe.
#
# **Fernet es aleatorio a propósito**: el mismo nombre cifrado dos veces da dos textos distintos. Eso
# es lo que se quiere para privacidad, y también significa que **no se puede buscar por ese campo**:
# Firestore no puede hacer `where` sobre un texto cifrado. Si hay que buscar por un dato personal, va
# hasheado (y entonces solo se puede buscar por igualdad, nunca por rango ni por prefijo).


def cifrar(valor: str, *, clave: str) -> str:
    """Cifra un campo que hay que poder leer de vuelta."""
    from cryptography.fernet import Fernet  # import perezoso: no todos los despliegues lo necesitan

    if not clave:
        raise SinClave(
            f"falta la clave ({SECRETO_CLAVE} en Secret Manager): sin ella no se puede cifrar ni "
            "descifrar, y guardar el valor en claro no es una opción"
        )
    return Fernet(clave.encode()).encrypt(valor.encode()).decode()


def descifrar(token: str, *, clave: str) -> str:
    """Descifra un campo para mostrarlo.

    Si el token fue alterado, o la clave no es la que lo cifró, **falla en vez de devolver algo**:
    Fernet es autenticado, así que un dato manipulado no se puede leer como si fuera bueno.
    """
    from cryptography.fernet import Fernet

    if not clave:
        raise SinClave(f"falta la clave ({SECRETO_CLAVE} en Secret Manager)")
    return Fernet(clave.encode()).decrypt(token.encode()).decode()


def descifrar_con_rotacion(token: str, *, claves: list[str]) -> str:
    """Descifra probando varias claves, de la más nueva a la más vieja.

    Es lo que permite rotar la clave sin perder los datos: se agrega la nueva al principio, se
    descifra con ella lo nuevo, y lo viejo se sigue leyendo con las anteriores hasta re-cifrarlo.
    """
    from cryptography.fernet import Fernet, InvalidToken

    if not claves:
        raise SinClave(f"falta la clave ({SECRETO_CLAVE} en Secret Manager)")
    error: Exception | None = None
    for clave in claves:
        try:
            return Fernet(clave.encode()).decrypt(token.encode()).decode()
        except InvalidToken as fallo:  # se prueba la siguiente, no se pierde el dato
            error = fallo
    raise ValueError("ninguna clave pudo descifrar el dato (¿se perdió la clave vieja?)") from error


def clave_del_secret_manager(*, proyecto: str, nombre: str = SECRETO_CLAVE, version: str = "latest") -> str:
    """La clave de cifrado, de Secret Manager. Falla si no está, en vez de inventar una."""
    return _leer_secreto(proyecto=proyecto, nombre=nombre, version=version)
