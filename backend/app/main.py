import os
from functools import lru_cache
from typing import TypeVar

import firebase_admin
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from pydantic import BaseModel

from .schemas import (
    DossierInput,
    DossierOutput,
    OutboundOutput,
    ProspectInput,
    RoiInput,
    RoiOutput,
)

app = FastAPI(
    title="ConfIA AI API",
    version="0.1.0",
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


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
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


def generate_structured(
    prompt: str,
    response_model: type[ResponseModel],
) -> ResponseModel:
    from google.genai import types

    client = get_client()
    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
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


@app.post("/generate/dossier", response_model=DossierOutput)
def generate_dossier(
    payload: DossierInput,
    _: dict = Depends(require_authenticated_user),
) -> DossierOutput:
    prompt = f"""
Prepara un resumen de dossier regulatorio para revisión humana.
Los campos regulatorios deben copiarse exactamente desde
validated_regulatory_data. Está prohibido inventar, corregir o completar
Registro Sanitario, clasificación, certificados o plantillas.
Incluye verification_required=true y advierte que el equipo regulatorio debe
verificar la vigencia antes de cualquier envío.

Datos:
{payload.model_dump_json(indent=2)}

Devuelve únicamente el esquema JSON solicitado.
"""
    return generate_structured(prompt, DossierOutput)
