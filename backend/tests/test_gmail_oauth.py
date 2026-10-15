import json
from urllib.parse import parse_qs, urlparse

import pytest

from app import gmail_service


@pytest.fixture
def client_secrets(tmp_path, monkeypatch):
    path = tmp_path / "client_secret.json"
    path.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "test-client.apps.googleusercontent.com",
                    "client_secret": "test-secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8000/gmail/auth/callback"],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GMAIL_CLIENT_SECRETS", str(path))
    monkeypatch.setenv("GMAIL_REDIRECT_URI", "http://localhost:8000/gmail/auth/callback")
    return path


def test_authorization_url_has_state_and_no_pkce_challenge(client_secrets):
    # Regresión: con PKCE el canje del código falla porque el verificador se pierde entre peticiones.
    url = gmail_service.start_authorization()
    query = parse_qs(urlparse(url).query)

    assert query["scope"] == ["https://www.googleapis.com/auth/gmail.send"]
    assert query["state"][0]
    assert "code_challenge" not in query


def test_callback_with_unknown_state_is_rejected(client_secrets):
    with pytest.raises(gmail_service.GmailAuthRequired):
        gmail_service.finish_authorization(
            "http://localhost:8000/gmail/auth/callback?state=nope&code=abc", "nope"
        )
