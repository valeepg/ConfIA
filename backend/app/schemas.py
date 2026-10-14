from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class ValidatedRegulatoryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registry_number: str = Field(min_length=1, max_length=120)
    classification: str = Field(min_length=1, max_length=160)
    calibration_certificate: str = Field(min_length=1, max_length=160)
    good_practices_certificate: str = Field(min_length=1, max_length=200)
    informed_consent_template: str = Field(min_length=1, max_length=200)


class DossierInput(ProspectInput):
    validated_regulatory_data: ValidatedRegulatoryData


class DossierOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    registry_number: str
    classification: str
    calibration_certificate: str
    good_practices_certificate: str
    informed_consent_template: str
    verification_required: bool
    warnings: list[str] = Field(min_length=1, max_length=10)
