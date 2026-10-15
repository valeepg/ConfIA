"""Deterministic commercial priority score (RF-05).

Every point is traceable to a source column:

| component       | weight | source                                                |
|-----------------|--------|-------------------------------------------------------|
| establishment   |     25 | CATEGORIA (I-3/I-4) + CLASIFICACION (specialised)      |
| capacity        |     30 | Consulta A, CA_MEDICOS_TOTAL, banded                   |
| market          |     25 | DEPARTAMENTO (Lima first, then the expansion phase)     |
| reachability    |     20 | TELEFONO + DIRECCION                                   |
| penalty         |    -40 | Consulta G: ozone therapy already offered                |

Missing evidence is redistributed, never scored as a zero
--------------------------------------------------------
Consulta A is a monthly activity report, not a roster: it covers 248 of the 2.459
target IPRESS. Scoring an unknown headcount as a zero headcount cost every
uncovered clinic 30 points and pushed 90 % of the list out of `high`, so the
weight of a component without evidence is excluded and the remaining evidence is
rescaled to the full 0-100 range.

`measured_weight` reports how much of the scale had evidence (70 or 100), so a
100 over three quarters of the evidence is distinguishable from a real 100. The
absolute scale still applies whenever capacity is on record, which keeps scores
comparable inside each group and keeps old results valid.

`high` additionally requires full evidence. A redistributed 100 is a lead, not a
verified one: in the measured run 1.307 of the 1.429 `high` prospects were `high`
on the absence of a capacity record rather than on evidence. Everything below that
keeps its redistributed rank, so an uncovered clinic is still ordered fairly
against its peers and is promoted to `high` the moment capacity is on record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .renipress import Ipress

LEVEL_HIGH = "high"
LEVEL_MEDIUM = "medium"
LEVEL_LOW = "low"

HIGH_THRESHOLD = 70
MEDIUM_THRESHOLD = 45
OZONE_PENALTY = -40

WEIGHT_ESTABLISHMENT = 25
WEIGHT_CAPACITY = 30
WEIGHT_MARKET = 25
WEIGHT_REACHABILITY = 20
TOTAL_WEIGHT = WEIGHT_ESTABLISHMENT + WEIGHT_CAPACITY + WEIGHT_MARKET + WEIGHT_REACHABILITY

# Components that always carry evidence, whatever the sources publish.
WEIGHT_WITHOUT_CAPACITY = WEIGHT_ESTABLISHMENT + WEIGHT_MARKET + WEIGHT_REACHABILITY

SPECIALIZED_CLASSIFICATIONS = (
    "CENTROS MEDICOS ESPECIALIZADOS",
    "CENTROS DE SALUD CON CAMAS DE INTERNAMIENTO",
)
EXPANSION_DEPARTMENTS = ("AREQUIPA", "LA LIBERTAD", "LAMBAYEQUE", "CUSCO")

CAP_ESTABLISHMENT = WEIGHT_ESTABLISHMENT
CAP_CAPACITY = WEIGHT_CAPACITY
CAP_MARKET = WEIGHT_MARKET
CAP_REACHABILITY = WEIGHT_REACHABILITY

_MINIMUM_PHONE_DIGITS = 6


@dataclass(frozen=True)
class Score:
    total: int
    level: str
    components: dict[str, int]
    # Sum of the weights that had evidence. 100 = full evidence, 70 = capacity unknown.
    measured_weight: int = TOTAL_WEIGHT


def is_valid_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone or "")
    return len(digits) >= _MINIMUM_PHONE_DIGITS


def _establishment(ipress: Ipress) -> int:
    base = CAP_ESTABLISHMENT if ipress.category == "I-4" else 15
    bonus = 5 if any(marker in ipress.classification for marker in SPECIALIZED_CLASSIFICATIONS) else 0
    return min(base + bonus, CAP_ESTABLISHMENT)


def _capacity(doctors_total: int | None) -> int:
    """Band the headcount. `None` means the source has no record, not zero doctors."""
    if doctors_total is None:
        return 0
    if doctors_total >= 10:
        return 30
    if doctors_total >= 4:
        return 20
    if doctors_total >= 1:
        return 10
    return 0


def _market(department: str) -> int:
    if department == "LIMA":
        return 25
    if department in EXPANSION_DEPARTMENTS:
        return 15
    return 8


def _reachability(ipress: Ipress) -> int:
    points = 15 if is_valid_phone(ipress.phone) else 0
    if ipress.address.strip():
        points += 5
    return min(points, CAP_REACHABILITY)


def _level(total: int, *, full_evidence: bool) -> str:
    if total >= HIGH_THRESHOLD:
        # A high score over incomplete evidence stays a lead, not a verified one.
        return LEVEL_HIGH if full_evidence else LEVEL_MEDIUM
    if total >= MEDIUM_THRESHOLD:
        return LEVEL_MEDIUM
    return LEVEL_LOW


def score_prospect(
    ipress: Ipress,
    *,
    doctors_total: int | None,
    performs_ozone_therapy: bool,
) -> Score:
    """Score one IPRESS. Pass `doctors_total=None` when capacity is unknown."""
    components = {
        "establishment": _establishment(ipress),
        "capacity": _capacity(doctors_total),
        "market": _market(ipress.department),
        "reachability": _reachability(ipress),
        "penalty": OZONE_PENALTY if performs_ozone_therapy else 0,
    }

    measured = {
        "establishment": WEIGHT_ESTABLISHMENT,
        "capacity": 0 if doctors_total is None else WEIGHT_CAPACITY,
        "market": WEIGHT_MARKET,
        "reachability": WEIGHT_REACHABILITY,
    }
    # The three always-measured components keep this above zero by construction.
    measured_weight = sum(measured.values())
    earned = sum(components[name] for name in measured)

    total = max(round(earned * TOTAL_WEIGHT / measured_weight) + components["penalty"], 0)
    level = _level(total, full_evidence=measured_weight == TOTAL_WEIGHT)
    if performs_ozone_therapy and level == LEVEL_HIGH:
        level = LEVEL_MEDIUM
    return Score(
        total=total,
        level=level,
        components=components,
        measured_weight=measured_weight,
    )
