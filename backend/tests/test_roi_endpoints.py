import json

import pytest
from fastapi.testclient import TestClient

from app import main
from app.proforma import build_proforma_markdown
from app.negotiation_params import PRODUCTS
from app.roi_engine import Offer, evaluate
from app.storage import LEADS_DIR

INITIAL = {
    "product_id": "ozonette",
    "session_price_pen": 120,
    "sessions_per_month": 40,
    "equipment_price_usd": 6500,
    "installation_included": False,
    "training_included_sessions": 2,
    "installments": 1,
    "warranty_months": 12,
}
NO_DEAL = {**INITIAL, "session_price_pen": 90, "sessions_per_month": 30}


@pytest.fixture
def client():
    main.app.dependency_overrides[main.require_authenticated_user] = lambda: {"uid": "demo"}
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_simulate_returns_procedure_values_and_green_zone(client):
    response = client.post("/roi/simulate", json=INITIAL)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["zone"] == "win_win"
    assert body["status"] == "green"
    assert body["violations"] == []
    assert body["recovery_months"] == pytest.approx(10.15, abs=0.05)
    assert body["margin"] == pytest.approx(0.338, abs=0.001)
    assert body["data_status"] == "mock"


def test_simulate_reports_violations_as_red_without_failing(client):
    response = client.post("/roi/simulate", json={**INITIAL, "equipment_price_usd": 7000})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "red"
    assert any("supera la lista" in v for v in body["violations"])


def test_simulate_rejects_unknown_product(client):
    response = client.post("/roi/simulate", json={**INITIAL, "product_id": "no_existe"})
    assert response.status_code == 422


def test_proforma_refused_when_there_is_no_deal(client):
    response = client.post("/roi/proforma", json={**NO_DEAL, "lead_name": "Clínica Sin Trato"})

    assert response.status_code == 422
    assert "No se genera la propuesta" in response.json()["detail"]


def test_proforma_creates_versioned_pdf_and_params(client):
    payload = {**INITIAL, "lead_name": "Clínica Versionada", "lead_id": "clinica-versionada-roi"}

    first = client.post("/roi/proforma", json=payload)
    second = client.post("/roi/proforma", json=payload)

    assert first.status_code == 200, first.text
    assert first.json()["version_label"] == "v1"
    assert second.json()["version_label"] == "v2"

    folder = LEADS_DIR / "clinica-versionada-roi" / "v1"
    assert (folder / "propuesta_comercial.pdf").read_bytes().startswith(b"%PDF-")
    params = json.loads((folder / "parametros.json").read_text(encoding="utf-8"))
    assert params["evaluation"]["zone"] == "win_win"
    assert params["data_status"] == "mock"


def test_proforma_pdf_is_downloadable(client):
    payload = {**INITIAL, "lead_name": "Clínica Descarga", "lead_id": "clinica-descarga-roi"}
    created = client.post("/roi/proforma", json=payload).json()

    response = client.get(created["download_urls"]["pdf"])

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_client_document_never_exposes_margin_or_costs():
    offer = Offer(**{k: INITIAL[k] for k in Offer.__dataclass_fields__})
    evaluation = evaluate(offer)
    markdown = build_proforma_markdown(
        "Clínica Demo", PRODUCTS["ozonette"], offer, evaluation, "2026-10-15T00:00:00+00:00"
    )
    lowered = markdown.lower()

    assert "margen" not in lowered
    assert "costo" not in lowered
    assert "4,570" not in markdown and "4570" not in markdown  # costo total de Tecnocare
    assert "5,693" not in markdown  # precio mínimo del equipo
    assert "Borrador" in markdown
    assert "[pendiente" in markdown
