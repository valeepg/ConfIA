# Segmento por especialidad: fisioterapia y rehabilitación

> Extiende el Módulo 1. Responde a una pregunta que el padrón **no puede** contestar:
> ¿qué clínicas ofrecen fisioterapia, rehabilitación o terapia del dolor?
> Reutiliza la misma clave de búsqueda y escribe en el mismo contrato de prospectos.

---

## 1. El problema que resuelve

El plan original filtraba IPRESS por **categoría I-3/I-4**. Medido el 14-10-2026:

| Verificación | Resultado |
|---|---|
| Clínicas de fisioterapia en los 10 distritos más poblados de Lima, según Google | **93** |
| De esas 93, presentes en nuestra lista de 2.459 | **0** |
| Prospectos del padrón clasificados como `MEDICINA FISICA` | **1 de 2.459** |
| Prospectos con algún marcador de fisio/rehab/dolor en el nombre | 11 (y varios son *rehabilitación **dental***) |

**No es un error de datos: es que la fuente no tiene esa dimensión.** RENIPRESS clasifica
**establecimientos** (policlínico, centro médico, odontológico, hospital), no especialidades
clínicas. Un centro de fisioterapia no entra en la categoría I-3/I-4, así que el filtro lo
excluye por diseño.

**Conclusión:** para este segmento la búsqueda es la fuente **primaria** y el padrón es, a lo
sumo, un enriquecimiento.

## 2. Cómo se corre

```bash
# Todo Lima: los 55 distritos que aparecen en el padrón, x 5 especialidades = 275 consultas
uv run python -m scraper --segment-places

# Un subconjunto explícito
uv run python -m scraper --segment-places --segment-districts "SAN ISIDRO,MIRAFLORES,SAN BORJA"

# Otro departamento, o solo los 10 distritos con más prospectos
uv run python -m scraper --segment-places --segment-department AREQUIPA --segment-top 10

# -> data/out/segmento_places.json
```

**Cada consulta se cachea en `data/places/`.** Volver a armar el segmento, cambiar umbrales o
agregar campos derivados **no vuelve a gastar un crédito**. Perder esa caché ya nos costó diez
créditos una vez, y no se repite.

## 3. Las dos fuentes conviven en el mismo contrato

Un prospecto dice de dónde viene, porque las dos fuentes responden preguntas distintas y
mezclarlas sin decirlo sería deshonesto:

| Campo | `origin: "renipress"` | `origin: "places"` |
|---|---|---|
| `institution`, `category`, `classification` | del padrón | **`null`** |
| `location.ubigeo` | del padrón | **`null`** (el distrito viene de la consulta) |
| `location.coordinates` | 85 % de cobertura | del resultado |
| `capacity` | 10 % de cobertura | vacío |
| `score` | puntaje del padrón | **`null`**: el modelo del padrón no aplica |
| `google` | `null` | **categoría, rating, reseñas, sitio web, cadena** |

Los puntajes ordenan primero y los del segmento van después, en orden estable.

## 4. Qué trae cada clínica del segmento, para filtrar

```jsonc
{
  "id": "places:1585704026956535642",
  "origin": "places",
  "name": "Artrauma",
  "location": { "department": "LIMA", "district": "HUAURA",
                "coordinates": { "latitude": -11.1, "longitude": -77.6 } },
  "contact": { "phone": "993 923 680", "phone_valid": true,
               "address": "Av. Las Begonias 475, San Isidro 15046" },
  "google": {
    "cid": "1585704026956535642",          // identificador estable
    "query": "fisioterapia San Isidro Lima",
    "category": "Fisioterapeuta",          // la especialidad, que el padrón no tiene
    "rating": 4.8, "rating_count": 553,
    "rating_band": "alta",                 // alta | buena | baja | sin datos
    "reviews_band": "alta",                // alta | media | baja | sin reseñas | sin datos
    "website": "https://fisiathlon.pe/",
    "chain_brand": "artrauma", "chain_sites": 2
  },
  "score": null,
  "pipeline_stage": "discovered",
  "tags": ["physiotherapy-segment", "chain"]
}
```

**Los filtros que habilita**, que es el punto de todo esto:

| Filtro | Campo |
|---|---|
| **Está en el segmento** | tag `physiotherapy-segment`, que sale de la **categoría de Google** y no de la consulta: si un lugar aparece pero su categoría no es de fisio/rehab/dolor, se cuenta aparte en `fuera_de_categoria` y **no** se etiqueta |
| Especialidad concreta | `google.category` (`Fisioterapeuta`, `Clínica de fisioterapia`, `Centro de rehabilitación física`, `Clínica del dolor`, `Quiropráctico`) |
| Actividad real de pacientes | `google.reviews_band` (bandas, no un número a interpretar) |
| Calidad percibida | `google.rating_band` |
| Tiene presencia web | tag `no-website`, o `google.website` |
| Vale una conversación con la casa central | tag `chain` + `google.chain_sites` |
| Se puede llamar | `contact.phone_valid` |
| Ruteo de visitas | `location.coordinates` |

> **Por qué el tag no sale de la consulta.** Medido sobre 180 consultas reales: las cinco
especialidades también devuelven `Servicio de salud mental` (10), `Hospital` (22) y `Médico` (18).
Etiquetar todo lo que devuelve una consulta haría que el filtro del CRM signifique *"preguntamos"*
en vez de *"es del segmento"*. `Masajista` tampoco cuenta como marcador: es otro servicio, y el
lugar queda en el archivo con su categoría visible.

## 5. Límites y advertencias

| Tema | Estado |
|---|---|
| **Cinco especialidades son demasiadas** | Medido sobre 180 consultas: `centro de rehabilitacion` aporta **116** lugares exclusivos y `clinica del dolor` **109**, contra **57** de `terapia fisica`, **55** de `fisioterapia` y **40** de `medicina fisica y rehabilitacion`. Para el próximo departamento alcanzan **2 o 3**: las cinco cuestan 40 % más y agregan poco |
| Solapamiento | 1.562 resultados crudos dieron 681 lugares únicos: **56 % es deduplicación**. Ninguna de las 180 consultas volvió vacía |
| **Almacenamiento de datos de Google** | Los datos de Places tienen **restricciones de caché**: la regla general permite guardar el `place_id`/`cid` indefinidamente, y el resto tiene límite temporal (del orden de 30 días). **Hay que verificarlo antes de archivar el segmento en Firestore** y decidir a propósito, no por descuido |
| Categoría de Google | No es una taxonomía controlada: 12 categorías distintas aparecieron, `Masajista` entre ellas |
| Cobertura del padrón | Estas clínicas **no están** en nuestra lista, así que no tienen `category`, `capacity` ni `score`. Si se quieren, hay que cruzar por nombre o dirección, con el problema de resolución de entidades ya medido |
| Duplicados | El mismo lugar puede aparecer con dos `cid` distintos (sedes o fichas viejas). El `cid` es la clave estable, pero conviene revisarlo |
| Nada se envía | Este módulo **busca y escribe un archivo**. No contacta a nadie |

## 6. Resultado de la corrida completa (Lima, 14-10-2026)

```bash
uv run python -m scraper --segment-places     # 55 distritos x 5 especialidades
```

| Métrica | Valor |
|---|---|
| Consultas | 275, **0 sin respuesta** |
| Créditos | **275** (uno por consulta, y quedan cacheadas) |
| Lugares únicos por `cid` | **829** (1.562 resultados crudos: **56 % es deduplicación**) |
| **En el segmento** | **529**, porque la categoría de Google es de fisio/rehab/dolor |
| Fuera de categoría | 300: clínica ambulatoria 46, centro médico 37, hospital 30, médico 22… |
| **Con teléfono válido** | **470 de 529** |
| **Con coordenadas** | **520 de 529** |
| Con teléfono **y** coordenada | **462** ← la lista accionable |
| Con sitio web | 256 de 529 |
| Con 100+ reseñas | **24** |
| En una cadena | 66, en 17 grupos (§ abajo) |

Las de más reseñas son la primera llamada: `Artrauma` (553 reseñas, 4.8), `FISIOTERAPIA Y VIDA`
(550, 4.9), `Fisiotherapy Madrid` (461, 5.0), `FISIOTERAPIA MIRAFLORES` (419, 4.9).

### Cadenas: 66 lugares, por la evidencia más fuerte disponible

Dos señales **exactas**, y nada más débil que ellas:

1. **El mismo teléfono publicado.** `Centro Médico OSI` tiene **8 sedes** en la hoja de llamados y
   todas publican `(01) 7390888`; `Clínica Internacional`, 4. La regla por nombre las perdía todas,
   porque cada sede lleva su distrito en el nombre.
2. **El mismo nombre normalizado con alguna palabra distintiva.**

Resultado: **66 lugares en 17 grupos** de dos o más sedes.

**Dos intentos fallidos antes de este** son la razón de que la regla sea tan estricta:

| Intento | Regla | Resultado | Por qué estaba mal |
|---|---|---|---|
| 1 | primera palabra no genérica, sobre el padrón | 350 marcas / **1.468** prospectos | agrupó `ESPECIALIZADO`, `VIRGEN`, `MEDICAL` |
| 2 | primera palabra no genérica, sobre el segmento | **385 de 829** lugares | agrupó `fisio` (34), `san` (24), `dolor` (14) |
| 3 | nombre idéntico + palabra distintiva | 24 | no veía las 8 sedes de OSI |
| 4 | **nombre idéntico, o teléfono idéntico** | **66** | — |

**La advertencia, porque la evidencia no es infalible:** de los 17 grupos, **6 emparejan nombres que
no se parecen**, y lo más probable es una centralita compartida en vez de un dueño común —
`Hospital de la Solidaridad` junto a `Policlínico Pachacamac Salud`, por ejemplo. Por eso el campo
`google.chain_brand` viene vacío en esos casos y la hoja los muestra solo como `si (N)`: un humano
tiene que mirarlos. Las cadenas por teléfono son buenas pistas, no una certeza.

### Las cinco especialidades son dos de más

Medido sobre las 275 consultas, lugares que **ninguna otra consulta** trajo:

| Especialidad | Lugares | Exclusivos |
|---|---|---|
| `centro de rehabilitacion` | 268 | **116** |
| `clinica del dolor` | 146 | **109** |
| `terapia fisica` | 299 | 57 |
| `fisioterapia` | 280 | 55 |
| `medicina fisica y rehabilitacion` | 242 | 40 |

Para el próximo departamento alcanzan **2 o 3**: las cinco cuestan 40 % más y agregan poco.
