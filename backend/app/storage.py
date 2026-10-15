import os
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STORAGE_ROOT = Path(os.getenv("CONFIA_STORAGE_DIR", BASE_DIR / "storage"))

INPUT_DIR = STORAGE_ROOT / "input"
TEMPLATES_DIR = INPUT_DIR / "templates"
ASSETS_DIR = INPUT_DIR / "assets"
OUTPUT_DIR = STORAGE_ROOT / "output"
LEADS_DIR = OUTPUT_DIR / "leads"

DOSSIER_TEMPLATE_PATH = TEMPLATES_DIR / "dossier_template.md"
PROPOSAL_TEMPLATE_PATH = TEMPLATES_DIR / "propuesta_template.md"
LOGO_PATH = ASSETS_DIR / "logo_confia.png"

MARKDOWN_FILENAME = "document.md"
PDF_FILENAME = "document.pdf"
PROPOSAL_PDF_FILENAME = "propuesta_comercial.pdf"
# Registro de parámetros y resultado de cada versión, para auditoría (sin sobrescribir).
PROPOSAL_PARAMS_FILENAME = "parametros.json"
DOWNLOADABLE_FILENAMES = (MARKDOWN_FILENAME, PDF_FILENAME, PROPOSAL_PDF_FILENAME, PROPOSAL_PARAMS_FILENAME)

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")
_VERSION_DIR = re.compile(r"v(\d+)")


def ensure_storage_dirs() -> None:
    for directory in (TEMPLATES_DIR, ASSETS_DIR, LEADS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def normalize_lead_id(raw: str) -> str:
    """Convierte un identificador libre en un slug seguro para usarlo como carpeta."""
    ascii_text = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    slug = _NON_SLUG_CHARS.sub("-", ascii_text.lower()).strip("-")
    if not slug:
        raise ValueError("El identificador del prospecto está vacío tras normalizarlo.")
    return slug[:120]


def lead_dir(lead_id: str) -> Path:
    return LEADS_DIR / normalize_lead_id(lead_id)


def version_dir(lead_id: str, version: int) -> Path:
    return lead_dir(lead_id) / f"v{version}"


def create_version_dir(lead_id: str) -> tuple[int, Path]:
    """Crea la siguiente carpeta vN de forma atómica y devuelve (N, ruta)."""
    directory = lead_dir(lead_id)
    directory.mkdir(parents=True, exist_ok=True)

    version = _last_version(directory) + 1
    while True:
        candidate = directory / f"v{version}"
        try:
            candidate.mkdir()
            return version, candidate
        except FileExistsError:
            # Otra petición creó esta versión entre medio; probamos la siguiente.
            version += 1


def _last_version(directory: Path) -> int:
    versions = []
    for entry in directory.iterdir():
        match = _VERSION_DIR.fullmatch(entry.name) if entry.is_dir() else None
        if match:
            versions.append(int(match.group(1)))
    return max(versions, default=0)
