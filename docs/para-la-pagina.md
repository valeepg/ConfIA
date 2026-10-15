# Para la página: qué JSON consume el frontend

> Módulo 2. Esto es lo que recibe la web, con las tres formas que traen los datos y las trampas
> que hay que respetar para no mostrar información falsa.

---

## 1. Los archivos

| Archivo | Registros | Quién lo genera | Para qué lo usa la página |
|---|---|---|---|
| `data/out/prospect_mock.json` | **2.459** | `uv run python -m scraper` | La lista y las tarjetas de clínicas del padrón |
| `data/out/segmento_places.json` | **829** | `uv run python -m scraper --segment-places` | La lista de fisioterapia, que es el foco del negocio |
| `data/out/drafts.json` | los que pidas | `--draft-limit N` | La **pantalla de aprobación**: el borrador y sus hallazgos |
| `data/out/hoja_de_llamados.md` | 30 | `--call-sheet 30` | Una vista imprimible; **no** es para parsear |

**Mientras maquetás**, usá `docs/prospect_mock.ejemplo.json` y `docs/drafts.ejemplo.json`: son
recortes **reales**, con las tres formas y dos borradores de verdad.

## 2. Tres formas, y hay que cubrir las tres

El archivo del padrón y el del segmento **no tienen la misma forma**. Un componente que solo
entienda la primera se rompe con la segunda, que es la más importante:

| | `origin: "renipress"` | `origin: "places"` |
|---|---|---|
| `score` | objeto con `total`, `level`, `components`, `measured_weight` | **`null`** |
| `google` | **`null`** | objeto con categoría, rating, reseñas, sitio, cadena |
| `category`, `classification`, `institution` | del padrón | **`null`** |
| `capacity` | puede tener datos (10 %) | siempre vacío, `period: null` |
| `location.ubigeo` | del padrón | **`null`** |
| `location.coordinates` | 85 % | casi siempre |
| `contact.phone` / `address` | 99,9 % / 100 % | del resultado de búsqueda |

**Y los dos orígenes no se solapan: cero clínicas del segmento están en el padrón.** No es una
lista filtrada de la otra, son dos segmentos. La página tiene que poder mostrarlos juntos **y**
distinguirlos.

## 3. Las cuatro trampas que convertirían la página en una mentira

| Campo | Cómo **no** mostrarlo |
|---|---|
| `capacity.doctors_total: 0` con `capacity.period: null` | **No es "0 médicos"**: es "no está en el registro". Si la tarjeta dice "0 médicos", miente. Usá el tag `no-capacity-data` o el `period` para decidir si mostrás el número |
| `score: null` | No es 0 puntos. Es "el puntaje del padrón no aplica a un resultado de búsqueda". No lo ordenes como si fuera el peor |
| `ozone_therapy.checked: false` | **No es "no ofrece ozono"**: es "no se determinó". Vale `false` en los 2.459 |
| `score.measured_weight` | Distingue un 100 real de un 100 sobre evidencia incompleta. Si mostrás el puntaje, mostralo |

## 4. Qué mostrar con cada campo

**Tarjeta de clínica (padrón):** `name`, `location.district`, `category`, `contact.phone`,
`score.level`, y `capacity.doctors_total` **solo si `capacity.period` no es `null`**.

**Tarjeta de clínica (segmento):** `name`, `location.district`, `google.category`,
`google.rating` con `google.rating_count`, `google.website`, y `google.chain_sites` si es > 1.

**Filtros que los datos sostienen de verdad:**

| Filtro | Campo |
|---|---|
| Por departamento, provincia o distrito | `location.*` (25 departamentos, 118 provincias, 259 distritos) |
| Por segmento | `origin`, o el tag `physiotherapy-segment` |
| Por especialidad | `google.category` |
| Por actividad de pacientes | `google.reviews_band` (`alta`/`media`/`baja`/`sin datos`) |
| Por calidad percibida | `google.rating_band` |
| Por prioridad comercial | `score.level` **y** `score.measured_weight` |
| Por cadena | tag `chain` + `google.chain_sites` |
| Por capacidad sin dato | tag `no-capacity-data` |

## 5. La pantalla de aprobación (`drafts.json`)

Cada elemento es un borrador listo para que el dueño lo apruebe o lo rechace:

```jsonc
{
  "prospect_id": "places:16002912900950143659",
  "template": "oaas-v1",
  "model": "openai/deepseek-v4-flash",
  "status": "pending_approval",          // pending_approval | approved | rejected
  "approver": null,
  "violations": [],                      // si NO está vacío, NO se puede aprobar
  "missing_human_data": ["[FIRMA DEL DUEÑO]"],
  "subject": "Ozonoterapia en comodato para Artrauma",
  "message": "…el texto completo, listo para leer…"
}
```

Dos reglas que la interfaz tiene que hacer cumplir, porque están en el diseño del sistema:

1. **Si `violations` no está vacío, el botón de aprobar tiene que estar deshabilitado.** El
   verificador encontró un dato inventado o una promesa que el dueño no autorizó.
2. **`missing_human_data` son los corchetes que el dueño completa a mano** (hoy, la firma). La
   pantalla los tiene que mostrar: si se envían sin completar, sale un mensaje con `[FIRMA DEL
   DUEÑO]` adentro.

**La página no envía nada.** El envío es del dueño, un mensaje por vez, y no existe código para
hacerlo automático.

## 6. Para tener datos reales mientras desarrollás

```bash
uv sync
uv run python -m scraper --segment-places --call-sheet 30 --draft-limit 5
```

Son unos minutos la primera vez; después es rápido porque las descargas y las búsquedas quedan
cacheadas en `data/`. Los archivos salen en `data/out/`.

Cuando el despliegue esté hecho, la misma información vive en **Firestore**, en dos colecciones:
`prospects` (el contrato, tal cual estos JSON) y `leads` (los mismos datos con los nombres de la
pantalla, que es la que conviene leer — ver la sección 7).

---

## 7. La forma que lee la pantalla: la colección `leads`

El mock del frontend y el contrato del scraper **no usan los mismos nombres**: el mock usa `lead-1`,
`directorMedico`, `outboundDraft` y `status`; el contrato usa el código de la IPRESS,
`pipeline_stage` y `origin`. Ninguna de las dos formas está mal: una está pensada para la pantalla y
la otra para el dato.

La ingesta escribe **cuatro** colecciones. Dos son el contrato (`prospects` y `proposals`, tal como
sale del scraper) y dos son la misma información con los nombres que ya usa el frontend (`leads` y
`approvals`). La proyección sale del mismo prospecto en cada corrida, así que no hay nada que
sincronizar a mano ni dos verdades que se puedan separar.

| Colección | Qué es | Quién la lee |
|---|---|---|
| `prospects` | El contrato, con los dos orígenes | El CRM y la API |
| `proposals` | Los borradores del copiloto | El CRM |
| **`leads`** | Los prospectos con los nombres de la pantalla | **La página** |
| **`approvals`** | Los borradores con los nombres de la pantalla de aprobación | **La página** |

**Lo único que hay que cambiar en la página son dos líneas:**

```js
const q = query(collection(db, "leads"));       // antes: "prospects"    -> la lista y las tarjetas
const r = query(collection(db, "approvals"));   // antes: "proposals"    -> la pantalla de aprobación
```

Si al leer te da «permiso denegado», revisá que las dos colecciones estén en `firestore.rules`: el
`match /{document=**}` del final cierra todo lo que no esté nombrado, y el error se parece a «la base
está vacía». Ya están las dos.

Y antes de la demo, **borrar los ocho documentos de prueba** (`lead-1` … `lead-8`) que hoy quedaron
en `prospects`: son el mock, no datos.

### Qué campo sale de dónde

| En la pantalla | De dónde sale | Ojo |
|---|---|---|
| `id` | `ipress_code`, o el `cid` de Places | Antes eran `lead-1`; ahora son los identificadores reales |
| `name` | `name` | |
| `district`, `department` | `location.*` | |
| `phone`, `address` | `contact.*` | **`phone` no estaba en el mock y es el campo que más sirve** |
| `phoneValid` | `contact.phone_valid` | Para no llamar a un número dudoso como si estuviera verificado |
| `specialty` | `google.category`, o el tipo de establecimiento del padrón | Los dos son cosas distintas: ver abajo |
| `directorMedico`, `doctorSpecialty` | **`null`, siempre** | Ningún dato público los trae |
| `status` | `pipeline_stage`, traducido | Se escribe **solo al crear** |
| `statusNote` | una línea armada con datos | Se escribe **solo al crear**: es una nota que podés editar |
| `aiSuggestion` | la misma línea, refrescada en cada corrida | No afirma nada sobre la competencia |
| `score`, `scoreLevel` | `score.total`, `score.level` | `null` en el segmento |
| `rating`, `reviews`, `website` | `google.*` | `null` en el padrón |
| `segment` | `"padron"`, `"fisioterapia"` o `"busqueda"` | **Tres** valores, no dos: `busqueda` son los resultados de Places que **no** entraron al segmento de fisioterapia — no vienen del registro de SUSALUD |
| `tags` | `tags` | |
| `stale` | `false` si esta corrida la vio | Ver abajo: las clínicas que no volvieron a aparecer |
| `hasAiDraft`, `outboundDraft` | de `proposals` | |
| `draftApproved` | **la decisión del dueño** | Se escribe **solo al crear**: la aprobación vive en `approvals`, y recalcularla en cada corrida la borraría |
| `telemetryActivity` | **no lo escribimos** | Es del Módulo 2/3: tratalo como opcional |

### Las tres cosas que la pantalla no va a poder mostrar

1. **`directorMedico` va vacío.** RENIPRESS publica el establecimiento, no a su gente, y ninguna de
   las fuentes trae el nombre de una persona. El mock lo tenía inventado. Una tarjeta con ese campo
   vacío es honesta; un nombre inventado en la demo de un cliente de salud, no.
2. **`suggestedChannel` dice `Teléfono`, no `Email`.** No hay ni un correo en los 3.288 prospectos
   (ver `dossier-evidencia.md`). El canal que los datos sostienen es el teléfono.
3. **`specialty` no siempre es una especialidad.** En el segmento es la categoría real de Google
   (`Fisioterapeuta`, `Clínica de dolor`); en el padrón cae al **tipo de establecimiento**
   (`CENTROS DE SALUD CON CAMAS DE INTERNAMIENTO`). Si la pantalla los muestra en la misma columna,
   conviene un color o un sufijo distinto, para no comparar dos cosas distintas.

### Las clínicas que no volvieron a aparecer

El segmento de Places **no devuelve el mismo conjunto en cada corrida** con la misma consulta:
medido, 829 un día, 791 al siguiente y 774 después. Como la ingesta solo hace *upsert*, las clínicas
que una corrida vio y la siguiente no **se quedan en la base**, marcadas con `stale: true`.

**No son basura y no se borran**: aparecieron de verdad, y borrar en un CRM es irreversible —nadie
sabe si el dueño ya llamó o anotó algo sobre esa clínica. La pantalla puede mostrarlas atenuadas, o
filtrarlas. Si filtrás:

```js
where("stale", "==", false)   // sí
where("stale", "!=", true)    // NO: en Firestore, `!=` excluye los documentos sin el campo
```

Esa trampa vale para **cualquier** filtro de la página: en Firestore, `==` y `!=` solo ven documentos
que tienen el campo. Un documento viejo, sin `stale`, no aparece en ninguna de las dos consultas. Si
agregás un filtro, contá con la migración de los documentos que ya están.

### El estado de la venta es de la persona, no de la ingesta

`status` y `statusNote` se escriben **una sola vez, al crear el lead**. Si el dueño mueve una tarjeta
a "contactado" y después corre el job otra vez, la ingesta **no lo devuelve a "descubierto"**. Es la
misma regla que ya rige para `manual_tags` en `prospects`.

### La pantalla de aprobación: la colección `approvals`

El mock guardaba los borradores con otra forma: `aiContent` como **objeto**, `type`, `createdBy`, y el
identificador `{id}-outbound`. Con la forma del contrato, el componente no encontraba **ninguno** de
los diez borradores reales: la pantalla de aprobación es la parte que el dueño usa todos los días, así
que es la que más importa que funcione.

| En la pantalla | De dónde sale |
|---|---|
| `id` | `{prospect_id}-outbound` |
| `prospectId` | `prospect_id`, y ya apunta al ID real del lead de `leads` |
| `type` | `"outbound"` |
| `status` | `status` — **ya se llama igual** (`pending_approval`, `approved`, `rejected`) |
| `aiContent.subject` | `subject` |
| `aiContent.body` | `message`, el texto completo listo para leer |
| `aiContent.recipientRole` | `"Dirección médica"` |
| `aiContent.recipientName` | **`null`** — el mock ponía «Dra. Valdivia» |
| `createdBy` | `"confia2-ingesta"` |
| `hasViolations`, `violations` | `violations` — si `hasViolations` es `true`, **deshabilitá aprobar** |
| `missingHumanData` | `missing_human_data` |
| `template`, `model` | los mismos nombres |
| `approvedBy`, `approvedAt` | **los escribe la página** cuando el dueño aprueba |

Dos reglas que se mantienen igual: **si `violations` no está vacío, aprobar tiene que estar
bloqueado**, y `approvedBy` **nunca lo escribe la ingesta**: si el dueño ya aprobó, una corrida nueva
regenera el texto pero **no revierte la aprobación**.
