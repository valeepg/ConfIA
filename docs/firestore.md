# Integración con Firestore

> Decisión del equipo: los prospectos viven en **Firestore**, dentro del proyecto de Firebase que
> ya existe. Este documento dice **qué se puede archivar y qué no**, porque hay una restricción
> real de Google que cambia el diseño.

---

## 1. Una colección, dos orígenes

Los dos artefactos entran a la misma colección `prospects`, y cada documento dice de dónde viene:

| `origin` | Clave | Qué trae | Cuántos |
|---|---|---|---|
| `renipress` | `ipress_code` | Categoría I-3/I-4, capacidad (10 %), coordenadas (85 %), puntaje del padrón | **2.459** |
| `places` | `cid` | La especialidad, rating, reseñas, sitio web, cadena | **829** |

**No se cruzan**: medido, **ninguna** de las 529 clínicas del segmento está en el padrón. Son dos
segmentos distintos, no dos vistas del mismo.

### Y dos proyecciones, con los nombres de la pantalla

`prospects` y `proposals` guardan el contrato, que es para el dato. La página lee **`leads`** y
**`approvals`**, que son la misma información proyectada con los nombres que el frontend ya usa
(`status` en vez de `pipeline_stage`, `aiContent` en vez de `message`). Las proyecciones salen del
mismo prospecto en cada corrida, así que no agregan una segunda fuente de verdad que haya que
sincronizar a mano.

El detalle y las tablas de equivalencias están en `para-la-pagina.md`, sección 7. Lo que importa acá:
las dos proyecciones tienen **la misma regla de propiedad** que el contrato —`status` y `statusNote`
se escriben solo al crear, y después son del CRM— y los campos que ninguna fuente trae
(`directorMedico`, `aiContent.recipientName`) van en `null`.

Y las dos tienen que estar en `firestore.rules`: el `match /{document=**}` del final cierra todo lo
que no esté nombrado, y desde la página eso no se ve como un error de permisos sino como una base
vacía.

## 2. La restricción que hay que respetar (verificada)

De los términos de Google Maps Platform, textual:

> *"Customer may temporarily cache latitude and longitude values from the Places API for up to
> **30 consecutive calendar days**, after which Customer must delete the cached ... values."*

> *"You must not pre-fetch, cache, or store Places API content beyond the allowed exceptions,
> although the `place_id` is exempt from caching restrictions. You can therefore store place ID
> values **indefinitely**."*

Traducido a este proyecto:

| Dato | ¿Se puede archivar para siempre? |
|---|---|
| `cid` (equivalente al `place_id`) | **Sí**, es el identificador y está exento |
| `query` que lo encontró, y nuestras derivaciones (`rating_band`, `reviews_band`, tags) | **Sí**, son nuestros |
| Nombre, dirección, teléfono, sitio web, rating, reseñas, **coordenadas** | **No.** Es contenido de Places: se lee, se usa, y se vuelve a leer |

**Y una advertencia aparte, porque acá se paga con el bolsillo ajeno:** nosotros **no somos
clientes de Google Maps Platform**, usamos **Serper**, que es scraping de resultados revendido.
Serper no ofrece acuerdo de tratamiento de datos, ni SLA, ni cobertura legal, y los términos de
Google sobre extracción automática siguen existiendo del otro lado. Para una hackathon es
razonable; para vender en producción conviene **migrar a la API oficial de Places**, que además
resuelve el problema de caché con una regla clara en vez de una zona gris.

## 3. La forma del documento, con el snapshot separado

La restricción anterior obliga a separar lo permanente de lo releíble:

```jsonc
// prospects/{cid}
{
  "origin": "places",
  "id": "places:1585704026956535642",
  "cid": "1585704026956535642",        // permanente
  "query": "fisioterapia San Isidro Lima",
  "refreshed_at": "2026-10-14T06:31Z", // cuándo se leyó el snapshot
  "google_snapshot": {                 // se reemplaza entero en cada re-lectura
    "name": "Artrauma", "category": "Fisioterapeuta",
    "phone": "993 923 680", "address": "…",
    "latitude": -11.1, "longitude": -77.6,
    "rating": 4.8, "rating_count": 553, "website": "…"
  },
  "derived": {                         // nuestro: puede quedar
    "rating_band": "alta", "reviews_band": "alta",
    "tags": ["physiotherapy-segment", "chain"], "chain_sites": 2, "district": "HUAURA"
  },
  "pipeline_stage": "discovered",      // del CRM: el job NUNCA lo escribe
  "notes": [], "proposals": []
}
```

Para `origin: "renipress"` es igual pero con `ipress_code`, la categoría y la capacidad del
padrón, y **sin** `google_snapshot`. El padrón es dato abierto reutilizable: eso sí se archiva.

## 4. Qué escribe el job y qué no (la trampa que hay que evitar)

`pipeline_stage` **lo muta el CRM**, no la ingesta. Si el job reescribe el documento completo, un
prospecto en `contract_signed` vuelve a `discovered` y **el trabajo comercial del dueño se pierde
sin que nadie se entere**.

| El job lo escribe (upsert) | El job nunca lo toca |
|---|---|
| `google_snapshot`, `refreshed_at`, `derived` | `pipeline_stage` |
| Los campos del padrón y su `score` | `notes`, `proposals`, borradores |
| `tags` de origen | `tags` agregados por una persona |
| `sources` | Estado de aprobación del copiloto |

Al crear el documento, `pipeline_stage` nace en `discovered`. **Después, el job no lo escribe
nunca más.**

## 5. Frescura y costo

- **Re-leer el segmento cada mes** cuesta **275 créditos** (~10 % del cupo gratuito de Serper) y
  es lo que mantiene el cumplimiento de la regla de caché. Es barato porque las consultas ya están
  cacheadas: re-leer es volver a correr `--segment-places` con `--refresh`.
- **El padrón no necesita esa frecuencia**: SUSALUD publica por mes y `sources` trae el `sha256`,
  así que si nada cambió el job no escribe nada. Revisar si el `sha256` cambió es suficiente.
- **Volumen:** 3.288 documentos = **7 lotes** de 500 operaciones, o un `bulk_writer`.

## 6. Seguridad y datos personales

- **Reglas de Firestore (RNF-07):** solo el administrador autenticado lee y escribe `prospects`,
  `proposals`, `leads`, `approvals` e `installed_base`. Nada de lectura pública.
- **Ley N.° 29733 (RNF-03):** los datos de prospecto son **institucionales** (nombre comercial,
  teléfono y dirección del establecimiento, que SUSALUD y Google publican). No hay datos de
  pacientes en ningún artefacto. Lo que sí hay es **teléfono y dirección de una clínica**: es dato
  de contacto de una persona jurídica, y conviene que el aviso de privacidad del CRM lo diga.
- **Secretos (RNF-02):** `NAN_API_KEY` y `SERPER_API_KEY` van a **Secret Manager** para el job
  desplegado. Nunca al repositorio ni a la imagen: `.env` está en `.gitignore` y en
  `.dockerignore`, y hay un test que falla si eso cambia.

## 7. Lo que falta decidir

1. **¿Se migra a la API oficial de Places?** Resuelve la zona gris legal y la regla de caché, a
   cambio de costo por consulta y una cuenta de Google Cloud con facturación.
2. **¿El job escribe directo a Firestore o deja el JSON en un bucket intermedio?** Escribir directo
   es menos piezas; el bucket deja un rastro auditable de cada corrida, que ya existe como
   `sources` con `sha256`.
3. **La forma del contrato frente a la página.** Se resolvió por proyección en vez de por acuerdo:
   `prospects` mantiene el contrato `prospect_mock/v0` y `leads` le da a la pantalla sus propios
   nombres. No hace falta que el frontend adopte el contrato ni al revés, pero **falta que el dueño
   de la página confirme** que lee `leads` (es una línea) y borre sus ocho documentos de prueba de
   `prospects`.
