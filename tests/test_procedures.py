"""S4: the Consulta G table tells whether the IPRESS already performs ozone therapy.

Business rule: the commercial target is a pain/trauma clinic that does NOT
offer ozone therapy yet (docs/Document from Diego.markdown, section 4).
"""

from pathlib import Path

from scraper.procedures import detect_ozone_therapy, is_ozone_procedure

FIXTURES = Path(__file__).parent / "fixtures"
MINI = FIXTURES / "consulta_g_mini.csv"
NO_OZONE_MINI = FIXTURES / "consulta_g_sin_ozono_mini.csv"
CODES = {"00024663", "00011122"}


def test_is_ozone_procedure_matches_uppercase_and_word_variants():
    assert is_ozone_procedure("OZONOTERAPIA SISTEMICA") is True
    assert is_ozone_procedure("Aplicacion de ozono medicinal") is True
    assert is_ozone_procedure("Consejeria en higiene de manos") is False


def test_detect_ozone_therapy_decodes_latin1_and_sums_attendances():
    detection = detect_ozone_therapy(MINI, CODES)
    assert detection.signal_available is True
    vertebral = detection.therapy["00024663"]
    assert vertebral.checked is True
    assert vertebral.performs is True
    assert vertebral.total_attendances == 14
    assert vertebral.procedures == ["Aplicación de ozonoterapia sistémica"]


def test_detect_ozone_therapy_reports_false_when_the_ipress_is_present_without_ozone():
    dolor = detect_ozone_therapy(MINI, CODES).therapy["00011122"]
    assert dolor.checked is True
    assert dolor.performs is False
    assert dolor.total_attendances == 0


def test_detect_ozone_therapy_marks_absent_ipress_as_not_checked():
    therapy = detect_ozone_therapy(MINI, CODES | {"00099999"}).therapy["00099999"]
    assert therapy.checked is False
    assert therapy.performs is False


def test_detect_ozone_therapy_reports_the_signal_unavailable_when_the_catalog_has_no_ozone():
    """The published catalog has 7.457 distinct procedures and none is ozone therapy.

    A `performs: false` there would read as "confirmed negative" while the source
    simply cannot express the question, so nothing may be marked as checked.
    """
    detection = detect_ozone_therapy(NO_OZONE_MINI, CODES)
    assert detection.signal_available is False
    assert all(
        not entry.checked and not entry.performs for entry in detection.therapy.values()
    )
    assert set(detection.therapy) == CODES
