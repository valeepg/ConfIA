# Qué datos hay, cuáles son personales y qué se cifra

> La pregunta que este documento contesta: **qué ciframos y qué no.** La respuesta corta es que
> primero hay que separar dos cosas que se mezclan todo el tiempo — lo que **ya está cifrado** (todo,
> en reposo, por Google) y lo que queremos que **ni nosotros podamos leer**. Confundirlas da la
> sensación de estar protegido sin estarlo.

---

## 1. Lo que Firestore ya cifra, y por qué no alcanza

Todo lo que está en Firestore está cifrado en reposo con claves administradas por Google, y viaja
cifrado en tránsito (TLS). En el sentido literal, «cifrado en la nube» **ya es verdad**: nada de lo
que hay hoy en la base está en texto plano sobre el disco de Google.

Lo que eso **no** resuelve es la pregunta que importa para la Ley N.° 29733. Si mañana alguien tiene
permiso de lectura sobre el proyecto —un empleado, una credencial filtrada, un `gcloud` mal usado—,
**lee todo**. El cifrado en reposo protege contra el robo del disco; no protege contra el uso indebido
de un permiso. Son amenazas distintas y se defienden distinto.

## 2. Qué hay hoy en la base, y qué es personal

| Colección | Dato | ¿Personal? | Por qué |
|---|---|---|---|
| `prospects`, `leads` | Nombre del establecimiento | **No** | Persona jurídica, publicado por SUSALUD |
| `prospects`, `leads` | Teléfono y dirección del establecimiento | **No** | Publicados por SUSALUD y Google; son de contacto comercial |
| `prospects`, `leads` | Distrito, categoría, especialidad, coordenadas | **No** | Del establecimiento |
| `leads.google` | Rating, reseñas, sitio web | **No** | Publicado por Google |
| `proposals`, `approvals` | El texto del borrador | **No** | No contiene datos de ninguna persona |
| `confia2_meta` | Fechas y `sha256` de los archivos leídos | **No** | Metadatos de la corrida |
| `users` | Correo y rol del personal | **Sí** | Identifica a una persona |
| `installed_base` | **Vacío hoy** | — | Cuando el dueño convierta un cliente, acá sí van a caer datos personales |

**Hoy la ingesta no guarda un solo dato personal de una persona física.** Nombre, teléfono y dirección
de una clínica son de una persona jurídica, y por eso se pueden archivar y mostrar. El dato personal
aparece en dos lugares, y ninguno es todavía una colección con datos: `users` (el personal, 4 personas)
e `installed_base` (el cliente del negocio, que es **la parte que falta construir**).

## 3. La decisión: cada dato cae en una de tres categorías

La regla es que un dato cae en **una sola**, y se decide dato por dato, no "ciframos todo":

**a. No se guarda.** La Ley N.° 29733 pide minimización: lo que no hace falta, no se pide. La pregunta
a contestar antes de agregar un campo es *para qué*, y "por si acaso" no es una respuesta.

**b. Se guarda con hash (irreversible).** Cuando solo se necesita **comparar** si dos registros son la
misma persona, un hash con sal alcanza, y es irreversible: si se filtra, no se puede volver al DNI.
El DNI es el caso típico de esto.

**c. Se guarda cifrado a nivel aplicación.** Cuando hay que **leerlo** —el nombre de la persona con la
que habla el vendedor, su teléfono— va cifrado con una clave que **no vive en Firestore**. Cloud KMS,
en un proyecto con un permiso IAM separado. Así, una credencial que lee Firestore **no alcanza** para
leer el dato: es exactamente la amenaza de la sección 1.

## 4. Lo que hay que decidir antes de escribir código

| Decisión | Opciones | Recomendación |
|---|---|---|
| ¿Se guarda el DNI? | sí / no / solo hash | **No** hoy. Si el negocio lo necesita para el contrato, **hash**, nunca en claro |
| ¿Quién custodia la clave? | Cloud KMS / Secret Manager | **Cloud KMS**, con IAM separado del de Firestore y plan de rotación |
| ¿Qué se cifra a nivel aplicación? | — | Solo lo que identifique a una persona física: nombre del contacto, su teléfono, su correo |
| ¿Quién puede descifrar? | — | El dueño y el vendedor, **en la pantalla**. La ingesta, nunca |

Mientras esas cuatro no estén decididas, `installed_base` puede construirse con los datos del
establecimiento (que no son personales) y **dejar los campos de persona vacíos**, igual que se hizo
con `directorMedico`: vacío declarado vale más que dato inventado o mal protegido.

## 5. Tres cosas que **no** hay que hacer

- **No cifrar el nombre ni el teléfono de la clínica.** Son datos públicos de una persona jurídica:
  cifrarlos rompería los filtros y las búsquedas de la página, y no protegería a nadie. Cifrar de más
  también es un error, porque hace que el sistema parezca más seguro de lo que es y esconde el trabajo
  que sí importa.
- **No guardar la clave junto a los datos.** Una clave en el mismo proyecto que la base no protege
  contra la amenaza de la sección 1: si alguien tiene acceso de lectura, probablemente también la clave.
- **No cifrar para cumplir.** La Ley N.° 29733 no exige cifrado: exige finalidad, proporcionalidad y
  seguridad **adecuada al riesgo**. Un DNI que no se necesitaba, cifrado, sigue siendo un dato que no
  había que pedir.
