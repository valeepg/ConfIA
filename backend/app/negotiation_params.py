"""Parámetros de la oferta y contraoferta de Tecnocare (Módulo 3).

Fuente: `handsoff/bp_contraofertas/` (procedimiento v0.3 y Excel 01 a 06).
Todos los valores son de prueba (mock): ninguna lista de precios ni umbral está aprobado
por el dueño (INV-30). Cuando el dueño los apruebe, esta tabla pasa a un snapshot versionado.

Los costos de Tecnocare (03) son confidenciales: nunca deben salir en una propuesta a la clínica.
"""

from types import MappingProxyType

from pydantic import BaseModel, ConfigDict

DATA_STATUS = "mock"

# 04 · P-01 y P-03
EXCHANGE_RATE_PEN_PER_USD = 3.75
EVALUATION_HORIZON_MONTHS = 24

# 06 · umbrales
CLINIC_MAX_RECOVERY_MONTHS = 12  # U-01
TECNOCARE_MIN_MARGIN = 0.25  # U-02
MIN_INCLUDED_TRAINING_SESSIONS = 1  # U-03
MAX_INSTALLMENTS = 6  # U-04
MIN_WARRANTY_MONTHS = 12  # U-05


class Product(BaseModel):
    """Un equipo: precios de venta (02), costos internos (03) y capacitación requerida (01)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    product_id: str
    name: str
    list_price_usd: float  # 02 · precio de lista del equipo
    installation_price_usd: float  # 02 · instalación: precio de venta
    training_price_per_session_usd: float  # 02 · capacitación por sesión adicional
    consumable_per_session_usd: float  # 03 · insumo por sesión
    acquisition_cost_usd: float  # 03 · costo de adquisición
    installation_cost_usd: float  # 03 · costo de instalación
    training_cost_per_session_usd: float  # 03 · costo de capacitación por sesión
    required_training_sessions: int  # 01 · capacitación requerida por venta
    warranty_months: int  # 01 · garantía


PRODUCTS: MappingProxyType[str, Product] = MappingProxyType(
    {
        product.product_id: product
        for product in (
            Product(
                product_id="ozonette",
                name="Ozonette",
                list_price_usd=6500,
                installation_price_usd=400,
                training_price_per_session_usd=150,
                consumable_per_session_usd=15,
                acquisition_cost_usd=4200,
                installation_cost_usd=250,
                training_cost_per_session_usd=60,
                required_training_sessions=2,
                warranty_months=12,
            ),
            Product(
                product_id="ozonette_dent",
                name="Ozonette Dent",
                list_price_usd=6800,
                installation_price_usd=400,
                training_price_per_session_usd=150,
                consumable_per_session_usd=15,
                acquisition_cost_usd=4400,
                installation_cost_usd=250,
                training_cost_per_session_usd=60,
                required_training_sessions=2,
                warranty_months=12,
            ),
            Product(
                product_id="ozonette_woman_care",
                name="Ozonette Woman Care",
                list_price_usd=6800,
                installation_price_usd=400,
                training_price_per_session_usd=150,
                consumable_per_session_usd=15,
                acquisition_cost_usd=4400,
                installation_cost_usd=250,
                training_cost_per_session_usd=60,
                required_training_sessions=2,
                warranty_months=12,
            ),
            Product(
                product_id="ozonette_vet",
                name="Ozonette Vet",
                list_price_usd=6200,
                installation_price_usd=400,
                training_price_per_session_usd=150,
                consumable_per_session_usd=12,
                acquisition_cost_usd=4000,
                installation_cost_usd=250,
                training_cost_per_session_usd=60,
                required_training_sessions=2,
                warranty_months=12,
            ),
            Product(
                product_id="ozonobaric_p",
                name="Ozonobaric P",
                list_price_usd=7000,
                installation_price_usd=400,
                training_price_per_session_usd=150,
                consumable_per_session_usd=18,
                acquisition_cost_usd=4500,
                installation_cost_usd=250,
                training_cost_per_session_usd=60,
                required_training_sessions=2,
                warranty_months=12,
            ),
            Product(
                product_id="om_302_d",
                name="OM-302 D",
                list_price_usd=7500,
                installation_price_usd=450,
                training_price_per_session_usd=180,
                consumable_per_session_usd=20,
                acquisition_cost_usd=4900,
                installation_cost_usd=300,
                training_cost_per_session_usd=70,
                required_training_sessions=2,
                warranty_months=24,
            ),
        )
    }
)
