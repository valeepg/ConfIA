import pytest
from fastapi.testclient import TestClient

from app import main
from app.confia_product_catalog import PRODUCT_LINES
from app.documents import build_dossier_prompt, render_dossier_markdown
from app.storage import LEADS_DIR

BODY = """## Resumen ejecutivo
El equipo ofrece {{registry_number}} de clasificación {{classification}}.

| Campo | Valor |
|---|---|
| Certificado | {{calibration_certificate}} |
"""


@pytest.fixture
def client(monkeypatch):
    app = main.app
    app.dependency_overrides[main.require_authenticated_user] = lambda: {"uid": "demo"}

    prompts = []

    def fake_generate_markdown(prompt):
        prompts.append(prompt)
        return BODY

    monkeypatch.setattr(main, "generate_markdown", fake_generate_markdown)
    # WeasyPrint necesita Pango; aquí solo probamos el flujo, el PDF real va en el contenedor.
    monkeypatch.setattr(main, "render_pdf", lambda markdown_text: b"%PDF-fake")

    client = TestClient(app)
    client.prompts = prompts
    yield client
    app.dependency_overrides.clear()


def prospect(**overrides):
    data = {
        "name": "Clínica San Gabriel",
        "district": "San Isidro",
        "specialty": "Traumatología y Quemados",
        "director_medico": "Dra. Ana Torres",
        "doctor_specialty": "Traumatología",
        "score": 82,
        "ai_suggestion": "Ofrecer demo del modelo OaaS",
    }
    data.update(overrides)
    return data


def test_new_lead_without_regulatory_payload_succeeds_with_catalog_data(client):
    response = client.post("/generate/dossier", json=prospect())

    assert response.status_code == 200, response.text
    body = response.json()
    line = PRODUCT_LINES["ozonette_infiltracion"]
    assert body["product_line"] == line.key
    assert body["catalog_match"] == "specialty"
    assert body["regulatory_data"] == line.regulatory.model_dump()
    assert body["verification_required"] is True


def test_document_contains_official_registry_and_no_placeholders(client):
    body = client.post("/generate/dossier", json=prospect(lead_id="clinica-test-doc")).json()

    from app.storage import version_dir

    document = (version_dir("clinica-test-doc", body["version"]) / "document.md").read_text(encoding="utf-8")
    assert "DM-14820-E" in document
    assert "{{" not in document


def test_prompt_contains_official_catalog_data_and_markers(client):
    client.post("/generate/dossier", json=prospect())

    prompt = client.prompts[-1]
    line = PRODUCT_LINES["ozonette_infiltracion"]
    assert line.name in prompt
    assert "DM-14820-E" in prompt
    assert "{{registry_number}}" in prompt


def test_versions_increment_per_lead(client):
    first = client.post("/generate/dossier", json=prospect(lead_id="clinica-versiones")).json()
    second = client.post("/generate/dossier", json=prospect(lead_id="clinica-versiones")).json()

    assert first["version_label"] == "v1"
    assert second["version_label"] == "v2"
    assert (LEADS_DIR / "clinica-versiones" / "v2" / "document.pdf").is_file()


def test_unknown_explicit_product_line_returns_422(client):
    response = client.post("/generate/dossier", json=prospect(product_line="no_existe"))

    assert response.status_code == 422
    assert "no existe en el catálogo" in response.json()["detail"]


def test_explicit_product_line_is_used(client):
    body = client.post(
        "/generate/dossier",
        json=prospect(product_line="ozonobaric_ahtm", lead_id="clinica-explicita"),
    ).json()

    assert body["catalog_match"] == "explicit"
    assert body["product_line"] == "ozonobaric_ahtm"


def test_requires_firebase_token_when_auth_is_enabled(monkeypatch):
    monkeypatch.setattr(main, "auth_required", lambda: True)
    unauthenticated = TestClient(main.app)
    response = unauthenticated.post("/generate/dossier", json=prospect())
    assert response.status_code == 401


def test_works_without_token_in_demo_mode(monkeypatch):
    monkeypatch.delenv("CONFIA_REQUIRE_AUTH", raising=False)
    monkeypatch.setattr(main, "generate_markdown", lambda prompt: BODY)
    monkeypatch.setattr(main, "render_pdf", lambda markdown_text: b"%PDF-fake")

    response = TestClient(main.app).post("/generate/dossier", json=prospect(lead_id="clinica-demo-anonima"))

    assert response.status_code == 200, response.text
    assert response.json()["version_label"] == "v1"


def test_prompt_builder_is_pure():
    line = PRODUCT_LINES["ozonobaric_ahtm"]
    prompt = build_dossier_prompt({"name": "X"}, line)
    assert line.regulatory.registry_number in prompt
    assert "Datos del prospecto" in prompt


def test_render_keeps_catalog_values_in_document():
    line = PRODUCT_LINES["ozonobaric_ahtm"]
    document = render_dossier_markdown(BODY, "X", line.regulatory.model_dump())
    assert line.regulatory.registry_number in document
