"""S5: the commercial priority score must be deterministic and traceable.

Every component is computed only from verifiable source columns: establishment
level, medical capacity, market and reachability. No invented values.
"""

from scraper.renipress import Ipress
from scraper.scoring import HIGH_THRESHOLD, score_prospect


def ipress(**overrides) -> Ipress:
    base = dict(
        ipress_code="00000001",
        name="CLINICA X",
        institution="PRIVADO",
        classification="POLICLINICOS",
        establishment_type="ESTABLECIMIENTO DE SALUD SIN INTERNAMIENTO",
        department="LIMA",
        province="LIMA",
        district="LIMA",
        ubigeo="150101",
        address="AV. UNO 100",
        category="I-3",
        phone="999888777",
        schedule="8:00 - 20:00",
        status="ACTIVO",
    )
    base.update(overrides)
    return Ipress(**base)


def test_ideal_target_in_lima_scores_high_priority():
    score = score_prospect(
        ipress(category="I-4", classification="CENTROS MEDICOS ESPECIALIZADOS"),
        doctors_total=12,
        performs_ozone_therapy=False,
    )
    assert score.level == "high"
    assert score.total >= 70


def test_without_phone_or_address_priority_drops_out_of_high():
    score = score_prospect(ipress(phone="", address=""), doctors_total=6, performs_ozone_therapy=False)
    assert score.total == 60
    assert score.level == "medium"


def test_no_component_exceeds_its_cap():
    score = score_prospect(
        ipress(category="I-4", classification="CENTROS MEDICOS ESPECIALIZADOS"),
        doctors_total=500,
        performs_ozone_therapy=False,
    )
    caps = {
        "establishment": 25,
        "capacity": 30,
        "market": 25,
        "reachability": 20,
        "penalty": 0,
    }
    assert score.total == 100
    for component, cap in caps.items():
        assert score.components[component] <= cap


def test_confirmed_ozone_therapy_penalizes_and_never_stays_high():
    entity = ipress(category="I-4", classification="CENTROS MEDICOS ESPECIALIZADOS")
    without = score_prospect(entity, doctors_total=12, performs_ozone_therapy=False)
    with_ozone = score_prospect(entity, doctors_total=12, performs_ozone_therapy=True)
    assert with_ozone.total < without.total
    assert with_ozone.components["penalty"] == -40
    assert with_ozone.level != "high"


def test_score_is_deterministic_for_the_same_input():
    entity = ipress()
    assert score_prospect(entity, doctors_total=4, performs_ozone_therapy=False) == score_prospect(
        entity, doctors_total=4, performs_ozone_therapy=False
    )


def test_medical_capacity_is_banded():
    for doctors, expected in {0: 0, 3: 10, 9: 20, 10: 30}.items():
        score = score_prospect(ipress(), doctors_total=doctors, performs_ozone_therapy=False)
        assert score.components["capacity"] == expected


def test_measured_capacity_keeps_the_absolute_scale():
    """Regression guard: with capacity on record the score is unchanged."""
    score = score_prospect(ipress(), doctors_total=6, performs_ozone_therapy=False)
    assert score.measured_weight == 100
    assert score.total == 80
    # Sin redistribucion el total es exactamente la suma de los componentes.
    assert score.total == sum(score.components.values())


def test_missing_capacity_redistributes_its_weight_instead_of_penalizing():
    """Consulta A covers 10 % of the targets, so an unknown headcount must not
    be scored as a zero headcount: that single conflation cost every uncovered
    clinic 30 points.

    The redistributed total is comparable, but it is not evidence: `level`
    handles that separately (see `test_high_requires_full_evidence`).
    """
    entity = ipress(category="I-4", classification="CENTROS MEDICOS ESPECIALIZADOS")
    score = score_prospect(entity, doctors_total=None, performs_ozone_therapy=False)
    assert score.components["capacity"] == 0  # nothing is invented for the missing datum
    assert score.measured_weight == 70  # 25 establecimiento + 25 mercado + 20 contacto
    assert score.total == 100


def test_high_requires_full_evidence():
    """A perfect score over three quarters of the evidence is a lead, not a
    verified one: 1.307 of the 1.429 `high` in the real run rested on the
    absence of a capacity record rather than on evidence.
    """
    entity = ipress(category="I-4", classification="CENTROS MEDICOS ESPECIALIZADOS")
    unproven = score_prospect(entity, doctors_total=None, performs_ozone_therapy=False)
    assert unproven.total >= HIGH_THRESHOLD
    assert unproven.measured_weight == 70
    assert unproven.level == "medium"


def test_full_evidence_still_reaches_high():
    entity = ipress(category="I-4", classification="CENTROS MEDICOS ESPECIALIZADOS")
    proven = score_prospect(entity, doctors_total=10, performs_ozone_therapy=False)
    assert proven.measured_weight == 100
    assert proven.total == 100
    assert proven.level == "high"


def test_missing_capacity_rescales_over_the_measured_weight():
    score = score_prospect(ipress(), doctors_total=None, performs_ozone_therapy=False)
    # I-3 (15) + Lima (25) + telefono y direccion (20) = 60 sobre 70 medidos
    assert score.measured_weight == 70
    assert score.total == round(60 * 100 / 70) == 86


def test_missing_capacity_still_penalizes_confirmed_ozone_therapy():
    entity = ipress(category="I-4", classification="CENTROS MEDICOS ESPECIALIZADOS")
    with_ozone = score_prospect(entity, doctors_total=None, performs_ozone_therapy=True)
    assert with_ozone.components["penalty"] == -40
    assert with_ozone.total == 60
    assert with_ozone.level != "high"
