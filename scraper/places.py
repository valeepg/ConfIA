"""Google Places as a source: the segment the registry cannot see.

Measured on 2026-10-14: RENIPRESS classifies **establishments**, not clinical specialties,
so exactly one clinic out of 2,459 is filed as `MEDICINA FISICA` and none of the 93
physiotherapy clinics Google returns for the ten busiest Lima districts is in the
registry-based list. For the focused segment the search source is therefore the primary one
and the registry is at best an enrichment.

Two rules this module keeps:

1. **A credit is never spent twice on the same question.** The raw provider answer is cached
   per query under `data/places/`, so re-analysing a segment, changing thresholds or adding
   derived fields costs nothing. Losing that cache already cost this project ten credits once.
2. **Bands are derived here, not in the reader.** `reviews_band` and `rating_band` turn two
   numbers into three filterable values, so the CRM does not have to agree on thresholds by
   convention.

The provider is the same one the rest of the project uses, so its key and its degradation
behaviour are already documented. Nothing here talks to the network during tests.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from .enrichment import phone_numbers
from .text import fold_text

PLACES_ENDPOINT = "https://google.serper.dev/places"
RESULTS_PER_QUERY = 20
CACHE_SUFFIX = ".json"

# Statuses worth trying again. A 401, a 403 or a 400 are not: insisting on a wrong key or a
# malformed request only wastes time.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5

# Words that are a type of business rather than a brand. They must not become the brand, or
# `CENTRO MEDICO` would look like the largest chain in Peru.
_GENERIC_WORDS = frozenset(
    {
        "centro", "centros", "clinica", "clinicas", "fisioterapia", "fisioterapeuta",
        "rehabilitacion", "terapia", "terapias", "fisica", "fisico", "salud", "medical",
        "medico", "medicos", "medicina", "instituto", "consultorio", "consultorios",
        "servicio", "servicios", "spa", "masaje", "masajes", "sede", "sedes", "grupo",
        "policlinico", "dental", "odontologia", "de", "del", "la", "el", "los", "las", "y",
        # Palabras de servicio o adjetivos: medido, `terapia del dolor` se repite dos veces y no
        # es una marca. Sin esto el detector la reporta como una cadena de dos sedes.
        "dolor", "vida", "casa", "comunidad", "integral", "especializado", "profesional",
        "internacional", "hospital", "mental", "bienestar", "movimiento", "total", "calido",
    }
)


@dataclass(frozen=True)
class PlaceRecord:
    """One place as the provider describes it, plus the query that surfaced it."""

    cid: str
    name: str
    category: str | None = None
    phone: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    website: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    position: int | None = None
    query: str = ""

    @property
    def has_website(self) -> bool:
        return bool(self.website)

    @property
    def reviews_band(self) -> str:
        return reviews_band(self.rating_count)

    @property
    def rating_band(self) -> str:
        return rating_band(self.rating)


@dataclass(frozen=True)
class Chain:
    """A brand with more than one site: one conversation, several placements."""

    brand: str | None
    sites: int
    # How the grouping was established: `phone`, `name` or None for a single site.
    evidence: str | None = None

    @property
    def is_chain(self) -> bool:
        return self.sites > 1


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: object, cast):
    if value is None or value == "":
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def _to_record(item: dict, query: str) -> PlaceRecord:
    return PlaceRecord(
        cid=str(item.get("cid") or item.get("title") or ""),
        name=str(item.get("title") or "").strip(),
        category=_text(item.get("category")),
        phone=_text(item.get("phoneNumber")),
        address=_text(item.get("address")),
        latitude=_number(item.get("latitude"), float),
        longitude=_number(item.get("longitude"), float),
        website=_text(item.get("website")),
        rating=_number(item.get("rating"), float),
        rating_count=_number(item.get("ratingCount"), int),
        position=_number(item.get("position"), int),
        query=query,
    )


def reviews_band(count: int | None) -> str:
    """How much patient activity the reviews suggest, as three filterable values."""
    if count is None:
        return "sin datos"
    if count == 0:
        return "sin reseñas"
    if count < 20:
        return "baja"
    if count <= 100:
        return "media"
    return "alta"


def rating_band(rating: float | None) -> str:
    if rating is None:
        return "sin datos"
    if rating < 4.0:
        return "baja"
    if rating <= 4.5:
        return "buena"
    return "alta"


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", fold_text(name)).strip()


def distinctive_tokens(name: str) -> list[str]:
    """The words of a name that are not a type of business."""
    return [
        token
        for token in re.split(r"[^a-z0-9]+", fold_text(name))
        if len(token) > 2 and token not in _GENERIC_WORDS
    ]


def _common_prefix(names: list[str]) -> str:
    """The words every name in the group starts with, which is the closest thing to a brand
    label that a group sharing a phone number has."""
    partes = [_normalize_name(name).split() for name in names]
    comunes: list[str] = []
    for palabras in zip(*partes):
        if len(set(palabras)) == 1:
            comunes.append(palabras[0])
        else:
            break
    return " ".join(comunes)


def derive_chains(records: tuple[PlaceRecord, ...]) -> dict[str, Chain]:
    """Group sites by evidence that cannot be argued with, and nothing else.

    Two exact signals, in this order:

    1. **The same published phone number.** Measured on the Lima segment: `Centro Médico OSI`
       has eight branches in the call sheet and all of them publish `(01) 7390888`, while the
       name rule missed every one of them because each branch name carries its district. Six of
       the groups were found by the phone alone.
    2. **The same normalized name with at least one distinctive word.** This is what the two
       earlier heuristics were replaced with: grouping by the first word produced `ESPECIALIZADO`
       with 60 sites in the registry and `fisio` with 34 here, and an exact repetition of
       `medicina fisica y rehabilitacion` is a generic descriptor, not a brand.

    Places writes titles for search (`Fisioterapia X - Miraflores`), not as brands, so anything
    weaker than these two signals would only inflate the number.
    """
    por_nombre: dict[str, set[str]] = {}
    por_telefono: dict[str, set[str]] = {}
    for record in records:
        clave = _normalize_name(record.name)
        if clave and distinctive_tokens(record.name):
            por_nombre.setdefault(clave, set()).add(record.cid)
        for numero in phone_numbers(record.phone):
            por_telefono.setdefault(numero, set()).add(record.cid)

    resultado: dict[str, Chain] = {}
    for record in records:
        clave = _normalize_name(record.name)
        grupo_nombre = por_nombre.get(clave, set())
        grupos_telefono = [por_telefono.get(numero, set()) for numero in phone_numbers(record.phone)]
        grupo_telefono = max(grupos_telefono, key=len) if grupos_telefono else set()

        if len(grupo_nombre) > 1 and len(grupo_nombre) >= len(grupo_telefono):
            resultado[record.cid] = Chain(brand=clave, sites=len(grupo_nombre), evidence="name")
        elif len(grupo_telefono) > 1:
            hermanos = [otro.name for otro in records if otro.cid in grupo_telefono]
            resultado[record.cid] = Chain(
                brand=_common_prefix(hermanos) or None,
                sites=len(grupo_telefono),
                evidence="phone",
            )
        else:
            # Un lugar es al menos una sede: el 0 seria un cero falso.
            resultado[record.cid] = Chain(brand=None, sites=1)
    return resultado


def search_places(
    client: httpx.Client,
    query: str,
    *,
    api_key: str,
    num: int = RESULTS_PER_QUERY,
) -> tuple[PlaceRecord, ...]:
    response = client.post(
        PLACES_ENDPOINT,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "gl": "pe", "hl": "es", "num": num},
    )
    response.raise_for_status()
    return tuple(_to_record(item, query) for item in response.json().get("places") or [])


def _fetch_one(
    client: httpx.Client,
    query: str,
    *,
    api_key: str,
    num: int,
    attempts: int = RETRY_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
) -> dict | None:
    """One query, retried while the failure is transient. `None` means it never answered.

    Measured: a single 500 from the provider killed a 275-query run whose earlier answers were
    already paid for. A batch has to survive one bad response, so an exhausted query is skipped
    instead of ending the run, and only the queries that never answered are reported as such.
    """
    for intento in range(attempts):
        respuesta = client.post(
            PLACES_ENDPOINT,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "gl": "pe", "hl": "es", "num": num},
        )
        if respuesta.status_code == 200:
            return respuesta.json()
        if respuesta.status_code not in RETRYABLE_STATUS:
            respuesta.raise_for_status()
        if intento + 1 < attempts:
            sleep(RETRY_BACKOFF_SECONDS * (intento + 1))
    return None


def cache_name(query: str) -> str:
    """The cache file for a query: the query itself, made safe for a file name."""
    return re.sub(r"[^a-z0-9]+", "-", fold_text(query)).strip("-") + CACHE_SUFFIX


def fetch_segment(
    client: httpx.Client,
    queries: list[str],
    *,
    api_key: str,
    cache_dir: Path,
    num: int = RESULTS_PER_QUERY,
    refresh: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[PlaceRecord, ...]:
    """Run every query once, cache the raw answer, and return the deduplicated segment.

    The cached payload keeps the `credits` the provider reported, so the cost of a segment can
    be audited later without spending anything. A query that never answered is skipped and
    leaves no cache file, which is what `unanswered_queries` looks for.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    vistos: dict[str, PlaceRecord] = {}

    for query in queries:
        archivo = cache_dir / cache_name(query)
        if archivo.exists() and not refresh:
            crudo = json.loads(archivo.read_text(encoding="utf-8"))
        else:
            crudo = _fetch_one(client, query, api_key=api_key, num=num, sleep=sleep)
            if crudo is None:
                continue
            archivo.write_text(json.dumps(crudo, ensure_ascii=False), encoding="utf-8")

        for item in crudo.get("places") or []:
            registro = _to_record(item, query)
            if registro.cid:
                vistos.setdefault(registro.cid, registro)

    return tuple(vistos.values())


def unanswered_queries(cache_dir: Path, queries: list[str]) -> list[str]:
    """The queries that never produced an answer: they leave no cache file behind."""
    return [
        query
        for query in queries
        if not (Path(cache_dir) / cache_name(query)).exists()
    ]
