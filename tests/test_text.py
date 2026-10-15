"""Accent and case folding, shared by the two modules that match Spanish text.

The published sources and the clinics' web pages write the same terms in every
combination of case and accents, so matching happens on a folded copy. This is the
single place that decides what "folded" means: if it drifts, ozone detection and
procedure detection would disagree about the same word.
"""

from scraper.text import fold_text


def test_fold_text_removes_accents_and_case():
    assert fold_text("OZONOTERAPIA SISTÉMICA") == "ozonoterapia sistemica"
    assert fold_text("Aplicación de ozono") == "aplicacion de ozono"
    assert fold_text("Terapéutico") == "terapeutico"


def test_fold_text_keeps_oxygen_and_ozone_apart():
    """`oxigenoterapia` and `camara hiperbarica` are not ozone therapy.

    The validation sample surfaced exactly this text one search away from a
    clinic that does offer ozone, so the fold must not blur them together.
    """
    assert "ozono" not in fold_text("oxigenoterapia")
    assert "ozono" not in fold_text("cámara hiperbárica")
    assert "ozono" not in fold_text("oxígeno medicinal")
    assert "ozono" in fold_text("OZONO MEDICINAL")


def test_fold_text_handles_empty_input():
    assert fold_text("") == ""
    assert fold_text(None) == ""
