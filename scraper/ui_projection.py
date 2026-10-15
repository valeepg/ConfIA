"""La forma que espera la página, proyectada desde el contrato.

El mock del frontend (`lead-1`, `directorMedico`, `outboundDraft`, `status`) y el contrato
(`pipeline_stage`, `origin`, `google.*`) son dos formas distintas, y ninguna está mal: una está
pensada para la pantalla y la otra para el dato.

Este módulo las une **sin duplicar la verdad**: la proyección sale del mismo prospecto en cada
corrida, va a su propia colección, y los campos que los datos no tienen quedan en `None` en vez de
inventarse. La página no cambia sus componentes: cambia de dónde lee.

Tres campos merecen una explicación, porque son donde la proyección podría mentir:

- **`directorMedico` queda en `None`.** Ninguna fuente pública trae el nombre del director médico:
  ni RENIPRESS (publica el establecimiento, no a su gente), ni la búsqueda, ni el padrón. El mock
  del frontend lo inventó, y una página que lo muestre vacío es honesta; una que lo rellene con
  cualquier cosa, no.
- **`specialty` sale de `google.category`** (que es la especialidad real: `Fisioterapeuta`,
  `Clínica de dolor`) y cae a `classification` del padrón, que es el **tipo de establecimiento**.
  No es lo mismo, y por eso el campo se llama distinto que en el contrato.
- **`suggestedChannel` dice `Teléfono`.** El mock dice `Email`, y no hay un solo correo en los
  3.288 prospectos: es el hallazgo que corrige el plan de outbound del documento maestro.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .contract import Prospect
from .copilot import STATUS_APPROVED, DraftSubmission

LEADS_COLLECTION = "leads"
APPROVALS_COLLECTION = "approvals"
APPROVAL_SUFFIX = "-outbound"
# El unico canal que los datos sostienen: no hay un solo email en los 3.288 prospectos, asi que
# 'Email' seria una promesa que no se puede cumplir. En un solo lugar para que no se pueda divergir.
CANAL_DE_CONTACTO = "Teléfono"

# Las columnas del Kanban del CRM. **Los valores tienen que ser exactamente los de
# `PipelineStatus` en `src/types/index.ts` del repo de la pagina** (`'descubierto' | 'contactado' |
# 'propuesta_enviada' | 'cierre'`): el Kanban ubica las tarjetas por ese string, asi que
# `'propuesta enviada'` con espacio no cae en ninguna columna y desaparece de la vista.
#
# Se comparo contra el **tipo**, no contra el mock: el mock solo usa `'descubierto'`, y por eso el
# desajuste no se veia.
ESTADO_EN_LA_PANTALLA = {
    "discovered": "descubierto",
    "contacted": "contactado",
    "proposal_sent": "propuesta_enviada",
    "contract_signed": "cierre",
}


def segmento_de(origin: str | None, tags) -> str:
    """De que lista salio el prospecto, en las palabras de la pantalla.

    Son **tres** clases, no dos, y esa es la trampa: las del padron, las del segmento de fisioterapia,
    y los resultados de busqueda que Places devolvio pero que **no** entraron al segmento (una clinica
    de otra especialidad, por ejemplo). A esas ultimas les decia "padron", y es falso: no vienen del
    registro de SUSALUD, vienen de una busqueda. Es el tipo de etiqueta que se lee como procedencia y
    que este proyecto no puede permitirse inventar.
    """
    if origin == "renipress":
        return "padron"
    return "fisioterapia" if "physiotherapy-segment" in set(tags or ()) else "busqueda"


def sugerencia(prospect: Prospect) -> str | None:
    """Una línea de contexto armada con datos, sin LLM y sin prometer nada.

    El mock del frontend tiene un `aiSuggestion` con texto libre y afirmaciones sobre la competencia
    ("sin ozonoterapia") que nuestros datos **no** pueden sostener por clínica. Esto es lo mismo pero
    verificable: cuenta lo que el prospecto es, no lo que nos gustaría que fuera.
    """
    partes: list[str] = []
    if prospect.google and prospect.google.category:
        partes.append(prospect.google.category)
    elif prospect.classification:
        partes.append(prospect.classification.capitalize())
    if prospect.google and prospect.google.rating_count:
        partes.append(f"{prospect.google.rating_count} reseñas")
    if prospect.google and prospect.google.chain_sites > 1:
        partes.append(f"{prospect.google.chain_sites} sucursales")
    if prospect.capacity.period:
        partes.append(f"{prospect.capacity.doctors_total} médicos")
    if prospect.score:
        partes.append(f"prioridad {prospect.score.level}")
    return " · ".join(partes) or None


def lead_document(
    prospect: Prospect,
    *,
    submission: DraftSubmission | None = None,
    include_status: bool = True,
) -> dict[str, Any]:
    """Un prospecto en la forma de la pantalla.

    `include_status` es falso al actualizar: el estado de la venta lo mueve el CRM, y la ingesta no
    puede devolver a `descubierto` un prospecto que el dueño ya movió.
    """
    google = prospect.google
    payload: dict[str, Any] = {
        "id": prospect.id,
        "name": prospect.name,
        "district": prospect.location.district.title(),
        "department": prospect.location.department.title(),
        "phone": prospect.contact.phone,
        # Sin esto la página no puede distinguir un teléfono verificado de uno dudoso, y son la
        # diferencia entre llamar y llamar al azar: 462 de las 529 son llamables.
        "phoneValid": prospect.contact.phone_valid,
        "address": prospect.contact.address,
        # `capitalize()` y no `title()`: el padron viene en mayusculas y «Centros De Salud Con
        # Camas De Internamiento» es peor que «Centros de salud con camas de internamiento».
        "specialty": (
            google.category
            if google and google.category
            else (prospect.classification.capitalize() if prospect.classification else None)
        ),
        # Los dos campos que no podemos llenar, y por qué: ver el docstring del módulo.
        "doctorSpecialty": None,
        "directorMedico": None,
        # `aiSuggestion` es la lectura de la máquina y se refresca en cada corrida. `statusNote`
        # es una nota que una persona puede editar, así que se escribe al crear y después no se
        # pisa: es el mismo criterio que `status`.
        "aiSuggestion": sugerencia(prospect),
        "origin": prospect.origin,
        "segment": segmento_de(prospect.origin, prospect.tags),
        "score": prospect.score.total if prospect.score else None,
        "scoreLevel": prospect.score.level if prospect.score else None,
        "rating": google.rating if google else None,
        "reviews": google.rating_count if google else None,
        "website": google.website if google else None,
        "tags": list(prospect.tags),
        # El segmento de Places no devuelve el mismo conjunto en cada corrida, asi que hay documentos
        # que una corrida escribe y la siguiente no ve. Se marcan, no se borran: ver
        # `repair_leads`. Todo lo que esta corrida escribe nace al dia.
        "stale": False,
        "draftType": "outbound",
        "hasAiDraft": submission is not None,
        "outboundDraft": None,
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="minutes"),
    }
    if include_status:
        payload["status"] = ESTADO_EN_LA_PANTALLA.get(prospect.pipeline_stage, "descubierto")
        payload["statusNote"] = sugerencia(prospect)
        # `draftApproved` es la decisión del dueño, no un dato de la corrida, y por eso va acá y no
        # en el payload que se reescribe: la aprobación vive en `approvals`, y el borrador de cada
        # corrida **siempre nace pendiente**. Recalcularlo cada vez borraba la aprobación del dueño y
        # dejaba a `leads` («no aprobado») contradiciendo a `approvals` («aprobado»).
        payload["draftApproved"] = bool(submission and submission.status == STATUS_APPROVED)

    if submission is not None:
        payload["outboundDraft"] = {
            "subject": submission.draft.subject,
            "body": submission.message,
            # El mock dice Email y no tenemos ni uno: el canal que sostienen los datos es el teléfono.
            "suggestedChannel": "Teléfono",
            "recipientName": None,
            "recipientRole": "Dirección médica",
            "violations": list(submission.violations),
            "missingHumanData": list(submission.missing_human_data),
        }
    return payload


def write_leads(
    prospects: list[Prospect],
    *,
    client,
    submissions: list[DraftSubmission] | None = None,
    collection: str = LEADS_COLLECTION,
    log=print,
) -> dict[str, int]:
    """Upsert de la proyección, con el mismo cuidado que el contrato: no pisa lo que mueve una persona."""
    por_clinica = {submission.prospect_id: submission for submission in (submissions or [])}
    conteos = {"nuevos": 0, "actualizados": 0}

    for prospect in prospects:
        reference = client.collection(collection).document(prospect.id)
        existe = reference.get().exists
        reference.set(
            lead_document(
                prospect,
                submission=por_clinica.get(prospect.id),
                include_status=not existe,
            ),
            merge=True,
        )
        conteos["actualizados" if existe else "nuevos"] += 1

    log(
        f"  firestore: {conteos['nuevos']} leads nuevos y {conteos['actualizados']} actualizados "
        f"en {collection} (la forma que lee la pantalla)"
    )
    return conteos


def repair_leads(
    *,
    client,
    seen_since: str,
    collection: str = LEADS_COLLECTION,
    log=print,
) -> dict[str, int]:
    """Repara los campos derivados de la coleccion de la pantalla **sin volver a pagar la busqueda**.

    Dos cosas que se arreglan releyendo la coleccion, y que no valen 275 creditos:

    - **Los leads que no volvieron a aparecer.** El segmento de Places no devuelve el mismo conjunto en
      cada corrida (medido 829, 791 y 774). Se marcan `stale`, **no se borran**: son clinicas reales
      que aparecieron antes, y borrar en un CRM es irreversible —nadie sabe si el dueno ya llamo o
      anoto algo sobre esa clinica.
    - **La etiqueta de segmento**, derivable del documento (`origin` + `tags`), asi que la unica razon
      para que este mal es una version anterior del codigo.

    `seen_since` es el instante en que empezo la escritura de la ultima corrida: lo que tenga
    `updatedAt` anterior no lo vio. Se escribe solo lo que cambia.
    """
    al_dia = 0
    viejos = 0
    escritos = 0
    for instantanea in client.collection(collection).stream():
        datos = instantanea.to_dict() or {}
        visto = str(datos.get("updatedAt") or "") >= seen_since
        if visto:
            al_dia += 1
        else:
            viejos += 1

        correccion: dict[str, Any] = {}
        # Se escribe tambien cuando el campo NO esta (los documentos anteriores a este arreglo), o si
        # no, la pantalla que filtre por `stale == false` no los veria nunca.
        if "stale" not in datos or bool(datos["stale"]) != (not visto):
            correccion["stale"] = not visto
        esperado = segmento_de(datos.get("origin"), datos.get("tags") or ())
        if datos.get("segment") != esperado:
            correccion["segment"] = esperado

        if not correccion:
            continue  # ya esta como tiene que estar: no se reescribe
        instantanea.reference.set(correccion, merge=True)
        escritos += 1

    # Se reporta el ESTADO (cuantos hay de cada clase) y aparte el costo: en la primera pasada se
    # escribe todo, y despues solo lo que cambia.
    log(
        f"  firestore: {al_dia} leads al dia y {viejos} sin volver a aparecer "
        f"(marcados, no borrados; {escritos} escrituras)"
    )
    return {"al_dia": al_dia, "viejos": viejos, "escritos": escritos}


def approval_document(
    submission: DraftSubmission, *, include_status: bool = True
) -> dict[str, Any]:
    """Un borrador en la forma que espera la pantalla de aprobación.

    El mock del frontend guarda los borradores en `proposals` con otra forma: `aiContent` como
    **objeto** (no un texto), `type`, `createdBy`, y los identifica como `{id}-outbound`. Con la
    forma del contrato, su componente no encontraba ninguno de los borradores reales: la pantalla
    de aprobación es la parte que el dueño usa todos los días, así que es la que más importa.

    Se proyecta a su propia colección (`approvals`) y `proposals` queda con el contrato intacto.
    """
    payload: dict[str, Any] = {
        "id": f"{submission.prospect_id}{APPROVAL_SUFFIX}",
        "prospectId": submission.prospect_id,
        "type": "outbound",
        "aiContent": {
            "subject": submission.draft.subject,
            # Sin nombre de persona ni género: ninguna fuente trae el de la dirección médica.
            "recipientRole": "Dirección médica",
            "recipientName": None,
            # El tipo de la pagina (`aiContent: OutboundDraft`) exige este campo, y la union de
            # `suggestedChannel` no incluye 'Telefono': el PR agrega ese valor. Es el unico que los
            # datos sostienen, porque no hay un solo email en los 3.288 prospectos.
            "suggestedChannel": CANAL_DE_CONTACTO,
            "body": submission.message,
        },
        "createdBy": "confia2-ingesta",
        "hasViolations": bool(submission.violations),
        "violations": list(submission.violations),
        "missingHumanData": list(submission.missing_human_data),
        "template": submission.template_name,
        "model": submission.model,
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="minutes"),
    }
    # `pending_approval` ya se llama igual en las dos formas: no hay que traducir nada.
    if include_status:
        payload["status"] = submission.status
    return payload


def write_approvals(
    submissions: list[DraftSubmission],
    *,
    client,
    collection: str = APPROVALS_COLLECTION,
    log=print,
) -> dict[str, int]:
    """Upsert de la pantalla de aprobación, con la regla de siempre: la decisión del dueño no se pisa."""
    conteos = {"nuevos": 0, "actualizados": 0}
    for submission in submissions:
        referencia = client.collection(collection).document(
            f"{submission.prospect_id}{APPROVAL_SUFFIX}"
        )
        existe = referencia.get().exists
        referencia.set(approval_document(submission, include_status=not existe), merge=True)
        conteos["actualizados" if existe else "nuevos"] += 1

    log(
        f"  firestore: {conteos['nuevos']} aprobaciones nuevas y {conteos['actualizados']} "
        f"actualizadas en {collection} (la forma que lee la pantalla de aprobación)"
    )
    return conteos
