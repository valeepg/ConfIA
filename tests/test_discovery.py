"""Discovery against a mocked provider and mocked pages.

Every test here runs offline. The query shape, the browser-like headers and the
robots.txt check are all locked in as tests because each one was measured against
the real web and each one failed at least once before it was right.
"""

import json
from pathlib import Path

import httpx
import pytest

from scraper.contract import Prospect
from scraper.discovery import (
    SERPER_ENDPOINT,
    EnrichmentOutcome,
    apply_enrichment,
    build_query,
    enrich_ipress,
    fetch_page,
    search_clinic,
)
from scraper.enrichment import OzoneMention
from scraper.renipress import Ipress

PAGE_URL = "https://www.cefraperu.com/inicio"
OTHER_URL = "https://otra-clinica.test/servicios"


def ipress(**overrides) -> Ipress:
    """The published data of CEFRA, one of the clinics of the validation sample."""
    base = dict(
        ipress_code="00000001",
        name="CEFRA",
        institution="PRIVADO",
        classification="CENTROS MEDICOS ESPECIALIZADOS",
        establishment_type="ESTABLECIMIENTO DE SALUD SIN INTERNACION",
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


def client_with(routes: dict[str, httpx.Response], requests: list | None = None) -> httpx.Client:
    """An httpx client that answers only the exact URLs given."""

    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        return routes.get(str(request.url), httpx.Response(404))

    return httpx.Client(transport=httpx.MockTransport(handler))


def serper_payload(*links: tuple[str, str]) -> httpx.Response:
    organic = [
        {"title": f"Titulo {index}", "link": link, "snippet": snippet, "position": index + 1}
        for index, (link, snippet) in enumerate(links)
    ]
    return httpx.Response(200, json={"organic": organic, "credits": 1})


def test_build_query_quotes_the_name_and_appends_the_district():
    """The measured shape: quoting the full name is what made Google find the site."""
    assert build_query(ipress()) == '"CEFRA" SAN BORJA'


def test_search_maps_organic_results_and_reports_the_credit_cost():
    routes = {SERPER_ENDPOINT: serper_payload((PAGE_URL, "centro de fertilidad"))}
    with client_with(routes) as client:
        outcome = search_clinic(client, ipress(), api_key="clave")
    assert outcome.query == '"CEFRA" SAN BORJA'
    assert outcome.credits == 1
    assert [candidate.url for candidate in outcome.candidates] == [PAGE_URL]
    assert "centro de fertilidad" in outcome.candidates[0].text


def test_search_sends_the_key_and_the_peruvian_locale():
    requests: list = []
    routes = {SERPER_ENDPOINT: serper_payload((PAGE_URL, "x"))}
    with client_with(routes, requests) as client:
        search_clinic(client, ipress(), api_key="clave-secreta")

    request = requests[0]
    assert request.headers["x-api-key"] == "clave-secreta"
    body = json.loads(request.content)
    assert body["gl"] == "pe"
    assert body["hl"] == "es"
    assert body["num"] > 0
    assert body["q"] == '"CEFRA" SAN BORJA'


def test_fetch_page_sends_browser_like_headers():
    """A plain client got HTTP 406 from Mod_Security on a real clinic site."""
    requests: list = []
    routes = {
        "https://www.cefraperu.com/robots.txt": httpx.Response(404),
        PAGE_URL: httpx.Response(200, content=b"<html><body>hola</body></html>"),
    }
    with client_with(routes, requests) as client:
        fetch_page(client, PAGE_URL)

    page_request = requests[-1]
    assert page_request.headers["user-agent"].startswith("Mozilla/5.0")
    assert "es-PE" in page_request.headers["accept-language"]


def test_fetch_page_reduces_markup_to_text():
    routes = {
        "https://www.cefraperu.com/robots.txt": httpx.Response(404),
        PAGE_URL: httpx.Response(
            200,
            content=(
                b"<html><head><script>var x='ozonoterapia';</script></head>"
                b"<body><p>Reservas: 999 888 777</p></body></html>"
            ),
        ),
    }
    with client_with(routes) as client:
        page = fetch_page(client, PAGE_URL)

    assert "999 888 777" in page.text
    assert "var x" not in page.text  # el script no es texto de la pagina


def test_fetch_page_respects_a_robots_disallow():
    requests: list = []
    routes = {
        "https://www.cefraperu.com/robots.txt": httpx.Response(
            200, content=b"User-agent: *\nDisallow: /privado"
        ),
        "https://www.cefraperu.com/privado": httpx.Response(200, content=b"ozono"),
    }
    with client_with(routes, requests) as client:
        page = fetch_page(client, "https://www.cefraperu.com/privado")

    assert page.allowed is False
    assert page.status == 0
    assert [str(request.url) for request in requests] == ["https://www.cefraperu.com/robots.txt"]


def test_fetch_page_reads_the_page_when_robots_txt_is_missing():
    routes = {
        "https://www.cefraperu.com/robots.txt": httpx.Response(404),
        PAGE_URL: httpx.Response(200, content=b"<html><body>ozono</body></html>"),
    }
    with client_with(routes) as client:
        page = fetch_page(client, PAGE_URL)
    assert page.allowed is True
    assert page.status == 200


def test_fetch_page_reports_a_non_200_status():
    routes = {
        "https://www.cefraperu.com/robots.txt": httpx.Response(404),
        PAGE_URL: httpx.Response(406, content=b"Not Acceptable"),
    }
    with client_with(routes) as client:
        page = fetch_page(client, PAGE_URL)
    assert page.status == 406
    assert page.text == ""


def test_enrich_marks_unknown_when_no_page_can_be_attributed(tmp_path):
    routes = {
        SERPER_ENDPOINT: serper_payload((OTHER_URL, "otra clinica")),
        "https://otra-clinica.test/robots.txt": httpx.Response(404),
        OTHER_URL: httpx.Response(200, content=b"<html><body>Ozonoterapia en otra clinica</body></html>"),
    }
    with client_with(routes) as client:
        outcome = enrich_ipress(
            client, ipress(), api_key="clave", enrichment_dir=tmp_path / "enr"
        )

    assert outcome.checked is False
    assert outcome.performs is False
    assert outcome.attribution is None
    assert outcome.note == "not-attributed"


def test_enrich_reads_ozone_mentions_from_an_attributed_page(tmp_path):
    routes = {
        SERPER_ENDPOINT: serper_payload((PAGE_URL, "centro medico")),
        "https://www.cefraperu.com/robots.txt": httpx.Response(404),
        PAGE_URL: httpx.Response(
            200,
            content=(
                "<html><body>Reservas: 999 888 777. "
                "Nuestra unidad de ozonoterapia aplica ozono medicinal.</body></html>"
            ).encode(),
        ),
    }
    with client_with(routes) as client:
        outcome = enrich_ipress(
            client, ipress(), api_key="clave", enrichment_dir=tmp_path / "enr"
        )

    assert outcome.checked is True
    assert outcome.attribution == "phone"
    assert outcome.performs is True
    assert outcome.source_url == PAGE_URL
    assert any("ozono" in mention.markers for mention in outcome.mentions)


def test_enrich_reports_checked_without_mentions_when_the_page_has_no_ozone(tmp_path):
    """Read and clean is not the same claim as "does not offer ozone therapy".

    The page was attributed and read, so `checked` is true, and no mention was
    found. Inner pages are not followed yet, so this stays a weak negative.
    """
    routes = {
        SERPER_ENDPOINT: serper_payload((PAGE_URL, "centro de fertilidad")),
        "https://www.cefraperu.com/robots.txt": httpx.Response(404),
        PAGE_URL: httpx.Response(
            200,
            content=(
                "<html><body>CEFRA, Av. Guardia Civil 715. Reproduccion asistida.</body></html>"
            ).encode(),
        ),
    }
    with client_with(routes) as client:
        outcome = enrich_ipress(
            client, ipress(), api_key="clave", enrichment_dir=tmp_path / "enr"
        )

    assert outcome.checked is True
    assert outcome.attribution == "address"
    assert outcome.performs is False
    assert outcome.mentions == ()


def test_enrich_reuses_the_cache_without_spending_another_query(tmp_path):
    requests: list = []
    routes = {
        SERPER_ENDPOINT: serper_payload((PAGE_URL, "centro medico")),
        "https://www.cefraperu.com/robots.txt": httpx.Response(404),
        PAGE_URL: httpx.Response(
            200, content="<html><body>999 888 777 ozono</body></html>".encode()
        ),
    }
    enrichment_dir = tmp_path / "enr"
    with client_with(routes, requests) as client:
        first = enrich_ipress(client, ipress(), api_key="clave", enrichment_dir=enrichment_dir)
        spent = len(requests)
        second = enrich_ipress(client, ipress(), api_key="clave", enrichment_dir=enrichment_dir)

    assert first.performs is True
    assert second.performs is True
    assert second.note == "cache"
    assert second.credits == 0
    assert len(requests) == spent  # la segunda corrida no tocó la red
    assert (Path(enrichment_dir) / "00000001.json").exists()


def test_enrich_records_the_provider_credit_cost(tmp_path):
    routes = {
        SERPER_ENDPOINT: serper_payload((PAGE_URL, "x")),
        "https://www.cefraperu.com/robots.txt": httpx.Response(404),
        PAGE_URL: httpx.Response(200, content=b"<html><body>nada</body></html>"),
    }
    with client_with(routes) as client:
        outcome = enrich_ipress(
            client, ipress(), api_key="clave", enrichment_dir=tmp_path / "enr"
        )
    assert outcome.credits == 1
    assert outcome.pages_fetched == 1


def test_enrich_skips_a_page_blocked_by_robots_and_keeps_trying(tmp_path):
    routes = {
        SERPER_ENDPOINT: serper_payload(("https://www.cefraperu.com/privado", "x"), (PAGE_URL, "y")),
        "https://www.cefraperu.com/robots.txt": httpx.Response(
            200, content=b"User-agent: *\nDisallow: /privado"
        ),
        PAGE_URL: httpx.Response(200, content="<html><body>999 888 777 ozono</body></html>".encode()),
    }
    with client_with(routes) as client:
        outcome = enrich_ipress(
            client, ipress(), api_key="clave", enrichment_dir=tmp_path / "enr"
        )
    assert outcome.checked is True
    assert outcome.source_url == PAGE_URL
    assert outcome.pages_fetched == 1


@pytest.mark.parametrize("status", [403, 429, 500])
def test_fetch_page_never_raises_on_an_error_status(status):
    routes = {
        "https://www.cefraperu.com/robots.txt": httpx.Response(404),
        PAGE_URL: httpx.Response(status, content=b"error"),
    }
    with client_with(routes) as client:
        assert fetch_page(client, PAGE_URL).status == status


# --- third-party pages ------------------------------------------------------
#
# Measured: San Felipe, whose registry page is in Lurigancho, was attributed to a
# Waze map listing. Reading a map and reporting "no ozone" would be a confident
# false negative, because a map cannot answer the question at all.

WAZE_URL = "https://www.waze.com/es-419/live-map/directions/centro-medico-san-felipe"

# Every host below was measured in the 50-clinic run: those are the directories the
# search actually attributed pages to. Not one of the 24 attributed pages mentioned
# ozone, and 13 of them were directories, which is why a page on such a host can
# never produce a negative.
NON_CLINICAL_SAMPLES = (
    WAZE_URL,
    "https://directorio.cuidamisalud.com/clinica/centro-medico-x",
    "https://tumedico.pe/centros-de-salud/lima/centro-medico-x",
    "https://www.establecimientosdesalud.info/centro-medico-x",
)


@pytest.mark.parametrize("url", NON_CLINICAL_SAMPLES)
def test_enrich_never_reports_a_negative_from_a_third_party_page(tmp_path, url):
    """No mention on a map or directory listing leaves the clinic unknown."""
    origin = "/".join(url.split("/")[:3])
    routes = {
        SERPER_ENDPOINT: serper_payload((url, "Centro Medico, Chosica")),
        f"{origin}/robots.txt": httpx.Response(404),
        url: httpx.Response(
            200,
            content="<html><body>999 888 777 Av. Guardia Civil 715</body></html>".encode(),
        ),
    }
    with client_with(routes) as client:
        outcome = enrich_ipress(
            client, ipress(), api_key="clave", enrichment_dir=tmp_path / "enr"
        )

    assert outcome.attribution == "phone"  # la pagina si es de la clinica
    assert outcome.checked is False  # pero no puede negar nada
    assert outcome.performs is False
    assert outcome.note == "third-party-host"


def test_enrich_keeps_a_mention_found_on_a_third_party_page(tmp_path):
    """A positive claim is evidence wherever it appears."""
    routes = {
        SERPER_ENDPOINT: serper_payload((WAZE_URL, "Centro Medico San Felipe")),
        "https://www.waze.com/robots.txt": httpx.Response(404),
        WAZE_URL: httpx.Response(
            200,
            content=(
                "<html><body>San Felipe, 999 888 777. Servicio de ozonoterapia.</body></html>"
            ).encode(),
        ),
    }
    with client_with(routes) as client:
        outcome = enrich_ipress(
            client, ipress(), api_key="clave", enrichment_dir=tmp_path / "enr"
        )

    assert outcome.checked is True
    assert outcome.performs is True
    assert outcome.mentions


# --- how an outcome lands in the contract -----------------------------------


def prospect(**overrides) -> Prospect:
    base = dict(
        id="00000001",
        ipress_code="00000001",
        name="CEFRA",
        institution="PRIVADO",
        category="I-3",
        classification="CENTROS MEDICOS ESPECIALIZADOS",
        establishment_type="ESTABLECIMIENTO DE SALUD SIN INTERNAMIENTO",
        location={"department": "LIMA", "province": "LIMA", "district": "SAN BORJA", "ubigeo": "150130"},
        contact={"phone": "999888777", "phone_valid": True, "address": "X", "schedule": ""},
        capacity={},
        ozone_therapy={},
        score={"total": 60, "level": "medium", "components": {}},
    )
    base.update(overrides)
    return Prospect(**base)


def test_apply_enrichment_records_the_claim_with_its_source():
    """A claim the sales team will act on must be auditable by a human."""
    outcome = EnrichmentOutcome(
        ipress_code="00000001",
        checked=True,
        attribution="phone",
        source_url="https://www.cefraperu.com/servicios/ozono",
        mentions=(OzoneMention(text="Unidad de ozonoterapia", markers=("ozonoterapia",)),),
    )
    enriched = apply_enrichment(prospect(), outcome)

    assert enriched.ozone_therapy.checked is True
    assert enriched.ozone_therapy.performs is True
    assert enriched.ozone_therapy.evidence == ["Unidad de ozonoterapia"]
    assert enriched.ozone_therapy.source_url == "https://www.cefraperu.com/servicios/ozono"
    assert enriched.ozone_therapy.attribution == "phone"
    assert "already-offers-ozone-therapy" in enriched.tags
    assert "web-enriched" in enriched.tags


def test_apply_enrichment_keeps_the_rest_of_the_prospect_untouched():
    outcome = EnrichmentOutcome(ipress_code="00000001", checked=True, source_url="https://x.test")
    enriched = apply_enrichment(prospect(), outcome)
    assert enriched.score.total == 60
    assert enriched.capacity.doctors_total == 0
    assert enriched.pipeline_stage == "discovered"


def test_apply_enrichment_leaves_an_unattributed_clinic_unknown():
    """No evidence is not a negative: nothing is added and nothing is changed."""
    outcome = EnrichmentOutcome(ipress_code="00000001", checked=False, note="not-attributed")
    enriched = apply_enrichment(prospect(), outcome)
    assert enriched.ozone_therapy.checked is False
    assert enriched.ozone_therapy.performs is False
    assert enriched.ozone_therapy.source_url is None
    assert "already-offers-ozone-therapy" not in enriched.tags
    assert "web-enriched" not in enriched.tags


def test_apply_enrichment_refuses_an_outcome_for_another_clinic():
    """Attaching one clinic's claim to another is the failure this guards against."""
    outcome = EnrichmentOutcome(ipress_code="00000099", checked=True, source_url="https://x.test")
    with pytest.raises(ValueError, match="00000099"):
        apply_enrichment(prospect(), outcome)
