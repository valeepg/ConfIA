from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .confia_product_catalog import RegulatoryData
from .roi_engine import Offer, Zone


class ProspectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    district: str = Field(min_length=1, max_length=120)
    specialty: str = Field(min_length=1, max_length=160)
    director_medico: str = Field(min_length=1, max_length=160)
    doctor_specialty: str = Field(min_length=1, max_length=160)
    score: int = Field(ge=0, le=100)
    ai_suggestion: str = Field(min_length=1, max_length=2000)


class RoiInput(ProspectInput):
    equipment_model: str = Field(min_length=1, max_length=200)
    monthly_lease_cost: float = Field(ge=0)
    minimum_kits_per_month: int = Field(ge=0)
    cost_per_session: float = Field(ge=0)
    patient_price_avg: float = Field(ge=0)
    projected_sessions_month: int = Field(ge=0)


class RoiOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2000)
    equipment_model: str
    monthly_lease_cost: float = Field(ge=0)
    minimum_kits_per_month: int = Field(ge=0)
    cost_per_session: float = Field(ge=0)
    patient_price_avg: float = Field(ge=0)
    projected_sessions_month: int = Field(ge=0)
    estimated_net_monthly: float = Field(ge=0)
    assumptions: list[str] = Field(min_length=1, max_length=10)


class OutboundOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_name: str
    recipient_role: str
    subject: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=4000)
    suggested_channel: Literal["Email", "LinkedIn", "WhatsApp Directo"]
    evidence_used: list[str] = Field(min_length=1, max_length=10)


class DossierInput(ProspectInput):
    # Opcional: si no llega, la carpeta del lead se deriva del nombre normalizado.
    lead_id: str | None = Field(default=None, min_length=1, max_length=160)
    # Opcional: fuerza una línea del catálogo. Si no llega, se resuelve por especialidad.
    product_line: str | None = Field(default=None, min_length=1, max_length=80)


class DossierDocumentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str
    version: int = Field(ge=1)
    version_label: str
    product_line: str
    product_name: str
    # explicit: pedida en la petición; specialty: por especialidad; default: sin coincidencia.
    catalog_match: Literal["explicit", "specialty", "default"]
    regulatory_data: RegulatoryData
    markdown_path: str
    pdf_path: str
    download_urls: dict[str, str]
    generated_at: str
    # Siempre True: el documento lo revisa el equipo regulatorio antes de enviarse.
    verification_required: Literal[True] = True


class OfferInput(BaseModel):
    """Parámetros que ajusta el dueño en el simulador de contraofertas."""

    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(min_length=1, max_length=80)
    session_price_pen: float = Field(ge=0, le=100000)
    sessions_per_month: int = Field(ge=0, le=1000)
    equipment_price_usd: float = Field(ge=0, le=1000000)
    installation_included: bool = False
    training_included_sessions: int = Field(ge=0, le=20)
    installments: int = Field(ge=1, le=60)
    warranty_months: int = Field(ge=0, le=240)

    def to_offer(self) -> Offer:
        # Solo los campos de la oferta: las subclases añaden datos del lead que no van al motor.
        return Offer(**{name: getattr(self, name) for name in Offer.__dataclass_fields__})


class EvaluationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    investment_usd: float
    monthly_flow_usd: float
    recovery_months: float | None
    return_24m: float | None
    margin: float | None
    installation_charged_usd: float
    training_charged_usd: float
    clinic_viable: bool
    tecnocare_viable: bool
    zone: Zone
    min_equipment_price_usd: float | None
    violations: list[str]
    status: Literal["green", "red"]
    message: str
    data_status: str


class ProformaInput(OfferInput):
    lead_name: str = Field(min_length=1, max_length=160)
    lead_id: str | None = Field(default=None, min_length=1, max_length=160)


class ProformaOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str
    version: int = Field(ge=1)
    version_label: str
    product_name: str
    evaluation: EvaluationOutput
    pdf_path: str
    params_path: str
    download_urls: dict[str, str]
    generated_at: str


class LeadDocumentFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    filename: str
    label: str
    download_url: str


class LeadDocumentsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str
    files: list[LeadDocumentFile]


class AttachmentRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    filename: Literal["document.pdf", "propuesta_comercial.pdf"]


class OutboundSendInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str = Field(min_length=1, max_length=160)
    lead_name: str = Field(min_length=1, max_length=160)
    to: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    subject: str = Field(min_length=1, max_length=180)
    # Cuerpo editado por el dueño en el modal (texto plano).
    body: str = Field(min_length=1, max_length=8000)
    attachments: list[AttachmentRef] = Field(default_factory=list, max_length=5)


class OutboundSendOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["contactado"]
    message_id: str
    sent_at: str
    to: str
    subject: str
    attachments: list[str]
