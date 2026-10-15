"""End-to-end ingestion: resolve, download, normalize, score, emit JSON (RF-01/RF-02)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx

from pydantic import ValidationError

from .capacity import consolidate_capacity
from .callsheet import CALL_SHEET_OUTPUT, rank_for_calling, write_call_sheet
from .ckan import DatasetUnavailable, Resource, resolve_resource
from .config import (
    DATASET_FILE_PATTERN,
    DRAFTS_DIR,
    HTTP_TIMEOUT_SECONDS,
    OUTREACH_TEMPLATE,
    OUTPUT_DIR,
    RAW_DIR,
    USER_AGENT,
    resolve_llm_endpoint,
)
from .contract import Prospect, ProspectArchive, Source, build_archive, build_prospect
from .copilot import DraftSubmission, draft_outreach, load_template, submission_to_dict
from .fetch import Download, download, file_sha256, newest_matching
from .firestore import (
    DEFAULT_COLLECTION,
    firestore_client,
    upsert,
    write_metadata,
    write_submissions,
    write_watermark,
)
from .procedures import OzoneTherapy, detect_ozone_therapy
from .renipress import filter_target_profile, read_renipress
from .scoring import TOTAL_WEIGHT, score_prospect
from .segment import SEGMENT_OUTPUT, run_segment, top_districts
from .ui_projection import repair_leads, write_approvals, write_leads


@dataclass
class PipelineReport:
    archive: ProspectArchive
    sources: list[Download] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    output_path: Path | None = None


def _filename(url: str) -> str:
    return url.rsplit("/", 1)[-1] or "source.csv"


def _source_meta(download: Download, dataset: str, resource: Resource | None) -> Source:
    return Source(
        dataset=dataset,
        url=download.url,
        sha256=download.sha256,
        last_modified=download.last_modified or (resource.last_modified if resource else None),
    )


def _fetch(
    client: httpx.Client,
    dataset: str,
    *,
    raw_dir: Path,
    force: bool,
    year: int | None,
    period: int | None,
    log,
) -> tuple[Download, Resource | None]:
    """Resolve and download one source, or fall back to the local copy the catalogue ignored."""
    try:
        resource = resolve_resource(
            client, dataset, year=year, period=period, include_alternatives=False
        )
    except DatasetUnavailable as error:
        # El catalogo se movio. La copia local va ANTES que un dataset alternativo, porque es el
        # dato que ya conocemos. Medido: preferir el dataset viejo corto la cobertura de capacidad
        # de 248 prospectos a 33, en silencio, y el artefacto emitido parecia normal.
        cached = newest_matching(raw_dir, DATASET_FILE_PATTERN[dataset])
        if cached is not None:
            log(f"  AVISO: el catalogo ya no publica '{dataset}'.")
            log(f"         {error}")
            log(
                f"         se usa la copia local {cached.name}; puede estar desactualizada, "
                "y esta corrida NO la puede refrescar."
            )
            return (
                Download(
                    path=cached,
                    url=f"(copia local de {dataset}: el catalogo ya no lo publica)",
                    sha256=file_sha256(cached),
                    from_cache=True,
                    last_modified=datetime.fromtimestamp(
                        cached.stat().st_mtime, timezone.utc
                    ).isoformat(timespec="minutes"),
                    size_bytes=cached.stat().st_size,
                ),
                None,
            )

        log(f"  AVISO: '{dataset}' no tiene copia local, asi que se prueban identificadores")
        log("         alternativos, que pueden ser de un anio ANTERIOR y bajar la cobertura.")
        resource = resolve_resource(client, dataset, year=year, period=period)

    result = download(client, resource.url, raw_dir / _filename(resource.url), force=force)
    origin = "cache local" if result.from_cache else "descargado"
    log(f"  {dataset:<12} {result.sha256[:12]}  {result.size_bytes / 1e6:6.1f} MB  ({origin})")
    return result, resource


def run(
    *,
    output_path: Path | None = None,
    include_procedures: bool = False,
    refresh: bool = False,
    limit: int | None = None,
    year: int | None = None,
    period: int | None = None,
    draft_limit: int | None = None,
    llm_model: str | None = None,
    template_path: Path | None = None,
    segment_places: bool = False,
    segment_department: str = "LIMA",
    segment_districts: list[str] | None = None,
    segment_top: int | None = None,
    segment_output: Path | None = None,
    call_sheet_limit: int | None = None,
    call_sheet_output: Path | None = None,
    firestore_project: str | None = None,
    firestore_collection: str = DEFAULT_COLLECTION,
    raw_dir: Path = RAW_DIR,
    log=print,
) -> PipelineReport:
    """Build the prospect archive from the live SUSALUD open data."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    sources: list[Download] = []
    source_meta: list[Source] = []

    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}) as client:
        log("resolviendo recursos vigentes en el CKAN de SUSALUD...")

        renipress, resource = _fetch(
            client, "renipress", raw_dir=raw_dir, force=refresh, year=year, period=period, log=log
        )
        sources.append(renipress)
        source_meta.append(_source_meta(renipress, "renipress", resource))

        rows = list(read_renipress(renipress.path))
        targets = filter_target_profile(rows)
        counts["renipress_rows"] = len(rows)
        counts["target_ipress"] = len(targets)
        log(f"  perfil objetivo: {len(targets)} IPRESS privadas activas I-3/I-4 de {len(rows)} registradas")

        codes = {row.ipress_code for row in targets}

        capacity_download, resource = _fetch(
            client, "capacity", raw_dir=raw_dir, force=refresh, year=year, period=period, log=log
        )
        sources.append(capacity_download)
        source_meta.append(_source_meta(capacity_download, "capacity", resource))

        capacity = consolidate_capacity(capacity_download.path, codes)
        counts["with_capacity_data"] = sum(1 for entry in capacity.values() if entry.period)
        log(f"  capacidad instalada disponible para {counts['with_capacity_data']} de {len(codes)} IPRESS")

        ozone: dict[str, OzoneTherapy] = {code: OzoneTherapy() for code in codes}
        if include_procedures:
            procedures, resource = _fetch(
                client, "procedures", raw_dir=raw_dir, force=refresh, year=year, period=period, log=log
            )
            sources.append(procedures)
            source_meta.append(_source_meta(procedures, "procedures", resource))
            detection = detect_ozone_therapy(procedures.path, codes)
            ozone = detection.therapy
            counts["ozone_signal_available"] = int(detection.signal_available)
            counts["already_offer_ozone"] = sum(1 for entry in ozone.values() if entry.performs)
            if detection.signal_available:
                log(f"  ya ofrecen ozonoterapia: {counts['already_offer_ozone']} (fuente Consulta G)")
            else:
                log("  AVISO: el catalogo de la Consulta G no contiene ningun procedimiento de ozono,")
                log("         asi que esa fuente no puede determinar quien ya la ofrece. Se emite SIN DATO.")

    prospects: list[Prospect] = []
    for row in targets:
        row_capacity = capacity[row.ipress_code]
        row_ozone = ozone[row.ipress_code]
        # `period is None` means Consulta A has no record for this IPRESS. The
        # headcount is unknown, which is not the same as zero doctors.
        doctors_total = None if row_capacity.period is None else row_capacity.doctors_total
        prospects.append(
            build_prospect(
                row,
                capacity=row_capacity,
                ozone_therapy=row_ozone,
                score=score_prospect(
                    row,
                    doctors_total=doctors_total,
                    performs_ozone_therapy=row_ozone.performs,
                ),
            )
        )

    prospects.sort(key=lambda prospect: (-prospect.score.total, prospect.id))
    # La lista de distritos se saca del total, no del archivo truncado por --limit.
    distritos_del_segmento: list[str] | None = None
    if segment_places:
        distritos_del_segmento = segment_districts or top_districts(
            prospects, department=segment_department, limit=segment_top
        )
    if limit is not None:
        prospects = prospects[:limit]

    archive = build_archive(prospects, sources=source_meta)
    counts["emitted"] = archive.total
    counts["priority_high"] = sum(1 for prospect in prospects if prospect.score.level == "high")
    counts["scores_rescaled"] = sum(
        1 for prospect in prospects if prospect.score.measured_weight < TOTAL_WEIGHT
    )

    destination = Path(output_path) if output_path else OUTPUT_DIR / "prospect_mock.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(archive.model_dump_json(indent=2), encoding="utf-8")
    log(f"escrito {destination} con {archive.total} prospectos")
    if limit is not None and archive.total < counts.get("target_ipress", archive.total):
        # Medido: una corrida de prueba con --limit sobrescribió el archivo completo y una
        # medición posterior se hizo sobre 5 registros sin que nada lo advirtiera.
        log(
            f"  AVISO: --limit {limit} sobrescribió {destination.name} con {archive.total} de "
            f"{counts['target_ipress']} prospectos. Para el archivo completo, corré sin --limit."
        )

    informe = None
    submissions: list[DraftSubmission] = []
    if segment_places:
        distritos = distritos_del_segmento or []
        if not distritos:
            log(
                f"  AVISO: no hay distritos de {segment_department} en el archivo, "
                "asi que no hay nada que buscar."
            )
        else:
            log(
                f"segmento de especialidad en {segment_department}: "
                f"{len(distritos)} distritos (1 credito por distrito y especialidad)"
            )
            informe = run_segment(
                districts=distritos,
                department=segment_department,
                output_path=segment_output or SEGMENT_OUTPUT,
                log=log,
            )
            counts["segmento_clinicas"] = informe.counts["clinicas_del_segmento"]
            counts["segmento_creditos"] = informe.credits

            if call_sheet_limit:
                hoja = write_call_sheet(
                    informe.archive,
                    call_sheet_output or CALL_SHEET_OUTPUT,
                    limit=call_sheet_limit,
                )
                counts["hoja_de_llamados"] = call_sheet_limit
                log(f"escrito {hoja} con las {call_sheet_limit} clinicas para llamar")

    if draft_limit:
        # Los borradores siguen a la hoja de llamados cuando hay segmento. Redactar para el
        # padrón cuando el foco del negocio es fisioterapia seria redactar para la lista
        # equivocada, que es el error que este proyecto ya cometió una vez.
        objetivo = (
            rank_for_calling(informe.archive.prospects, limit=draft_limit)
            if informe is not None
            else prospects[:draft_limit]
        )
        if not objetivo:
            log("  AVISO: no hay clinicas accionables para redactar.")
        else:
            template = load_template(template_path or OUTREACH_TEMPLATE)
            endpoint = resolve_llm_endpoint(llm_model)
            log(
                f"redactando {len(objetivo)} borradores con {endpoint.describe()} "
                f"(plantilla {template.name})..."
            )
            submissions = _draft_top(
                objetivo,
                endpoint=endpoint,
                template=template,
                log=log,
                cache_dir=DRAFTS_DIR,
                refresh=refresh,
            )
            drafts_path = destination.with_name("drafts.json")
            drafts_path.write_text(
                json.dumps(
                    [submission_to_dict(item) for item in submissions],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            counts["drafts"] = len(submissions)
            counts["drafts_flagged"] = sum(1 for item in submissions if not item.is_clean)
            log(
                f"escrito {drafts_path} con {len(submissions)} borradores "
                f"({counts['drafts_flagged']} con hallazgos, todos pendientes de aprobacion)"
            )

    if firestore_project:
        # En Cloud Run el sistema de archivos es efímero: un JSON dentro del contenedor se pierde
        # cuando el job termina. Por eso el destino real es la base, y los archivos son el
        # subproducto auditable.
        store = firestore_client(firestore_project)
        log(f"escribiendo en Firestore: {firestore_project}/{firestore_collection}")
        counts.update(
            write_to_firestore(
                archive=archive,
                informe=informe,
                submissions=submissions,
                store=store,
                collection=firestore_collection,
                log=log,
            )
        )

    return PipelineReport(
        archive=archive, sources=sources, counts=counts, output_path=destination
    )


def write_to_firestore(
    *,
    archive: ProspectArchive,
    informe,
    submissions: list[DraftSubmission],
    store,
    collection: str = DEFAULT_COLLECTION,
    log=print,
) -> dict[str, int]:
    """Escribe las tres colecciones de una corrida: el contrato, los borradores y la pantalla.

    Está aparte de `run_pipeline` para poder probarlo sin red ni credenciales, porque es el bloque
    donde un error se lleva puesta la única copia: en Cloud Run los JSON viven en `/tmp` y no
    sobreviven al contenedor.
    """
    counts: dict[str, int] = {}
    registro = upsert(archive, client=store, collection=collection, log=log)
    counts["firestore_nuevos"] = registro["nuevos"]
    counts["firestore_actualizados"] = registro["actualizados"]
    write_metadata(archive, client=store, name="ingestion", log=log)
    if informe is not None:
        segmento = upsert(informe.archive, client=store, collection=collection, log=log)
        counts["firestore_nuevos"] += segmento["nuevos"]
        counts["firestore_actualizados"] += segmento["actualizados"]
        write_metadata(informe.archive, client=store, name="segment", log=log)

    if submissions:
        # Los borradores tambien van a la base. Sin esto, un job programado que redacte descartaria
        # su propia salida, y la pantalla de aprobacion no tendria que leer.
        borradores = write_submissions(submissions, client=store, log=log)
        counts["proposals_nuevos"] = borradores["nuevos"]
        counts["proposals_actualizados"] = borradores["actualizados"]
        # Y la pantalla de aprobacion lee su propia forma (`aiContent`, `type`, `{id}-outbound`).
        aprobaciones = write_approvals(submissions, client=store, log=log)
        counts["approvals_nuevos"] = aprobaciones["nuevos"]
        counts["approvals_actualizados"] = aprobaciones["actualizados"]

    # La proyeccion que lee la pantalla: una sola forma para los dos origenes del contrato, con los
    # nombres que el frontend ya usa. Los campos que los datos no tienen quedan en null.
    todos = list(archive.prospects) + (
        list(informe.archive.prospects) if informe is not None else []
    )
    # El instante desde el que esta corrida "vio" los datos. Se toma ANTES de escribir para que todo
    # lo que escribe quede de este lado; lo que tenga `updatedAt` anterior no lo vio esta corrida.
    escrito_desde = datetime.now(timezone.utc).isoformat(timespec="minutes")
    # Se graba el corte ANTES de escribir: es lo unico que despues permite reparar sin adivinar una
    # fecha, y no se puede reconstruir a posteriori (ver `write_watermark`).
    write_watermark(store, seen_since=escrito_desde)
    leads = write_leads(todos, client=store, submissions=submissions, log=log)
    counts["leads_nuevos"] = leads["nuevos"]
    counts["leads_actualizados"] = leads["actualizados"]
    # Y despues de escribir: los que esta corrida no vio se marcan, no se borran. El segmento de
    # Places no devuelve el mismo conjunto en cada corrida.
    viejos = repair_leads(client=store, seen_since=escrito_desde, log=log)
    counts["leads_sin_volver_a_aparecer"] = viejos["viejos"]
    return counts


def _draft_top(
    prospects: list[Prospect],
    *,
    endpoint,
    template,
    log,
    cache_dir: Path | None = None,
    refresh: bool = False,
) -> list[DraftSubmission]:
    """Draft one message per clinic, in the order it was given. Never sends anything.

    The caller decides the order: when the segment ran, it is the call sheet's ranking.
    A model or credential misconfiguration stops the run on the first draft instead of
    repeating the same failure once per clinic, and `cache_dir` keeps a run that dies halfway
    from charging again for what it already produced.
    """
    submissions: list[DraftSubmission] = []
    fallidos: list[str] = []
    total = len(prospects)
    for position, prospect in enumerate(prospects, start=1):
        try:
            submissions.append(
                draft_outreach(
                    prospect,
                    template=template,
                    model=endpoint.model,
                    api_base=endpoint.api_base,
                    api_key=endpoint.api_key,
                    response_format=endpoint.response_format,
                    cache_dir=cache_dir,
                    refresh=refresh,
                )
            )
        except ValidationError:
            # Una respuesta que no encaja con el esquema es un problema de ESA clinica: se saltea y
            # se reporta. Medido: el modelo devolvio un objeto sin `opening` y esa sola respuesta
            # abandono un lote de diez borradores. Un borrador incompleto se rechaza; el lote sigue.
            fallidos.append(prospect.id)
            log(f"  AVISO: respuesta invalida para {prospect.name[:38]}; se saltea esa clinica.")
            continue
        except Exception as error:
            # Esto si es de configuracion, y va a fallar para todas: se corta antes de repetirlo.
            raise RuntimeError(
                f"no se pudo redactar con el modelo '{endpoint.model}': {error}\n"
                "Revisa la clave del proveedor en .env (por ejemplo NAN_API_KEY) y el modelo "
                "con CONFIA2_LLM_MODEL o --llm-model."
            ) from error
        if position % 5 == 0 or position == total:
            log(f"  borradores {position}/{total}")

    if fallidos:
        log(
            f"  {len(fallidos)} de {total} clinicas quedaron sin borrador; "
            "se pueden reintentar solas volviendo a correr el comando."
        )
    return submissions
