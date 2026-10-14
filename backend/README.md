# ConfIA AI API

Servicio FastAPI para generar borradores estructurados que siempre requieren
aprobación humana en el CRM.

## Ejecución local

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Configurar ADC localmente con: gcloud auth application-default login
uvicorn app.main:app --reload --port 8000
```

Endpoints:

- `GET /health`
- `POST /generate/roi`
- `POST /generate/outbound`
- `POST /generate/dossier`

Los endpoints de generación requieren un Firebase ID token en el encabezado
`Authorization: Bearer <token>`. La API no acepta credenciales de Gemini desde
el frontend. En local usa ADC
(`gcloud auth application-default login`). En Cloud Run usa la cuenta de
servicio asignada al servicio y `GOOGLE_CLOUD_PROJECT`; no se necesita una
API key de Gemini.

Servicio desplegado actualmente:

`https://confia-ai-api-37ivgnr2qa-uc.a.run.app`
