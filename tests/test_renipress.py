"""S2: RENIPRESS is the prospect base and is filtered by target profile.

Business rule (docs/Document from Diego.markdown, section 4): only private,
active IPRESS of category I-3 / I-4 are in scope.
"""

from pathlib import Path

import pytest

from scraper.renipress import UnexpectedColumns, filter_target_profile, read_renipress

FIXTURES = Path(__file__).parent / "fixtures"
MINI = FIXTURES / "renipress_mini.csv"


def test_read_renipress_handles_bom_and_semicolon_separator():
    rows = list(read_renipress(MINI))
    assert len(rows) == 7
    first = rows[0]
    assert first.ipress_code == "00024663"
    assert first.name == "CLINICA VERTEBRAL"
    assert first.ubigeo == "150131"
    assert first.department == "LIMA"
    assert first.phone == "984337558"


def test_read_renipress_keeps_semicolons_inside_quoted_fields():
    """270 rows of the published registry quote a phone like `3515111; 3515116`.

    Reading the file without `quote_char` makes those rows overflow the header
    and shifts every following column, so the phone and the district both serve
    as canaries here.
    """
    quoted = next(i for i in read_renipress(MINI) if i.ipress_code == "00000222")
    assert quoted.phone == "3515111; 3515116"
    assert quoted.district == "ATE"
    assert quoted.ubigeo == "150103"


def test_filter_target_profile_keeps_only_private_active_i3_i4():
    codes = [i.ipress_code for i in filter_target_profile(read_renipress(MINI))]
    assert codes == ["00024663", "00011122", "00077777"]


def test_filter_target_profile_drops_public_downgraded_and_smaller_than_i3():
    codes = {i.ipress_code for i in filter_target_profile(read_renipress(MINI))}
    # 00000161 -> GOBIERNO REGIONAL (public sector)
    # 00099999 -> category I-1
    # 00055555 -> ESTADO = BAJA DEFINITIVA
    assert codes.isdisjoint({"00000161", "00099999", "00055555"})


def test_read_renipress_fails_loudly_when_the_source_schema_changes(tmp_path):
    """A silent column rename would corrupt every prospect downstream."""
    broken = tmp_path / "renipress_broken.csv"
    broken.write_text("INSTITUCION;COD_IPRESS;NOMBRE\nPRIVADO;0001;X\n", encoding="utf-8")
    with pytest.raises(UnexpectedColumns, match="CATEGORIA"):
        list(read_renipress(broken))


# --- coordenadas ------------------------------------------------------------
#
# RENIPRESS las publica en columnas llamadas NORTE y ESTE, pero medido sobre los 2.459
# objetivos los valores son **latitud y longitud**: NORTE va de -18,07 a 0 y ESTE de
# -81,28 a 0, y no hay un solo valor en el rango de UTM. Fiarse del nombre habría puesto
# cada clínica en el lugar equivocado.


def test_read_renipress_reads_the_published_coordinates():
    vertebral = next(i for i in read_renipress(MINI) if i.ipress_code == "00024663")
    assert vertebral.latitude == pytest.approx(-12.0977)
    assert vertebral.longitude == pytest.approx(-77.0365)


def test_read_renipress_leaves_an_unpublished_coordinate_unknown():
    sin = next(i for i in read_renipress(MINI) if i.ipress_code == "00077777")
    assert sin.latitude is None
    assert sin.longitude is None


def test_read_renipress_rejects_the_zero_sentinel_the_source_publishes():
    """Dos de los 2.093 objetivos traen `-6e-08` y `-7.8e-07`: el punto (0,0), en el
    océano frente a África. Es un dato faltante disfrazado de coordenada."""
    sentinela = next(i for i in read_renipress(MINI) if i.ipress_code == "00000222")
    assert sentinela.latitude is None
    assert sentinela.longitude is None


def test_filter_target_profile_keeps_the_coordinates():
    objetivo = next(i for i in filter_target_profile(read_renipress(MINI)) if i.ipress_code == "00011122")
    assert objetivo.latitude == pytest.approx(-16.3947)
    assert objetivo.longitude == pytest.approx(-71.5456)
