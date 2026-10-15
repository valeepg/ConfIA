"""Envío de correos con la API de Gmail, autorizada por OAuth del usuario dueño.

Alcance mínimo: solo `gmail.send`. El refresh token se guarda en un archivo local
(GMAIL_TOKEN_PATH) que nunca debe subirse al repositorio.

Variables de entorno:
  GMAIL_CLIENT_SECRETS  ruta al client_secret.json del cliente OAuth "Aplicación web"
  GMAIL_REDIRECT_URI    p. ej. http://localhost:8000/gmail/auth/callback (debe estar registrada en Google)
  GMAIL_TOKEN_PATH      opcional; por defecto storage/secrets/gmail_token.json
"""

import base64
import os
import secrets
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from .storage import STORAGE_ROOT

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
DEFAULT_REDIRECT_URI = "http://localhost:8000/gmail/auth/callback"

# Estados OAuth emitidos y aún no canjeados (demo: un solo proceso, en memoria).
_pending_states: set[str] = set()


class GmailAuthRequired(Exception):
    """No hay credenciales válidas: el dueño debe vincular su cuenta de Gmail."""


class GmailConfigError(Exception):
    """Falta configuración del cliente OAuth en el servidor."""


class GmailSendError(Exception):
    """Gmail rechazó el envío."""


@dataclass(frozen=True)
class Attachment:
    filename: str
    data: bytes


def build_raw_message(to: str, subject: str, body: str, attachments: list[Attachment]) -> str:
    """Construye un MIME multipart (texto + PDFs) listo para la API de Gmail."""
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    for attachment in attachments:
        message.add_attachment(
            attachment.data,
            maintype="application",
            subtype="pdf",
            filename=attachment.filename,
        )

    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def token_path() -> Path:
    return Path(os.getenv("GMAIL_TOKEN_PATH", STORAGE_ROOT / "secrets" / "gmail_token.json"))


def client_secrets_path() -> Path:
    raw = os.getenv("GMAIL_CLIENT_SECRETS")
    if not raw:
        raise GmailConfigError("GMAIL_CLIENT_SECRETS no está configurado en el backend.")
    path = Path(raw)
    if not path.is_file():
        raise GmailConfigError(f"No existe el archivo de credenciales OAuth: {path}")
    return path


def redirect_uri() -> str:
    return os.getenv("GMAIL_REDIRECT_URI", DEFAULT_REDIRECT_URI)


def _allow_local_http() -> None:
    # oauthlib exige HTTPS salvo en localhost; en desarrollo el callback es http://localhost.
    if redirect_uri().startswith("http://localhost") or redirect_uri().startswith("http://127.0.0.1"):
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")


def _load_credentials():
    path = token_path()
    if not path.is_file():
        return None

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    credentials = Credentials.from_authorized_user_file(str(path), GMAIL_SCOPES)
    if not credentials.valid and credentials.refresh_token:
        credentials.refresh(Request())
        _save_credentials(credentials)
    return credentials if credentials.valid else None


def _save_credentials(credentials) -> None:
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(credentials.to_json(), encoding="utf-8")


def is_connected() -> bool:
    try:
        return _load_credentials() is not None
    except Exception:
        # Token corrupto o revocado: se trata como no vinculado.
        return False


def start_authorization() -> str:
    """Devuelve la URL de consentimiento de Google para vincular la cuenta."""
    from google_auth_oauthlib.flow import Flow

    _allow_local_http()
    # Cliente confidencial (client_secret): sin PKCE. Debe ser igual en inicio y callback.
    flow = Flow.from_client_secrets_file(
        str(client_secrets_path()),
        scopes=GMAIL_SCOPES,
        redirect_uri=redirect_uri(),
        autogenerate_code_verifier=False,
    )
    state = secrets.token_urlsafe(24)
    url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
    _pending_states.add(state)
    return url


def finish_authorization(callback_url: str, state: str) -> None:
    """Canjea el código de Google por tokens y los guarda. Valida el state para evitar CSRF."""
    from google_auth_oauthlib.flow import Flow

    if state not in _pending_states:
        raise GmailAuthRequired("La autorización expiró o no corresponde a esta sesión. Vuelve a intentarlo.")
    _pending_states.discard(state)

    _allow_local_http()
    flow = Flow.from_client_secrets_file(
        str(client_secrets_path()),
        scopes=GMAIL_SCOPES,
        redirect_uri=redirect_uri(),
        state=state,
        autogenerate_code_verifier=False,
    )
    flow.fetch_token(authorization_response=callback_url)
    _save_credentials(flow.credentials)


def send_email(to: str, subject: str, body: str, attachments: list[Attachment]) -> str:
    """Envía el correo desde la cuenta vinculada y devuelve el id del mensaje de Gmail."""
    credentials = _load_credentials()
    if credentials is None:
        raise GmailAuthRequired("La cuenta de Gmail no está vinculada.")

    from googleapiclient.discovery import build

    raw = build_raw_message(to, subject, body, attachments)
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    try:
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    except Exception as error:
        raise GmailSendError(f"Gmail rechazó el envío: {error}") from error
    return sent["id"]
