"""Catálogo maestro de ConfIA: datos regulatorios oficiales por línea de producto.

Los registros sanitarios, certificados y consentimientos pertenecen a los equipos que
ConfIA comercializa, no a la clínica prospecto. Por eso viven aquí, inmutables, y el
backend los asigna a cada dossier. Ningún cliente puede enviarlos ni modificarlos.

Fuente: datos mock de `src/data/mockData.ts`. Son el estándar provisional hasta que el
equipo regulatorio confirme los valores reales.
"""

import unicodedata
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict


class RegulatoryData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    registry_number: str
    classification: str
    calibration_certificate: str
    good_practices_certificate: str
    informed_consent_template: str


class ProductLine(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    name: str
    equipment_model: str
    # Palabras clave normalizadas (sin tildes, minúsculas) que activan esta línea
    # a partir de la especialidad de la clínica.
    specialty_keywords: tuple[str, ...]
    regulatory: RegulatoryData


DEFAULT_PRODUCT_LINE_KEY = "ozonobaric_ahtm"

PRODUCT_LINES: MappingProxyType[str, ProductLine] = MappingProxyType(
    {
        line.key: line
        for line in (
            ProductLine(
                key="ozonette_infiltracion",
                name="Ozonette — Generador compacto para infiltración y dolor",
                equipment_model="Ozonette (SEDECAL)",
                specialty_keywords=(
                    "traumat",
                    "ortop",
                    "dolor",
                    "columna",
                    "rehabilit",
                    "fisiatr",
                    "deporte",
                    "dermat",
                    "estetic",
                ),
                regulatory=RegulatoryData(
                    registry_number="DM-14820-E",
                    classification="Dispositivo Médico Clase IIb (SEDECAL, España)",
                    calibration_certificate="Calibración de fábrica — SEDECAL ISO 13485",
                    good_practices_certificate="Droguería Autorizada Tecnology Care SRL — DIGEMID",
                    informed_consent_template="Formato de consentimiento informado para autohemoterapia mayor (AHTm)",
                ),
            ),
            ProductLine(
                key="ozonobaric_ahtm",
                name="Ozonobaric P — Equipo clínico multidisciplinar (AHTm)",
                equipment_model="Ozonobaric P (SEDECAL)",
                specialty_keywords=("reumat", "antienvejec", "regenerat", "ahtm", "autohemoterapia"),
                regulatory=RegulatoryData(
                    registry_number="DM-15943-E",
                    classification="Dispositivo Médico Clase IIb (DIGEMID)",
                    calibration_certificate="Calibración de fábrica — SEDECAL ISO 13485",
                    good_practices_certificate="Droguería Autorizada Tecnology Care SRL — DIGEMID",
                    informed_consent_template="Formato de consentimiento informado para autohemoterapia mayor (AHTm)",
                ),
            ),
        )
    }
)


class UnknownProductLineError(ValueError):
    """La línea de producto pedida explícitamente no existe en el catálogo."""


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def resolve_product_line(specialty: str, explicit_key: str | None = None) -> tuple[ProductLine, str]:
    """Devuelve la línea de producto y cómo se eligió: explicit, specialty o default.

    Nunca falla por falta de datos del lead: si la especialidad no coincide con ninguna
    línea, se usa la línea por defecto.
    """
    if explicit_key is not None:
        line = PRODUCT_LINES.get(explicit_key)
        if line is None:
            raise UnknownProductLineError(f"La línea de producto '{explicit_key}' no existe en el catálogo.")
        return line, "explicit"

    normalized = _normalize(specialty)
    for line in PRODUCT_LINES.values():
        if any(keyword in normalized for keyword in line.specialty_keywords):
            return line, "specialty"

    return PRODUCT_LINES[DEFAULT_PRODUCT_LINE_KEY], "default"
