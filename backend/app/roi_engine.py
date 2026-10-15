"""Motor de la oferta y contraoferta (procedimiento v0.3, calculadora 07).

Calcula inversión, flujo, recuperación, retorno, margen de Tecnocare y la zona de acuerdo.
No hay IA aquí: las cifras son deterministas y las valida el dueño.
"""

from dataclasses import dataclass
from enum import Enum

from .negotiation_params import (
    CLINIC_MAX_RECOVERY_MONTHS,
    EVALUATION_HORIZON_MONTHS,
    EXCHANGE_RATE_PEN_PER_USD,
    MAX_INSTALLMENTS,
    MIN_INCLUDED_TRAINING_SESSIONS,
    MIN_WARRANTY_MONTHS,
    PRODUCTS,
    TECNOCARE_MIN_MARGIN,
    Product,
)


class UnknownProductError(ValueError):
    """El product_id no existe en el catálogo de negociación."""


class Zone(str, Enum):
    WIN_WIN = "win_win"  # Clínica y Tecnocare cumplen: viable
    CLINIC_ONLY = "clinic_only"  # Solo la clínica cumple: subir el precio del equipo hasta el mínimo
    TECNOCARE_ONLY = "tecnocare_only"  # Solo Tecnocare cumple: mover palancas
    NONE = "none"  # Ninguno cumple: no hay trato


@dataclass(frozen=True)
class Offer:
    product_id: str
    session_price_pen: float  # precio por sesión que cobra la clínica (PEN)
    sessions_per_month: int
    equipment_price_usd: float
    installation_included: bool
    training_included_sessions: int
    installments: int
    warranty_months: int


@dataclass(frozen=True)
class Evaluation:
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
    violations: tuple[str, ...]

    @property
    def is_win_win(self) -> bool:
        return self.zone is Zone.WIN_WIN and not self.violations


def get_product(product_id: str) -> Product:
    product = PRODUCTS.get(product_id)
    if product is None:
        raise UnknownProductError(f"El producto '{product_id}' no existe en el catálogo de negociación.")
    return product


def validate_offer(offer: Offer) -> list[str]:
    """Reglas de la oferta que no se pueden saltar (piso de capacitación, plazo y garantía)."""
    product = get_product(offer.product_id)
    violations: list[str] = []

    if offer.equipment_price_usd <= 0:
        violations.append("El precio del equipo debe ser mayor que cero.")
    if offer.equipment_price_usd > product.list_price_usd:
        violations.append(
            f"El precio del equipo ({offer.equipment_price_usd:,.0f} USD) supera la lista "
            f"({product.list_price_usd:,.0f} USD)."
        )
    if offer.session_price_pen < 0 or offer.sessions_per_month < 0:
        violations.append("El precio por sesión y las sesiones por mes no pueden ser negativos.")
    if offer.training_included_sessions < MIN_INCLUDED_TRAINING_SESSIONS:
        violations.append(
            f"La capacitación incluida mínima es {MIN_INCLUDED_TRAINING_SESSIONS} sesión (U-03)."
        )
    if not 1 <= offer.installments <= MAX_INSTALLMENTS:
        violations.append(f"El plazo de pago máximo es {MAX_INSTALLMENTS} cuotas (U-04).")
    if offer.warranty_months < MIN_WARRANTY_MONTHS:
        violations.append(f"La garantía mínima es {MIN_WARRANTY_MONTHS} meses (U-05).")

    return violations


def evaluate(offer: Offer) -> Evaluation:
    product = get_product(offer.product_id)

    session_usd = offer.session_price_pen / EXCHANGE_RATE_PEN_PER_USD
    monthly_flow = offer.sessions_per_month * (session_usd - product.consumable_per_session_usd)

    installation_charged = 0.0 if offer.installation_included else product.installation_price_usd
    training_charged = (
        max(0, product.required_training_sessions - offer.training_included_sessions)
        * product.training_price_per_session_usd
    )
    investment = offer.equipment_price_usd + installation_charged + training_charged

    recovery = investment / monthly_flow if monthly_flow > 0 else None
    return_24m = (monthly_flow * EVALUATION_HORIZON_MONTHS - investment) / investment if investment > 0 else None
    clinic_viable = recovery is not None and recovery <= CLINIC_MAX_RECOVERY_MONTHS

    # Costo de Tecnocare: la instalación se paga aunque el cliente no la pague.
    cost_total = (
        product.acquisition_cost_usd
        + product.installation_cost_usd
        + product.required_training_sessions * product.training_cost_per_session_usd
    )
    margin = (investment - cost_total) / investment if investment > 0 else None
    tecnocare_viable = margin is not None and margin >= TECNOCARE_MIN_MARGIN
    min_equipment_price = cost_total / (1 - TECNOCARE_MIN_MARGIN) - installation_charged - training_charged

    if clinic_viable and tecnocare_viable:
        zone = Zone.WIN_WIN
    elif clinic_viable:
        zone = Zone.CLINIC_ONLY
    elif tecnocare_viable:
        zone = Zone.TECNOCARE_ONLY
    else:
        zone = Zone.NONE

    return Evaluation(
        investment_usd=investment,
        monthly_flow_usd=monthly_flow,
        recovery_months=recovery,
        return_24m=return_24m,
        margin=margin,
        installation_charged_usd=installation_charged,
        training_charged_usd=training_charged,
        clinic_viable=clinic_viable,
        tecnocare_viable=tecnocare_viable,
        zone=zone,
        min_equipment_price_usd=min_equipment_price,
        violations=tuple(validate_offer(offer)),
    )


ZONE_MESSAGES = {
    Zone.WIN_WIN: "Zona de acuerdo: margen aceptable y recuperación dentro del umbral.",
    Zone.CLINIC_ONLY: (
        "Alerta: el margen de Tecnocare queda bajo el piso. Requiere aprobación gerencial; "
        "subir el precio del equipo hasta el mínimo sin pasar la lista."
    ),
    Zone.TECNOCARE_ONLY: (
        "Alerta: la clínica no recupera dentro del umbral. Mover las palancas de Tecnocare "
        "en orden, sin bajar de ningún piso."
    ),
    Zone.NONE: "Sin acuerdo: ninguna versión cumple a la vez a la clínica y a Tecnocare.",
}
