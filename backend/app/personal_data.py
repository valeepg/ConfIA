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


class SinPimienta(RuntimeError):
    """Se pidió un hash y no hay pimienta configurada.

    Se falla en vez de usar una por defecto: una pimienta por defecto en el código es lo mismo que
    no tener pimienta, y el error se descubre tarde, cuando ya hay datos guardados con ella.
    """


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
    from google.cloud import secretmanager  # import perezoso: solo si se usa

    cliente = secretmanager.SecretManagerServiceClient()
    ruta = f"projects/{proyecto}/secrets/{nombre}/versions/{version}"
    return cliente.access_secret_version(name=ruta).payload.data.decode()
