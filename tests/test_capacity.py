"""S3: the Consulta A table provides installed capacity per IPRESS.

Business rule: scoring needs to know how many doctors and consulting rooms a
clinic has. The last published month is used, not a historical average.
"""

from pathlib import Path

from scraper.capacity import IpressCapacity, consolidate_capacity

FIXTURES = Path(__file__).parent / "fixtures"
MINI = FIXTURES / "consulta_a_mini.csv"
CODES = {"00024663", "00011122"}


def test_consolidate_capacity_uses_the_last_published_month_per_ipress():
    capacity = consolidate_capacity(MINI, CODES)
    vertebral = capacity["00024663"]
    assert vertebral.period == "2026-02"
    assert vertebral.doctors_total == 6
    assert vertebral.consulting_rooms == 9
    assert vertebral.nurses == 7


def test_consolidate_capacity_respects_the_only_available_month():
    dolor = consolidate_capacity(MINI, CODES)["00011122"]
    assert dolor.period == "2026-01"
    assert dolor.doctors_total == 12
    assert dolor.beds == 4


def test_consolidate_capacity_ignores_ipress_outside_the_target_profile():
    assert set(consolidate_capacity(MINI, CODES)) == CODES


def test_consolidate_capacity_never_invents_data_for_a_missing_ipress():
    missing = consolidate_capacity(MINI, {"00024663", "00000000"})["00000000"]
    assert missing == IpressCapacity(ipress_code="00000000")
    assert missing.doctors_total == 0
    assert missing.period is None
    assert missing.legal_name is None
