"""Source catalogue and target-profile settings for the outbound scraper.

Everything here is either a published open-data identifier or a business rule
traceable to `docs/Document from Diego.markdown`. No contact data is hardcoded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# In a container the working directory is the image root, so the data directory
# is overridable instead of being derived from the module location only.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# `.env` is a local convenience: in Cloud Run these variables come from Secret
# Manager and no file exists. `override=False` lets a real environment variable or
# a secret win over a stale local file.
load_dotenv(PROJECT_ROOT / ".env", override=False)

DATA_DIR = Path(os.environ.get("CONFIA2_DATA_DIR", PROJECT_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
# Derived artifacts (transcoded copies of the latin-1 sources) never sit next to
# the source: the fixtures directory and any read-only mount must stay untouched.
CACHE_DIR = DATA_DIR / "cache"
# One JSON per enriched IPRESS, so repeating a sample never spends a query twice.
ENRICHMENT_DIR = DATA_DIR / "enrichment"
# One JSON per drafted clinic, for the same reason: a batch that dies halfway must not charge
# again for the drafts it already produced.
DRAFTS_DIR = DATA_DIR / "drafts"
OUTPUT_DIR = DATA_DIR / "out"

# SUSALUD runs its own CKAN instance; the national portal blocks plain clients.
CKAN_BASE_URL = os.environ.get("CONFIA2_CKAN_BASE_URL", "http://datos.susalud.gob.pe")
CKAN_API_URL = f"{CKAN_BASE_URL}/api/3/action"
USER_AGENT = "confia2-scraper/0.1 (academic project; SUSALUD open data)"

DATASETS = {
    "renipress": "registro-nacional-de-ipress-renipress",
    "capacity": "consulta-recursos-de-salud-por-ipress",
    "procedures": "consulta-g-produccion-asistencial-de-procedimientos-por-ipress",
}

# El catálogo no es estable: medido el 14-10-2026, SUSALUD **retiró** el paquete histórico de
# recursos de salud y el identificador que usábamos pasó a dar 404, mientras la copia local
# seguía siendo válida. Cada fuente acepta alternativas, y `package_search` no sirve como plan B
# porque en ese CKAN devuelve HTML en vez de JSON.
DATASET_ALTERNATIVES = {
    "renipress": (
        "registro-nacional-de-ipress-renipress",
        "registro-nacional-de-entidades-prestadoras-de-servicios-de-salud-renipress",
    ),
    "capacity": (
        "consulta-recursos-de-salud-por-ipress",
        "consulta-recursos-de-salud-2018",
        "consulta-recursos-de-salud-2017",
        "consulta-recursos-de-salud-2016",
        "consulta-recursos-de-salud-2015",
    ),
    "procedures": (
        "consulta-g-produccion-asistencial-de-procedimientos-por-ipress",
        "consulta-g-produccion-asistencial-de-procedimientos",
    ),
}

# Cómo se reconoce la copia local de cada fuente cuando el catálogo ya no la publica.
DATASET_FILE_PATTERN = {
    "renipress": "RENIPRESS_*.csv",
    "capacity": "ConsultaA_*.csv",
    "procedures": "ConsultaG_*.csv",
}

# Target profile: private, active, I-3 / I-4 (docs section 4).
TARGET_INSTITUTIONS = frozenset({"PRIVADO"})
TARGET_CATEGORIES = frozenset({"I-3", "I-4"})
ACTIVE_STATUS = "ACTIVO"

HTTP_TIMEOUT_SECONDS = 60.0

# Search provider for the web enrichment, and the environment variable each one
# reads. The key is never written to the repository: locally it lives in `.env`
# (gitignored, dockerignored) and in production it comes from Secret Manager.
SEARCH_PROVIDERS = {
    "serper": "SERPER_API_KEY",
    "brave": "BRAVE_API_KEY",
    "google_cse": "GOOGLE_CSE_API_KEY",
}
SEARCH_PROVIDER_VARIABLE = "CONFIA2_SEARCH_PROVIDER"

# The model that fills the outreach slots. LiteLLM addresses any provider as
# `provider/model`, so the document's Gemini Flash stays a configuration detail and
# the code carries no provider lock-in.
LLM_MODEL_VARIABLE = "CONFIA2_LLM_MODEL"
LLM_API_BASE_VARIABLE = "CONFIA2_LLM_API_BASE"
LLM_API_KEY_VARIABLE = "CONFIA2_LLM_API_KEY_VAR"
LLM_RESPONSE_FORMAT_VARIABLE = "CONFIA2_LLM_RESPONSE_FORMAT"
RESPONSE_FORMATS = ("auto", "schema", "json_object", "plain")

# What the document names as the stack.
DOCUMENT_DEFAULT_MODEL = "gemini/gemini-2.0-flash"

# The NaN API is OpenAI-compatible (https://api.nan.builders/v1), so LiteLLM reaches it
# with the `openai/` prefix. When NAN_API_KEY is the only credential present, these are
# the documented starting values, which is what makes the owner's key work with no
# further configuration.
NAN_API_BASE = "https://api.nan.builders/v1"
NAN_API_KEY_VARIABLE = "NAN_API_KEY"
NAN_DEFAULT_MODEL = "openai/deepseek-v4-flash"
# Medido el 13-10-2026: la API de NaN respondió 400 a `response_format` con esquema
# estricto y aceptó modo JSON. Fijarlo evita gastar un request en cada corrida y evita
# ensuciar el log con un banner de error que parece del proveedor y no lo es. La garantía
# sigue siendo la validación local con Pydantic, no la imposición del esquema en el server.
NAN_DEFAULT_RESPONSE_FORMAT = "json_object"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTREACH_TEMPLATE = TEMPLATES_DIR / "outreach-oaas.md"


class MissingCredentialsError(RuntimeError):
    """A required API key is not present in the environment."""


def _near_miss_variable(variable: str) -> str | None:
    """A name that differs from `variable` only by surrounding whitespace.

    Measured on this project: `NAN_API_KEY =sk-...` in `.env` is tolerated by
    python-dotenv but not by `podman --env-file`, which hands the container the name
    *with* the trailing space. Inside, the variable is invisible and the symptom is
    "missing key", which sends the operator looking in the wrong place.
    """
    return next(
        (name for name in os.environ if name != variable and name.strip() == variable),
        None,
    )


def _whitespace_hint(variable: str) -> str:
    offender = _near_miss_variable(variable)
    if not offender:
        return ""
    return (
        f"\nHay una variable '{offender}' en el entorno: en .env sobra un espacio "
        "alrededor del '='. Python lo tolera, 'podman --env-file' no. Escribilo como "
        f"'{variable}=tu_clave', sin espacios."
    )


def resolve_search_credentials(provider: str | None = None) -> tuple[str, str]:
    """Return `(provider, api_key)` for the search step.

    The provider can be named explicitly, by argument or by
    `CONFIA2_SEARCH_PROVIDER`; otherwise the single key present in the environment
    decides, so pasting one key is enough to make the enrichment work.

    Every failure path names the variable to fill in, because the alternative is a
    provider-specific crash deep inside a request.
    """
    configured = (provider or os.environ.get(SEARCH_PROVIDER_VARIABLE) or "").strip().lower()
    if configured and configured not in SEARCH_PROVIDERS:
        raise MissingCredentialsError(
            f"unknown search provider '{configured}'; known providers: "
            + ", ".join(sorted(SEARCH_PROVIDERS))
        )

    candidates = (
        [(configured, SEARCH_PROVIDERS[configured])]
        if configured
        else sorted(SEARCH_PROVIDERS.items())
    )
    present = [
        (name, os.environ.get(variable, "").strip())
        for name, variable in candidates
    ]
    with_key = [(name, key) for name, key in present if key]

    if len(with_key) == 1:
        return with_key[0]
    if len(with_key) > 1:
        raise MissingCredentialsError(
            "more than one search API key is set; choose one with "
            f"{SEARCH_PROVIDER_VARIABLE}=" + "|".join(name for name, _ in with_key)
        )

    variable = present[0][1] if len(present) == 1 else SEARCH_PROVIDERS["serper"]
    raise MissingCredentialsError(
        f"no search API key found: {variable} is empty. "
        f"Put your key in .env at the project root, like this:\n    {variable}=tu_clave"
        + _whitespace_hint(variable)
    )


@dataclass(frozen=True)
class LlmEndpoint:
    """Where the drafts come from: a model, plus a custom endpoint when there is one."""

    model: str
    api_base: str | None = None
    api_key: str | None = None
    response_format: str = "auto"

    @property
    def uses_custom_endpoint(self) -> bool:
        return self.api_base is not None

    def describe(self) -> str:
        """Safe to log: the key is never part of it."""
        where = self.api_base and f" via {self.api_base}"
        if self.uses_custom_endpoint:
            return f"{self.model}{where} (clave presente, formato {self.response_format})"
        return f"{self.model} (el proveedor resuelve la clave, formato {self.response_format})"


def _with_openai_prefix(model: str) -> str:
    """LiteLLM routes an OpenAI-compatible endpoint by the `openai/` prefix.

    Adding it here keeps the failure from showing up as an opaque provider error.
    """
    return model if "/" in model else f"openai/{model}"


def resolve_llm_endpoint(
    model: str | None = None,
    api_base: str | None = None,
    api_key_variable: str | None = None,
) -> LlmEndpoint:
    """Resolve the model, and the custom endpoint when one is in play.

    Order, documented so nobody has to guess: explicit argument, then the environment,
    then the NaN API when its key is the only credential present, and otherwise the
    model the document names.
    """
    configured_base = (api_base or os.environ.get(LLM_API_BASE_VARIABLE) or "").strip()
    configured_model = (model or os.environ.get(LLM_MODEL_VARIABLE) or "").strip()
    nan_key = os.environ.get(NAN_API_KEY_VARIABLE, "").strip()

    requested_format = (os.environ.get(LLM_RESPONSE_FORMAT_VARIABLE) or "").strip().lower()
    if requested_format and requested_format not in RESPONSE_FORMATS:
        raise ValueError(
            f"unknown {LLM_RESPONSE_FORMAT_VARIABLE}='{requested_format}'; "
            f"known values: {', '.join(RESPONSE_FORMATS)}"
        )

    if not configured_base and not configured_model and nan_key:
        return LlmEndpoint(
            model=NAN_DEFAULT_MODEL,
            api_base=NAN_API_BASE,
            api_key=nan_key,
            response_format=requested_format or NAN_DEFAULT_RESPONSE_FORMAT,
        )

    if not configured_base:
        return LlmEndpoint(
            model=configured_model or DOCUMENT_DEFAULT_MODEL,
            response_format=requested_format or "auto",
        )

    variable = (
        api_key_variable or os.environ.get(LLM_API_KEY_VARIABLE) or NAN_API_KEY_VARIABLE
    ).strip()
    key = os.environ.get(variable, "").strip()
    if not key:
        raise MissingCredentialsError(
            f"a custom api_base needs its key, and {variable} is empty. "
            f"Put it in .env at the project root, like this:\n    {variable}=tu_clave"
            + _whitespace_hint(variable)
        )

    chosen = configured_model or (NAN_DEFAULT_MODEL if configured_base == NAN_API_BASE else "")
    if not chosen:
        raise MissingCredentialsError(
            f"a custom api_base needs a model: set {LLM_MODEL_VARIABLE} to provider/model"
        )

    return LlmEndpoint(
        model=_with_openai_prefix(chosen),
        api_base=configured_base,
        api_key=key,
        response_format=requested_format or "auto",
    )
