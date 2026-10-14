\---



\## 🛠 Stack Tecnológico

\* \*\*Frontend:\*\* Next.js / React (Desplegado en \*\*Vercel\*\*).

\* \*\*Backend Core:\*\* \*\*FastAPI\*\* en \*\*Google Cloud Run\*\* (Arquitectura Stateless).

\* \*\*Base de Datos \& Auth:\*\* \*\*Firebase Firestore\*\* + Firebase Auth.

\* \*\*Agente / Modelo LLM:\*\* \*\*Gemini Flash\*\* (vía Google Cloud / Vertex AI).

\* \*\*Seguridad:\*\* Google Cloud Secret Manager + Cloud KMS (Cifrado At-Rest / In-Transit).



\---



\## 📋 Requerimientos del Sistema Divididos por Módulo (4 Owners)



\### 🔹 MÓDULO 1: Extracción, Ingesta \& Seguridad de Infraestructura

> 👤 \*\*Owner:\*\* \*Data \& Security Engineer / Backend Scraper\*



\#### Requerimientos Funcionales:

\* \*\*RF-01 (Scraping de IPRESS y Directorios Médicos):\*\* Scripts de extracción sobre fuentes públicas (SUSALUD, Colegio Médico del Perú - CMP y padrones de licencias comerciales) para construir la base inicial de prospectos B2B.

\* \*\*RF-02 (Normalización y Limpieza de Datos):\*\* Transformar los datos extraídos (RUC, IPRESS, especialidades, ubicación, Director Médico) a formato JSON estandarizado para su inyección en la base de datos.



\#### Requerimientos No Funcionales (Seguridad \& Cumplimiento):

\* \*\*RNF-01 (Cifrado en Tránsito y Reposo):\*\* Garantizar comunicación mediante HTTPS/TLS 1.3 y verificar el cifrado \*at-rest\* en Firebase Firestore mediante Google Cloud KMS.

\* \*\*RNF-02 (Gestión Centralizada de Secretos):\*\* Configurar Google Cloud Secret Manager para almacenar credenciales, tokens y API Keys. Prohibidas llaves hardcodeadas en código fuente.

\* \*\*RNF-03 (Cumplimiento de Protección de Datos):\*\* Tratamiento de padrones comerciales e institucionales conforme a la Ley N° 29733 (Ley de Protección de Datos Personales del Perú).



\---



\### 🔹 MÓDULO 2: Maquetación Frontend CRM \& Experiencia de Usuario

> 👤 \*\*Owner:\*\* \*Frontend Engineer (UI/UX)\*



\#### Requerimientos Funcionales:

\* \*\*RF-03 (Dashboard de Pipeline Comercial Outbound):\*\* Interfaz tipo Kanban/Tabla (servida en \*\*Vercel\*\*) para visualizar el flujo de ventas B2B (\*Descubierto, Contactado, Propuesta Enviada, Contrato Firmado\*).

\* \*\*RF-04 (Módulo de Posventa y Retención):\*\* Panel de control para seguimiento del parque instalado, proyección de consumo de insumos (kits AHTm, líneas sin PVC) y alertas de mantenimiento preventivo DIGEMID.

\* \*\*RF-05 (Interfaz de Aprobación del Copiloto - Human-in-the-Loop):\*\* Pantalla para que el dueño apruebe con 1 clic los borradores Outbound y Dossiers generados por la IA antes del envío.



\#### Requerimientos No Funcionales:

\* \*\*RNF-04 (Rendimiento y Carga Rápida):\*\* Mantener un tiempo de carga (Largest Contentful Paint - LCP) inferior a 1.5 segundos en la interfaz del CRM.



\---



\### 🔹 MÓDULO 3: Lógicas de Negocio, Scoring \& Outbound Proactivo

> 👤 \*\*Owner:\*\* \*Core Backend \& Business Logic Engineer\*



\#### Requerimientos Funcionales:

\* \*\*RF-06 (Algoritmo de Lead Scoring B2B):\*\* Función en \*\*FastAPI\*\* que evalúa variables de la IPRESS (infraestructura, especialidades de dolor/traumatología, ubicación) y asigna un puntaje de prioridad comercial.

\* \*\*RF-07 (Lógica de Alertas de Posventa):\*\* Motor de cálculo que estima la tasa de agotamiento de consumibles médicos basándose en fecha de instalación y volumen de uso.

\* \*\*RF-08 (Orquestación del Flujo Outbound):\*\* Reglas de negocio para activar secuencias de contacto B2B personalizadas según la calificación del lead.



\#### Requerimientos No Funcionales:

\* \*\*RNF-05 (Arquitectura Stateless Escalable):\*\* Microservicios de lógica en FastAPI sobre \*\*Google Cloud Run\*\* diseñados sin estado para permitir autoescalado horizontal.



\---



\### 🔹 MÓDULO 4: Agente de IA (Gemini Flash) \& Arquitectura de Base de Datos

> 👤 \*\*Owner:\*\* \*AI \& Database Engineer\*



\#### Requerimientos Funcionales:

\* \*\*RF-09 (Modelado de Datos en Firebase Firestore):\*\* Diseñar y mantener el esquema NoSQL (colecciones: `prospects`, `proposals`, `installed\_base`, `users`).

\* \*\*RF-10 (Agente Redactor Outbound - Gemini Flash):\*\* Integración con Gemini Flash para redactar mensajes de contacto hiperpersonalizados dirigidos a Directores Médicos (\*Modelo Ozone-as-a-Service / OpEx\*).

\* \*\*RF-11 (Generador de Dossier Regulatorio y ROI):\*\* Agente de IA que compila datos del lead para generar propuestas de costo-beneficio financiero y carpetas de cumplimiento con normativas DIGEMID.



\#### Requerimientos No Funcionales:

\* \*\*RNF-06 (Estructuración Rígida Anti-Alucinaciones):\*\* Implementar \*Structured Outputs\* (modo JSON/Pydantic) en Gemini Flash para garantizar que la IA no invente Registros Sanitarios ni especificaciones técnicas.

\* \*\*RNF-07 (Reglas de Seguridad en Base de Datos):\*\* Configuración estricta de \*Firestore Security Rules\* para restringir accesos según el rol autenticado.



\---



\## ⚡ Regla de Integración Rápida (Paso Cero para la Hackathon)



Para evitar bloqueos e integrar todos los componentes sin fricción en pocas horas:



1\. \*\*Definición del Mock JSON (30 mins iniciales):\*\* El \*Owner del Database\* comparte el archivo `prospect\_mock.json` oficial con el esquema exacto de Firebase.

2\. \*\*Desarrollo en Paralelo:\*\* 

&#x20;  \* \*\*Frontend\*\* maqueta pantallas usando la estructura del JSON falso.

&#x20;  \* \*\*Scraper\*\* sabe qué campos poblar.

&#x20;  \* \*\*AI Agent\*\* sabe qué variables leer y sobreescribir.

3\. \*\*Conexión Final:\*\* Sustituir los Mocks locales por las llamadas a las APIs de FastAPI y Firebase.



\---

