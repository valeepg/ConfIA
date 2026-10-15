"""The back-office copilot: drafts a personalized outreach message, and cannot invent.

The master document is explicit (docs/Document from Diego.markdown):

- "la IA trabaja en el back-office y nunca habla con el paciente";
- "toda salida de IA es un borrador sujeto a aprobación del dueño antes de salir";
- "Gemini no redacta libremente especificaciones técnicas ni normativas. Rellena
  variables sobre plantillas fijas" (guardarraíl anti-alucinación, RNF-06).

So this is deliberately **not** an agent: no tools, no free-form prose over regulation.
The owner's text lives in a `Template`; the model only fills the personalized slots.
Assembly happens in code, which means the commercial and regulatory paragraphs are
byte-identical to what the owner approved, no matter what the model returns.

And the result is verified, not merely requested: a draft that contains a quantity or a
piece of regulatory vocabulary that is not in the facts and not in the template is
**rejected**. A prompt is a request; a verifier is a guarantee.

There is no send path in this module, by design. Sending is the owner's action, one
message at a time, exactly as the document requires.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from .contract import Prospect
from .text import fold_text

STATUS_PENDING = "pending_approval"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

# Medido: una corrida de 10 borradores murió en el sexto por un fallo transitorio del proveedor,
# sin dejar mensaje y con lo ya pagado perdido. Es la misma lección que las consultas de búsqueda:
# un hipo del proveedor no puede voltear un lote, y no se paga dos veces por lo mismo.
RETRY_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 120.0
# Una respuesta que no valida se reintenta una vez pidiendo las claves que faltan: medido, una
# respuesta sin `opening` aborto un lote de diez borradores.
REPAIR_ATTEMPTS = 1
CACHE_SUFFIX = ".json"

# Vocabulary the model may only use when the owner's template already uses it. The
# guardarraíl exists so a model cannot promise compliance, cite a norm or describe a
# dose on its own initiative.
SENSITIVE_TERMS = (
    "registro sanitario",
    "digemid",
    "minsa",
    "ley",
    "decreto",
    "iso ",
    "clase ii",
    "clase iii",
    "bpm",
    "buenas practicas",
    "certificado",
    "calibracion",
    "declaracion de madrid",
    "isco3",
    "ahtm",
    "autohemoterapia",
    "dosis",
    "concentracion",
    "ug/ml",
    "endovenosa",
    "comodato",
    "leasing",
)

# Numeric runs shorter than this are ignored: they are usually ordinals or part of a
# word, and the guard is aimed at quantities somebody would act on.
_MINIMUM_QUANTITY_DIGITS = 2
_DIGIT_RUN = re.compile(r"\D+")
_PLACEHOLDER = re.compile(r"\[[^\[\]]+\]")


class OutreachDraft(BaseModel):
    """The only thing the model is allowed to produce: the personalized slots."""

    subject: str = Field(min_length=1, max_length=140)
    greeting: str = Field(min_length=1, max_length=200)
    opening: str = Field(min_length=1, max_length=600)
    talking_points: list[str] = Field(default_factory=list, max_length=4)


class Completer(Protocol):
    """A model call. Injected so every test in this file runs without a network."""

    def __call__(
        self, *, model: str, system: str, user: str, schema: type[BaseModel]
    ) -> BaseModel: ...


@dataclass(frozen=True)
class Template:
    """The owner's approved text, with slots the model may fill.

    Nothing outside the slots is ever produced by a model.
    """

    name: str
    text: str
    slots: tuple[str, ...] = ("subject", "greeting", "opening", "talking_points")


@dataclass(frozen=True)
class OutreachFacts:
    """Everything the model is allowed to know about one clinic.

    For a registry prospect that is the registry fields; for a place found by search it is what
    Google knows, which is where the personalization for the focused segment actually lives: the
    type of centre, how many patients reviewed it, and whether it belongs to a brand with several
    sites.
    """

    prospect_id: str
    clinic_name: str
    district: str
    department: str
    category: str
    classification: str
    doctors_total: int | None
    score_level: str
    tags: tuple[str, ...] = ()
    google_category: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    website: str | None = None
    chain_sites: int = 1

    def render(self) -> str:
        doctors = (
            "sin dato en el registro"
            if self.doctors_total is None
            else str(self.doctors_total)
        )
        lineas = [
            f"nombre: {self.clinic_name}",
            f"distrito: {self.district}",
            f"departamento: {self.department}",
            f"categoria: {self.category}",
            f"clasificacion: {self.classification}",
            f"medicos registrados: {doctors}",
            f"prioridad: {self.score_level}",
        ]
        if self.google_category:
            lineas.append(f"tipo de centro segun Google: {self.google_category}")
        if self.rating is not None:
            lineas.append(f"calificacion de pacientes: {self.rating}")
        if self.rating_count is not None:
            lineas.append(f"cantidad de resenas de pacientes: {self.rating_count}")
        if self.chain_sites > 1:
            lineas.append(f"sucursales de la misma marca: {self.chain_sites}")
        if self.website:
            lineas.append(f"sitio web: {self.website}")
        return "\n".join(lineas)

    def allowed_quantities(self) -> frozenset[str]:
        return quantities_in(self.render())

    def allowed_terms(self) -> frozenset[str]:
        return sensitive_terms_in(self.render())


def facts_from_prospect(prospect: Prospect) -> OutreachFacts:
    """Build the facts bundle from either origin.

    Measured: this read `prospect.score.level` unconditionally and crashed on a search result,
    where the registry score is null and the category is unknown. Both are now stated as missing
    instead of assumed, and what Google knows is added, because that is where the personalization
    for the focused segment lives.
    """
    google = prospect.google
    return OutreachFacts(
        prospect_id=prospect.id,
        clinic_name=prospect.name,
        district=prospect.location.district,
        department=prospect.location.department,
        category=prospect.category or "sin dato en el registro",
        classification=prospect.classification or "sin dato en el registro",
        # Unknown must stay unknown: a clinic with no capacity record is not a clinic
        # with zero doctors, and the model would happily write "0 medicos".
        doctors_total=None if prospect.capacity.period is None else prospect.capacity.doctors_total,
        score_level=prospect.score.level if prospect.score else "sin puntaje del padron",
        tags=tuple(prospect.tags),
        google_category=google.category if google else None,
        rating=google.rating if google else None,
        rating_count=google.rating_count if google else None,
        website=google.website if google else None,
        chain_sites=google.chain_sites if google else 1,
    )


def quantities_in(text: str) -> frozenset[str]:
    """Digit runs of the text, normalised, long enough to be a quantity."""
    return frozenset(
        run for run in _DIGIT_RUN.split(text or "") if len(run) >= _MINIMUM_QUANTITY_DIGITS
    )


def sensitive_terms_in(text: str) -> frozenset[str]:
    folded = fold_text(text)
    return frozenset(term for term in SENSITIVE_TERMS if term in folded)


def unresolved_placeholders(text: str) -> tuple[str, ...]:
    return tuple(_PLACEHOLDER.findall(text or ""))


def verify_draft(
    draft: OutreachDraft,
    *,
    facts: OutreachFacts,
    template: Template,
) -> tuple[str, ...]:
    """Return every reason this draft must not leave the back office.

    An empty tuple means the draft stayed inside what it was given.
    """
    rendered = "\n".join(
        (draft.subject, draft.greeting, draft.opening, *draft.talking_points)
    )
    allowed_quantities = facts.allowed_quantities() | quantities_in(template.text)
    allowed_terms = facts.allowed_terms() | sensitive_terms_in(template.text)

    violations: list[str] = []

    for quantity in sorted(quantities_in(rendered) - allowed_quantities):
        if not any(quantity in allowed for allowed in allowed_quantities):
            violations.append(f"cantidad no respaldada por los datos: '{quantity}'")

    for term in sorted(sensitive_terms_in(rendered) - allowed_terms):
        violations.append(
            f"vocabulario regulatorio que el template no autoriza: '{term}'"
        )

    return tuple(violations)


def assemble_message(template: Template, draft: OutreachDraft) -> str:
    """Put the model's slots inside the owner's text, in code.

    The template text is copied byte for byte: the model cannot rewrite a paragraph it
    never produced.
    """
    points = "\n".join(f"- {point}" for point in draft.talking_points)
    return (
        template.text.replace("{subject}", draft.subject)
        .replace("{greeting}", draft.greeting)
        .replace("{opening}", draft.opening)
        .replace("{talking_points}", points)
    )


@dataclass(frozen=True)
class DraftSubmission:
    prospect_id: str
    template_name: str
    model: str
    draft: OutreachDraft
    message: str
    violations: tuple[str, ...] = ()
    status: str = STATUS_PENDING
    approver: str | None = None

    @property
    def is_clean(self) -> bool:
        return not self.violations

    @property
    def missing_human_data(self) -> tuple[str, ...]:
        """Placeholders the owner still has to fill, for the approval screen to show."""
        return unresolved_placeholders(self.message)

    @property
    def can_be_sent(self) -> bool:
        """Clean and approved. Sending itself is not this module's job."""
        return self.is_clean and self.status == STATUS_APPROVED

    def to_json(self) -> str:
        return json.dumps(
            {
                "prospect_id": self.prospect_id,
                "template_name": self.template_name,
                "model": self.model,
                "draft": self.draft.model_dump(mode="json"),
                "message": self.message,
                "violations": list(self.violations),
                "status": self.status,
                "approver": self.approver,
            },
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, raw: str) -> "DraftSubmission":
        data = json.loads(raw)
        return cls(
            prospect_id=data["prospect_id"],
            template_name=data["template_name"],
            model=data["model"],
            draft=OutreachDraft.model_validate(data["draft"]),
            message=data["message"],
            violations=tuple(data.get("violations", [])),
            status=data.get("status", STATUS_PENDING),
            approver=data.get("approver"),
        )


def build_prompt(facts: OutreachFacts, template: Template) -> tuple[str, str]:
    system = (
        "Escribis un borrador de contacto comercial B2B para clinicas peruanas, en "
        "espanol, tono profesional y breve. Reglas que no se negocian: usa solo los "
        "datos que te doy; no inventes cifras, precios, normas, registros sanitarios "
        "ni dosis; no prometas eficacia clinica; no menciones al paciente."
    )
    user = (
        "Datos reales de la clinica (es lo unico que podes afirmar):\n"
        f"{facts.render()}\n\n"
        "Texto del dueño donde entran tus partes (no lo reescribas):\n"
        f"{template.text}\n\n"
        "Devolve: subject, greeting (sin nombre de persona, no lo tenemos), opening "
        "(una o dos frases sobre por que le escribimos a ESTA clinica, solo con los "
        "datos de arriba) y hasta 4 talking_points, cada uno apoyado en un dato y diciendo "
        "que le habilita ese dato a la clinica.\n"
        "No menciones etiquetas, puntajes ni codigos internos: son nuestros, no de ellos. "
        "No prometas resultados clinicos ni comerciales.\n"
        "Responde unicamente con un objeto JSON con esas cuatro claves; talking_points "
        "es una lista de textos."
    )
    return system, user


# Which attempt worked for each model, learned once per process so a provider without
# schema support pays for the discovery only on its first call.
_WORKING_ATTEMPT: dict[str, int] = {}


def _response_format_attempts(
    schema: type[BaseModel], response_format: str = "auto"
) -> tuple[dict[str, Any], ...]:
    """Strongest form first, then weaker ones, unless the format is pinned.

    Server-side schema enforcement is a convenience, not the guarantee: the reply is
    validated against the Pydantic schema here either way, and the verifier runs after
    that. A provider that cannot enforce schemas therefore loses nothing that matters,
    and an unknown OpenAI-compatible endpoint is covered without a capability guess.

    A pinned format is a decision, not a hint: it is used alone, so a wrong pin fails
    loudly instead of silently degrading.
    """
    if response_format == "schema":
        return ({"response_format": schema},)
    if response_format == "json_object":
        return ({"response_format": {"type": "json_object"}},)
    if response_format == "plain":
        return ({},)
    return (
        {"response_format": schema},
        {"response_format": {"type": "json_object"}},
        {},
    )


def _rejected_response_format(error: Exception) -> bool:
    message = str(error).lower()
    return "response_format" in message or "json_schema" in message


def litellm_completer(
    *,
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel],
    api_base: str | None = None,
    api_key: str | None = None,
    response_format: str = "auto",
) -> BaseModel:
    """The real model call, with a bounded repair round. `litellm` is imported here.

    Measured: the model once answered with a JSON object that had no `opening` key, and that single
    malformed reply aborted a batch of ten drafts. A reply that does not match the schema is not a
    reason to lose the other nine, so one explicit correction is asked for — naming the keys that
    were missing — and only then does this give up, raising the `ValidationError` so the caller can
    tell a content problem from a configuration one.
    """
    import litellm

    # The provider list and the "file a bug" banner are noise for a rejection we handle.
    litellm.suppress_debug_info = True

    kwargs: dict[str, Any] = {
        "model": model,
        # El proveedor reintenta solo lo transitorio: un 429 o un 5xx no es un error de la
        # petición, y perder diez borradores por uno es desproporcionado.
        "num_retries": RETRY_ATTEMPTS,
        "timeout": REQUEST_TIMEOUT_SECONDS,
    }
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    attempts = _response_format_attempts(schema, response_format)
    discovering = response_format == "auto"
    first = min(_WORKING_ATTEMPT.get(model, 0), len(attempts) - 1) if discovering else 0
    conversacion: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    last_error: Exception | None = None

    for ronda in range(REPAIR_ATTEMPTS + 1):
        for index in range(first, len(attempts)):
            try:
                response = litellm.completion(
                    **kwargs, messages=conversacion, **attempts[index]
                )
            except Exception as error:
                last_error = error
                if index + 1 < len(attempts) and _rejected_response_format(error):
                    continue
                raise

            contenido = response.choices[0].message.content
            try:
                if discovering:
                    _WORKING_ATTEMPT[model] = index
                return schema.model_validate_json(contenido)
            except ValidationError as error:
                last_error = error
                esperadas = ", ".join(schema.model_fields)
                faltantes = [
                    str(fallo["loc"][0])
                    for fallo in error.errors()
                    if fallo.get("type") == "missing"
                ]
                detalle = (
                    f"Faltaron las claves: {', '.join(faltantes)}. " if faltantes else ""
                )
                conversacion = conversacion + [
                    {"role": "assistant", "content": contenido or ""},
                    {
                        "role": "user",
                        "content": (
                            f"Esa respuesta no valida como JSON del esquema. {detalle}"
                            f"Devolve SOLO un objeto JSON con estas claves: {esperadas}."
                        ),
                    },
                ]
                break  # el problema es el contenido, no el formato: no se prueban mas formatos

    if isinstance(last_error, ValidationError):
        raise last_error
    raise RuntimeError(f"no response format worked for {model}") from last_error


def _cache_path(cache_dir: Path, prospect_id: str) -> Path:
    return Path(cache_dir) / (re.sub(r"[^a-zA-Z0-9]+", "-", prospect_id) + CACHE_SUFFIX)


def draft_outreach(
    prospect: Prospect,
    *,
    template: Template,
    model: str,
    api_base: str | None = None,
    api_key: str | None = None,
    response_format: str = "auto",
    cache_dir: Path | None = None,
    refresh: bool = False,
    completer: Completer | None = None,
) -> DraftSubmission:
    """Produce one draft for one clinic, reusing the cached one when there is one.

    The cache matters for the same reason it does for search queries: a batch that dies halfway
    must not charge again for the drafts it already produced. Never sends anything.
    """
    cached = _cache_path(cache_dir, prospect.id) if cache_dir is not None else None
    if cached is not None and cached.exists() and not refresh:
        return DraftSubmission.from_json(cached.read_text(encoding="utf-8"))

    facts = facts_from_prospect(prospect)
    system, user = build_prompt(facts, template)
    caller: Any = completer or litellm_completer
    call: dict[str, Any] = {
        "model": model,
        "system": system,
        "user": user,
        "schema": OutreachDraft,
    }
    if api_base is not None:
        call["api_base"] = api_base
    if api_key is not None:
        call["api_key"] = api_key
    if response_format != "auto":
        call["response_format"] = response_format
    draft = caller(**call)

    submission = DraftSubmission(
        prospect_id=prospect.id,
        template_name=template.name,
        model=model,
        draft=draft,
        message=assemble_message(template, draft),
        violations=verify_draft(draft, facts=facts, template=template),
        status=STATUS_PENDING,
    )
    if cached is not None:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(submission.to_json(), encoding="utf-8")
    return submission


def approve(submission: DraftSubmission, *, approver: str) -> DraftSubmission:
    """Record the owner's approval. A draft that invented something cannot be approved."""
    if not submission.is_clean:
        raise ValueError(
            "no se puede aprobar un borrador con hallazgos: "
            + "; ".join(submission.violations)
        )
    return _replace(submission, status=STATUS_APPROVED, approver=approver)


def reject(submission: DraftSubmission, *, approver: str, reason: str) -> DraftSubmission:
    return _replace(
        submission,
        status=STATUS_REJECTED,
        approver=f"{approver}: {reason}",
    )


def _replace(submission: DraftSubmission, **changes: Any) -> DraftSubmission:
    return replace(submission, **changes)


def load_template(path: Path) -> Template:
    """Read the owner's template from a Markdown file.

    The commercial and regulatory text belongs to the owner, not to a developer, so it
    lives in `templates/` where it can be edited without touching code. An optional
    front-matter block carries the template name.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"no encuentro la plantilla del mensaje en '{path}'. La edita el dueño y vive en "
            "templates/ (por defecto templates/outreach-oaas.md); en el contenedor esa "
            "carpeta tiene que estar copiada en la imagen. Podés apuntar a otra con "
            "--template."
        )
    raw = path.read_text(encoding="utf-8")
    name = path.stem

    if raw.startswith("---"):
        _, _, rest = raw.partition("---")
        header, _, body = rest.partition("---")
        for line in header.splitlines():
            if line.strip().lower().startswith("name:"):
                name = line.split(":", 1)[1].strip()
        raw = body

    return Template(name=name, text=raw.strip() + "\n")


def submission_to_dict(submission: DraftSubmission) -> dict[str, Any]:
    """The reviewable form the approval screen reads, with the findings and the draft."""
    return {
        "prospect_id": submission.prospect_id,
        "template": submission.template_name,
        "model": submission.model,
        "status": submission.status,
        "approver": submission.approver,
        "violations": list(submission.violations),
        "missing_human_data": list(submission.missing_human_data),
        "subject": submission.draft.subject,
        "message": submission.message,
    }
