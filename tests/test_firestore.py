"""Las reglas del escritor a Firestore, probadas sin Google y sin red.

La que importa: **la ingesta no puede pisar `pipeline_stage`**, porque ahí vive el trabajo
comercial del dueño. Si el job reescribe todo, un prospecto en `contract_signed` vuelve a
`discovered` y nadie se entera.
"""

from types import SimpleNamespace

from scraper.contract import Prospect, ProspectArchive
from scraper.copilot import DraftSubmission, OutreachDraft
from scraper.firestore import (
    META_COLLECTION,
    META_DOCUMENT,
    PROPOSALS_COLLECTION,
    document_for,
    submission_document,
    upsert,
    write_metadata,
    write_submissions,
)


class FakeSnapshot:
    """Lo que devuelve `reference.get()` en el cliente real: un snapshot con `.exists` y `.to_dict()`.

    `to_dict()` devuelve `None` si el documento no existe, igual que el cliente de Google.
    """

    def __init__(self, exists: bool, data: dict | None = None):
        self.exists = exists
        self._data = data

    def to_dict(self) -> dict | None:
        return dict(self._data) if self._data else None


class FakeSnapshotDocument:
    """Un elemento de `stream()`: el cliente real entrega instantaneas, no documentos."""

    def __init__(self, store: dict, key: str):
        self.store = store
        self.key = key

    def to_dict(self) -> dict:
        return dict(self.store.get(self.key, {}))

    @property
    def reference(self) -> "FakeDocument":
        return FakeDocument(self.store, self.key)


class FakeCollection:
    """Lo minimo de una coleccion: referencia por id, y recorrerla entera con `stream()`."""

    def __init__(self, store: dict):
        self.store = store

    def document(self, key: str) -> "FakeDocument":
        return FakeDocument(self.store, key)

    def stream(self) -> list[FakeSnapshotDocument]:
        return [FakeSnapshotDocument(self.store, key) for key in sorted(self.store)]


class FakeDocument:
    """Lo mínimo de una referencia de documento: leer si existe y escribir con merge.

    Deliberadamente **no** tiene `.exists`: el cliente de Google tampoco lo tiene, y esa diferencia
    es la que dejó pasar un defecto que ningún test veía. La primera corrida en la nube se murió en
    la primera escritura con `'DocumentReference' object has no attribute 'exists'`, después de
    haber hecho todo el trabajo.
    """

    def __init__(self, store: dict, key: str):
        self.store = store
        self.key = key

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self.key in self.store, self.store.get(self.key))

    def set(self, payload: dict, *, merge: bool) -> None:
        if not merge:
            self.store[self.key] = dict(payload)
            return
        actual = dict(self.store.get(self.key, {}))
        actual.update(payload)
        self.store[self.key] = actual


class FakeFirestore:
    def __init__(self):
        self.data: dict[str, dict] = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self.data.setdefault(name, {}))

    def documents(self, name: str = "prospects") -> dict:
        return self.data.get(name, {})


def prospect(**overrides) -> Prospect:
    base = dict(
        id="places:1",
        origin="places",
        name="Artrauma",
        location={"department": "LIMA", "district": "HUAURA"},
        contact={"phone": "993 923 680", "phone_valid": True},
        google={"cid": "1", "query": "q", "category": "Fisioterapeuta", "rating_count": 553},
        tags=["physiotherapy-segment", "chain"],
    )
    base.update(overrides)
    return Prospect(**base)


def archive(*prospects: Prospect) -> ProspectArchive:
    return ProspectArchive(
        generated_at="2026-10-14T00:00:00+00:00",
        sources=[],
        total=len(prospects),
        prospects=list(prospects),
    )


# --- los fakes tienen que modelar la API real --------------------------------- #


def test_the_fake_does_not_invent_an_exists_on_the_reference():
    """El defecto que se escapó: el fake tenía `.exists` en la referencia y el cliente de Google no.

    La primera corrida en la nube se murió en la primera escritura —`'DocumentReference' object has
    no attribute 'exists'`— después de haber hecho todo el trabajo, y los 241 tests pasaban. Un
    fake que no modela la API real miente para el lado equivocado.
    """
    assert not hasattr(FakeDocument, "exists")
    assert hasattr(FakeDocument, "get")


# --- la regla que importa ---------------------------------------------------- #


def test_a_new_document_is_created_in_the_discovered_stage():
    client = FakeFirestore()
    upsert(archive(prospect()), client=client, log=lambda *_: None)
    assert client.documents()["places:1"]["pipeline_stage"] == "discovered"


def test_the_job_never_overwrites_the_stage_of_an_existing_document():
    """El CRM movió el prospecto a contrato firmado; la ingesta no puede devolverlo al principio."""
    client = FakeFirestore()
    upsert(archive(prospect()), client=client, log=lambda *_: None)

    client.documents()["places:1"]["pipeline_stage"] = "contract_signed"
    client.documents()["places:1"]["notes"] = ["Llamado el martes"]
    client.documents()["places:1"]["manual_tags"] = ["vip"]

    upsert(archive(prospect()), client=client, log=lambda *_: None)

    guardado = client.documents()["places:1"]
    assert guardado["pipeline_stage"] == "contract_signed"
    assert guardado["notes"] == ["Llamado el martes"]
    assert guardado["manual_tags"] == ["vip"]


def test_the_job_does_update_the_fields_it_owns():
    """No pisar lo humano no significa no actualizar lo propio: el rating cambia."""
    client = FakeFirestore()
    upsert(archive(prospect()), client=client, log=lambda *_: None)
    upsert(
        archive(prospect(name="Artrauma Renovada")),
        client=client,
        log=lambda *_: None,
    )
    assert client.documents()["places:1"]["name"] == "Artrauma Renovada"


# --- el contenido ------------------------------------------------------------ #


def test_the_payload_carries_the_origin_and_the_google_block():
    payload = document_for(prospect(), include_stage=False)
    assert payload["origin"] == "places"
    assert payload["google"]["cid"] == "1"
    assert payload["tags"] == ["physiotherapy-segment", "chain"]


def test_the_update_payload_does_not_carry_the_stage():
    assert "pipeline_stage" not in document_for(prospect(), include_stage=False)
    assert document_for(prospect(), include_stage=True)["pipeline_stage"] == "discovered"


def test_the_counts_tell_new_documents_from_updated_ones():
    client = FakeFirestore()
    primero = upsert(archive(prospect()), client=client, log=lambda *_: None)
    segundo = upsert(archive(prospect()), client=client, log=lambda *_: None)
    assert primero == {"nuevos": 1, "actualizados": 0}
    assert segundo == {"nuevos": 0, "actualizados": 1}


# --- los borradores, que son la pantalla de aprobación ------------------------ #
#
# Sin esto, un job programado que redacte descartaría su propia salida: en Cloud Run el sistema de
# archivos es efímero y `drafts.json` vive adentro del contenedor.


def borrador(**overrides) -> DraftSubmission:
    base = dict(
        prospect_id="places:1",
        template_name="oaas-v1",
        model="openai/deepseek-v4-flash",
        draft=OutreachDraft(
            subject="Ozonoterapia en comodato para Artrauma",
            greeting="Estimado equipo de Artrauma:",
            opening="Le escribimos porque figura como clinica de fisioterapia.",
        ),
        message="Asunto\n\nEstimado equipo de Artrauma:\n\nLe escribimos.\n\n[FIRMA DEL DUEÑO]\n",
        violations=(),
        status="pending_approval",
    )
    base.update(overrides)
    return DraftSubmission(**base)


def test_a_submission_is_written_with_its_message_and_what_is_missing():
    client = FakeFirestore()
    write_submissions([borrador()], client=client, log=lambda *_: None)

    guardado = client.documents(PROPOSALS_COLLECTION)["places:1"]
    assert guardado["subject"] == "Ozonoterapia en comodato para Artrauma"
    assert "Artrauma" in guardado["message"]
    assert guardado["status"] == "pending_approval"
    assert guardado["missing_human_data"] == ["[FIRMA DEL DUEÑO]"]
    assert guardado["violations"] == []


def test_the_job_never_reopens_a_draft_the_owner_already_decided():
    """El dueño aprobó un borrador: una corrida posterior no puede devolverlo a pendiente."""
    client = FakeFirestore()
    write_submissions([borrador()], client=client, log=lambda *_: None)

    aprobado = client.documents(PROPOSALS_COLLECTION)["places:1"]
    aprobado["status"] = "approved"
    aprobado["approver"] = "el dueño"

    write_submissions(
        [borrador(message="Otro texto, regenerado por una corrida nueva.\n")],
        client=client,
        log=lambda *_: None,
    )

    guardado = client.documents(PROPOSALS_COLLECTION)["places:1"]
    assert guardado["status"] == "approved"
    assert guardado["approver"] == "el dueño"
    assert "regenerado" in guardado["message"]  # lo que sí es del job se actualiza


def test_the_update_payload_of_a_submission_does_not_carry_the_status():
    assert "status" not in submission_document(borrador(), include_status=False)
    assert submission_document(borrador(), include_status=True)["status"] == "pending_approval"


def test_the_metadata_records_which_bytes_produced_the_store():
    from scraper.contract import Source

    client = FakeFirestore()
    contenido = ProspectArchive(
        generated_at="2026-10-14T00:00:00+00:00",
        total=1,
        sources=[Source(dataset="renipress", url="http://x/RENIPRESS.csv", sha256="abc")],
        prospects=[prospect()],
    )
    write_metadata(contenido, client=client, log=lambda *_: None)

    meta = client.data[META_COLLECTION][META_DOCUMENT]
    assert meta["sources"][0]["sha256"] == "abc"
    assert meta["total"] == 1
    assert "recorded_at" in meta


def test_la_marca_de_agua_guarda_el_corte_de_la_ultima_corrida():
    """Es la fecha que usa `--repair-leads` para reparar sin que nadie tenga que acordarse de nada.

    Y no sirve `recorded_at` en su lugar: se escribe en el medio de la fase de escritura, asi que
    marcaria como viejos leads que la misma corrida acaba de escribir.
    """
    from scraper.firestore import last_view_watermark, write_watermark

    client = FakeFirestore()
    assert last_view_watermark(client) is None  # ninguna corrida con esta version todavia

    write_watermark(client, seen_since="2026-10-14T22:12")

    assert last_view_watermark(client) == "2026-10-14T22:12"
