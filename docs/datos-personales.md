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

## 4. Decidido

| Decisión | Qué se decidió |
|---|---|
| ¿Se guarda el DNI? | **Sí, hasheado.** Nunca en claro: el hash alcanza para buscar y comparar, y no se puede revertir |
| ¿Quién custodia la clave? | **Secret Manager** (la pimienta, `PERSONAL_DATA_PEPPER`) |
| ¿Qué se protege? | **Los campos que sean información personal de una persona física** |

### Cómo queda cada campo

| Campo | Cómo se guarda | Por qué |
|---|---|---|
| DNI, número de documento | **Hash con pimienta**, irreversible | Solo hay que comparar: nunca hay que mostrarlo |
| Nombre del contacto, su teléfono, su correo | **Cifrado reversible** (especificado, no implementado) | El vendedor tiene que leerlos para hablar con la persona |
| Nombre, teléfono y dirección del establecimiento | En claro, como hoy | Persona jurídica, dato público (ver §2) |

### Dos consecuencias que no son obvias

1. **La pimienta necesita un permiso separado del de Firestore.** Si el mismo permiso da acceso a la
   base y al secreto, la pimienta no protege de la amenaza de §1. Y tiene que poder **rotarse**: una
   pimienta cacheada en una variable global de larga vida es una pimienta que no se puede rotar.
   Ojo con el costo de rotar: los datos ya hasheados **dejan de encontrarse** hasta re-hashearlos.
2. **El dato personal se escribe desde el backend, no desde el navegador.** La página escribe hoy
   directo a Firestore, y eso está bien para datos públicos. Para un dato personal no: una clave que
   se usa en la página viaja al navegador, o sea que está en la máquina de cualquiera que abra las
   herramientas de desarrollo. **`installed_base` con datos personales tiene que escribirse por la
   API**, que es la única que tiene la pimienta.

### Qué va hasheado, qué va cifrado y qué queda en claro

La regla, en una frase: **si hay que mostrarlo, cifrado; si solo hay que compararlo, hasheado; si es
del establecimiento, en claro.**

| Dato | Cómo se guarda | Se puede buscar por él |
|---|---|---|
| DNI, número de documento | Hash con pimienta | Sí, **solo por igualdad** (nunca por rango ni por prefijo) |
| Nombre del contacto, su teléfono, su correo | Cifrado reversible | **No** |
| Nombre, teléfono y dirección del establecimiento | En claro | Sí, con cualquier filtro |
| `directorMedico` | No se guarda: ninguna fuente lo trae | — |

**Ese "no" de la tercera columna es la trampa de "ciframos todo".** Firestore no puede hacer
`where("distrito", "==", ...)` sobre un texto cifrado, y Fernet es aleatorio a propósito: el mismo
nombre cifrado dos veces da dos textos distintos, así que ni siquiera se puede agrupar por él. Cifrar
un campo es decidir que no se va a poder filtrar por él — y los filtros del CRM son el producto.

### Estado de la implementación

Los dos mecanismos están **hechos y probados** en `backend/app/personal_data.py`, con **16 tests**:

- **Hash con pimienta** (`hash_identificador`, `coincide`, `normalizar`) para lo que solo hay que
  comparar. Solo biblioteca estándar.
- **Cifrado reversible** (`cifrar`, `descifrar`, `descifrar_con_rotacion`) para lo que hay que leer.
  Fernet, de `cryptography`, con la clave en Secret Manager.

Cuatro detalles que los tests fijan a propósito:

1. **Sin pimienta o sin clave, falla** en vez de usar una por defecto o guardar en claro. Una clave por
   defecto es lo mismo que no tener clave, y se descubre cuando ya hay datos guardados con ella.
2. **Un dato manipulado no se puede leer**: Fernet es autenticado, así que un texto cifrado alterado
   falla en vez de devolver basura como si fuera un dato bueno.
3. **`coincide` usa `hmac.compare_digest`**: comparar con `==` corta en el primer byte distinto, y ese
   tiempo distinto alcanza para adivinar el hash byte por byte.
4. **Rotar la clave no pierde datos**: `descifrar_con_rotacion` prueba la nueva y después las
   anteriores, así que al rotar se agrega una clave y lo viejo se sigue leyendo hasta re-cifrarlo.

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
