import base64
from email import message_from_bytes
from email.header import decode_header, make_header

import pytest
from fastapi.testclient import TestClient

from app import main
from app.gmail_service import Attachment, GmailAuthRequired, GmailSendError, build_raw_message
from app.storage import LEADS_DIR, create_version_dir


def _decode_subject(message) -> str:
    return str(make_header(decode_header(message["Subject"])))


@pytest.fixture
def client():
    main.app.dependency_overrides[main.require_authenticated_user] = lambda: {"uid": "demo"}
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture
def sent(monkeypatch):
    """Reemplaza el envío real: registra lo que se enviaría. Ningún correo sale de aquí."""
    calls = []

    def fake_send(to, subject, body, attachments):
        calls.append({"to": to, "subject": subject, "body": body, "attachments": attachments})
        return "msg-test-123"

    monkeypatch.setattr(main, "send_email", fake_send)
    return calls


def _lead_with_documents(lead_id: str) -> None:
    """Crea v1 con dossier y propuesta, como si ya se hubieran generado."""
    version, directory = create_version_dir(lead_id)
    (directory / "document.pdf").write_bytes(b"%PDF-dossier")
    (directory / "propuesta_comercial.pdf").write_bytes(b"%PDF-propuesta")


def test_mime_message_has_utf8_body_subject_and_pdf_attachments():
    raw = build_raw_message(
        to="director@clinica.pe",
        subject="Propuesta para la clínica — ozonoterapia",
        body="Hola Dra. Torres, ajusté la oferta según lo conversado.",
        attachments=[Attachment(filename="propuesta-comercial-v1.pdf", data=b"%PDF-x")],
    )
    message = message_from_bytes(base64.urlsafe_b64decode(raw))

    assert message["To"] == "director@clinica.pe"
    assert _decode_subject(message) == "Propuesta para la clínica — ozonoterapia"
    parts = [part for part in message.walk() if part.get_content_maintype() != "multipart"]
    text = [part for part in parts if part.get_content_type() == "text/plain"][0]
    assert "ajusté la oferta" in text.get_payload(decode=True).decode("utf-8")
    pdf = [part for part in parts if part.get_content_type() == "application/pdf"][0]
    assert pdf.get_filename() == "propuesta-comercial-v1.pdf"
    assert pdf.get_payload(decode=True) == b"%PDF-x"


def test_lists_attachable_documents_newest_first(client):
    _lead_with_documents("clinica-lista-docs")

    response = client.get("/leads/clinica-lista-docs/documents")

    assert response.status_code == 200
    files = response.json()["files"]
    assert {f["filename"] for f in files} == {"document.pdf", "propuesta_comercial.pdf"}
    assert all(f["download_url"].startswith("/documents/leads/clinica-lista-docs/versions/") for f in files)


def test_sends_email_with_selected_attachments_and_logs_trace(client, sent):
    _lead_with_documents("clinica-envio-ok")

    response = client.post(
        "/outbound/send",
        json={
            "lead_id": "clinica-envio-ok",
            "lead_name": "Clínica Envío OK",
            "to": "director@clinica.pe",
            "subject": "Propuesta",
            "body": "Texto editado por el dueño.",
            "attachments": [{"version": 1, "filename": "propuesta_comercial.pdf"}],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "contactado"
    assert body["message_id"] == "msg-test-123"
    assert body["attachments"] == ["propuesta-comercial-v1.pdf"]

    assert len(sent) == 1
    assert sent[0]["body"] == "Texto editado por el dueño."
    assert sent[0]["attachments"][0].data == b"%PDF-propuesta"

    trace = (LEADS_DIR / "clinica-envio-ok" / "envios.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(trace) == 1
    assert '"new_status": "contactado"' in trace[0]


def test_rejects_arbitrary_file_names(client, sent):
    response = client.post(
        "/outbound/send",
        json={
            "lead_id": "clinica-traversal",
            "lead_name": "X",
            "to": "a@b.pe",
            "subject": "s",
            "body": "b",
            "attachments": [{"version": 1, "filename": "../../secrets/gmail_token.json"}],
        },
    )

    assert response.status_code == 422
    assert sent == []


def test_rejects_version_that_does_not_exist(client, sent):
    _lead_with_documents("clinica-sin-version")

    response = client.post(
        "/outbound/send",
        json={
            "lead_id": "clinica-sin-version",
            "lead_name": "X",
            "to": "a@b.pe",
            "subject": "s",
            "body": "b",
            "attachments": [{"version": 9, "filename": "document.pdf"}],
        },
    )

    assert response.status_code == 422
    assert "v9" in response.json()["detail"]
    assert sent == []


def test_rejects_invalid_recipient(client, sent):
    response = client.post(
        "/outbound/send",
        json={"lead_id": "x", "lead_name": "X", "to": "no-es-correo", "subject": "s", "body": "b"},
    )
    assert response.status_code == 422
    assert sent == []


def test_returns_auth_required_when_gmail_is_not_linked(client, monkeypatch):
    _lead_with_documents("clinica-sin-gmail")

    def not_linked(*args, **kwargs):
        raise GmailAuthRequired("La cuenta de Gmail no está vinculada.")

    monkeypatch.setattr(main, "send_email", not_linked)

    response = client.post(
        "/outbound/send",
        json={"lead_id": "clinica-sin-gmail", "lead_name": "X", "to": "a@b.pe", "subject": "s", "body": "b"},
    )

    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "gmail_auth_required"
    assert detail["auth_url"] == "/gmail/auth/start"
    assert not (LEADS_DIR / "clinica-sin-gmail" / "envios.jsonl").exists()


def test_gmail_rejection_is_reported_and_not_logged(client, monkeypatch):
    _lead_with_documents("clinica-gmail-falla")

    def rejected(*args, **kwargs):
        raise GmailSendError("Gmail rechazó el envío: cuota diaria")

    monkeypatch.setattr(main, "send_email", rejected)

    response = client.post(
        "/outbound/send",
        json={"lead_id": "clinica-gmail-falla", "lead_name": "X", "to": "a@b.pe", "subject": "s", "body": "b"},
    )

    assert response.status_code == 502
    assert not (LEADS_DIR / "clinica-gmail-falla" / "envios.jsonl").exists()
