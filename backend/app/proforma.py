"""Propuesta comercial ajustada (procedimiento de oferta, sección 5, paso 7).

El documento que recibe la clínica solo muestra la oferta y el cálculo referencial.
Nunca incluye costos, margen ni precio mínimo de Tecnocare: eso queda en parametros.json,
que es interno. Los textos legales (T-01, T-02) no están aprobados: van marcados como borrador.
"""

import json
from dataclasses import asdict
from datetime import datetime, timezone

from .documents import _fill, _logo_markdown
from .negotiation_params import DATA_STATUS, EXCHANGE_RATE_PEN_PER_USD, Product
from .roi_engine import ZONE_MESSAGES, Evaluation, Offer
from .schemas import EvaluationOutput
from .storage import PROPOSAL_TEMPLATE_PATH

# T-01 de 05_textos_aprobados.xlsx: borrador, pendiente de aprobación del asesor.
DISCLAIMER = "Cálculo referencial con datos aportados por la clínica. No constituye garantía de resultados."
STATUS_TEXT = "Borrador: pendiente de aprobación del asesor y del dueño antes de enviar."
# T-02: nombre y cargo pendientes. No se inventan.
SIGNATURE = "[pendiente: nombre y cargo del remitente]"


def _usd(value: float) -> str:
    return f"USD {value:,.0f}"


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _months(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f} meses"


def to_evaluation_output(evaluation: Evaluation) -> EvaluationOutput:
    if evaluation.violations:
        message = "La oferta incumple reglas: " + " ".join(evaluation.violations)
    else:
        message = ZONE_MESSAGES[evaluation.zone]

    return EvaluationOutput(
        investment_usd=round(evaluation.investment_usd, 2),
        monthly_flow_usd=round(evaluation.monthly_flow_usd, 2),
        recovery_months=None if evaluation.recovery_months is None else round(evaluation.recovery_months, 2),
        return_24m=None if evaluation.return_24m is None else round(evaluation.return_24m, 4),
        margin=None if evaluation.margin is None else round(evaluation.margin, 4),
        installation_charged_usd=round(evaluation.installation_charged_usd, 2),
        training_charged_usd=round(evaluation.training_charged_usd, 2),
        clinic_viable=evaluation.clinic_viable,
        tecnocare_viable=evaluation.tecnocare_viable,
        zone=evaluation.zone,
        min_equipment_price_usd=None
        if evaluation.min_equipment_price_usd is None
        else round(evaluation.min_equipment_price_usd, 2),
        violations=list(evaluation.violations),
        status="green" if evaluation.is_win_win else "red",
        message=message,
        data_status=DATA_STATUS,
    )


def build_proforma_markdown(
    lead_name: str,
    product: Product,
    offer: Offer,
    evaluation: Evaluation,
    generated_at: str,
) -> str:
    template = PROPOSAL_TEMPLATE_PATH.read_text(encoding="utf-8")

    installation = (
        "Incluida"
        if offer.installation_included
        else _usd(product.installation_price_usd)
    )
    training = f"{offer.training_included_sessions} de {product.required_training_sessions} sesiones incluidas"
    if evaluation.training_charged_usd > 0:
        training += f"; sesiones adicionales: {_usd(evaluation.training_charged_usd)}"

    session_usd = offer.session_price_pen / EXCHANGE_RATE_PEN_PER_USD
    values = {
        "logo": _logo_markdown(),
        "lead_name": lead_name,
        "product_name": product.name,
        "generated_at": generated_at,
        "status": STATUS_TEXT,
        "equipment_price": _usd(offer.equipment_price_usd),
        "installation": installation,
        "training": training,
        "investment": _usd(evaluation.investment_usd),
        "installments": f"{offer.installments} cuota(s)",
        "warranty": f"{offer.warranty_months} meses",
        "session_price": f"PEN {offer.session_price_pen:,.0f} (USD {session_usd:,.2f})",
        "sessions_per_month": str(offer.sessions_per_month),
        "monthly_flow": _usd(evaluation.monthly_flow_usd),
        "recovery": _months(evaluation.recovery_months),
        "return_24m": _percent(evaluation.return_24m),
        "disclaimer": DISCLAIMER,
        "signature": SIGNATURE,
    }
    return _fill(template, values)


def proposal_params(
    lead_name: str,
    offer: Offer,
    evaluation: Evaluation,
    generated_at: str,
) -> str:
    """Registro interno de la versión: parámetros, resultado y margen (no se envía a la clínica)."""
    payload = {
        "lead_name": lead_name,
        "generated_at": generated_at,
        "data_status": DATA_STATUS,
        "offer": asdict(offer),
        "evaluation": to_evaluation_output(evaluation).model_dump(mode="json"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
