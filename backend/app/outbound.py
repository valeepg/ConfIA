"""Adjuntos y traza del envío de outbound.

Los adjuntos se resuelven por (versión, nombre de archivo) dentro de
output/leads/{lead_id}/v{n}/. Nunca se acepta una ruta libre del cliente.
"""

import json
import re
from datetime import datetime, timezone

from .gmail_service import Attachment
from .storage import (
    PDF_FILENAME,
    PROPOSAL_PDF_FILENAME,
    lead_dir,
    version_dir,
)

# Documentos que pueden adjuntarse y su etiqueta en el modal.
ATTACHABLE_FILES = {
    PDF_FILENAME: "Dossier regulatorio (PDF)",
    PROPOSAL_PDF_FILENAME: "Propuesta comercial (PDF)",
}
# Nombre con el que llega el archivo al destinatario (incluye la versión).
ATTACHMENT_NAMES = {
    PDF_FILENAME: "dossier-regulatorio",
    PROPOSAL_PDF_FILENAME: "propuesta-comercial",
}

TRACE_FILENAME = "envios.jsonl"
_VERSION_DIR = re.compile(r"v(\d+)")


def list_lead_documents(lead_id: str) -> list[dict]:
    """Archivos adjuntables que existen para el lead, por versión (más reciente primero)."""
    directory = lead_dir(lead_id)
    if not directory.is_dir():
        return []

    entries = []
    for version_path in sorted(directory.iterdir(), key=_version_key, reverse=True):
        match = _VERSION_DIR.fullmatch(version_path.name)
        if not (version_path.is_dir() and match):
            continue
        version = int(match.group(1))
        for filename, label in ATTACHABLE_FILES.items():
            if (version_path / filename).is_file():
                entries.append(
                    {
                        "version": version,
                        "filename": filename,
                        "label": f"{label} · v{version}",
                        "download_url": f"/documents/leads/{lead_id}/versions/{version}/{filename}",
                    }
                )
    return entries


def _version_key(path) -> int:
    match = _VERSION_DIR.fullmatch(path.name)
    return int(match.group(1)) if match and path.is_dir() else -1


def read_attachments(lead_id: str, refs: list[tuple[int, str]]) -> list[Attachment]:
    attachments = []
    for version, filename in refs:
        if filename not in ATTACHABLE_FILES:
            raise ValueError(f"El archivo '{filename}' no se puede adjuntar.")
        path = version_dir(lead_id, version) / filename
        if not path.is_file():
            raise ValueError(f"No existe {filename} en la versión v{version} de este prospecto.")
        attachments.append(
            Attachment(filename=f"{ATTACHMENT_NAMES[filename]}-v{version}.pdf", data=path.read_bytes())
        )
    return attachments


def append_trace(lead_id: str, record: dict) -> None:
    """Agrega una línea a envios.jsonl. Es append-only: nunca reescribe envíos anteriores."""
    directory = lead_dir(lead_id)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / TRACE_FILENAME).open("a", encoding="utf-8") as trace:
        trace.write(json.dumps(record, ensure_ascii=False) + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
