"""The call sheet: turn ranked data into the thing a salesperson actually uses.

A JSON contract is for machines. The owner needs a list he can read on a Monday morning:
which clinics to call, in what order, with the number in front of him and the reason that
clinic is on the list at all.

The ranking rule is evidence of real patient activity, and nothing else is allowed in:

1. the clinic must be in the segment (its Google category says physiotherapy, rehabilitation
   or pain) and have a phone, because a worklist you cannot call is not a worklist;
2. more reviews first, then a better rating, then the name for a stable order.

Deliberately absent from the ranking: how much we would like to sell to them. The sheet says
what is known, and the caveats travel with it so nobody reads more into it than there is.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .config import OUTPUT_DIR
from .contract import Prospect, ProspectArchive
from .segment import SEGMENT_TAG

DEFAULT_LIMIT = 30
TITLE = "Hoja de llamados"
CALL_SHEET_OUTPUT = OUTPUT_DIR / "hoja_de_llamados.md"


def rank_for_calling(
    prospects: list[Prospect],
    *,
    limit: int | None = None,
    only_segment: bool = True,
) -> list[Prospect]:
    """Order the clinics by evidence of patient activity, ready to be called."""
    candidatos = [
        prospect
        for prospect in prospects
        if prospect.contact.phone_valid
        and (not only_segment or SEGMENT_TAG in prospect.tags)
    ]
    candidatos.sort(
        key=lambda prospect: (
            -(prospect.google.rating_count or 0) if prospect.google else 0,
            -(prospect.google.rating or 0) if prospect.google else 0,
            prospect.name,
        )
    )
    return candidatos[:limit] if limit is not None else candidatos


def _row(index: int, prospect: Prospect) -> str:
    google = prospect.google
    reseñas = f"{google.rating_count}" if google and google.rating_count else "—"
    rating = f"{google.rating}" if google and google.rating is not None else "—"
    categoria = (google.category if google and google.category else "—").replace("|", "/")
    cadena = f"si ({google.chain_sites})" if google and google.chain_sites > 1 else "no"
    web = "si" if google and google.website else "no"
    return (
        f"| {index} | {prospect.name.replace('|', '/')} | {prospect.location.district.title()} "
        f"| {prospect.contact.phone} | {reseñas} | {rating} | {categoria} | {web} | {cadena} |"
    )


def build_call_sheet(
    archive: ProspectArchive,
    *,
    limit: int = DEFAULT_LIMIT,
    generated_at: str | None = None,
) -> str:
    """The readable worklist, with the caveats that travel with the data."""
    seleccion = rank_for_calling(archive.prospects, limit=limit)
    momento = generated_at or datetime.now(timezone.utc).isoformat(timespec="minutes")
    fuentes = ", ".join(sorted({source.dataset for source in archive.sources})) or "—"

    lineas = [
        f"# {TITLE}",
        "",
        f"Generada el {momento} · fuente: {fuentes} · mostrando **{len(seleccion)}** "
        f"de {archive.total} prospectos.",
        "",
        "**Cómo se ordenó:** primero las que tienen más reseñas, después mejor rating, después por",
        "nombre. Solo entran las que están en el segmento y tienen teléfono válido: una lista que no",
        "se puede llamar no es una lista.",
        "",
        "| # | Clínica | Distrito | Teléfono | Reseñas | Rating | Categoría | Web | Cadena |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    lineas += [_row(i, p) for i, p in enumerate(seleccion, start=1)]
    lineas += [
        "",
        "## Antes de usarla",
        "",
        "- **Las reseñas son actividad de pacientes, no intención de compra.** Son el mejor",
        "  indicador disponible de que la clínica atiende gente, y nada más que eso.",
        "- **Ninguna clínica de esta lista está en el padrón de SUSALUD.** Es otro segmento: por eso",
        "  no tiene categoría I-3/I-4 ni dato de capacidad médica.",
        "- **Los datos vienen de Google Places y tienen restricción de caché.** El identificador",
        "  `cid` se puede conservar; el resto conviene releerlo periódicamente en vez de archivarlo",
        "  como fuente permanente.",
        "- **Un LLM no redacta nada que salga de acá sin aprobación humana**, y este módulo no envía",
        "  mensajes a nadie.",
        "",
    ]
    return "\n".join(lineas)


def write_call_sheet(
    archive: ProspectArchive,
    destination: Path,
    *,
    limit: int = DEFAULT_LIMIT,
) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_call_sheet(archive, limit=limit), encoding="utf-8")
    return destination
