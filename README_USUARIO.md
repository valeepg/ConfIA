# ConfIA · Guía de usuario y despliegue

Esta guía explica cómo abrir, probar y desplegar ConfIA, qué está simulado y qué falta
decidir. Es documentación, no un registro de cambios. Para la documentación de producto
original ver `README.md`.

> **Estado:** demostración funcional. Hay datos mock, autenticación simulada y varias
> decisiones de negocio pendientes (sección 8).

---

## 1. Qué incluye ConfIA

| Módulo | Qué hace | Dónde |
|---|---|---|
| Acceso | Pantalla de login simulada con un usuario demo; panel de cuenta con "Repetir tutorial" y cierre de sesión | Pantalla inicial, botón con iniciales arriba a la derecha |
| Seguimiento de clientes | Tablero Kanban de prospectos (Descubierto → Contactado → Propuesta enviada → Cierre). Interruptor **Dashboard** con indicadores, embudo, distribución de score y un asesor simulado | Pestaña "Seguimiento de Clientes" |
| Propuesta económica (ROI) | Simulador de contraofertas en vivo: precio por sesión, sesiones, precio del equipo, capacitación, cuotas y garantía. Indica zona de acuerdo (🟢) o alerta (🔴). Genera propuestas PDF versionadas (solo en zona de acuerdo) | Botón "Generar propuesta económica (Retorno)" en la ficha del prospecto |
| Dossier regulatorio DIGEMID | Carpeta regulatoria en Markdown y PDF, con datos del catálogo maestro y versionado | Ficha del prospecto |
| Outbound por Gmail | Borrador de IA editable (asunto, cuerpo, destinatario), adjuntos versionados y envío con cuenta de Gmail vinculada por OAuth | Botón de generar contacto → modal de revisión |
| Equipos y mantenimiento | Vista operativa (equipos, insumos, capacitación) y **Dashboard** de salud del parque | Pestaña "Equipos y Mantenimiento" |
| Catálogo y configuración | Catálogo de equipos, esquema de datos y regulación | Pestañas correspondientes |
| Tutorial con Zonito | Mascota (molécula de O₃) que recorre la aplicación en 9 pasos. Se presenta sola la primera vez | Botón flotante abajo a la derecha |

**Principio de diseño:** la IA redacta, el sistema calcula y una persona aprueba. Ningún
correo ni documento sale sin un clic humano.

---

## 2. Requisitos

- **Node.js 22** o superior (frontend).
- **Python 3.13** (backend).
- **Git**.
- **Docker Desktop**, solo si quieres levantar todo con contenedores.
- **Google Cloud CLI** (`gcloud`), solo si vas a usar Gemini o Gmail reales.

---

## 3. Arranque rápido (desarrollo local)

### 3.1 Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Comprueba que responde: `http://localhost:8000/health` debe devolver `{"status":"ok"}`.

### 3.2 Frontend

En otra terminal, desde la raíz del proyecto:

```powershell
npm install
npm run dev
```

Abre `http://localhost:3000`. Si no existe `.env.local`, la app apunta a
`http://localhost:8000` por defecto.

### 3.3 Acceso demo

| Campo | Valor |
|---|---|
| Correo | `lucia.mendoza@confia-demo.test` |
| Contraseña | `confia2026` |

Son datos ficticios para la demostración. Se cambian en `src/lib/demoSession.ts`
(constante `DEMO_USER`).

---

## 4. Variables de entorno

### 4.1 Backend (`backend/.env`)

El archivo se carga al arrancar si `python-dotenv` está instalado (incluido en
`requirements-dev.txt`). Las variables ya definidas en la terminal tienen prioridad.
**Nunca subas `.env` al repositorio.** La raíz ya lo ignora.

| Variable | Obligatoria | Para qué |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | Sí, para IA | Proyecto de Google Cloud con Vertex AI habilitado |
| `GOOGLE_CLOUD_LOCATION` | No | Región (por defecto `us-central1`) |
| `GEMINI_MODEL` | No | Modelo (por defecto `gemini-2.5-flash`) |
| `CORS_ALLOWED_ORIGINS` | No | Orígenes del frontend, separados por coma (por defecto `http://localhost:3000`) |
| `GMAIL_CLIENT_SECRETS` | Sí, para enviar correos | Ruta al `client_secret.json` del cliente OAuth |
| `GMAIL_REDIRECT_URI` | No | Callback de OAuth (por defecto `http://localhost:8000/gmail/auth/callback`) |
| `GMAIL_TOKEN_PATH` | No | Dónde guardar el token de Gmail (por defecto `storage/secrets/gmail_token.json`) |
| `CONFIA_STORAGE_DIR` | No | Carpeta de almacenamiento local (por defecto `backend/app/storage`) |
| `CONFIA_REQUIRE_AUTH` | No | Ver nota en la sección 8 |

Autenticación de Google para Gemini: `gcloud auth application-default login` y
`gcloud config set project TU_PROYECTO`. Luego `gcloud services enable aiplatform.googleapis.com`.

### 4.2 Frontend (`.env.local`, opcional)

| Variable | Para qué |
|---|---|
| `NEXT_PUBLIC_AI_API_URL` | URL del backend. Por defecto `http://localhost:8000` |
| `NEXT_PUBLIC_USE_FIREBASE` | `true` para usar Firebase (Auth y Firestore). Por defecto `false` |
| `NEXT_PUBLIC_FIREBASE_*` | Configuración pública de Firebase, solo si `NEXT_PUBLIC_USE_FIREBASE=true` |

Las variables `NEXT_PUBLIC_*` se **incrustan al compilar**. Si cambias una, hay que
volver a ejecutar `npm run build` (o reconstruir la imagen de Docker).

---

## 5. Enviar correos con Gmail (una vez)

1. En Google Cloud Console, habilita la **Gmail API**.
2. Crea un cliente OAuth de tipo **Aplicación web**.
3. Agrega como URI de redirección `http://localhost:8000/gmail/auth/callback`.
4. Si la app está en modo de prueba, agrega tu correo como usuario de prueba.
5. Descarga el `client_secret.json` y en `backend/.env` define `GMAIL_CLIENT_SECRETS`.
6. Reinicia el backend. En el modal de outbound pulsa **Vincular cuenta de Gmail**.
7. Google mostrará "app no verificada". Es esperado para una app personal: pulsa
   *Avanzado* → *Ir a ConfIA (no seguro)* y acepta el permiso `gmail.send`.

Notas:
- En modo de prueba, el token caduca cada **7 días**. Si el envío responde
  `gmail_auth_required`, vuelve a vincular la cuenta.
- Prueba primero con **tu propio correo** como destinatario.

---

## 6. Levantar todo con Docker

```powershell
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000/health`

Limitaciones actuales de la versión con Docker:
- Las credenciales de Google (ADC) no están montadas por defecto. Para usar Gemini
  dentro del contenedor, descomenta el volumen de `gcloud` en `docker-compose.yml`
  (en Windows: `${APPDATA}/gcloud`).
- El archivo de credenciales de Gmail (`client_secret.json`) y el token **no** están
  montados. El envío de correos funciona solo en ejecución local con `uvicorn`.
- Los archivos generados (PDF, Markdown, trazas) quedan dentro del contenedor y se
  pierden al borrarlo.

---

## 7. Pruebas

```powershell
# Frontend (desde la raíz)
npm test            # 36 pruebas: API, asesor, sesión, cálculos de Posventa
npx tsc --noEmit    # comprobación de tipos
npm run build       # build de producción (exportación estática en out/)

# Backend (desde backend/, con el venv activo)
python -m pytest -q  # 51 pruebas: motor de ROI, dossier, PDF, outbound, OAuth
```

Las pruebas del backend no llaman a Gemini ni a Gmail: el envío y la IA se sustituyen
por simulaciones. Lo que **no** cubren las pruebas es la interfaz en un navegador y las
llamadas reales a Google.

---

## 8. Qué está simulado o pendiente

### Simulado (intencional, para la demo)
- **Login:** un único usuario ficticio. No hay autenticación real en la pantalla de acceso.
- **Asesor IA del dashboard:** responde con reglas sobre los datos del pipeline. No llama a ningún modelo.
- **Datos:** prospectos, insumos, equipos, capacitación y catálogo son **mock** (`src/data/mockData.ts`).
  Los precios, costos y márgenes del motor de negociación son de prueba (`backend/app/negotiation_params.py`).
- **Persistencia:** la demo no guarda cambios en Firestore. Los estados se mantienen
  en memoria, y las trazas de envío se escriben en `backend/app/storage/output/leads/`.

### Decisiones pendientes (bloquean despliegue real)

1. **Leasing vs. procedimiento.** El procedimiento de oferta v0.3 dice "sin comodato ni
   leasing" (RN-002, RN-044, INV-33). El pedido inicial incluía ajustar un costo de leasing.
   No está implementado. Hay que decidir cuál regla manda.
2. **Registro sanitario de Ozonette.** El procedimiento cita `DB7384E`, pendiente de
   verificar en DIGEMID. El catálogo de la app usa `DM-14820-E`. Confirma el valor
   oficial antes de enviar cualquier dossier o propuesta.
3. **Datos mock → datos reales.** Costo de adquisición (4,200 USD en el mock), precios de
   lista, garantía final y ficha técnica deben venir del dueño y del fabricante.
4. **Textos legales.** El descargo (T-01) y la firma (T-02) están como borrador. Los
   aprueba el asesor. La firma aparece como `[pendiente]` en las propuestas.
5. **Consentimiento informado de Ozonette.** El texto usado es el de autohemoterapia
   mayor (AHTm), tomado del mock. Confirma si aplica a infiltración.
6. **Logo corporativo.** Falta `backend/app/storage/input/assets/logo_confia.png`. Sin él,
   los documentos salen sin logotipo.

### Seguridad (antes de exponer el backend)

7. **Autenticación del backend.** `auth_required()` en `backend/app/main.py` devuelve
   `False` fijo, así que la variable `CONFIA_REQUIRE_AUTH` no tiene efecto. Mientras
   esto sea así, cualquiera con la URL puede generar documentos y gastar cuota de Gemini
   y enviar correos desde la cuenta vinculada. **Restaura la lectura de la variable antes
   de publicar.**
8. **Autorización por rol.** Hoy cualquier usuario autenticado puede leer cualquier
   prospecto. Falta el modelo de roles (dueño, asesor, médico) en el backend.
9. **Token de Gmail en texto plano** dentro de `storage/secrets/`. Para producción usa
   un gestor de secretos.

### Técnico
10. **`.dockerignore` de la raíz** contiene reglas de otro proyecto (`data`, `.venv`, `docs`,
    `tests`) y no excluye `node_modules`, `.next` ni `out`. Reemplázalo por el correcto
    antes de construir la imagen del frontend.
11. **Modelo ROI antiguo.** El endpoint `/generate/roi` y el campo `roiProposal` usan un
    modelo que no corresponde al procedimiento. Conviene retirarlos.
12. **"Aprobar y enviar" en ROI** todavía guarda el borrador antiguo, no la propuesta
    versionada del simulador.
13. **Contador de versiones compartido.** El dossier y la propuesta comparten `v{n}` por
    prospecto.
14. **Modo oscuro** no está validado para los gráficos. Solo se probó la paleta clara.
15. **Dashboard y tutorial** no se han revisado en navegador real. Revísalos antes de la
    presentación.

---

## 9. Despliegue (propuesta)

Estas son las piezas. Los nombres y valores finales los defines tú.

### Backend → Google Cloud Run
1. Construye la imagen desde `backend/` (ya tiene `Dockerfile`).
2. Define las variables de la sección 4.1 como variables del servicio o en Secret Manager.
   **No subas `.env`.**
3. Asigna una cuenta de servicio con el rol `roles/aiplatform.user` para Gemini.
4. Registra la URL de Cloud Run como URI de redirección de OAuth
   (`https://<servicio>/gmail/auth/callback`) y actualiza `GMAIL_REDIRECT_URI`.
5. Configura `CORS_ALLOWED_ORIGINS` con la URL del frontend.
6. Recuerda: el disco de Cloud Run es **efímero**. Los PDF y las trazas se pierden al
   reiniciar. Para producción hace falta Cloud Storage o Firestore.

### Frontend → Vercel (o cualquier hosting estático)
1. El proyecto exporta un sitio estático (`output: "export"`). Puedes servir `out/`.
2. Define `NEXT_PUBLIC_AI_API_URL` con la URL de Cloud Run **antes del build**.
   Si falta, la app apuntará a `localhost` desde el navegador de cada usuario.
3. Si usas Firebase, define `NEXT_PUBLIC_USE_FIREBASE=true` y las variables `NEXT_PUBLIC_FIREBASE_*`.

### Orden recomendado
1. Resolver las decisiones 1 a 6 y los puntos de seguridad 7 y 8.
2. Desplegar el backend y comprobar `/health`.
3. Vincular Gmail desde la URL de producción y probar con un correo propio.
4. Desplegar el frontend con `NEXT_PUBLIC_AI_API_URL` apuntando al backend.
5. Revisar el flujo completo en navegador real (login, Kanban, dashboard, ROI, dossier,
   outbound, posventa y tutorial).

---

## 10. Estructura del proyecto (resumen)

```
src/                 Frontend (Next.js, App Router, exportación estática)
  app/page.tsx       Pantalla principal del CRM
  components/        Modales, simulador ROI, outbound, dashboards, tutorial, cuenta
  lib/               Cliente de API, motor de asesor, sesión demo, pasos del tutorial
  data/mockData.ts   Datos de demostración
backend/
  app/main.py        Endpoints FastAPI
  app/roi_engine.py  Cálculo de oferta y contraoferta
  app/proforma.py    Propuesta comercial en PDF
  app/documents.py   Dossier regulatorio (Markdown y PDF)
  app/gmail_service.py  Envío por Gmail con OAuth
  app/storage/       Plantillas, logo y salidas versionadas
  tests/             Pruebas del backend
handsoff/            Fuente de verdad del procedimiento de contraofertas (Excel y Word)
docker-compose.yml   Levantar frontend y backend con Docker
```
