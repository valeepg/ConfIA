"""Command line entry point.

    uv run python -m scraper                      # RENIPRESS + Consulta A
    uv run python -m scraper --include-procedures # adds the ozone detection
    uv run python -m scraper --limit 50 --refresh
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import OUTPUT_DIR, RAW_DIR
from .pipeline import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="confia2-scraper",
        description=(
            "Ingesta de fuentes publicas de SUSALUD para el motor de outbound B2B "
            "(Modulo 1: RF-01 extraccion, RF-02 normalizacion)."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "prospect_mock.json",
        help="ruta del JSON de prospectos (por defecto data/out/prospect_mock.json)",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="carpeta de cache de los CSV crudos (por defecto data/raw)",
    )
    parser.add_argument(
        "--include-procedures",
        action="store_true",
        help="cruce con Consulta G para detectar IPRESS que ya hacen ozonoterapia (descarga pesada)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="ignora la cache local y vuelve a descargar los CSV",
    )
    parser.add_argument("--limit", type=int, default=None, help="emite solo los N prospectos mejor puntuados")
    parser.add_argument(
        "--draft-limit",
        type=int,
        default=None,
        help="redacta borradores de contacto para los N mejor puntuados (nunca envia nada)",
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="modelo LiteLLM como proveedor/modelo (por defecto CONFIA2_LLM_MODEL o gemini/gemini-2.0-flash)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="plantilla del mensaje, editable por el dueño (por defecto templates/outreach-oaas.md)",
    )
    parser.add_argument(
        "--segment-places",
        action="store_true",
        help="ademas del padron, busca el segmento de fisioterapia/rehabilitacion en Google Places",
    )
    parser.add_argument(
        "--segment-districts",
        default=None,
        help="distritos separados por coma; si no se pasa, los N con mas prospectos del departamento",
    )
    parser.add_argument(
        "--segment-department", default="LIMA", help="departamento del segmento (por defecto LIMA)"
    )
    parser.add_argument(
        "--segment-top",
        type=int,
        default=None,
        help="cuantos distritos tomar; por defecto TODOS los del departamento",
    )
    parser.add_argument(
        "--segment-output",
        type=Path,
        default=None,
        help="ruta del JSON del segmento (por defecto data/out/segmento_places.json)",
    )
    parser.add_argument(
        "--call-sheet",
        type=int,
        default=None,
        help="ademas del segmento, escribe la hoja de llamados en Markdown con las N mejores",
    )
    parser.add_argument(
        "--call-sheet-output",
        type=Path,
        default=None,
        help="ruta de la hoja (por defecto data/out/hoja_de_llamados.md)",
    )
    parser.add_argument(
        "--firestore-project",
        default=None,
        help="proyecto de Firebase donde escribir los prospectos; sin esto solo se escriben archivos",
    )
    parser.add_argument(
        "--firestore-collection",
        default=None,
        help="coleccion destino (por defecto prospects)",
    )
    parser.add_argument(
        "--repair-leads",
        action="store_true",
        help=(
            "no scrapea nada: recorre la coleccion de la pantalla y repara lo derivable de cada "
            "documento (la marca `stale` y la etiqueta de segmento). No borra nada y no gasta busqueda"
        ),
    )
    parser.add_argument(
        "--seen-since",
        default=None,
        help=(
            "con --repair-leads: instante ISO desde el que se considera visto "
            "(por defecto, el `recorded_at` de la ultima ingesta en confia2_meta)"
        ),
    )
    parser.add_argument("--year", type=int, default=None, help="anio del recurso a usar (por defecto, el mas reciente)")
    parser.add_argument("--period", type=int, default=None, help="periodo del recurso (mes o trimestre) a usar")
    return parser


def _reparar_leads(args) -> int:
    """Repara la coleccion de la pantalla **sin volver a scrapear**: es la unica salida que no gasta
    creditos de busqueda, y por eso vale la pena que exista como modo aparte."""
    from .firestore import firestore_client, last_view_watermark
    from .ui_projection import LEADS_COLLECTION, repair_leads

    if not args.firestore_project:
        print("error: --repair-leads necesita --firestore-project", file=sys.stderr)
        return 1

    store = firestore_client(args.firestore_project)
    visto_desde = args.seen_since or last_view_watermark(store)
    if not visto_desde:
        # Sin instante de corte, `None` marcaria TODO como viejo: es el unico error irreversible de
        # este modo, asi que se corta aca en vez de adivinar.
        print(
            "error: no hay --seen-since y confia2_meta no tiene marca de agua de una corrida "
            "anterior; pasalo explicito para no marcar todo como viejo",
            file=sys.stderr,
        )
        return 1

    print(f"marcando lo anterior a {visto_desde} en {LEADS_COLLECTION} (no se borra ninguno)...")
    counts = repair_leads(client=store, seen_since=visto_desde, collection=LEADS_COLLECTION)
    for key, value in counts.items():
        print(f"{key}: {value}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.repair_leads:
            return _reparar_leads(args)
        report = run(
            output_path=args.output,
            include_procedures=args.include_procedures,
            refresh=args.refresh,
            limit=args.limit,
            year=args.year,
            period=args.period,
            draft_limit=args.draft_limit,
            llm_model=args.llm_model,
            template_path=args.template,
            segment_places=args.segment_places,
            segment_department=args.segment_department,
            segment_districts=(
                [d.strip() for d in args.segment_districts.split(",") if d.strip()]
                if args.segment_districts
                else None
            ),
            segment_top=args.segment_top,
            segment_output=args.segment_output,
            call_sheet_limit=args.call_sheet,
            call_sheet_output=args.call_sheet_output,
            firestore_project=args.firestore_project,
            firestore_collection=args.firestore_collection or "prospects",
            raw_dir=args.raw_dir,
        )
    except Exception as error:  # surfaced as a non-zero exit for scripts and CI
        print(f"error: {error}", file=sys.stderr)
        return 1

    for key, value in report.counts.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
