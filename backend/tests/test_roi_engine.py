import pytest

from app.roi_engine import Offer, Zone, UnknownProductError, evaluate, validate_offer

# Los tres escenarios de la tabla de la sección 6 del procedimiento v0.3 (y hoja 07).
INITIAL = Offer(
    product_id="ozonette",
    session_price_pen=120,
    sessions_per_month=40,
    equipment_price_usd=6500,
    installation_included=False,
    training_included_sessions=2,
    installments=1,
    warranty_months=12,
)
COUNTER = Offer(
    product_id="ozonette",
    session_price_pen=110,
    sessions_per_month=40,
    equipment_price_usd=6100,
    installation_included=True,
    training_included_sessions=2,
    installments=1,
    warranty_months=12,
)
NO_DEAL = Offer(
    product_id="ozonette",
    session_price_pen=90,
    sessions_per_month=30,
    equipment_price_usd=6500,
    installation_included=False,
    training_included_sessions=2,
    installments=1,
    warranty_months=12,
)


def test_initial_offer_matches_procedure_table():
    result = evaluate(INITIAL)

    assert result.investment_usd == pytest.approx(6900)
    assert result.monthly_flow_usd == pytest.approx(680)
    assert result.recovery_months == pytest.approx(10.1, abs=0.05)
    assert result.return_24m == pytest.approx(1.365, abs=0.001)
    assert result.margin == pytest.approx(0.338, abs=0.001)
    assert result.zone is Zone.WIN_WIN
    assert result.is_win_win


def test_counter_offer_matches_procedure_table():
    result = evaluate(COUNTER)

    assert result.investment_usd == pytest.approx(6100)
    assert result.monthly_flow_usd == pytest.approx(573.33, abs=0.01)
    assert result.recovery_months == pytest.approx(10.6, abs=0.05)
    assert result.return_24m == pytest.approx(1.256, abs=0.001)
    assert result.margin == pytest.approx(0.251, abs=0.001)
    assert result.zone is Zone.WIN_WIN


def test_no_deal_scenario_is_tecnocare_only_and_negative_return():
    result = evaluate(NO_DEAL)

    assert result.investment_usd == pytest.approx(6900)
    assert result.monthly_flow_usd == pytest.approx(270)
    assert result.recovery_months == pytest.approx(25.6, abs=0.05)
    assert result.return_24m == pytest.approx(-0.061, abs=0.001)
    assert result.clinic_viable is False
    assert result.tecnocare_viable is True
    assert result.zone is Zone.TECNOCARE_ONLY


def test_minimum_equipment_price_matches_procedure_example():
    # Procedimiento §4: para Ozonette, con los valores de prueba, el precio mínimo es 5,693 USD.
    assert evaluate(INITIAL).min_equipment_price_usd == pytest.approx(5693, abs=1)


def test_clinic_only_zone_when_tecnocare_falls_below_floor():
    offer = Offer(
        product_id="ozonette",
        session_price_pen=120,
        sessions_per_month=40,
        equipment_price_usd=6000,
        installation_included=True,
        training_included_sessions=2,
        installments=1,
        warranty_months=12,
    )
    result = evaluate(offer)

    assert result.clinic_viable is True
    assert result.tecnocare_viable is False
    assert result.zone is Zone.CLINIC_ONLY


def test_none_zone_when_nobody_meets_thresholds():
    offer = Offer(
        product_id="ozonette",
        session_price_pen=60,
        sessions_per_month=30,
        equipment_price_usd=4500,
        installation_included=True,
        training_included_sessions=2,
        installments=1,
        warranty_months=12,
    )
    assert evaluate(offer).zone is Zone.NONE


def test_installation_is_a_cost_for_tecnocare_even_when_not_charged():
    # Si la instalación va incluida, la clínica no la paga pero Tecnocare sí la asume.
    included = evaluate(COUNTER)
    assert included.installation_charged_usd == 0
    assert included.margin == pytest.approx(0.251, abs=0.001)


def test_validation_rejects_price_above_list():
    offer = Offer(**{**INITIAL.__dict__, "equipment_price_usd": 7000})
    assert any("supera la lista" in v for v in validate_offer(offer))


def test_validation_enforces_training_installments_and_warranty_thresholds():
    offer = Offer(
        **{**INITIAL.__dict__, "training_included_sessions": 0, "installments": 7, "warranty_months": 6}
    )
    violations = validate_offer(offer)

    assert any("capacitación incluida mínima" in v for v in violations)
    assert any("cuotas" in v for v in violations)
    assert any("garantía mínima" in v for v in violations)


def test_valid_offer_has_no_violations():
    assert validate_offer(INITIAL) == []
    assert evaluate(INITIAL).violations == ()


def test_unknown_product_raises():
    with pytest.raises(UnknownProductError):
        evaluate(Offer(**{**INITIAL.__dict__, "product_id": "no_existe"}))
