"""Attribution of ozone evidence found on the web to the right IPRESS.

The 3-clinic validation sample produced **0 reliable answers** and all three
failures were attribution failures, not detection failures:

- a same-named clinic in another department (San Felipe, Chosica vs Huancayo);
- a *different* clinic in the same district that does offer ozone (the San Borja
  ozone unit vs CEFRA, also in San Borja);
- oxygen therapy and a hyperbaric chamber one search away from ozone therapy.

So the rule under test is: only a comparable street address attributes a page to
an IPRESS, and anything that cannot be attributed is `unknown`, never a negative.

The addresses below are the real ones published in RENIPRESS.
"""

from scraper.enrichment import (
    Candidate,
    clinic_owns_result,
    find_ozone_mentions,
    phone_numbers,
    resolve_ozone_evidence,
)
from scraper.renipress import Ipress

# The real page of a San Borja clinic that does offer ozone.
OZONE_PAGE_TEXT = (
    "Unidad de Ozono - Centro Medico San Borja\n"
    "Ozonoterapia Método terapéutico complementario efectivo, que se usa con fines terapéuticos.\n"
    "Av. Aviación 2612, San Borja, Lima\n"
)

# The kind of text that sits one search away and is NOT ozone therapy.
OXYGEN_PAGE_TEXT = (
    "PERIMEDIC es una clínica con médicos especialistas en medicina hiperbárica, "
    "oxigenoterapia, medicina interna y cirugía plástica.\n"
    "Contamos con cámara hiperbárica y administración de oxígeno medicinal.\n"
)


def ipress(**overrides) -> Ipress:
    """An IPRESS built from addresses published in RENIPRESS.

    Both IPRESS records below carry the real district and street published in the
    registry for the clinics of the validation sample, so the attribution cases are
    reproducible. The addresses inside each candidate are illustrative free text
    standing for whatever a search result declares about itself.
    """
    base = dict(
        ipress_code="00000001",
        name="CLINICA X",
        institution="PRIVADO",
        classification="POLICLINICOS",
        establishment_type="ESTABLECIMIENTO DE SALUD SIN INTERNAMIENTO",
        department="LIMA",
        province="LIMA",
        district="SAN BORJA",
        ubigeo="150130",
        address="AV. GUARDIA CIVIL 715-721 URB CORPAC",
        category="I-3",
        phone="999888777",
        schedule="8:00 - 20:00",
        status="ACTIVO",
    )
    base.update(overrides)
    return Ipress(**base)


CEFRA = ipress()  # AV. GUARDIA CIVIL 715-721 URB CORPAC / SAN BORJA / LIMA
SAN_FELIPE = ipress(
    ipress_code="00000002",
    name="CENTRO MEDICO ESPECIALIZADO SAN FELIPE",
    district="LURIGANCHO",
    address="JR. PUNO 182- CHOSICA",
)


def test_find_ozone_mentions_returns_the_citing_sentence():
    mentions = find_ozone_mentions(OZONE_PAGE_TEXT)
    assert mentions
    assert any("Ozonoterapia" in mention.text for mention in mentions)
    assert any("ozonoterapia" in mention.markers for mention in mentions)


def test_find_ozone_mentions_matches_accented_and_uppercase_text():
    mentions = find_ozone_mentions("APLICACIÓN DE OZONO MEDICINAL SISTÉMICO")
    assert len(mentions) == 1
    assert mentions[0].markers == ("ozono",)


def test_find_ozone_mentions_ignores_oxygen_therapy_and_hyperbaric_chamber():
    """The cheapest available false positive in this domain."""
    assert find_ozone_mentions(OXYGEN_PAGE_TEXT) == ()


def test_find_ozone_mentions_handles_a_real_sentence_that_mixes_ozone_and_oxygen():
    """Verbatim from a live page (centromedicosanborja.com, Unidad de Ozono).

    The sentence brings up oxygen twice in the same breath, which is precisely why
    the marker has to be `ozono` and never `oxigeno`.
    """
    text = (
        "El ozono es un gas formado por una mezcla de ozono y oxigeno que se obtiene a "
        "partir del oxigeno medicinal mediante un generador."
    )
    mentions = find_ozone_mentions(text)
    assert len(mentions) == 1
    assert "ozono" in mentions[0].markers


def test_clinic_owns_result_rejects_a_same_named_clinic_in_another_department():
    candidate = Candidate(
        url="https://www.beneficenciadehuancayo.org/cmsanfelipe/",
        address="Mantaro, Huancayo",
        district="HUANCAYO",
        department="JUNIN",
    )
    evidence = resolve_ozone_evidence(candidate, SAN_FELIPE)
    assert evidence.checked is False
    assert evidence.performs is False


def test_clinic_owns_result_rejects_a_neighbouring_clinic_in_the_same_district():
    """Same district and department, different street: the ozone unit vs CEFRA.

    This is the case that proves a district match cannot attribute a page, because
    the whole neighbourhood shares it.
    """
    candidate = Candidate(
        url="https://centromedicosanborja.com/servicios/unidad-de-ozono/",
        text=OZONE_PAGE_TEXT,
        address="Av. Aviación 2612",
        district="SAN BORJA",
        department="LIMA",
    )
    evidence = resolve_ozone_evidence(candidate, CEFRA)
    assert evidence.checked is False
    assert evidence.performs is False


def test_clinic_owns_result_accepts_the_published_street():
    candidate = Candidate(
        url="https://www.cefraperu.com/inicio",
        text="Conoce nuestra sede en Av. Guardia Civil 715, San Borja.",
        address="Av. Guardia Civil 715 - 721 Urb. Corpac",
        district="SAN BORJA",
        department="LIMA",
    )
    evidence = resolve_ozone_evidence(candidate, CEFRA)
    assert evidence.checked is True
    assert evidence.performs is False  # atribuida, pero esa pagina no menciona ozono


def test_clinic_owns_result_fails_closed_without_a_comparable_address():
    """No address means `unknown`, which is not the same as `no`."""
    candidate = Candidate(url="https://example.test/clinica", text=OZONE_PAGE_TEXT)
    evidence = resolve_ozone_evidence(candidate, CEFRA)
    assert evidence.checked is False
    assert evidence.performs is False
    assert "example.test" in evidence.source_url


def test_owned_page_that_mentions_ozone_resolves_to_performs():
    candidate = Candidate(
        url="https://www.cefraperu.com/servicios/ozono",
        text=OZONE_PAGE_TEXT,
        address="Avenida Guardia Civil 715, San Borja",
        district="San Borja",
        department="Lima",
    )
    evidence = resolve_ozone_evidence(candidate, CEFRA)
    assert evidence.checked is True
    assert evidence.performs is True
    assert evidence.mentions[0].text


# --- phone as the stronger attribution signal -------------------------------
#
# A street is shared by the whole district; a phone number is not. RENIPRESS
# publishes a phone for 2,457 of the 2,459 targets, so the phone is the signal the
# search step can actually use when the result declares no address at all.


def test_phone_numbers_reads_a_published_field_with_two_numbers():
    """RENIPRESS publishes some switchboards as `3515111; 3515116`."""
    assert phone_numbers("3515111; 3515116") == frozenset({"3515111", "3515116"})


def test_phone_numbers_ignores_fragments_too_short_to_identify_a_clinic():
    assert phone_numbers("Av. Guardia Civil 715, piso 3, ano 2024") == frozenset()
    assert phone_numbers("") == frozenset()


def test_phone_numbers_does_not_merge_a_phone_with_a_following_street_number():
    """Measured on a real page: `999 888 777 Av. Guardia Civil 715` used to merge the
    phone and the street number into one 12-digit run, so a real phone match was lost.
    """
    assert phone_numbers("999 888 777 Av. Guardia Civil 715") == frozenset({"999888777"})
    assert phone_numbers("Reservas 999 888 777, Av. Uno 715") == frozenset({"999888777"})


def test_phone_numbers_ignores_a_run_of_years():
    assert phone_numbers("Sedes 2024 2025 2026") == frozenset()


def test_phone_numbers_drops_the_country_code():
    assert phone_numbers("+51 999 888 777") == frozenset({"999888777"})
    assert phone_numbers("054-123456") == frozenset({"054123456"})


def test_clinic_owns_result_accepts_the_published_phone_number():
    candidate = Candidate(
        url="https://www.cefraperu.com/contacto",
        text="Reservas al 999 888 777 o escribinos. Atendemos en San Borja.",
    )
    assert clinic_owns_result(candidate, CEFRA) is True


def test_clinic_owns_result_accepts_an_international_prefix_on_the_phone():
    candidate = Candidate(
        url="https://www.cefraperu.com/", text="Llamanos al +51 999 888 777"
    )
    assert clinic_owns_result(candidate, CEFRA) is True


def test_clinic_owns_result_rejects_a_page_with_another_clinics_phone():
    candidate = Candidate(
        url="https://centromedicosanborja.com/",
        text="Central telefonica: 01 224 9090",
        district="SAN BORJA",
        department="LIMA",
    )
    assert clinic_owns_result(candidate, CEFRA) is False


def test_clinic_owns_result_needs_two_street_name_tokens_not_a_number_and_a_town():
    """A street number and the shared town name are not an identification.

    Measured: the Waze listing of San Felipe matched on `182` (its street number) and
    `chosica` (the town every clinic there shares). One alphabetic token is not a
    street name, so the match is refused and the clinic stays unknown.
    """
    candidate = Candidate(
        url="https://www.waze.com/es-419/live-map/directions/centro-medico-san-felipe",
        text="Prolongacion 28 de Julio 182, Lurigancho Chosica",
    )
    assert clinic_owns_result(candidate, SAN_FELIPE) is False


def test_clinic_owns_result_still_accepts_two_street_name_tokens():
    """The refinement must not break a real street match."""
    candidate = Candidate(
        url="https://www.cefraperu.com/contacto",
        text="Visitanos en Avenida Guardia Civil 715, San Borja.",
    )
    assert clinic_owns_result(candidate, CEFRA) is True
