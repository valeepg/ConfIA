## Datos de prospectos (Módulo 1) — cómo obtenerlos

El contrato de prospectos es la entrada de los otros tres módulos, y **no está versionado**:
es un artefacto generado a partir de datos abiertos de SUSALUD.

```bash
uv sync                       # dependencias
uv run python -m scraper      # 7 s con la caché; la primera vez descarga ~28 MB
# -> data/out/prospect_mock.json   (2.459 prospectos, ~3,6 MB)
uv run pytest                 # 148 tests, ninguno toca la red
```

- **Formato con ejemplos reales:** `docs/prospect_mock.ejemplo.json` — **tres** prospectos que
  cubren las tres formas (padrón con capacidad, padrón sin capacidad y segmento de búsqueda), y
  `docs/drafts.ejemplo.json` con dos borradores para la pantalla de aprobación.
- **Para la página (Módulo 2):** `docs/para-la-pagina.md` — qué archivo alimenta qué, las tres
  formas, las cuatro trampas, los filtros que los datos sostienen de verdad y **las dos colecciones
  que lee la pantalla** (`leads` y `approvals`, con los nombres que el frontend ya usa).
- **Contrato comentado, campo por campo:** `docs/modulo-1-scraper.md` §3.
- **Todo el módulo:** fuentes, decisiones y límites medidos, en el mismo documento.
- **Despliegue:** `docs/modulo-1-scraper.md` §5 — dónde vive el JSON y **qué escribe y qué no**
  escribe el job en cada corrida.
- **Copiloto de outbound (RF-10):** `docs/copiloto-outbound.md`.
- **Integración con Firestore:** `docs/firestore.md` — el contrato con dos orígenes, las dos
  proyecciones que lee la pantalla, la regla de qué escribe el job y qué nunca toca, y **la
  restricción de caché de Google** verificada antes de archivar nada.
- **Despliegue en Google Cloud:** `docs/despliegue.md` — la receta completa para cuando conectes la
  cuenta: Firestore, Artifact Registry, Secret Manager, la cuenta de servicio con permisos mínimos,
  el Cloud Run Job y el horario.
- **Segmento por especialidad (fisioterapia y rehabilitación):** `docs/segmento-especialidad.md`
  — por qué el padrón **no puede** ver ese segmento (1 de 2.459 figura como `MEDICINA FISICA` y
  ninguna de las 93 clínicas de fisio de Lima está en la lista) y cómo se busca por especialidad
  con `uv run python -m scraper --segment-places`.

### La hoja de llamados (lo que usa el vendedor)

```bash
uv run python -m scraper --segment-places --call-sheet 30
# -> data/out/hoja_de_llamados.md
```

Las mejores 30 clínicas del segmento ordenadas por **actividad real de pacientes**, con teléfono,

Distrito, sitio web y si pertenecen a una cadena. Volver a generarla es gratis: las consultas
quedan cacheadas en `data/places/`.

### Antes de consumirlo, cuatro cosas

1. `capacity.period: null` **no es "0 médicos"**, es "no está en el registro". Mirá también
   `score.measured_weight`: `100` significa evidencia completa, `70` significa que falta la capacidad.
2. `ozone_therapy.checked: false` **no es "no ofrece ozono"**, es "no se determinó". Hoy vale
   `false` en los 2.459 registros.
3. `score.total` y `score.level` responden preguntas distintas: el total es la calidad sobre la
   evidencia disponible, y el nivel exige evidencia completa para llegar a `high`.
4. **No hay email, ni nombre del director médico, ni RUC** en ningún registro: las fuentes no los
   publican. El canal que sostienen los datos es teléfono o visita, no correo.

La clave única para cruzar con cualquier otra fuente es `id`, que es el código de IPRESS de SUSALUD.

### Coordenadas

Vienen en `location.coordinates` y cubren **2.091 de 2.459 (85 %)**, así que un mapa o un ruteo
de visitas es viable. Ojo con el nombre de origen: RENIPRESS las publica en columnas llamadas
`NORTE` y `ESTE`, pero **son latitud y longitud** — está medido y verificado contra Google
Places. Cuando no hay dato va `null`, nunca `(0,0)`.

> El README del proyecto está pendiente; esta sección solo documenta la entrada de datos.
