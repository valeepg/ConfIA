# Copiloto de outbound (borradores con IA)

> Cubre **RF-10** (agente redactor del mensaje de contacto) y el guardarraíl **RNF-06**
> (estructura rígida anti-alucinaciones). Es territorio del **Módulo 4**; lo construyó el
> owner del Módulo 1 porque el contrato de prospectos ya estaba listo y el copiloto es lo
> único que le falta para tener sentido.
> Estado: funcionando y probado sin red. **No envía nada, por diseño.**

---

## 1. Qué problema resuelve de verdad

El documento maestro pide que la IA redacte el contacto personalizado. El riesgo que el
mismo documento nombra es la alucinación: *"un número de Registro Sanitario o un precio
inventado destruiría la credibilidad del dueño"*.

La forma ingenua de evitarlo es **pedirle** al modelo que no invente. Eso no es una
garantía, es un deseo. Acá la garantía está en la arquitectura:

| Riesgo | Cómo se evita |
|---|---|
| El modelo escribe texto comercial o regulatorio | **No lo escribe.** El texto del dueño vive en `templates/outreach-oaas.md` y se ensambla **en código**. El modelo solo llena ranuras |
| El modelo inventa una cifra | Un verificador compara cada número del borrador contra los datos reales. Si no está, el borrador se **rechaza** |
| El modelo promete cumplimiento normativo | Vocabulario vigilado (`registro sanitario`, `digemid`, `dosis`, `concentracion`…): solo puede usarlo si la plantilla del dueño ya lo usa |
| Un borrador con hallazgos se aprueba igual | `approve()` **falla** si hay hallazgos. El humano es parte del circuito, no un sello |
| Alguien automatiza el envío | No hay ninguna función de envío, y un test lo verifica |

## 2. El flujo

```
Prospect real (del scraper)          templates/outreach-oaas.md  ← editable por el dueño
        │                                       │
        └────────► datos que el modelo puede ver ┘
                            │
                   LiteLLM (proveedor/modelo configurable)
                            │  JSON estricto contra OutreachDraft
                            ▼
                    verificación ──► ¿inventó algo? ──► se rechaza
                            │
                            ▼
        ensamblado en código (la plantilla se copia igual, byte a byte)
                            │
                            ▼
     drafts.json  ·  status = pending_approval  ·  el dueño aprueba o rechaza
                            │
                            ▼
                  (el envío NO existe en este módulo)
```

Lo que el modelo puede producir son **cuatro ranuras**: `subject`, `greeting`, `opening` y
hasta 4 `talking_points`. Nada más. Los párrafos comerciales y regulatorios son del dueño.

## 3. Cómo se corre

```bash
# Escribe data/out/drafts.json con los borradores de los N mejores prospectos
uv run python -m scraper --limit 20 --draft-limit 5

# Elegir modelo y plantilla
uv run python -m scraper --draft-limit 5 --llm-model groq/llama-3.3-70b-versatile
uv run python -m scraper --draft-limit 5 --template templates/otra-plantilla.md
```

### Desde el contenedor

```bash
podman build -t confia2-scraper:dev .
podman run --rm --env-file .env -v ./data:/app/data:Z --userns=keep-id \
  confia2-scraper:dev --limit 5 --draft-limit 2
```

La imagen copia `scraper/` **y `templates/`**, así que la plantilla que edita el dueño viaja
con el contenedor. La clave entra por `--env-file`, **nunca adentro de la imagen**.
`tests/test_container.py` falla si alguna de esas dos carpetas deja de copiarse o si el
`.dockerignore` deja de excluir `.env`.

**El proveedor es configuración, no código.** LiteLLM direcciona cualquiera como
`proveedor/modelo`, así que el "Gemini Flash" del documento es un valor por defecto, no una
atadura. Tres formas de configurarlo, en `.env`:

```bash
# A) La API de NaN (OpenAI-compatible). Basta con su clave: el resto se deduce.
NAN_API_KEY=sk-tu_clave

# B) Gemini, el que dice el documento
GEMINI_API_KEY=tu_clave

# C) Cualquier otro proveedor
CONFIA2_LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=tu_clave
```

**Cómo se resuelve, en orden** (así nadie tiene que adivinar): argumento de la CLI, después
las variables `CONFIA2_LLM_MODEL` / `CONFIA2_LLM_API_BASE` / `CONFIA2_LLM_API_KEY_VAR`,
después la API de NaN cuando su clave es la única presente, y si no el modelo del documento.

Un `api_base` propio (el caso de NaN, documentado en `https://api.nan.builders/v1`) se
prefija con `openai/`, que es como LiteLLM decide enrutar a un endpoint compatible. Ese
prefijo se agrega solo, para que el error no aparezca como un fallo opaco del proveedor.

**Si el proveedor no soporta esquemas estrictos, el adapter degrada solo.** Prueba primero
`response_format` con el esquema, después modo JSON, y por último texto plano. Lo aprendido
se recuerda por modelo dentro del proceso, así que el descubrimiento se paga una vez. No se
pierde ninguna garantía: **la garantía es la validación local con Pydantic y el verificador**,
no la imposición del esquema en el servidor.

Ese aprendizaje es **por proceso**, así que una corrida nueva volvía a pagar el intento
rechazado. Por eso el formato se puede **fijar**:

```bash
# auto (por defecto) descubre; los otros se usan solos, sin degradar
CONFIA2_LLM_RESPONSE_FORMAT=json_object
```

Con el endpoint de NaN el valor por defecto es `json_object`, porque eso es lo que se midió
(ver §6). Un formato fijado es **una decisión, no una sugerencia**: si falla, falla fuerte en
vez de degradar en silencio y dejarte creyendo que usaste el esquema estricto.

Si falta la clave, el comando **sale con código 1** y dice qué variable falta. Verificado:

```
error: no se pudo redactar con el modelo 'gemini/gemini-2.0-flash':
litellm.APIConnectionError: Missing Gemini API key. Set the GEMINI_API_KEY or GOOGLE_API_KEY ...
```

## 4. La plantilla la edita el dueño, no un programador

`templates/outreach-oaas.md` es un Markdown con ranuras. Los corchetes marcan lo que **el
dueño** completa a mano antes de que el mensaje salga (la firma, o cualquier dato del que
todavía no tenemos evidencia). El sistema los lista en `missing_human_data` para que la
pantalla de aprobación los muestre.

Confirmado con el convenio del documento maestro: lo que falta va entre corchetes y **no se
inventa**.

## 5. Verificación

```bash
uv run pytest tests/test_copilot.py -q     # 27 tests, sin red
```

Los tests que importan son los negativos: que **rechace** un borrador con `2500 soles`, con
`272 clinicas`, con `Registro Sanitario vigente` o con `concentracion de 30 ug/ml`.

Como la implementación se escribió antes que los tests, se hizo además una **prueba de
mutación** para no confiar en tests que pasan de casualidad:

| Sabotaje | Resultado |
|---|---|
| El chequeo de cantidades devuelve vacío | **5 tests se caen** |
| El vocabulario regulatorio deja de vigilarse | **2 tests se caen** |
| Restaurado | 27 verdes |

El adapter de LiteLLM se prueba con el proveedor **simulado**: se verifica que el esquema
viaje como `response_format` y que la respuesta se valide contra el modelo Pydantic. Lo
único no verificable sin clave es el comportamiento del proveedor real.

## 6. Verificación en vivo con la API de NaN (13-10-2026)

```
$ uv run python -m scraper --limit 5 --draft-limit 2
redactando 2 borradores con openai/deepseek-v4-flash via https://api.nan.builders/v1 (clave presente)
escrito data/out/drafts.json con 2 borradores (0 con hallazgos, todos pendientes de aprobacion)
```

| Qué se midió | Resultado |
|---|---|
| Modelos que ve la clave (`GET /v1/models`) | 13, incluido `deepseek-v4-flash` |
| Formato que aceptó el proveedor | **Rechazó el esquema estricto y degradó a modo JSON** (intento 1). La degradación funcionó y quedó memorizada por modelo |
| Borradores | 2, **0 con hallazgos** |
| Datos faltantes detectados | `[FIRMA DEL DUEÑO]`, correctamente listado para que lo complete el dueño |
| Capacidad desconocida | El modelo escribió *"No contamos con el dato de médicos registrados, por lo que una visita técnica permitiría conocer su equipo"* **en vez de inventar un número**. Ese era exactamente el objetivo del diseño |
| Párrafo comercial del dueño | Copiado byte a byte en los dos mensajes |

**Nada se envió.** Los dos quedaron en `pending_approval`.

> **Corregido después de medir:** ese rechazo se pagaba una vez **por proceso**, así que cada
> corrida nueva gastaba un request en un intento que ya sabíamos que iba a fallar, y dejaba
> en el log un banner de LiteLLM que parece un problema del proveedor y no lo es. El formato
> de respuesta ahora se puede fijar y, con el endpoint de NaN, el valor por defecto es
> `json_object`. Verificado con un test: un formato fijado hace **una sola** llamada y no
> visita los otros intentos.

## 7. La regla del `.env`: sin espacios alrededor del `=`

Medido: `NAN_API_KEY =sk-...` (con un espacio antes del `=`) lo tolera `python-dotenv`, así que
la aplicación funciona, pero **`podman --env-file` no**: le pasa al contenedor el nombre con el
espacio, `"NAN_API_KEY "`, y adentro la variable queda invisible. El síntoma engaña: parece
que falta la clave cuando en realidad está mal escrita.

Verificado con valores ficticios, dentro del contenedor:

| `.env` | El contenedor ve | Resultado |
|---|---|---|
| `NAN_API_KEY =valor` | `"NAN_API_KEY "` | **no la encuentra** |
| `NAN_API_KEY=valor` | `"NAN_API_KEY"` | la encuentra y resuelve el endpoint |

Por eso el resolver ahora **nombra la variable con espacio** cuando no encuentra la clave, en
vez de limitarse a decir que falta. Para corregir un `.env` ya escrito sin tocar los valores
(probado sobre un archivo ficticio, incluido un valor con `=` adentro):

```bash
sed -i -E 's/^([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=/\1=/; s/^([A-Za-z_][A-Za-z0-9_]*)=[[:space:]]+/\1=/' .env
```

> La imagen del contenedor **hay que reconstruirla** cuando cambia el código o las
dependencias: la que existía antes del copiloto no tenía `litellm`. Verificado tras
reconstruir: `import litellm` funciona adentro.

## 8. Límites conocidos y pendientes

| Tema | Estado |
|---|---|
| **RF-11 dossier regulatorio y ROI** | **No hecho.** Necesita los textos regulatorios reales del dueño y los precios. La misma arquitectura lo soporta: plantilla + ranuras + verificación |
| Persistencia en Firestore (RF-09) | Pendiente de que se ratifique el contrato v0 |
| Pantalla de aprobación (RF-05, Módulo 2) | `drafts.json` ya tiene todo lo que la interfaz necesita: hallazgos, datos faltantes, estado y aprobador |
| `litellm` como dependencia | Trae ~30 paquetes (tiktoken, tokenizers, openai…). Engorda la imagen del contenedor: hay que medirlo antes de desplegar |
| Envío | **No existe y no debe existir acá.** El dueño envía, un mensaje por vez, como pide el documento |
