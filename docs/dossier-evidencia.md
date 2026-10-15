# Dossier de evidencia

> Todo lo que sigue está **medido**, no estimado. Cada fila dice con qué comando se verifica.
> Lo que no se pudo medir está en la sección 5, junto con la razón: **un dato que no existe
> declarado vale más que un dato inventado.**
>
> **Las cifras son del 14-10-2026, y hay que fecharlas al citarlas, porque no todas envejecen igual.**
> El **padrón** es estable: los 2.459 salen de un CSV de SUSALUD y solo cambian cuando se sube uno
> nuevo. El **segmento no lo es**: Google Places no devuelve el mismo conjunto en cada corrida con la
> misma consulta. Medido el mismo día: **829** (20:56), **791** (21:51) y **774** (22:12). Los números
> del segmento de este documento (829, 529, 505, 462) son de esas corridas, y en la última quedaron
> **511** clínicas dentro del segmento. Un número del segmento sin fecha no es evidencia: es una
> medición de un momento.

---

## 1. El problema, en números

| Hecho | Número | Cómo se verifica |
|---|---|---|
| Leads serios por semana que recibe la empresa hoy | **1 a 3** | Dato del documento maestro (§1), a confirmar con el dueño |
| Clínicas de fisioterapia y rehabilitación **llamables** en Lima | **462** | `uv run python -m scraper --segment-places --call-sheet 30` |
| Personas dedicadas a prospectar | **1** (el dueño, que además vende) | Documento maestro §2 |

No falta demanda. Falta **capacidad de prospección**: hay 462 clínicas identificadas por nombre,
teléfono y ubicación, y una sola persona para contactarlas.

## 2. El mercado, contado con datos abiertos

Del registro oficial de SUSALUD (RENIPRESS), corte 30-09-2026:

| Escalón | Registros | Qué es |
|---|---|---|
| IPRESS registradas en el Perú | **36.128** | Todo el universo |
| Activas y privadas de categoría I-3/I-4 | **2.459** | El perfil objetivo del documento maestro |
| De esas, en Lima | **898** | Donde el negocio quiere empezar |

Y la calidad del dato, que es lo que hace usable esa lista:

| Campo | Cobertura sobre los 2.459 |
|---|---|
| Teléfono válido | **2.457 (99,9 %)** |
| Dirección y distrito | **2.459 (100 %)** |
| Coordenadas para mapa y ruteo | **2.091 (85 %)** |
| Categoría y clasificación del establecimiento | **100 %** |
| Años de operación (10 o más) | **921 (37 %)** |
| Capacidad médica declarada | 248 (10 %) |

## 3. El segmento enfocado: fisioterapia y rehabilitación

**El hallazgo comercial más importante del proyecto.** El registro de SUSALUD clasifica
**establecimientos, no especialidades**: de 2.459 prospectos, exactamente **uno** figura como
`MEDICINA FISICA`. Buscando por especialidad en Google aparecieron **93 clínicas de fisioterapia
en los 10 distritos más poblados de Lima**, y **ninguna estaba en la lista del padrón**.

| Métrica | Valor |
|---|---|
| Consultas ejecutadas (55 distritos × 5 especialidades) | 275 |
| Lugares únicos encontrados | **829** (1.562 resultados crudos: 56 % de duplicación) |
| **En el segmento** (su categoría es fisio/rehab/dolor) | **529** |
| Fuera de categoría, contados aparte | 300 |
| **Con teléfono y coordenada: llamables hoy** | **462** |
| Con sitio web | 256 |
| Con 100 reseñas o más | **24** |
| En una marca con varias sedes | **66**, en 17 grupos |

**Lo que cambia el argumento de venta:** el segmento no admite un contacto genérico. Son centros
de fisioterapia con reseñas públicas, calificación visible y un dueño o fisioterapeuta jefe que
decide rápido — nada que ver con el comité de compra de una clínica I-4.

### La competencia, medida

| Verificación | Resultado |
|---|---|
| Lugares que **ya ofrecen ozonoterapia** en Lima (55 distritos) | **113** |
| De esos, que están en nuestro segmento de fisioterapia | **24** |
| **Clínicas del segmento SIN oferta visible de ozono** | **505 de 529 (95,5 %)** |

El 95,5 % del segmento enfocado es **espacio libre**: clínicas de fisioterapia y rehabilitación que
atienden dolor y no ofrecen ozonoterapia. Y los 113 que sí la ofrecen quedaron identificados
—`Instituto Médico de Ozonoterapia`, `Ozono Integral Perú`, `Ozonomédica`, `Unidad de Ozonoterapia
Perú`—, lo que además responde quién es la competencia actual en el canal.

> **Ojo con la interpretación:** "sin oferta visible" significa que no aparece publicando
> ozonoterapia, no que se haya verificado clínicamente. Una clínica puede ofrecerla sin
> publicitarla. El número es un piso de espacio libre, y así se reporta.

### Cuánto hay fuera de Lima (piso, no techo)

| Ciudad | Lugares |
|---|---|
| Arequipa · Cusco · Huancayo · Trujillo · Ica | 18 cada una |
| Piura · Cajamarca · Chiclayo | 17 cada una |
| Tacna | 16 |
| Puno | 15 |
| **Total en 10 ciudades** | **≥ 172** |

**Es un piso, no un total:** cada consulta devuelve una página (20 resultados como máximo) y las
ciudades quedaron en 15 a 18, o sea que se topó con la página. Medir una ciudad de verdad exige
consultar por distrito, como se hizo en Lima.

### Cadenas: una llamada, varias colocaciones

| Marca | Sedes |
|---|---|
| Centro Médico OSI | **8** |
| Clínica Internacional | 4 |
| Fisiomanos Perú / FisioRenova / FisioPerú | 3 |
| Artrauma, Fisiofort, Fisio Centro, ArthroSalud, ARIE… | 2 cada una |

Sin la detección de cadenas, el vendedor hacía **8 llamadas** donde hay **una conversación con 8
colocaciones posibles**. Se detectan por el mismo teléfono publicado, que es evidencia exacta.

## 4. Lo que construimos, medido

| Pieza | Resultado | Costo |
|---|---|---|
| Ingesta de datos abiertos de SUSALUD | 2.459 prospectos, 3,6 MB, con `sha256` de cada archivo leído | **7 segundos** (con caché) |
| Búsqueda del segmento en Google | 529 clínicas en 55 distritos | **275 consultas**, ~9 minutos |
| Copiloto de redacción | Borradores personalizados con verificación anti-invención | ~30 s por borrador |
| Hoja de llamados | Markdown con las mejores N, con teléfono y motivo | instantánea |
| Pruebas automáticas | **211 tests**, ninguno toca la red | 4 segundos |

**Créditos gastados en todo el proyecto: menos de 400** de un cupo gratuito de 2.500.

### El tiempo, que es lo que se ahorra

| Tarea | A mano | Con el sistema |
|---|---|---|
| Identificar las 529 clínicas del segmento | ~44 horas | **9 minutos** |
| Saber cuáles ya publican ozonoterapia | hay que repetir la búsqueda clínica por clínica | incluidas las 55 consultas |
| Redactar el primer contacto personalizado | ~10 minutos por clínica | ~30 segundos |
| Armar la hoja de llamados | una planilla mantenida a mano | instantánea, y se regenera gratis |

**Qué está medido y qué no:** los 9 minutos son el tiempo real de la corrida, y los 30 segundos por
borrador también. Los **~44 horas** salen de suponer 5 minutos por clínica, y los 10 minutos de
redacción son una estimación. Esos dos hay que validarlos con el dueño: son los únicos números de
esta tabla que no salen de una medición.

### La garantía anti-invención, que es lo que se puede defender ante un jurado

El copiloto no le *pide* al modelo que no invente: se lo **impide**. El texto comercial y
regulatorio vive en una plantilla que edita el dueño y se ensambla en código; el modelo solo llena
cuatro ranuras. Después, un verificador compara **cada número** del borrador contra los datos
reales, y un borrador con una cifra o una promesa regulatoria no respaldada **se rechaza**.

En la corrida real con una clínica sin dato de capacidad, el modelo escribió *"No contamos con el
dato de médicos registrados, por lo que una visita técnica permitiría conocer su equipo"* en vez de
inventar un número. Ese era el objetivo.

## 4bis. El último paso del circuito: los borradores

Se generaron **10 borradores** para las 10 primeras de la hoja de llamados:

| Verificación | Resultado |
|---|---|
| Borradores | **10** |
| Con hallazgos del verificador | **0** |
| Estado | `pending_approval`: **ninguno se envió** |
| Datos que faltan completar a mano | solo `[FIRMA DEL DUEÑO]`, que es del dueño |

El ejemplo de `Artrauma` (553 reseñas) usa la categoría, el distrito, las **2 sucursales**, la
calificación de 4,8, las 553 reseñas y el sitio web. El párrafo comercial del dueño quedó **byte a
byte**, porque el modelo no lo produjo: se ensambla en código.

> **Y un defecto que salió de leerlos en vez de contarlos:** el modelo citaba nuestra jerga interna
> —*"tiene la etiqueta physiotherapy-segment"*— en un mensaje dirigido a un médico. Las etiquetas
> son para filtrar en el CRM, no vocabulario para el cliente. Se sacaron de los datos que ve el
> modelo y el prompt ahora lo prohíbe explícitamente.

## 5. Lo que **no** se puede obtener, con la razón

| Lo que se querría | Por qué no se puede |
|---|---|
| Email de las clínicas | **Ninguna de las fuentes lo publica.** Se probaron los sitios de clínicas: 0 de 3 lo muestran. El canal es teléfono o visita |
| Nombre del director médico | RENIPRESS publica el establecimiento, no a su gente. CMP da médicos colegiados, pero sin ligarlos a una clínica |
| RUC | RENIPRESS no lo trae; cruzarlo obliga a un *matching* por nombre, que falla (ver §6) |
| **"IPRESS que aún no ofrecen ozonoterapia"** | Medido: el catálogo nacional de SUSALUD (7.457 procedimientos) **no tiene** ozonoterapia codificada. No es que nadie la haga: es que la fuente no puede expresarlo |
| Capacidad médica para el 90 % del padrón | La Consulta A es un reporte de actividad, no un padrón: cubre 248 de 2.459. **Y SUSALUD retiró ese paquete del catálogo el 14-10-2026**, así que además puede no volver a actualizarse: quedaron publicados los de 2015 a 2018 |

## 6. Las tres veces que **corregimos un número propio antes de publicarlo**

Esto es lo que hace creíble al resto. Cada uno de estos números se informó primero mal y se
verificó después:

| Lo que decíamos | Lo que era | Cómo se descubrió |
|---|---|---|
| "El enriquecimiento web detecta quién hace ozono" | **0 de 50 usable**: las páginas que encontraba eran directorios, no las clínicas | Corrida de 50 clínicas con muestra sistemática |
| "385 de 829 clínicas están en cadenas" | **66**. El detector agrupaba por la primera palabra y daba `fisio` con 34 sedes | Verificar el número antes de publicarlo |
| "El enriquecimiento cubre el perfil" | El detector por nombre daba **1.468** prospectos; el preciso, **254** | Comparar dos métodos sobre el mismo dato |

Y tres defectos que encontró usar el software en vez de confiar en él: un `500` de Serper que
volteaba una corrida de 275 consultas, un espacio de más en el `.env` que rompía solo al
contenedor, y un `--segment-top` que sobrescribía el segmento completo con uno de un tercio.

Y un cuarto, el más peligroso de todos porque **el artefacto salía normal**: el fallback del
catálogo prefería un dataset de **2018** antes que la copia local de 2026, y la cobertura de
capacidad cayó de **248 prospectos a 33 sin decir nada**. Se detectó mirando los números de una
corrida que "funcionaba bien". Ahora la copia local va antes que cualquier dataset alternativo, y
la procedencia queda marcada en el contrato como copia local.

### Y uno de producción, que es el más serio

**SUSALUD retiró del catálogo el paquete de recursos de salud** mientras este proyecto se
construía: el identificador que usábamos pasó a responder `404` de un día para el otro. El
pipeline **moría con 404 aunque el CSV ya estuviera en disco**, que es la peor forma de fallar:
los datos están y el proceso se cae igual.

Ahora prueba todos los identificadores conocidos de cada fuente y, si ninguno resuelve, **usa la
copia local más reciente y lo dice en voz alta**, marcando la corrida como no refrescada. Un
dataset que se muda no puede voltear el sistema.

## 7. Cómo se verifica cada número

```bash
uv run python -m scraper                    # 2.459 prospectos del padrón, 7 s
uv run python -m scraper --segment-places   # 529 del segmento, 275 créditos la primera vez
uv run python -m scraper --segment-places --call-sheet 30   # la hoja de llamados
uv run pytest                               # 211 tests, ninguno toca la red
```

Los CSV crudos quedan en `data/raw/` y las búsquedas en `data/places/`: **volver a correr
cualquier cosa no cuesta créditos**, así que cualquiera puede auditar los números sin gastar nada.

## 8. Lo que este dossier **no** dice

- **No hay precios ni ROI.** Nadie definió el ticket ni el costo del equipo: en el documento
  maestro están como `[US$ __ / mes]`. Poner un número ahí sería inventarlo.
- **No hay compromiso de conversión.** El informe de investigación estima 10 a 15 leads semanales y
  más de 25 % de conversión: son **hipótesis del informe**, no mediciones nuestras.
- **No se contactó a ninguna clínica.** Todo lo de arriba es análisis de datos públicos.
