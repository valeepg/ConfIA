import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import TypeVar

import firebase_admin
from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from pydantic import BaseModel

from .confia_product_catalog import resolve_product_line
from .gmail_service import (
    GmailAuthRequired,
    GmailConfigError,
    GmailSendError,
    finish_authorization,
    is_connected,
    send_email,
    start_authorization,
)
from .outbound import append_trace, list_lead_documents, now_iso, read_attachments
from .documents import (
    DocumentRenderError,
    build_dossier_prompt,
    render_dossier_markdown,
    render_pdf,
)
from .proforma import build_proforma_markdown, proposal_params, timestamp, to_evaluation_output
from .roi_engine import ZONE_MESSAGES, evaluate, get_product
from .schemas import (
    DossierDocumentOutput,
    DossierInput,
    EvaluationOutput,
    LeadDocumentFile,
    LeadDocumentsOutput,
    OfferInput,
    OutboundOutput,
    OutboundSendInput,
    OutboundSendOutput,
    ProformaInput,
    ProformaOutput,
    ProspectInput,
    RoiInput,
    RoiOutput,
)
from .storage import (
    DOWNLOADABLE_FILENAMES,
    MARKDOWN_FILENAME,
    PDF_FILENAME,
    PROPOSAL_PARAMS_FILENAME,
    PROPOSAL_PDF_FILENAME,
    create_version_dir,
    ensure_storage_dirs,
    normalize_lead_id,
    version_dir,
)

# Solo desarrollo: carga backend/.env si python-dotenv está instalado (ver requirements-dev.txt).
# Las variables ya definidas en el entorno tienen prioridad sobre el archivo.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

logger = logging.getLogger("confia.api")

app = FastAPI(
    title="ConfIA AI API",
    version="0.2.0",
    description="Structured AI generation for ConfIA's human-approved CRM workflows.",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)
bearer_scheme = HTTPBearer(auto_error=False)

if not firebase_admin._apps:
    firebase_admin.initialize_app()

ensure_storage_dirs()


def auth_required() -> bool:
    # Demo: sin login. Poner CONFIA_REQUIRE_AUTH=true para volver a exigir token Firebase.
    # return os.getenv("CONFIA_REQUIRE_AUTH", "false").strip().lower() in ("1", "true", "yes")
    return False
    


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if not auth_required():
        return {"uid": "demo-anonymous"}

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Se requiere un token Firebase.")

    try:
        return firebase_auth.verify_id_token(credentials.credentials)
    except Exception as error:
        raise HTTPException(status_code=401, detail="Token Firebase inválido o expirado.") from error


@lru_cache(maxsize=1)
def get_client():
    try:
        from google import genai
    except ImportError as error:
        raise HTTPException(
            status_code=503,
            detail="El SDK google-genai no está disponible en el entorno del backend.",
        ) from error

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_CLOUD_PROJECT no está configurado en el backend.",
        )
    return genai.Client(
        vertexai=True,
        project=project,
        location=location,
    )


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def generate_structured(
    prompt: str,
    response_model: type[ResponseModel],
) -> ResponseModel:
    from google.genai import types

    client = get_client()
    try:
        response = client.models.generate_content(
            model=gemini_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=response_model,
            ),
        )
        if not response.parsed:
            raise HTTPException(
                status_code=502,
                detail="Gemini no devolvió una respuesta estructurada válida.",
            )
        return response.parsed
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo generar la respuesta de IA: {error}",
        ) from error


def generate_markdown(prompt: str) -> str:
    from google.genai import types

    client = get_client()
    try:
        response = client.models.generate_content(
            model=gemini_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="text/plain",
            ),
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo generar el documento de IA: {error}",
        ) from error

    text = (response.text or "").strip()
    if not text:
        raise HTTPException(status_code=502, detail="Gemini devolvió un documento vacío.")
    return text


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "confia-ai-api"}


@app.post("/generate/roi", response_model=RoiOutput)
def generate_roi(
    payload: RoiInput,
    _: dict = Depends(require_authenticated_user),
) -> RoiOutput:
    prompt = f"""
Eres el copiloto comercial interno de ConfIA. Genera una propuesta ROI B2B
para un director médico. Usa exclusivamente los datos suministrados.
No inventes precios, volúmenes, registros sanitarios ni resultados clínicos.
Si una afirmación no está respaldada por los datos, omítela.

Datos del prospecto:
{payload.model_dump_json(indent=2)}

Devuelve únicamente el esquema JSON solicitado. Calcula estimated_net_monthly
como (patient_price_avg - cost_per_session) * projected_sessions_month,
sin modificar los datos de entrada. Incluye las suposiciones explícitas.
"""
    return generate_structured(prompt, RoiOutput)


@app.post("/generate/outbound", response_model=OutboundOutput)
def generate_outbound(
    payload: ProspectInput,
    _: dict = Depends(require_authenticated_user),
) -> OutboundOutput:
    prompt = f"""
Redacta un borrador outbound B2B para el director médico del prospecto.
Usa únicamente el nombre, especialidad, ubicación, score y sugerencia recibidos.
No afirmes eficacia clínica, registros DIGEMID, certificados ni cifras que no
aparezcan en los datos. El texto requiere aprobación humana antes de enviarse.

Datos:
{payload.model_dump_json(indent=2)}

Devuelve JSON estricto y enumera en evidence_used los datos utilizados.
"""
    return generate_structured(prompt, OutboundOutput)


@app.post("/generate/dossier", response_model=DossierDocumentOutput)
def generate_dossier(
    payload: DossierInput,
    _: dict = Depends(require_authenticated_user),
) -> DossierDocumentOutput:
    try:
        lead_id = normalize_lead_id(payload.lead_id or payload.name)
        product, catalog_match = resolve_product_line(payload.specialty, payload.product_line)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    # Gemini trabaja con los datos oficiales del catálogo. La plantilla vuelve a inyectar
    # esos valores desde el catálogo, así que el LLM no puede alterarlos.
    prospect = payload.model_dump(exclude={"lead_id", "product_line"})
    body = generate_markdown(build_dossier_prompt(prospect, product))

    try:
        document_markdown = render_dossier_markdown(
            body=body,
            lead_name=payload.name,
            regulatory=product.regulatory.model_dump(),
        )
        pdf_bytes = render_pdf(document_markdown)
    except DocumentRenderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    # Se crea la versión solo cuando el render ya funcionó, para no dejar carpetas vacías.
    version, directory = create_version_dir(lead_id)
    (directory / MARKDOWN_FILENAME).write_text(document_markdown, encoding="utf-8")
    (directory / PDF_FILENAME).write_bytes(pdf_bytes)

    relative_base = f"output/leads/{lead_id}/v{version}"
    base_url = f"/documents/leads/{lead_id}/versions/{version}"
    return DossierDocumentOutput(
        lead_id=lead_id,
        version=version,
        version_label=f"v{version}",
        product_line=product.key,
        product_name=product.name,
        catalog_match=catalog_match,
        regulatory_data=product.regulatory,
        markdown_path=f"{relative_base}/{MARKDOWN_FILENAME}",
        pdf_path=f"{relative_base}/{PDF_FILENAME}",
        download_urls={
            "markdown": f"{base_url}/{MARKDOWN_FILENAME}",
            "pdf": f"{base_url}/{PDF_FILENAME}",
        },
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/documents/leads/{lead_id}/versions/{version}/{filename}")
def download_document(
    lead_id: str,
    version: int = Path(ge=1),
    filename: str = Path(),
    _: dict = Depends(require_authenticated_user),
) -> FileResponse:
    if filename not in DOWNLOADABLE_FILENAMES:
        raise HTTPException(status_code=404, detail="Archivo no disponible.")

    try:
        file_path = version_dir(lead_id, version) / filename
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="No existe esa versión del documento.")

    media_type = {
        ".pdf": "application/pdf",
        ".json": "application/json",
        ".md": "text/markdown; charset=utf-8",
    }[file_path.suffix]
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=f"{normalize_lead_id(lead_id)}-v{version}-{filename}",
    )


@app.post("/roi/simulate", response_model=EvaluationOutput)
def simulate_roi(
    payload: OfferInput,
    _: dict = Depends(require_authenticated_user),
) -> EvaluationOutput:
    # Sin IA: el cálculo es determinista y se recalcula en cada cambio del simulador.
    try:
        evaluation = evaluate(payload.to_offer())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return to_evaluation_output(evaluation)


@app.post("/roi/proforma", response_model=ProformaOutput)
def generate_proforma(
    payload: ProformaInput,
    _: dict = Depends(require_authenticated_user),
) -> ProformaOutput:
    try:
        lead_id = normalize_lead_id(payload.lead_id or payload.lead_name)
        offer = payload.to_offer()
        evaluation = evaluate(offer)
        product = get_product(offer.product_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    # RN-044: solo se genera propuesta cuando la clínica y Tecnocare cumplen a la vez.
    if not evaluation.is_win_win:
        reasons = list(evaluation.violations) or [ZONE_MESSAGES[evaluation.zone]]
        raise HTTPException(
            status_code=422,
            detail="No se genera la propuesta: " + " ".join(reasons),
        )

    generated_at = timestamp()
    try:
        markdown = build_proforma_markdown(payload.lead_name, product, offer, evaluation, generated_at)
        pdf_bytes = render_pdf(markdown)
    except (DocumentRenderError, OSError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    # Solo se crea la versión cuando el PDF ya está listo, para no dejar carpetas vacías.
    params_json = proposal_params(payload.lead_name, offer, evaluation, generated_at)
    version, directory = create_version_dir(lead_id)
    (directory / PROPOSAL_PDF_FILENAME).write_bytes(pdf_bytes)
    (directory / PROPOSAL_PARAMS_FILENAME).write_text(params_json, encoding="utf-8")

    relative_base = f"output/leads/{lead_id}/v{version}"
    base_url = f"/documents/leads/{lead_id}/versions/{version}"
    return ProformaOutput(
        lead_id=lead_id,
        version=version,
        version_label=f"v{version}",
        product_name=product.name,
        evaluation=to_evaluation_output(evaluation),
        pdf_path=f"{relative_base}/{PROPOSAL_PDF_FILENAME}",
        params_path=f"{relative_base}/{PROPOSAL_PARAMS_FILENAME}",
        download_urls={
            "pdf": f"{base_url}/{PROPOSAL_PDF_FILENAME}",
            "params": f"{base_url}/{PROPOSAL_PARAMS_FILENAME}",
        },
        generated_at=generated_at,
    )


@app.get("/leads/{lead_id}/documents", response_model=LeadDocumentsOutput)
def lead_documents(
    lead_id: str,
    _: dict = Depends(require_authenticated_user),
) -> LeadDocumentsOutput:
    try:
        normalized = normalize_lead_id(lead_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    files = [LeadDocumentFile(**entry) for entry in list_lead_documents(normalized)]
    return LeadDocumentsOutput(lead_id=normalized, files=files)


@app.get("/gmail/status")
def gmail_status(_: dict = Depends(require_authenticated_user)) -> dict[str, bool]:
    return {"connected": is_connected()}


@app.get("/gmail/auth/start")
def gmail_auth_start() -> RedirectResponse:
    # Se abre en una pestaña nueva; Google devuelve al callback de abajo.
    try:
        return RedirectResponse(start_authorization())
    except GmailConfigError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/gmail/auth/callback")
def gmail_auth_callback(request: Request, state: str = "", error: str | None = None) -> HTMLResponse:
    if error:
        raise HTTPException(status_code=400, detail=f"Google rechazó la autorización: {error}")
    try:
        finish_authorization(str(request.url), state)
    except GmailAuthRequired as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GmailConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # Canje de código fallido (credenciales, redirect URI, red): se registra la traza y se informa.
        logger.exception("Falló el canje OAuth de Gmail")
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo completar la vinculación con Gmail: {exc}",
        ) from exc

    return HTMLResponse(
        "<html><body style='font-family:sans-serif'>"
        "<h3>Gmail vinculado a ConfIA.</h3>"
        "<p>Puedes cerrar esta pestaña y volver al CRM.</p></body></html>"
    )


@app.post("/outbound/send", response_model=OutboundSendOutput)
def send_outbound(
    payload: OutboundSendInput,
    _: dict = Depends(require_authenticated_user),
) -> OutboundSendOutput:
    try:
        lead_id = normalize_lead_id(payload.lead_id)
        attachments = read_attachments(
            lead_id,
            [(ref.version, ref.filename) for ref in payload.attachments],
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    try:
        message_id = send_email(payload.to, payload.subject, payload.body, attachments)
    except GmailAuthRequired as error:
        # El frontend usa auth_url para pedirle al dueño que vincule Gmail.
        raise HTTPException(
            status_code=401,
            detail={
                "code": "gmail_auth_required",
                "message": str(error),
                "auth_url": "/gmail/auth/start",
            },
        ) from error
    except GmailConfigError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except GmailSendError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    sent_at = now_iso()
    attachment_names = [attachment.filename for attachment in attachments]
    # Traza append-only del envío. El cambio de estado del lead lo aplica el CRM.
    append_trace(
        lead_id,
        {
            "sent_at": sent_at,
            "message_id": message_id,
            "lead_name": payload.lead_name,
            "to": payload.to,
            "subject": payload.subject,
            "attachments": attachment_names,
            "new_status": "contactado",
        },
    )

    return OutboundSendOutput(
        status="contactado",
        message_id=message_id,
        sent_at=sent_at,
        to=payload.to,
        subject=payload.subject,
        attachments=attachment_names,
    )
