# Despliegue en Google Cloud

> La receta está **ejecutada sobre el proyecto real**, salvo lo que se marca como pendiente. La
> sección 0 dice qué existía ya, qué se creó y con qué criterio se decidió cada cosa.

---

## 0. Estado real de este proyecto (`confia-511504`)

Revisado **antes de crear nada**, para usar lo que ya existe en vez de duplicarlo:

| Cosa | Estado encontrado | Decisión |
|---|---|---|
| Facturación | **Activa** | — |
| Firestore | **Ya existe**, ubicación **`nam5`** (US multi-región) | No se crea: se usa, y su ubicación no se puede cambiar |
| Artifact Registry | Existe `cloud-run-source-deploy` en **`us-central1`** | No se crea repo nuevo |
| Cloud Run | Existe **`confia-ai-api`** en `us-central1` | El job va en la **misma región**, cerca de la base |
| Secret Manager | Habilitado, sin secretos | Se crea **solo `SERPER_API_KEY`** |
| Cuenta de servicio | No existía | Se creó **`confia2-ingesta@`** con `datastore.user` + `secretAccessor` |
| Cloud Scheduler | **No habilitado** | Pendiente: sin él, el job se ejecuta a mano |
| Firebase | Proyecto con Firestore y Auth | Faltan **las reglas** (§13) |

**El job no lleva la clave del modelo**, y es a propósito: no redacta borradores, solo ingesta y
escribe la base. Si más adelante querés que el job también redacte, hay que agregar el secreto
`NAN_API_KEY` y `--draft-limit` a los argumentos.

### Los comandos, con los valores reales

```bash
PROY=confia-511504
REGION=us-central1
IMG=$REGION-docker.pkg.dev/$PROY/cloud-run-source-deploy/scraper:latest
CUENTA=confia2-ingesta@$PROY.iam.gserviceaccount.com

# La imagen ya trae ENTRYPOINT python -m scraper, así que los flags van en --args
podman build -t $IMG . && podman push $IMG

gcloud run jobs create confia2-ingesta \
  --image=$IMG --region=$REGION --project=$PROY --service-account=$CUENTA \
  --set-secrets=SERPER_API_KEY=SERPER_API_KEY:latest \
  --set-env-vars=CONFIA2_DATA_DIR=/tmp/confia2 \
  --args=--segment-places,--call-sheet,30,--firestore-project,$PROY \
  --task-timeout=3600 --max-retries=1 --memory=1Gi

gcloud run jobs execute confia2-ingesta --region=$REGION --project=$PROY --wait
```

## 1. Qué se despliega, y por qué así

Un **Cloud Run Job**, no un servicio. La ingesta es un trabajo por lotes: resuelve los datos,
escribe y termina. No expone puertos ni atiende peticiones.

```
Cloud Scheduler (mensual)
        │
        ▼
Cloud Run Job ──► CSV de SUSALUD (RENIPRESS, Consulta A)
        │     ──► Google Places (el segmento de fisioterapia)
        ▼
   Firestore · collection: prospects
        │
        ▼
   El CRM y el BFF leen de ahí
```

**Por qué Firestore y no un archivo:** el sistema de archivos de Cloud Run es **efímero**: un JSON
dentro del contenedor se pierde cuando el job termina. Los archivos siguen existiendo como
subproducto auditable de cada corrida, pero el destino real es la base.

## 2. Preparación

```bash
export PROYECTO=tu-proyecto-de-firebase
export REGION=southamerica-west1          # Santiago, la más cercana a Perú
gcloud config set project $PROYECTO

gcloud services enable run.googleapis.com cloudscheduler.googleapis.com \
  secretmanager.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com
```

## 3. Firestore

```bash
# Modo nativo. La ubicación NO se puede cambiar después: elegila pensando en la latencia del CRM.
gcloud firestore databases create --location=$REGION
```

## 4. La imagen

```bash
gcloud artifacts repositories create confia2 --repository-format=docker --location=$REGION
gcloud auth configure-docker $REGION-docker.pkg.dev

# podman, que es lo que este proyecto usa y probó
podman build -t $REGION-docker.pkg.dev/$PROYECTO/confia2/scraper:latest .
podman push $REGION-docker.pkg.dev/$PROYECTO/confia2/scraper:latest
```

## 5. Los secretos

Nunca al repositorio ni a la imagen. Estos comandos leen tu `.env` **sin imprimir el valor**:

```bash
grep '^SERPER_API_KEY=' .env | cut -d= -f2- | tr -d '\n' | \
  gcloud secrets create SERPER_API_KEY --data-file=- --replication-policy=automatic

grep '^NAN_API_KEY=' .env | cut -d= -f2- | tr -d '\n' | \
  gcloud secrets create NAN_API_KEY --data-file=- --replication-policy=automatic
```

## 6. La cuenta de servicio, con permisos mínimos

```bash
gcloud iam service-accounts create confia2-ingesta --display-name="Ingesta de prospectos"
export CUENTA=confia2-ingesta@$PROYECTO.iam.gserviceaccount.com

gcloud projects add-iam-policy-binding $PROYECTO \
  --member="serviceAccount:$CUENTA" --role="roles/datastore.user"

for s in SERPER_API_KEY NAN_API_KEY; do
  gcloud secrets add-iam-policy-binding $s \
    --member="serviceAccount:$CUENTA" --role="roles/secretmanager.secretAccessor"
done
```

> `roles/datastore.user` permite leer y escribir documentos. **No le des `owner` ni
> `datastore.owner`**: la ingesta no administra índices ni borra la base.

## 7. El job

```bash
IMG=$REGION-docker.pkg.dev/$PROYECTO/confia2/scraper:latest

gcloud run jobs create confia2-ingesta \
  --image=$IMG --region=$REGION --service-account=$CUENTA \
  --set-secrets=SERPER_API_KEY=SERPER_API_KEY:latest,NAN_API_KEY=NAN_API_KEY:latest \
  --set-env-vars=CONFIA2_LLM_MODEL=openai/deepseek-v4-flash,CONFIA2_DATA_DIR=/tmp/confia2 \
  --args=--segment-places,--call-sheet,30,--firestore-project,$PROYECTO \
  --task-timeout=3600 --max-retries=1 --memory=1Gi
```

La imagen ya trae `ENTRYPOINT ["python", "-m", "scraper"]`, así que `--args` es lo único que hace
falta. `CONFIA2_DATA_DIR` apunta a `/tmp` porque en Cloud Run es lo único escribible.

> **Si algún día agregás `--include-procedures`,** la Consulta G pesa 226 MB y hay que subir la
> memoria a 2Gi. Hoy no está en la receta porque esa fuente no aporta señal (ver
> `docs/modulo-1-scraper.md` §2.3).

## 8. El horario

```bash
gcloud scheduler jobs create http confia2-ingesta-mensual \
  --schedule="0 6 1 * *" --time-zone="America/Lima" --location=$REGION \
  --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROYECTO/jobs/confia2-ingesta:run" \
  --http-method=POST --oauth-service-account-email=$CUENTA
```

Mensual alcanza: SUSALUD publica por mes, y la regla de caché de Google Places también se cumple
releyendo cada mes (`docs/firestore.md` §2).

## 9. Verificar

```bash
gcloud run jobs execute confia2-ingesta --region=$REGION --wait
gcloud run jobs executions list --job=confia2-ingesta --region=$REGION
```

El job **imprime los conteos** (`nuevos`, `actualizados`, `clinicas_del_segmento`, `creditos`), que
es la verificación: en la consola de Firestore deberían aparecer los documentos en `prospects` y
`proposals` (el contrato), los mismos en `leads` y `approvals` (las proyecciones con los nombres que
lee la página, ver `docs/para-la-pagina.md` §7) y la procedencia en `confia2_meta`.

Si la página recibe «permiso denegado» con los datos ya escritos, no es un problema de datos: es que
falta la colección en `firestore.rules`. El `match /{document=**}` del final cierra todo lo que no
esté nombrado, y desde el navegador eso se ve igual que una base vacía.

### Reparar los leads sin volver a pagar la búsqueda

El segmento de Places cambia entre corridas, así que quedan clínicas marcadas como `stale`, y hay
etiquetas de segmento viejas (ver `docs/para-la-pagina.md` §7). Las dos cosas se reparan en cada
corrida, pero si hace falta rehacerlo sin gastar los 275 créditos, hay un modo que **solo toca
Firestore**:

```bash
gcloud run jobs execute confia2-ingesta --region=$REGION --project=$PROY --wait \
  --args="--repair-leads,--firestore-project=$PROY"
```

Usa como corte la marca de agua que graba cada corrida (`confia2_meta/leads_watermark`). Si esa marca
no existe todavía (nunca corrió una versión que la grabe), hay que pasar el corte a mano, y el modo
**se niega a correr sin él** a propósito:

```bash
  --args="--repair-leads,--seen-since=2026-10-14T22:20,--firestore-project=$PROY"
```

Ese corte tiene que caer **entre dos corridas**. No uses `confia2_meta/segment.recorded_at`: se escribe
en el medio de la fase de escritura, así que marcaría como viejos leads que esa misma corrida escribió.
**No borra nada**: solo escribe campos derivados (`stale` y `segment`).

## 10. Qué escribe el job y qué nunca toca

Está en `docs/firestore.md` §4, y se aplica en código y con tests:

| El job escribe | El job **nunca** toca |
|---|---|
| Los campos que vienen de las fuentes | **`pipeline_stage`**: lo mueve el CRM |
| `tags` de origen | `manual_tags`, `notes`, `proposals`, `approvals` |

**Un prospecto en `contract_signed` no puede volver a `discovered`** por una corrida de ingesta.
Eso está cubierto por `tests/test_firestore.py`.

## 11. Dos cosas que **no** hace el despliegue, y conviene saber

1. **La caché de búsquedas no sobrevive entre corridas, y está bien que no.** `/tmp` es efímero,
   así que cada ejecución vuelve a hacer las 275 consultas de Places. Es tentador montar otro bucket
   para no pagarlas, y **sería un error**: la regla de caché de Google permite guardar el contenido
   de Places por una ventana limitada, así que **cada corrida tiene que releerlo**. La caché efímera
   no es una limitación: es lo que hace que el job cumpla la regla. Lo que sí se conserva para
   siempre es el `cid`, que está exento y viaja en cada documento.

   La caché **local** (`data/places/`) sigue siendo útil para no pagar dos veces el mismo día
   mientras se desarrolla; lo que no hay que hacer es archivarla como fuente permanente.
2. **Los borradores no se despliegan.** Son por campaña y cuestan llamadas al modelo: hoy se
   generan a mano con `--draft-limit` y quedan en `drafts.json`. Llevarlos a la base y que el
   dueño los apruebe desde el CRM es el paso siguiente, y es del Módulo 2.

## 12. Costos: lo que puedo decir sin inventar

- El job corre **minutos por mes**: Cloud Run cobra por uso, y con este volumen el nivel gratuito
  lo cubre.
- **Firestore:** ~3.300 documentos, una lectura y una escritura por documento y por corrida.
- **Places:** 275 consultas por corrida.
- **El modelo:** solo cuando se generan borradores, ~30 segundos cada uno.

**No pongo cifras en dólares** porque no verifiqué los precios de tu proyecto ni de tu región.
Mirá la consola de facturación después de la primera corrida real, no un estimado mío.

## 13. Las reglas de Firebase (lo que la página necesita)

La página lee Firestore con el **SDK de Firebase** desde el navegador, y ahí las reglas son la
única defensa. El repositorio trae el archivo listo:

```bash
firebase deploy --only firestore:rules --project confia-511504
```

**Antes de desplegarlas hay que completar el correo del dueño** en `firestore.rules`: si la lista
queda con el marcador, **nadie puede leer desde la página**.

Tres cosas que conviene tener claras:

1. **La ingesta no pasa por las reglas.** Escribe con su cuenta de servicio, y el Admin SDK las omite
   por diseño. Por eso `confia2_meta` queda de solo lectura para los clientes.
2. **Las reglas tienen que tener un solo dueño.** Si el repositorio de la página ya despliega reglas
   de Firestore para este mismo proyecto, hay que moverlas ahí: dos archivos desplegándose sobre el
   mismo proyecto se pisan sin avisar.
3. Para producción, un **custom claim** (`request.auth.token.admin == true`) es mejor que una lista
   de correos: no se rompe si el dueño cambia de correo y se administra desde Auth.

## 14. SUSALUD no se alcanza desde Cloud Run (medido, no supuesto)

**Es el hallazgo operativo más importante del despliegue, y salió de un job que terminó «en verde»
habiendo escrito cero documentos.** El log dijo por qué:

```
error: ningun identificador de 'renipress' resolvio en el catalogo:
       registro-nacional-de-ipress-renipress: ConnectTimeout;
       registro-nacional-de-entidades-prestadoras-de-servicios-de-salud-renipress: ConnectTimeout
Container called exit(1).
```

Desde una máquina en Perú el mismo pedido resuelve en **un segundo**. Desde `us-central1` **da
timeout**: el servidor de datos abiertos de SUSALUD no se deja leer desde afuera del país. El job
moría antes de escribir, con la base intacta y sin que nada lo advirtiera hasta mirar el log.

### La solución: una zona de aterrizaje en GCS

Los CSV se suben **una vez desde una máquina que sí alcanza SUSALUD** y el job los lee montados como
volumen. **No hizo falta tocar código**: el pipeline ya sabe usar la copia local cuando el catálogo no
responde, y lo dice por consola.

```bash
BUCKET=confia-511504-datos
gcloud storage buckets create gs://$BUCKET --project=$PROY --location=us-central1

# Los archivos van en la RAÍZ del bucket, no bajo un prefijo. El volumen expone el bucket
# entero en la ruta de montaje: si se suben a `raw/` y se monta en `/tmp/confia2/raw`, quedan en
# `/tmp/confia2/raw/raw/` y el patrón `RENIPRESS_*.csv` no los encuentra — y el job falla con
# «no tiene copia local» después de dos minutos de timeout contra el CKAN. Medido.
gcloud storage cp data/raw/RENIPRESS_*.csv data/raw/ConsultaA_*.csv gs://$BUCKET/

gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member="serviceAccount:$CUENTA" --role="roles/storage.objectViewer"

gcloud run jobs update confia2-ingesta --region=$REGION --project=$PROY \
  --add-volume=name=datos,type=cloud-storage,bucket=$BUCKET \
  --add-volume-mount=volume=datos,mount-path=/tmp/confia2/raw
```

**Y queda una tarea operativa que no desaparece:** refrescar los CSV del bucket es una corrida
**local** en una máquina en Perú (`uv run python -m scraper --refresh`) más un `gcloud storage cp`.
El job no puede hacerlo solo.

Por eso la procedencia importa: el contrato registra el `sha256` de cada archivo leído, así que se
puede ver cuándo la base quedó con datos viejos en vez de suponerlo. Y el job, cuando usa la copia
local, lo escribe en el contrato como *«copia local: el catálogo ya no lo publica»* en vez de
fingir que bajó de SUSALUD.
