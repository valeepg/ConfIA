"""Write the prospect archives into Firestore without touching what the CRM owns.

The rule that matters: `pipeline_stage` belongs to the CRM. The job only ever writes the fields
that come from the sources, so re-running ingestion cannot send a prospect that was already in
`contract_signed` back to `discovered` and silently erase the owner's commercial work.

This project already shipped one silent data loss of that shape — a catalogue fallback that cut
capacity coverage from 248 prospects to 33 without saying anything — so the split is enforced here
in code and covered by tests, instead of being left to whoever writes the first seeder.

Two field names deserve an explanation:

- `tags` is written by the job and holds the origin tags (`target-profile`, `chain`…). A tag a
  person adds by hand goes in `manual_tags`, because Firestore replaces a list rather than merging
  it: writing `tags` would quietly delete anything a human had put there.
- `sources` lives in a metadata document, not in every prospect, so the last ingestion is traceable
  without repeating the same hashes 3,288 times.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from .contract import Prospect, ProspectArchive
from .copilot import DraftSubmission

DEFAULT_COLLECTION = "prospects"
PROPOSALS_COLLECTION = "proposals"
META_COLLECTION = "confia2_meta"
META_DOCUMENT = "ingestion"
# La marca de agua de la coleccion que lee la pantalla: desde que instante la ultima corrida
# considero visto lo que ya estaba. No se puede reusar `recorded_at`: se escribe en el medio de la
# fase de escritura.
WATERMARK_DOCUMENT = "leads_watermark"

# Lo que la ingesta escribe en cada corrida.
SOURCE_OWNED = (
    "origin",
    "ipress_code",
    "name",
    "legal_name",
    "institution",
    "category",
    "classification",
    "establishment_type",
    "location",
    "contact",
    "capacity",
    "ozone_therapy",
    "score",
    "google",
    "tags",
)

# Lo que nunca reescribe: lo mueve o lo agrega una persona.
HUMAN_OWNED = ("pipeline_stage", "manual_tags", "notes", "proposals", "approvals")


class Document(Protocol):
    """The sliver of a Firestore document reference this module needs."""

    @property
    def exists(self) -> bool: ...

    def set(self, payload: dict, *, merge: bool) -> None: ...


class Collection(Protocol):
    def document(self, key: str) -> Document: ...


class Firestore(Protocol):
    def collection(self, name: str) -> Collection: ...


def document_for(prospect: Prospect, *, include_stage: bool) -> dict[str, Any]:
    """The payload for one prospect, narrowed to what the job owns.

    `include_stage` is true only when the document does not exist yet: on creation the stage is
    `discovered`, and after that it is the CRM's field.
    """
    complete = prospect.model_dump(mode="json")
    payload = {field: complete[field] for field in SOURCE_OWNED if field in complete}
    if include_stage:
        payload["pipeline_stage"] = prospect.pipeline_stage
    return payload


def upsert(
    archive: ProspectArchive,
    *,
    client: Firestore,
    collection: str = DEFAULT_COLLECTION,
    log=print,
) -> dict[str, int]:
    """Write every prospect, creating new documents and merging into existing ones.

    One read per document decides whether the initial stage has to be written. It is one extra
    read and the only way to know, since Firestore has no conditional field write.
    """
    conteos = {"nuevos": 0, "actualizados": 0}

    for prospect in archive.prospects:
        reference = client.collection(collection).document(prospect.id)
        exists = reference.get().exists
        reference.set(document_for(prospect, include_stage=not exists), merge=True)
        conteos["actualizados" if exists else "nuevos"] += 1

    log(
        f"  firestore: {conteos['nuevos']} documentos nuevos, "
        f"{conteos['actualizados']} actualizados (sin tocar lo que edita una persona)"
    )
    return conteos


def write_metadata(
    archive: ProspectArchive,
    *,
    client: Firestore,
    name: str = META_DOCUMENT,
    log=print,
) -> None:
    """Record which bytes produced the store, so a later reader can tell when it went stale."""
    payload = {
        "generated_at": archive.generated_at,
        "total": archive.total,
        "contract_version": archive.contract_version,
        "sources": [source.model_dump(mode="json") for source in archive.sources],
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
    }
    client.collection(META_COLLECTION).document(name).set(payload, merge=False)
    log(f"  firestore: procedencia registrada en {META_COLLECTION}/{name}")


def submission_document(submission: DraftSubmission, *, include_status: bool) -> dict[str, Any]:
    """The payload for one outreach draft, narrowed to what the job owns.

    `include_status` is true only when the document does not exist yet: the approval decision is
    the owner's, and a later run must never reopen a draft he already approved or rejected.
    """
    payload: dict[str, Any] = {
        "prospect_id": submission.prospect_id,
        "template": submission.template_name,
        "model": submission.model,
        "subject": submission.draft.subject,
        "message": submission.message,
        "violations": list(submission.violations),
        "missing_human_data": list(submission.missing_human_data),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
    }
    if include_status:
        payload["status"] = submission.status
    return payload


def write_submissions(
    submissions: list[DraftSubmission],
    *,
    client: Firestore,
    collection: str = PROPOSALS_COLLECTION,
    log=print,
) -> dict[str, int]:
    """Persist the drafts so the approval screen can read them.

    Without this the drafts would only exist inside the container, and Cloud Run's filesystem is
    ephemeral: a scheduled run that drafts would discard its own output.
    """
    conteos = {"nuevos": 0, "actualizados": 0}
    for submission in submissions:
        reference = client.collection(collection).document(submission.prospect_id)
        exists = reference.get().exists
        reference.set(submission_document(submission, include_status=not exists), merge=True)
        conteos["actualizados" if exists else "nuevos"] += 1

    log(
        f"  firestore: {conteos['nuevos']} borradores nuevos y {conteos['actualizados']} "
        f"actualizados en {collection} (sin tocar la aprobacion del dueño)"
    )
    return conteos


def write_watermark(client, *, seen_since: str, name: str = WATERMARK_DOCUMENT) -> None:
    """Guarda desde que instante la ingesta considera visto lo que ya estaba en la base.

    Es lo unico que permite reparar despues sin que nadie tenga que recordar una fecha, y **no sirve
    reusar `recorded_at`**: eso se escribe en el medio de la fase de escritura, asi que usarlo como
    corte marcaria como viejos leads que la misma corrida acaba de escribir. El corte tiene que caer
    ENTRE dos corridas, y el unico momento en que se sabe es mientras una corre.
    """
    client.collection(META_COLLECTION).document(name).set(
        {
            "seen_since": seen_since,
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        },
        merge=False,
    )


def last_view_watermark(client, *, name: str = WATERMARK_DOCUMENT) -> str | None:
    """El corte de la ultima corrida, o `None` si nunca corrio una version que lo grabe."""
    instantanea = client.collection(META_COLLECTION).document(name).get()
    datos = instantanea.to_dict() if instantanea.exists else None
    return (datos or {}).get("seen_since")


def firestore_client(project: str):
    """The real client. Imported here so nothing else needs Google installed to run tests.

    Authentication is the standard Google one: on Cloud Run the job's service account, locally
    `gcloud auth application-default login`. No key file is read by this code.
    """
    from google.cloud import firestore

    return firestore.Client(project=project)
