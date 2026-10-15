# Módulo 1 — Extracción, ingesta y normalización (scraper)

> Owner: Data & Security Engineer / Backend Scraper.
> Requerimientos cubiertos: **RF-01** (extracción) y **RF-02** (normalización a JSON).
> Estado: funcionando en local contra las fuentes vivas. Pendiente: contenedor y despliegue.

Este documento describe **de dónde salen los datos**, **qué contrato JSON se emite**
y **cómo se corre**. Es la referencia que leen los otros tres módulos.

---

## 1. Decisión de arquitectura: no todo se scrapea

La investigación previa a la implementación cambió el plantón inicial. De las fuentes
del requerimiento, **una ya se publica como dato abierto descargable** y otra tiene
protección anti-scraping explícita:

| Fuente | Cómo se accede realmente | ¿Scraping? | Qué aporta | Qué **no** aporta |
|---|---|---|---|---|
| **RENIPRESS** (SUSALUD) | CSV oficial de 19,8 MB vía portal de datos abiertos. La URL se resuelve con el **CKAN API** porque el nombre del archivo cambia en cada publicación (`RENIPRESS_2026_v7.csv`) | No | Identidad, categoría, clasificación, ubicación, teléfono y coordenadas de las 36.128 IPRESS del país | RUC, email y nombre del director médico |
| **Consulta A** (SUSALUD) | CSV oficial (~8,6 MB) vía CKAN API | No | Capacidad instalada por IPRESS: médicos, consultorios, camas, enfermeras, ambulancias | Nombres de los profesionales |
| **Consulta G** (SUSALUD) | CSV oficial (~226 MB por mes) vía CKAN API | No | 7.457 procedimientos codificados por IPRESS: laboratorio, consulta externa, consejerías | **No sirve para detectar ozonoterapia**: la terapia no está codificada en el catálogo. Ver §2.3 |
| **CMP "Conoce a tu Médico"** | SPA en React: el HTML llega vacío. Su API interna (`/api/colegiados/search`) exige sesión autenticada, cifra el payload con una clave embebida en el bundle y aplica *cooldown* de 30 s por detalle | **Sí, y no masivo** | Colegiatura y especialidad de un médico puntual | No es una fuente de volumen: su diseño limita las consultas a propósito |
| **Padrones municipales de licencias** | El portal nacional (`datosabiertos.gob.pe`) responde HTTP 418 a clientes que no son navegador | Sí | Licencia de funcionamiento | Sin verificar |

**Regla que queda para el equipo:** antes de escribir selectores, resolver si la fuente
publica un dataset o un API. El 90 % de este módulo es descarga + normalización, no scraping.

### Cuándo sí hace falta un LLM (y cuándo no)

Ninguna de las tres fuentes implementadas usa un modelo de lenguaje, y es deliberado:
los campos viven en una **posición fija** de un CSV publicado.

- **Selector o posición fija** → extracción determinista, gratis, repetible. Sin LLM.
- **Posición variable, texto libre o PDF sucio** → LLM con esquema estricto (Pydantic/JSON mode), cacheado por hash de contenido.
- **Nunca** un LLM para paginar, navegar o decidir qué visitar.

El LLM entra en este proyecto en el módulo de outbound (RF-06, RF-10), **aguas abajo** de este.

---

## 2. Pipeline

```
          CKAN API (datos.susalud.gob.pe)
                    │  resuelve la URL vigente
                    ▼
   RENIPRESS ──► filtrar perfil objetivo ─────────┐
   Consulta A ─► capacidad por CO_IPRESS ─────────┤
   Consulta G ─► procedimientos por IPRESS (opt-in; señal hoy vacía) ─┤
                                                  ▼
                                    scoring determinista (0-100)
                                                  ▼
                                     data/out/prospect_mock.json
```

La unión entre las tres tablas es el **código único de IPRESS** (`COD_IPRESS` en
RENIPRESS, `CO_IPRESS` en las Consultas A y G). Se usa como clave de deduplicación.

### Filtro de perfil objetivo

`RENIPRESS` se filtra por tres columnas y nada más: `ESTADO = ACTIVO`,
`INSTITUCION = PRIVADO` y `CATEGORIA ∈ {I-3, I-4}`.

Medido sobre la publicación vigente (corte 30-09-2026):

| Métrica | Valor |
|---|---|
| IPRESS registradas | 36.128 |
| ... con `ESTADO = ACTIVO` | 26.972 |
| ... además `PRIVADO` | 25.230 en total, 2.459 en el perfil I-3/I-4 |
| Prospectos emitidos | **2.459** |
| Con teléfono válido | 2.457 (99,9 %) |
| Lima | 898 (37 %) |

### Cobertura real de la Consulta A (limitación medida, no supuesta)

La Consulta A **no es un padrón de IPRESS: es un reporte mensual de actividad**, y solo
incluye a los establecimientos que reportan producción. Medición sobre la publicación
2026 (8 meses, 47.624 filas):

| Métrica | Valor |
|---|---|
| Establecimientos distintos en la Consulta A | 5.916 |
| De ellos, `SECTOR = PRIVADO` | ~584 |
| Cruce con nuestros 2.459 objetivos | **248 (10 %)** |
| Cruce sumando también la publicación 2025 | 255 (la unión aporta 7 casos) |

La ausencia se concentra en los establecimientos chicos: de los objetivos con
clasificación `POLICLINICOS`, 85 tienen dato de capacidad y 989 no.

**Consecuencias que el equipo debe conocer:**

1. El 90 % de los prospectos sale con `capacity.period = null`, ceros y el tag
   `no-capacity-data`. Es un **dato faltante, no un cero real**.
2. El puntaje trata ese faltante como 0 puntos en el componente `capacity` (techo 30).
   Por eso solo 125 de 2.459 prospectos alcanzan `high`: para llegar a 70 sin esos 30
   puntos hay que ser I-4 especializado en Lima y con contacto válido.
3. El sesgo resultante **favorece a las clínicas que reportan a SUSALUD**, que son
   las más formalizadas. Para un ICP de clínicas del dolor y traumatología con
   infraestructura real no es un sesgo absurdo, pero es un sesgo y está sin etiquetar
   en el puntaje: solo el tag lo delata.
4. Los pesos del scoring están calibrados contra una fuente que cubre el 10 % de la
   población objetivo. **La recalibración es la decisión abierta más importante del módulo.**

### 2.3 La ozonoterapia no está codificada en la Consulta G (señal vacía, verificada)

El diseño original asumía que la Consulta G permitiría filtrar "IPRESS que **ya** hacen
ozonoterapia". La verificación sobre la publicación 2026-08 lo desmiente:

| Verificación sobre el catálogo nacional | Resultado |
|---|---|
| Procedimientos distintos | 7.457 |
| Filas cuyo `PROCEDIMIENTO` contiene `ozon` / `ozonoterap` / `bioxidat` / `aht` | **0** |
| Filas cuyo `DES_DESCRIPCION` contiene `ozon` | **0** |
| `oxigen` (oxigenoterapia, otra cosa) | 218 |
| `hemoterapia` (banco de sangre, no autohemoterapia con ozono) | 253 |

El catálogo son pruebas de laboratorio, consulta externa y consejerías. **La ozonoterapia
no existe como procedimiento codificado**, así que la Consulta G no puede responder la
pregunta ni en positivo ni en negativo.

Por eso `detect_ozone_therapy` devuelve `signal_available`.

- `signal_available = true` → hay vocabulario de ozono en el catálogo: `checked` y
  `performs` sí distinguen "la hace" de "confirmado que no la hace".
- `signal_available = false` → ninguna IPRESS se marca `checked`. Emitir
  `performs: false` se leería como *"confirmado que no la hace"* cuando en realidad es
  *"esta fuente no sabe expresarlo"*.

El pipeline avisa por consola, expone el conteo `ozone_signal_available` y deja que el
contrato siga diciendo la verdad: sin dato.

**Consecuencia para el negocio:** el filtro "IPRESS sin ozonoterapia" del documento maestro
**no es derivable de los datos abiertos de SUSALUD**. Alternativas, en orden de esfuerzo:

1. Tratarlo como una incógnita a resolver en la llamada comercial (es lo que ocurre hoy).
2. Enriquecimiento puntual: buscar "ozono" en la web o la ficha de Google de cada clínica
   ya filtrada (2.459 consultas dirigidas, no un crawl abierto).
3. Cruzar con médicos formados en ozonoterapia (ASMPO3, posgrado USIL) como señal indirecta.

### 2.4 Enriquecimiento web: validación en muestra antes de gastar 2.459 consultas

El 13-10 se decidió resolver la incógnita buscando "ozono" por clínica. Antes de gastar
presupuesto se probó la premisa sobre **3 clínicas reales de la propia lista**. Resultado:
**0 de 3 produjo evidencia confiable**, con tres patrones de falla distintos.

| Clínica de la lista | Qué devolvió la búsqueda | Falla |
|---|---|---|
| CENTRO MEDICO ESPECIALIZADO SAN FELIPE (Lurigancho, Lima) | Una clínica **homónima en Huancayo, Junín**, con sitio propio. También una tesis sobre la de Chosica | **Colisión de nombres entre departamentos.** Atribuir esos datos a Lima es inventar |
| CEFRA (San Borja, Lima) | Es un centro de **fertilidad** (cefraperu.com). Pero el buscador devolvió *"Unidad de Ozono – Centro Médico San Borja"*, **otra clínica del mismo distrito** que sí ofrece ozono | **Falso positivo grave:** una clínica vecina contamina el resultado |
| POLICLÍNICO NUESTRA SEÑORA DE LA PAZ (Comas, Lima) | LinkedIn de la empresa, listado de la avenida, y **PERIMEDIC** con *"hyperbaric medicine, oxygen therapy"* | Sin evidencia de ozono. Aparece **oxigenoterapia y cámara hiperbárica**, que no es ozonoterapia: confundirlas es un error clínico |

**Consecuencias de diseño (no negociables):**

1. **Verificar pertenencia, no solo nombre.** RENIPRESS publica `DIRECCION` y coordenadas
   (latitud y longitud, pese a llamarse `NORTE`/`ESTE`), así que un resultado solo se acepta si
   su dirección o ubicación
   coincide con la de la IPRESS. La búsqueda por nombre + distrito no alcanza.
2. **Tercer estado obligatorio.** Si no se puede confirmar que el sitio es de la clínica,
   el resultado es `unknown`, nunca `performs: false`: es el mismo criterio que ya aplica
   `signal_available` en la Consulta G.
3. **Nunca preguntarle a un LLM "¿esta clínica hace ozonoterapia?"** con texto libre: la
   muestra ya mostró oxigenoterapia e hiperbárica a un paso de la ozonoterapia. El LLM solo
   puede *extraer menciones textuales de ozono con su cita*, y la decisión de confiar en
   ellas es determinista y auditable.
4. **Medir la tasa de acierto en muestra antes de correr las 2.459.** Con 0 de 3 en la
   prueba manual, el diseño debe demostrar que el filtro de direcciones sube el acierto
   antes de gastar presupuesto real.

#### Estado de implementación (13-10)

Implementado y probado **offline** en `scraper/enrichment.py` (9 tests en
`tests/test_enrichment.py`), que es justo donde estaba el riesgo real:

- `find_ozone_mentions(text)`: devuelve las **oraciones** que mencionan ozono con los
  marcadores que coincidieron, para que una persona pueda auditar la afirmación en vez de
  confiar en un booleano.
- `clinic_owns_result(candidate, ipress)`: atribuye una página a una IPRESS por su
  **teléfono publicado** —la señal fuerte: un teléfono identifica una clínica, una calle la
  comparte todo el distrito, y RENIPRESS publica teléfono de 2.457 de los 2.459 objetivos— o
  por dirección comparable (≥ 2 tokens de calle compartidos). Rechaza de entrada otro
  departamento o distrito declarados, y admite `+51` y los teléfonos con `;` del padrón.
- `resolve_ozone_evidence(...)`: el tri-estado. `checked=False` cuando no se puede atribuir,
  con el mismo criterio que `signal_available` en la Consulta G.

**Verificado contra páginas reales, no contra fixtures:**

| Página real | Resultado |
|---|---|
| `cefraperu.com/inicio` (clínica de nuestra lista) | 32.299 caracteres de texto, **0 menciones de ozono**, y sí publica su dirección `GUARDIA CIVIL` → atribuible |
| `centromedicosanborja.com/servicios/unidad-de-ozono` | **Sí menciona ozono** ("Unidad de Ozono" y el texto sobre el gas). Mismo distrito que CEFRA → `checked=False`, `performs=False` |

El falso positivo que la búsqueda ingenua producía —**otra clínica del mismo distrito que sí
ofrece ozono**— quedó rechazado sobre páginas reales.

**Hallazgo nuevo:** `centromedicosanborja.com` respondió **HTTP 406 de Mod_Security** a un
cliente HTTP plano, y **200** al mismo pedido con cabeceras de navegador. Parte del
enriquecimiento va a necesitar cabeceras de navegador o un fetcher stealth
(Scrapling `StealthyFetcher` / `DynamicFetcher`), no `httpx` pelado.

#### Descubrimiento: implementado, y la forma de la consulta está medida

`scraper/discovery.py` cierra el circuito: **una** consulta por clínica, lectura de las
páginas candidatas con **cabeceras de navegador** y respetando `robots.txt`, atribución, y
detección de menciones dentro de la página aceptada. La caché por IPRESS en
`data/enrichment/` evita gastar dos veces la misma consulta.

**La forma de la consulta no se adivinó: se midió** (13-10-2026, contra clínicas reales de
la propia lista, 9 créditos):

| Consulta probada | Resultado medido |
|---|---|
| `"NOMBRE COMPLETO" DISTRITO` | **La única que sirve.** Para CEFRA devolvió `cefraperu.com` primero |
| el teléfono publicado | Negocios sin relación: para San Felipe devolvió un Facebook con dirección de **Los Olivos**, no la de Lurigancho del padrón |
| `NOMBRE CORTO DISTRITO ozonoterapia` | Proveedores genéricos de ozono (`chacarilla.com.pe`, Facebook), nunca la clínica |

Dos conclusiones que **corrigen supuestos anteriores** de este mismo documento:

1. **El teléfono sirve para atribuir, no para descubrir.** Identifica una página una vez
   encontrada, pero buscarlo no encuentra el sitio de la clínica. Sigue siendo la señal
   fuerte dentro de una página ya descargada.
2. **Agregar "ozonoterapia" a la consulta destruye la precisión**: busca proveedores de
   ozono, no a la clínica. Las menciones hay que buscarlas *dentro* de la página atribuida.

Contrato del proveedor usado (**Serper**), verificado contra su OpenAPI y su documentación
de oficial, no supuesto:

```http
POST https://google.serper.dev/search
X-API-KEY: <clave>
Content-Type: application/json

{ "q": "<nombre de la clinica> <distrito> ozonoterapia", "gl": "pe", "hl": "es", "num": 10 }
```

Devuelve `organic[]` con `title`, `link`, `snippet` y `position`. Máximo 20 resultados por
llamada y **una sola página**: no hay offset, así que la consulta tiene que ser precisa.

#### Resultado de la corrida de 50 clínicas (medido, no estimado)

Muestra sistemática (1 de cada 49) sobre los 2.459 prospectos, con la caché limpia:

| Métrica | Valor |
|---|---|
| Clínicas procesadas | 48 de 50 (2 con error de red, manejado sin cortar la corrida) |
| Créditos de búsqueda | 48 (1 por clínica) |
| Tiempo | 184 s (~3 min) → ~2,5 h para las 2.459 |
| **Atribuidas a una página** | **24 (50 %)**: 10 por teléfono, 14 por dirección |
| Bloqueadas por `robots.txt` | 5 |
| Sin candidatos / sin atribuir | 1 / 18 |
| Páginas efectivamente leídas | 23 |
| **Menciones de ozono encontradas** | **0** |

**La composición de las páginas atribuidas es la que decide todo.** De las 24:

| Host | Veces | Qué es |
|---|---|---|
| `directorio.cuidamisalud.com` | 8 | directorio |
| `tumedico.pe` | 4 | directorio |
| `establecimientosdesalud.info`, `universidadperu.com` | 2 + 2 | directorios |
| `deperu.com`, `checksalud.com`, `guiabbb.pe`, `waze.com`, `upao.edu.pe` | 1 c/u | directorios, un mapa y una tesis |
| `policlinicolc.com`, `horizontemedic.com`, `insad.com.pe` | 1 c/u | **sitios de clínica** |

Aplicando el filtro de hosts no clínicos que salió de esta misma medición, de las 24
atribuidas **solo 4 son páginas que pueden contestar la pregunta**, y ninguna menciona ozono.

> **Conclusión: el enriquecimiento, así como está, no responde la pregunta.**

No es que nadie ofrezca ozonoterapia: es que las páginas que la búsqueda encuentra y la
atribución acepta son **directorios**, y un directorio no lista tratamientos. Con 4 lecturas
útiles sobre 50 clínicas el resultado no distingue "no ofrece" de "la página no lo dice", y
por eso `checked` nunca se debe leer como negación.

**Recomendación: no correr las 2.459.** Costaría unos 2.400 créditos (el cupo gratuito completo)
y ~2,5 h para producir una señal que hoy no existe. El camino, si se quiere la señal:

1. Filtrar los candidatos a dominios que parezcan de la clínica —y no de un directorio— y
   seguir 1 o 2 páginas de servicio dentro de ese dominio. Ese es el trabajo real que falta.
2. Antes de comprometer créditos, pilotear sobre ~200 clínicas y medir cuántas menciones
   aparecen. La tasa base puede ser baja: en esta muestra ni los 3-4 sitios propios de clínica
   que sí se leyeron mencionaban ozono.
3. Mientras tanto, "¿ya ofrece ozonoterapia?" sigue siendo una pregunta de la llamada
   comercial, que es la decisión que ya se había tomado antes de intentar automatizarla.

**Defecto encontrado después de la corrida:** la extracción de teléfonos fusionaba el número
con el de la calle cuando venían seguidos (`999 888 777 Av. Guardia Civil 715` daba una tira de
12 dígitos), así que algunos matches por teléfono se perdían. Está arreglado y cubierto con
test: el 50 % de atribución es un **piso**, no el valor real. El arreglo no cambia la
conclusión, porque el problema es la naturaleza de las páginas, no el matching.

Por eso el enriquecimiento **no se integró al pipeline**: emitir `checked=True` con 0 menciones
desde un directorio haría que el dueño leyera "no ofrece ozono", que es exactamente el error
que este módulo existe para no cometer. El código queda disponible y probado, sin cablear.

### Scoring (RF-05, versión determinista)

Cada punto es trazable a una columna de origen. No hay valores inventados.

| Componente | Techo | Regla |
|---|---|---|
| `establishment` | 25 | Categoría I-4 = 25, I-3 = 15; +5 si la clasificación es especializada |
| `capacity` | 30 | Médicos totales: 0 → 0, 1-3 → 10, 4-9 → 20, ≥10 → 30 |
| `market` | 25 | Lima 25; Arequipa, La Libertad, Lambayeque, Cusco 15 (fase de expansión); resto 8 |
| `reachability` | 20 | Teléfono válido 15; dirección presente 5 |
| `penalty` | −40 | Consulta G confirma que la IPRESS **ya** ofrece ozonoterapia. Regla implementada y probada, pero **sin efecto real hoy**: la señal está vacía (ver §2.3) |

**Nivel:** `high` exige `total` ≥ 70 **y evidencia completa** (`measured_weight == 100`,
es decir, con la capacidad de la IPRESS en registro). `medium` ≥ 45, o puntaje ≥ 70 sin
evidencia completa. `low` en el resto. Una IPRESS que ya hace ozonoterapia **nunca** queda
en `high`: es otra venta (insumos), no la primera colocación.

Medido sobre la corrida real con la regla aplicada: **122 `high` (5,0 %), 2.333 `medium`,
4 `low`**. Quedan 1.307 prospectos con puntaje ≥ 70 retenidos en `medium` por falta de
evidencia de capacidad.

#### Redistribución cuando falta evidencia (decisión del 13-10, con medición)

Como la Consulta A cubre solo el 10 % de los objetivos, puntuar una capacidad
desconocida como capacidad cero le costaba 30 puntos a 2.211 prospectos. Ahora el peso
de un componente sin evidencia **se excluye** y la evidencia restante se reescala a 0-100.
`score.measured_weight` publica cuánto de la escala tenía evidencia (100 o 70).

Medición sobre la corrida real, con la escala redistribuida y umbrales 70/45:

| Efecto medido | Valor |
|---|---|
| `priority-high` | **1.429 (58,1 %)** — antes 125 (5,1 %) |
| De esos 1.429, con dato de capacidad real | **122** |
| Prospectos empatados en un mismo puntaje | 802 empatados en 86, 747 en 61, 400 en 71 |
| Valores distintos en toda la escala | 27 para 2.459 prospectos |

**Dos defectos que la redistribución introdujo y que están sin resolver:**

1. **Premia la ignorancia.** Con el mismo perfil (I-3, policlínico, Lima, con teléfono y
dirección), una IPRESS **sin dato** saca 86 y le gana a una con 1-3 médicos (70) y a una
con 4-9 médicos (80). Solo la supera una con 10 o más (90). No saber el tamaño vale más
que saber que es chica.
2. **La etiqueta `high` dejó de discriminar.** 1.307 de los 1.429 `high` lo son por una
**ausencia**, no por evidencia. Además hay 802 empatados en el mismo puntaje, así que el
orden dentro del empate lo decide el código de IPRESS, que es arbitrario.

Ningún valor de umbral arreglaba esto solo: la escala tiene 27 valores posibles para 2.459
prospectos porque las columnas disponibles discriminan poco. Opciones evaluadas:

| Opción | `high` resultante | Estado |
|---|---|---|
| Escala redistribuida, umbrales 70/45 | 1.429 (58,1 %) | Descartada |
| Escala redistribuida, umbrales 80/60 | 898 (36,5 %) | Descartada |
| Escala redistribuida, umbrales 90/70 | 60 (2,4 %) | Descartada |
| **`high` exige evidencia completa** | **122 (5,0 %)** | **Aplicada el 13-10** |

**Consecuencia importante:** la regla elegida hace que `high` dependa del **dato de
capacidad**, no del puntaje. El enriquecimiento web, que aporta señal de ozonoterapia,
**no va a mover a nadie a `high`**: la restricción es la capacidad. Para promover a esas
1.307 clínicas hace falta una fuente de capacidad —la muestra del enriquecimiento ya
insinuó una: LinkedIn reportaba *"employs 6 people"* para una de las clínicas— o una regla
distinta para el nivel.

---

## 3. Contrato `prospect_mock.json`

Emitido en `data/out/prospect_mock.json` (ignorado por git, son 2.459 registros). Versionado
como `prospect_mock/v0`: **la versión v0 la propone el módulo 1 y la debe ratificar el owner
de la base de datos (RF-09).**

**Para maquetar sin correr nada:** `docs/prospect_mock.ejemplo.json` es una muestra real de
**tres** prospectos, elegidos a propósito para cubrir **las tres formas** que existen: uno **con**
dato de capacidad (`measured_weight: 100`), uno **sin** él (`measured_weight: 70`,
`capacity.period: null`, tag `no-capacity-data`) y uno del **segmento** (`origin: "places"`,
`score: null`, con el bloque `google`).

Con un solo ejemplo el error es inevitable: quien maqueta solo con la forma del padrón termina
mostrando "0 médicos" donde no hay dato, y **se le rompe la página con los 529 del segmento**, que
son los que más importan al negocio. El detalle para el frontend está en `docs/para-la-pagina.md`.

El archivo completo (2.459 prospectos) sale de `uv run python -m scraper`, y el segmento (829) de
`uv run python -m scraper --segment-places`.

```jsonc
{
  "contract_version": "prospect_mock/v0",
  "generated_at": "2026-10-13T17:31:00+00:00",
  "sources": [                     // trazabilidad: qué bytes produjeron este archivo
    { "dataset": "renipress", "url": "...", "sha256": "...", "last_modified": "..." }
  ],
  "total": 2459,
  "prospects": [
    {
      "id": "00024663",            // = ipress_code, clave de deduplicación
      "ipress_code": "00024663",
      "name": "CLINICA VERTEBRAL",
      "legal_name": "CLINICA VERTEBRAL SAC",   // null si no está en Consulta A
      "institution": "PRIVADO",
      "category": "I-3",
      "classification": "POLICLINICOS",
      "establishment_type": "ESTABLECIMIENTO DE SALUD SIN INTERNAMIENTO",
      "location":    { "department": "LIMA", "province": "LIMA", "district": "SAN ISIDRO",
                       "ubigeo": "150131",
                       "coordinates": { "latitude": -12.0977, "longitude": -77.0365 } },
      "contact":     { "phone": "984337558", "phone_valid": true, "address": "AV. JAVIER PRADO ESTE 1066", "schedule": "8:00 - 20:00" },
      "capacity":    { "doctors_total": 6, "consulting_rooms": 9, "functional_consulting_rooms": 8,
                       "beds": 0, "nurses": 7, "ambulances": 1, "period": "2026-02" },
      "ozone_therapy": { "checked": false, "performs": false, "total_attendances": 0,
                         "evidence": [], "source_url": null, "attribution": null },
      "score":       { "total": 80, "level": "high",
                       "components": { "establishment": 15, "capacity": 20, "market": 25,
                                       "reachability": 20, "penalty": 0 },
                       "measured_weight": 100 },
      "pipeline_stage": "discovered",
      "tags": ["target-profile", "priority-high"]
    }
  ]
}
```

### Reglas del contrato

> **Las coordenadas vienen en columnas llamadas `NORTE` y `ESTE`, y son latitud y longitud.**
> Medido sobre los 2.459 objetivos: `NORTE` va de −18,07 a 0 y `ESTE` de −81,28 a 0, sin un
> solo valor en rango UTM. Fiarse del nombre habría puesto cada clínica en el lugar equivocado.
> El contrato las nombra por lo que son.
>
> **Cobertura: 2.091 de 2.459 (85 %).** El resto va `null`, y eso incluye dos registros que
> publican `−6e-08`, que es el punto (0,0) en el océano frente a África: un dato faltante
> disfrazado de coordenada, que se descarta en vez de propagarse.
>
> Validación cruzada: para una clínica de la muestra, el padrón publica
> `(-11.9373125, -76.6950625)` y Google Places devuelve `(-11.937314, -76.69511)` para la
> misma dirección. Coinciden hasta el quinto decimal, con fuentes independientes.

- **`pipeline_stage`** usa exactamente las columnas del Kanban del CRM (RF-03):
  `discovered` → `contacted` → `proposal_sent` → `contract_signed`
  (Descubierto, Contactado, Propuesta enviada, Contrato firmado). El módulo 1 solo emite `discovered`.
- **`ozone_therapy.checked`** distingue *"confirmado que no hace"* de *"todavía no se miró"*.
  Vale `false` si no se corrió con `--include-procedures` **y también** si se corrió pero la
  fuente no puede expresar la pregunta (ver §2.3). Nunca se debe leer como negación.
- **`capacity.period`** es `null` cuando la IPRESS no aparece en Consulta A. En ese caso
  `capacity` queda en ceros y el prospecto lleva el tag `no-capacity-data`: es un dato
  faltante, no un cero real.
- Los campos sensibles son **institucionales** (teléfono y dirección de la IPRESS publicados
  por SUSALUD como dato abierto). No se extraen datos personales de pacientes ni de médicos.

### Etiquetas (`tags`)

| Tag | Significado |
|---|---|
| `target-profile` | Cumple el perfil objetivo (privada, activa, I-3/I-4) |
| `priority-high` | `score.level == "high"` |
| `already-offers-ozone-therapy` | Consulta G confirma ozonoterapia: otra conversación comercial. **Hoy no se puede emitir**: la señal está vacía (ver §2.3) |
| `no-capacity-data` | No está en Consulta A; el puntaje de capacidad es 0 por falta de dato |

---

## 4. Cómo se corre

```bash
uv sync                                 # instala dependencias
uv run python -m scraper                # RENIPRESS + Consulta A  (rápido)
uv run python -m scraper --include-procedures   # escanea Consulta G (~226 MB). Hoy no aporta señal: ver §2.3
uv run python -m scraper --limit 50     # solo los 50 mejores puntuados
uv run python -m scraper --refresh      # ignora la caché y vuelve a bajar
uv run python -m scraper --year 2025 --period 4 # una publicación concreta
uv run pytest                           # suite completa, sin red
```

Los CSV crudos quedan cacheados en `data/raw/` (ignorado por git) y la salida en
`data/out/`. Las copias transcodificadas a UTF-8 viven en `data/cache/`, **nunca al lado
del archivo de origen**: así un montaje de solo lectura o el directorio de fixtures quedan
intactos. Cada corrida reescribe `prospect_mock.json` con el `sha256` de los bytes que leyó,
así que dos corridas sobre los mismos datos son comparables.

### Credenciales de búsqueda web (dónde va la API key)

La clave **nunca** se escribe en el código ni se versiona. Va en un archivo `.env` en la
raíz del proyecto, al lado de `pyproject.toml`. Creálo vos, con tu editor:

```bash
cd /home/dafi/projects/confia2.0
printf 'SERPER_API_KEY=tu_clave_aca\n' > .env
chmod 600 .env     # que solo la lea tu usuario
```

> **Sin espacios alrededor del `=`.** `SERPER_API_KEY =valor` lo tolera python-dotenv pero
> **no** `podman --env-file`, que le pasa al contenedor el nombre con el espacio y adentro la
> variable queda invisible. Medido y documentado en `docs/copiloto-outbound.md` §7, con el
> `sed` para corregir un `.env` ya escrito.

Es una sola línea. `.env` ya está en `.gitignore` (no se commitea) y en `.dockerignore` (no
entra a la imagen). El código lee **variables de entorno**, así que `.env` es solo comodidad
de desarrollo: en Cloud Run la misma variable llega desde Secret Manager y el archivo no
existe.

`resolve_search_credentials()` resuelve la pareja proveedor + clave y falla con un mensaje
que nombra exactamente la variable que falta, en vez de romper dentro de un request:

- Si hay **una sola** clave cargada, deduce el proveedor sola. Pegar la clave alcanza.
- Si hay **dos**, exige elegir con `CONFIA2_SEARCH_PROVIDER=serper|brave|google_cse`.
- Si no hay ninguna, el error dice la ruta del archivo y el nombre de la variable.

Por podman hay que pasarla explícitamente, porque la imagen no la incluye:

```bash
podman run --rm --env-file .env -v ./data:/app/data:Z --userns=keep-id confia2-scraper:dev
```

> En producción el valor sale de **Google Secret Manager** y se inyecta como variable de
> entorno, cumpliendo RNF-02: sin llaves hardcodeadas en código fuente.

### Contenedor con podman

La ingesta es un **trabajo por lotes**, no un servicio: resuelve los recursos vigentes,
escribe el archivo y termina. Por eso la imagen no expone puertos ni arranca un servidor,
y la programación va por fuera (systemd timer, cron o Cloud Run Job + Cloud Scheduler).

```bash
podman build -t confia2-scraper:dev .

# La carpeta data/ entra montada: los CSV cacheados y la salida sobreviven al contenedor.
podman run --rm -v ./data:/app/data:Z --userns=keep-id confia2-scraper:dev
podman run --rm -v ./data:/app/data:Z --userns=keep-id confia2-scraper:dev --include-procedures --limit 50

# Ver la ayuda, sin montar datos ni tocar la red
podman run --rm confia2-scraper:dev --help
```

- **`--userns=keep-id` es obligatorio en la práctica.** La imagen corre como root (es un
  trabajo por lotes), así que sin este flag `prospect_mock.json` sale con dueño `root` en tu
  carpeta y después no lo podés borrar sin `sudo`. Verificado: con `--userns=keep-id` el
  archivo sale con tu usuario y tu grupo.
- **`:Z`** es el reetiquetado de SELinux para hosts en enforcing (Fedora, RHEL). En hosts sin
  SELinux podman lo ignora.
- Para apuntar los datos a otro lado, sobreescribí `CONFIA2_DATA_DIR` con `-e`, o pasá
  `--output` y `--raw-dir` explícitos.

La imagen fija las dependencias desde `uv.lock` (`uv sync --frozen`), así que el contenedor
resuelve exactamente las mismas versiones que la corrida local. `.dockerignore` deja afuera
`data/`, `.git`, `.venv`, `docs/` y `tests/`, y nunca copia `.env`.

---

## 5. Despliegue: dónde vive el JSON y qué escribe cada corrida

El JSON es un **artefacto intermedio**, no el destino final. La ingesta es un trabajo por lotes
(§4), así que el flujo desplegado queda así:

```
Cloud Scheduler ──► Cloud Run Job (esta imagen) ──► CSV de SUSALUD
                             │
                             ▼
                   el almacen que elija el equipo
                             │
                             ▼
              FastAPI (BFF) y/o el CRM leen de ahi
```

Dos caminos, y los dos son seguros con la misma regla:

| Camino | Cómo | Cuándo conviene |
|---|---|---|
| **A · Firestore** (lo que dice el `.md`) | El job hace *upsert* por `ipress_code` en `prospects` y `proposals` (el contrato) y proyecta la misma corrida en `leads` y `approvals` con los nombres que ya usa la página; todo se lee con reglas de seguridad (RNF-07) | Cuando el Kanban necesita leer **y escribir** estado |
| **B · GCS** | El job sube el JSON a un bucket; el BFF lo carga al arrancar o cuando cambia el `sha256` | Más rápido de construir, pero el estado del CRM tiene que vivir aparte |

### La trampa que hay que evitar: no pisar el trabajo del vendedor

`pipeline_stage` **lo mutala el CRM**, no la ingesta. Si el job reescribe el documento completo
en cada corrida, un prospecto que ya estaba en `contract_signed` vuelve a `discovered` y **el
trabajo comercial del dueño se pierde sin que nadie se entere.**

Regla: el job escribe **solo los campos que vienen de las fuentes** y nunca los que produce o
edita una persona.

| El job los escribe en cada corrida (upsert) | El job nunca los toca |
|---|---|
| `name`, `legal_name`, `institution`, `category`, `classification`, `establishment_type` | `pipeline_stage` (lo mueve el CRM) |
| `location.*`, `contact.*` | Notas, propuestas y borradores asociados |
| `capacity.*`, `score.*`, `sources` (procedencia) | `tags` agregados por una persona |
| `tags` de origen (`target-profile`, `priority-high`, `no-capacity-data`) | Estado de aprobación del copiloto |

Al crear el documento por primera vez, `pipeline_stage` nace en `discovered`. **Después, el job
no lo escribe nunca más.**

### Frescura y costo

`sources` trae el `sha256` de cada archivo leído. Si una corrida obtiene los mismos hashes que la
anterior, **nada cambió** y el job no necesita escribir nada: ahorra escrituras y, sobre todo,
evita tocar la base al pedo. SUSALUD publica por mes, así que la mayoría de las corridas
programadas no van a cambiar nada.

Y ojo con la forma de la escritura: los lotes de Firestore tienen límite de 500 operaciones, así
que 2.459 prospectos son **5 lotes** — o `bulk_writer`, que se encarga solo.

## 6. Decisiones y límites conocidos

| Tema | Decisión | Motivo |
|---|---|---|
| Velocidad de `--include-procedures` | Opt-in, no por defecto | La Consulta G pesa ~226 MB por mes. Se escanea de forma perezosa y se filtra a las IPRESS objetivo antes de materializar filas |
| Señal de ozonoterapia | Se emite como "sin dato" y se avisa por consola | La Consulta G no tiene el procedimiento codificado. Un `false` se leería como negación verificada, que es peor que no tener el dato |
| Codificación | Detección y transcodificación a UTF-8 con caché | RENIPRESS es UTF-8 y las Consultas A y G son latin-1. Leer latin-1 como UTF-8 convierte `Aplicación` en `Aplicaci<?>` |
| Cambios de esquema | Falla ruidosamente | Si SUSALUD renombra una columna, el pipeline levanta `UnexpectedColumns` en lugar de emitir prospectos vacíos |
| CMP | Fuera del alcance masivo | Su API tiene autenticación, cifrado de payload y cooldown: está diseñada para consultas puntuales, no para extracción de volumen |
| Enriquecimiento web | Decidido (13-10): se enriquecen las 2.459 clínicas filtradas | La validación en muestra dio 0 de 3 con evidencia confiable: obliga a verificar pertenencia por dirección y a admitir el estado `unknown`. Ver §2.4 |
| RUC / razón social | Solo `RAZON_SOC` de la Consulta A | RENIPRESS no publica RUC, así que cruzarlo obligaría a un *matching* por nombre, que no es confiable |
| Cobertura de la capacidad instalada | Aceptada y documentada arriba; el faltante se marca, no se inventa | La Consulta A solo cubre al 10 % de los objetivos. Tratarlo como cero es una decisión explícita, reversible y visible en el tag `no-capacity-data` |

## 7. Próximos pasos

1. **Contenedor: hecho.** Queda la ejecución programada (systemd timer, cron o Cloud Run
   Job + Cloud Scheduler), que es una decisión de despliegue del equipo.
2. Ratificar el contrato `prospect_mock/v0` con el owner de la base de datos (RF-09).
3. Decidir con el owner del CRM si la ingesta debe escribir directo en Firestore o
   quedarse como JSON en un bucket intermedio.
4. Decidir cómo se reemplaza la señal de ozonoterapia (ver §2.3) antes de prometerle al
   dueño que el sistema sabe quién ya la ofrece.
5. Recalibrar el scoring: hoy el componente `capacity` (techo 30) es inalcanzable para el
   90 % de los prospectos porque la Consulta A no los cubre.
