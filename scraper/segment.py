"""The focused segment, assembled from the search source into the same contract.

Why it exists: the registry files establishments, not clinical specialties. Of 2,459 registry
prospects exactly one is filed as `MEDICINA FISICA`, and of the 93 physiotherapy clinics
Google returns for the ten busiest Lima districts, none is in that list. The segment the
business wants has to be asked for by name, and it has to land in the same archive as the
registry prospects or the CRM needs two code paths.

Two origins now share one contract, told apart by `origin`:

- `renipress`: the registry, with category, capacity and the registry score.
- `places`: a search result, with Google's category, rating, review activity and website, and
  with `score` null because the registry scoring model does not apply to it.

Nothing here talks to the network during tests, and every query is cached, so re-tuning the
segment, the thresholds or the derived tags costs nothing.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import httpx

from .config import DATA_DIR, OUTPUT_DIR, resolve_search_credentials
from .contract import (
    Contact,
    Coordinates,
    GooglePlace,
    Location,
    Prospect,
    ProspectArchive,
    Source,
    build_archive,
)
from .places import (
    PLACES_ENDPOINT,
    RESULTS_PER_QUERY,
    Chain,
    PlaceRecord,
    cache_name,
    derive_chains,
    fetch_segment,
    unanswered_queries,
)
from .scoring import is_valid_phone
from .text import fold_text

PLACES_DIR = DATA_DIR / "places"
SEGMENT_OUTPUT = OUTPUT_DIR / "segmento_places.json"
# Markers of the segment in Google's own category. Substrings, because Google writes
# `Fisioterapeuta`, `Clínica de fisioterapia`, `Centro de rehabilitación física` and
# `Clínica del dolor`. `Masajista` is deliberately absent: it is a different service, and such
# a place stays in the archive with its category visible instead of being claimed as the
# segment.
SEGMENT_CATEGORY_MARKERS = (
    "fisioterap",
    "rehabilitacion",
    "fisiatria",
    "del dolor",
    "medicina fisica",
    "quiropr",
)


def is_segment_category(category: object) -> bool:
    """True only when the category itself says this is a physiotherapy, rehabilitation or
    pain service.

    Measured over 180 real queries: the five specialties also return
    `Servicio de salud mental`, `Hospital` and `Médico`, so tagging whatever a query returns
    would make the segment tag mean "we asked" instead of "this is the segment".
    """
    folded = fold_text(str(category or ""))
    return any(marker in folded for marker in SEGMENT_CATEGORY_MARKERS)


SEGMENT_TAG = "physiotherapy-segment"
ID_PREFIX = "places:"

# The specialties the business wants to focus on, in the words a clinic would use about
# itself. Measured: these return physiotherapy clinics, while RENIPRESS's own categories
# return none of them.
SPECIALTY_QUERIES = (
    "fisioterapia",
    "centro de rehabilitacion",
    "terapia fisica",
    "medicina fisica y rehabilitacion",
    "clinica del dolor",
)


@dataclass(frozen=True)
class SegmentQuery:
    text: str
    district: str
    department: str


@dataclass
class SegmentReport:
    archive: ProspectArchive
    credits: int = 0
    output_path: Path | None = None
    counts: dict[str, int] = field(default_factory=dict)


def build_queries(
    districts: Iterable[str],
    *,
    department: str,
    specialties: Iterable[str] = SPECIALTY_QUERIES,
) -> list[SegmentQuery]:
    """One query per district and specialty, naming the department to disambiguate.

    `SAN ISIDRO` is a district of Lima and also a town elsewhere, so the department goes in
    the query. When the district *is* the department name it is not repeated.
    """
    ciudad = department.title()
    consultas: list[SegmentQuery] = []
    for district in districts:
        lugar = district.title()
        cola = lugar if lugar == ciudad else f"{lugar} {ciudad}"
        for specialty in specialties:
            consultas.append(
                SegmentQuery(text=f"{specialty} {cola}", district=district, department=department)
            )
    return consultas


def top_districts(
    prospects: Iterable[Prospect], *, department: str, limit: int | None = None
) -> list[str]:
    """The districts where the registry profile concentrates, most first.

    Takes the prospects rather than the finished archive on purpose: the archive may already
    be truncated by `--limit`, and picking the districts from a truncated list would search
    the wrong places. Only `renipress` records count, so the search segment cannot feed back
    into its own district list.
    """
    cuenta = Counter(
        prospect.location.district
        for prospect in prospects
        if prospect.origin == "renipress"
        and prospect.location.department.upper() == department.upper()
    )
    ordenados = [district for district, _ in cuenta.most_common()]
    return ordenados[:limit] if limit is not None else ordenados


def build_segment_prospect(
    record: PlaceRecord,
    chain: Chain,
    *,
    district: str,
    department: str,
) -> Prospect:
    """One search result as a prospect, carrying the tags that make it filterable."""
    coordenadas = (
        Coordinates(latitude=record.latitude, longitude=record.longitude)
        if record.latitude is not None and record.longitude is not None
        else None
    )
    tags = []
    if is_segment_category(record.category):
        tags.append(SEGMENT_TAG)
    if chain.is_chain:
        tags.append("chain")
    if not record.has_website:
        tags.append("no-website")

    return Prospect(
        id=f"{ID_PREFIX}{record.cid}",
        origin="places",
        name=record.name,
        location=Location(
            department=department,
            district=district,
            coordinates=coordenadas,
        ),
        contact=Contact(
            phone=record.phone or "",
            phone_valid=is_valid_phone(record.phone or ""),
            address=record.address or "",
        ),
        google=GooglePlace(
            cid=record.cid,
            query=record.query,
            category=record.category,
            rating=record.rating,
            rating_count=record.rating_count,
            rating_band=record.rating_band,
            reviews_band=record.reviews_band,
            website=record.website,
            position=record.position,
            chain_brand=chain.brand,
            chain_sites=chain.sites,
        ),
        tags=tags,
    )


def _credits_in_cache(cache_dir: Path, queries: Iterable[str]) -> int:
    """What the cached answers cost when they were fetched, for cost accounting."""
    total = 0
    for query in queries:
        archivo = Path(cache_dir) / cache_name(query)
        if archivo.exists():
            total += int(json.loads(archivo.read_text(encoding="utf-8")).get("credits") or 0)
    return total


def run_segment(
    *,
    districts: Iterable[str],
    department: str = "LIMA",
    api_key: str | None = None,
    cache_dir: Path = PLACES_DIR,
    output_path: Path | None = None,
    specialties: Iterable[str] = SPECIALTY_QUERIES,
    refresh: bool = False,
    num: int = RESULTS_PER_QUERY,
    log=print,
) -> SegmentReport:
    """Fetch the segment, build its archive and write it. Nothing is sent anywhere."""
    if api_key is None:
        _provider, api_key = resolve_search_credentials()

    especialidades = list(specialties)
    distritos = list(districts)
    consultas = build_queries(distritos, department=department, specialties=especialidades)
    log(
        f"  segmento: {len(distritos)} distritos x {len(especialidades)} especialidades "
        f"= {len(consultas)} consultas"
    )

    with httpx.Client(timeout=30) as client:
        registros = fetch_segment(
            client,
            [consulta.text for consulta in consultas],
            api_key=api_key,
            cache_dir=cache_dir,
            num=num,
            refresh=refresh,
        )

    cadenas = derive_chains(registros)
    por_consulta = {consulta.text: consulta for consulta in consultas}
    prospectos = [
        build_segment_prospect(
            registro,
            cadenas[registro.cid],
            district=por_consulta[registro.query].district,
            department=department,
        )
        for registro in registros
        if registro.query in por_consulta
    ]

    archivo = build_archive(
        prospectos,
        sources=[
            Source(
                dataset="places",
                url=PLACES_ENDPOINT,
                queries=[consulta.text for consulta in consultas],
            )
        ],
    )

    destino = Path(output_path) if output_path else SEGMENT_OUTPUT
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(archivo.model_dump_json(indent=2), encoding="utf-8")

    con_web = sum(1 for p in prospectos if p.google and p.google.website)
    sin_respuesta = unanswered_queries(Path(cache_dir), [c.text for c in consultas])
    del_segmento = [p for p in prospectos if SEGMENT_TAG in p.tags]
    conteos = {
        "clinicas_del_segmento": len(del_segmento),
        "fuera_de_categoria": len(prospectos) - len(del_segmento),
        "con_telefono": sum(1 for p in prospectos if p.contact.phone_valid),
        "con_sitio_web": con_web,
        "con_coordenadas": sum(1 for p in prospectos if p.location.coordinates),
        "cadenas": sum(1 for p in prospectos if "chain" in p.tags),
        "resenas_altas": sum(1 for p in del_segmento if p.google and p.google.reviews_band == "alta"),
        "consultas_totales": len(consultas),
        "consultas_sin_respuesta": len(sin_respuesta),
        "creditos": _credits_in_cache(Path(cache_dir), [c.text for c in consultas]),
    }
    log(f"escrito {destino} con {archivo.total} clinicas del segmento")
    for clave, valor in conteos.items():
        log(f"  {clave}: {valor}")
    if sin_respuesta:
        # Una corrida incompleta tiene que decirlo: si no, alguien lee 200 clinicas como si
        # fueran el segmento entero. Volver a correr no vuelve a pagar lo ya cacheado.
        log(
            f"  AVISO: {len(sin_respuesta)} de {len(consultas)} consultas no respondieron, "
            "asi que el segmento esta INCOMPLETO. Volve a correr: solo se pagan las que faltan."
        )
        log(f"  sin respuesta: {', '.join(sin_respuesta[:5])}{' ...' if len(sin_respuesta) > 5 else ''}")

    return SegmentReport(archive=archivo, credits=conteos["creditos"], output_path=destino, counts=conteos)
