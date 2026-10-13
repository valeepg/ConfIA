# Especificación Técnica — Módulo 2: Maquetación Frontend CRM & Experiencia de Usuario

> **Owner:** Frontend Engineer (UI/UX)  
> **Estado:** Aprobado para Construcción  
> **Código de Módulo:** MOD-CRM-02  
> **Documentos de Referencia:** [README.md](file:///d:/Proyectos/Confia/README.md), [constitution.md](file:///d:/Proyectos/Confia/constitution.md), [AGENTS.md](file:///d:/Proyectos/Confia/AGENTS.md)

---

## 1. Resumen Ejecutivo y Objetivos

Este documento especifica la arquitectura, interfaces, modelos de datos de frontend y flujos de interacción para el **Módulo 2 (Frontend CRM & UX)** de la plataforma ConfIA. 

El objetivo es proveer al dueño y equipo comercial de la empresa distribuidora de ozonoterapia médica una consola de alta eficiencia servida en Vercel, optimizada para LCP < 1.5s, que operacionalice la venta B2B de equipos biomédicos bajo el modelo **Ozone-as-a-Service (OaaS)** y garantice la supervisión humana (*Human-in-the-Loop*) de los copilotos de IA.

---

## 2. Matriz de Requerimientos

| ID | Tipo | Nombre | Descripción Técnica |
|---|---|---|---|
| **RF-03** | Funcional | Dashboard de Pipeline Comercial Outbound | Vista Kanban y Tabla con 4 etapas comerciales (*Descubierto, Contactado, Propuesta Enviada, Cierre*), tarjetas con score del lead (0-100), filtros por especialidad y banner reactivo de telemetría de lectura desde OzonePedia. |
| **RF-04** | Funcional | Módulo de Posventa y Retención | Panel de control con métricas de parque instalado, tabla de monitoreo de insumos críticos (*Kits AHTm, líneas sin PVC, frascos de vacío*) con estados (*Agotado, Reabastecer pronto, Al día*), alertas de mantenimiento preventivo y calibración anual DIGEMID, y seguimiento de capacitación médica. |
| **RF-05** | Funcional | Interfaz de Aprobación del Copiloto (Human-in-the-Loop) | Drawer lateral y modales de aprobación de 1 clic para: (a) mensajes outbound personalizados, (b) propuesta financiera ROI OaaS, (c) dossier regulatorio DIGEMID (Clase II/III), y (d) recordatorios de insumos. |
| **RNF-04** | No Funcional | Rendimiento y Carga Rápida | LCP < 1.5s en conexiones estándar. Bundle optimizado, server-side/static rendering inicial con hidratación mínima, fuentes autoalojadas o pre-conectadas y zero bloqueo de renderizado. |

---

## 3. Sistema de Diseño (Design System Tokens)

El diseño replica con fidelidad médica y elegancia institucional las interfaces conceptuales validadas.

### 3.1. Paleta Cromática
- **Dark Slate Sidebar:** `#071C21` (fondo principal de navegación lateral), `#0E2E33` (hover y elementos activos).
- **Warm Canvas (Fondo):** `#FAF9F5` / `#F3EFE6` (sensación cálida, editorial y de alta confianza médica).
- **Surface Cards:** `#FFFFFF` con sutil borde `#E5E7EB` y sombra difusa `0 1px 3px rgba(0,0,0,0.05)`.
- **Clinical Emerald (Acentos principales):**
  - Botón de acción primaria: `#0B6E4F` / `#059669`.
  - Estados "Al día": `#10B981` (fondo suave: `#ECFDF5`, texto: `#065F46`).
- **Amber / Gold (Alertas IA & Telemetría):**
  - Banner y badges "Borrador de IA": `#D97706` (fondo suave: `#FEF3C7`, texto: `#92400E`).
- **Red Alert (Consumo crítico / Agotado):**
  - Badge "Agotado": `#DC2626` (fondo suave: `#FEE2E2`, texto: `#991B1B`).

### 3.2. Tipografía y Jerarquía
- **Encabezados Principales (`h1`, `h2`, títulos de clínicas):** Tipografía Serif (*Playfair Display* o *Merriweather*), peso 600/700, transmitiendo rigor científico y tradición clínica.
- **Cuerpo, Métricas y UI (`p`, `span`, botones, tablas):** Sans-serif humanista (*Plus Jakarta Sans* o *Inter*), peso 400/500/600.

---

## 4. Estructura de Pantallas y Componentes

### 4.1. Shell Global (Layout)
- **Barra Lateral Izquierda (Fija, 260px):**
  - Logotipo: `ConfIA` (isotipo de ozono / escudo clínico).
  - Menú de navegación:
    - 📊 **Pipeline** (Ruta activa por defecto)
    - 🏢 **Prospectos**
    - 🔄 **Posventa**
    - 📈 **Analítica del hub**
    - 📄 **Documentos**
  - Pie de barra: Perfil de usuario (`Dueño / Ventas`) con avatar circular y estado en línea.

---

### 4.2. Vista 1: Pipeline B2B Outbound (RF-03)
1. **Header de Métricas (KPI Cards Superiores):**
   - *Prospectos activos:* `8`
   - *Borradores por aprobar:* `1` (destacado en ámbar)
   - *Propuestas enviadas:* `2`
   - *Clientes activos:* `4` (destacado en verde)
2. **Banner Reactivo de Telemetría (Radar de Intención):**
   - Franja destacada en oro suave: `🔔 Alerta nueva: Clínica Santa Rosa Sur está leyendo protocolos en la OzonePedia.`
   - Al hacer clic abre directamente el Drawer de Detalle del Lead.
3. **Tablero Kanban (4 Columnas):**
   - **Columna 1: Descubierto (3)**
     - *Clínica Andina* (San Isidro · Traumatología, Score: 85, "Nueva clínica de rehabilitación detectada").
     - *Centro del Dolor Sur* (Surco · Medicina del dolor, Score: 76, "Sin ozonoterapia en su oferta").
     - *Clínica Pacífico Norte* (Miraflores · Rehabilitación, Score: 68, "Director médico identificado").
   - **Columna 2: Contactado (2)**
     - *Instituto Dolor Lima* (San Borja · Traumatología, Score: 91, Badge: `Borrador de IA por aprobar`).
     - *Clínica Santa Rosa Sur* (Chorrillos · Dolor y rehabilitación, Score: 71, Badge: `Alerta de lectura activa`).
   - **Columna 3: Propuesta enviada (2)**
     - *Centro Integral de Rehabilitación* (La Molina · Rehabilitación, Score: 92, "Propuesta ROI enviada").
     - *Clínica Vida Mar* (Barranco · Medicina del dolor, Score: 82, "Dossier DIGEMID enviado").
   - **Columna 4: Cierre (1)**
     - *Clínica del Prado* (Jesús María · Traumatología, Score: 89, "Acuerdo de comodato firmado").

---

### 4.3. Vista 2: Drawer Lateral de Detalle del Lead y Radar (RF-03 & RF-05)
Se abre al hacer clic sobre cualquier tarjeta de prospecto (ejemplo: *Clínica Santa Rosa Sur*):
1. **Encabezado del Prospecto:**
   - Nombre: `Clínica Santa Rosa Sur`
   - Ubicación & Especialidad: `Chorrillos · Dolor y rehabilitación`
   - Datos del decisor: `Director médico: Dr. Juan Carlos Ramos · Especialistas: Traumatología`
2. **Panel "Actividad en la OzonePedia" (Telemetría de Lectura):**
   - 📄 *Protocolo de autohemoterapia mayor (AHTm):* 2 lecturas
   - ⏱️ *Hernia discal lumbar:* 14 min de lectura
   - 🔍 *Búsqueda reciente:* "costo-beneficio ozonoterapia"
3. **Tarjeta "Sugerencia de la IA" (Copiloto):**
   - Texto generado: *"Preparar una propuesta enfocada en el ROI de consulta con dolor de espalda y fechar visita esta semana."*
   - Badge: `Borrador de IA: requiere tu aprobación`
4. **Acciones Human-in-the-Loop (1 Clic):**
   - Botón Primario: **Revisar propuesta ROI** (Abre modal de propuesta financiera OaaS).
   - Botón Secundario: **Ver dossier DIGEMID** (Abre visor de carpeta técnica regulatoria).
   - Enlace: *Posponer contacto*.

---

### 4.4. Vista 3: Modales de Aprobación Human-in-the-Loop (RF-05)
1. **Modal de Propuesta ROI OaaS:**
   - Modelo de equipo: *Generador O3 Médico Digital Clase IIb con Destructor de Ozono Catalítico*.
   - Modalidad: *Comodato OaaS condicionado a 25 kits AHTm/mes*.
   - Proyección financiera para la clínica:
     - Costo por sesión para clínica: ~S/ 35 (insumos).
     - Tarifa promedio al paciente en Lima: S/ 150 – 220 por sesión de AHTm.
     - Margen neto mensual estimado: S/ 8,500 – 14,000.
   - Acciones: `[Aprobar y Enviar]` (1 clic), `[Editar Variables]`, `[Descartar]`.
2. **Modal de Dossier Regulatorio DIGEMID:**
   - Verificación de Registro Sanitario DIGEMID (Código: `DM-XXXX-EE`).
   - Copia de Certificado de Calibración de fábrica.
   - Plantilla de Consentimiento Informado del MINSA/ISCO3.
   - Acciones: `[Adjuntar al Lead]`, `[Exportar PDF]`.
3. **Modal de Borrador Outbound (Correo / LinkedIn):**
   - Destinatario: Director Médico.
   - Asunto: *"Incorporación de Ozonoterapia Sistémica en [Nombre Clínica] sin inversión inicial (Modelo OaaS)"*.
   - Cuerpo de mensaje con referencias a la Declaración de Madrid.
   - Botón: `[Aprobar y Enviar Mensaje]`.

---

### 4.5. Vista 4: Módulo de Posventa y Retención (RF-04)
1. **Header de Métricas de Parque Instalado:**
   - *Equipos instalados:* `4`
   - *Kits por reabastecer:* `2` (alerta ámbar)
   - *Mantenimientos próximos:* `3`
   - *Médicos capacitados:* `9 de 12`
2. **Tabla Interactiva de Consumo de Insumos:**
   - Columnas: *Clínica | Insumo | Consumo estimado | Último pedido | Estado | Acciones*
   - Registros:
     - `Clínica del Valle` | Kits AHTm | 24 por mes | Hace 4 semanas | **Agotado** (Rojo)
     - `Centro Médico Rímac Norte` | Líneas sin PVC | 40 por mes | Hace 3 semanas | **Reabastecer pronto** (Ámbar)
     - `Policlínico Miraflores Sur` | Frascos de vacío | 32 por mes | Hace 1 semana | **Al día** (Verde)
     - `Instituto Lumbar Lima` | Kits AHTm | 18 por mes | Hace 1 semana | **Al día** (Verde)
3. **Caja de Sugerencia de la IA:**
   - *"Clínica del Valle lleva 4 semanas sin solicitar kits de AHTm. Enviar un recordatorio de reabastecimiento con la consulta de seguimiento técnico."*
   - Botón: **Revisar recordatorio** (Badge: `Borrador de IA: requiere tu aprobación`).
4. **Columna Lateral Derecha:**
   - **Widget "Mantenimiento y calibración":**
     - *Clínica del Valle:* Calibración anual: en 12 días
     - *Instituto Lumbar Lima:* Revisión del tubo de descarga: en 3 semanas
     - *Centro Médico Rímac Norte:* Renovación de garantía: en 2 meses
     - Nota: *Fechas agendadas automáticamente según el registro del equipo.*
   - **Widget "Capacitación continua":**
     - Progreso: `9 de 12 médicos` (barra de progreso al 75%).
     - Card de notificación: *"Nuevo protocolo en la OzonePedia: Artrosis de rodilla. Enviar una nota técnica a los clínicos de traumatología."* Enlace: *Preparar nota técnica*.

---

## 5. Estrategia de Rendimiento (RNF-04: LCP < 1.5s)

1. **Arquitectura Zero-Bloat:**
   - Evitar frameworks de UI sobredimensionados que incluyan runtime JavaScript masivo.
   - Utilizar CSS moderno con variables CSS y Tailwind optimizado para compilar solo clases en uso.
   - Íconos SVG limpios (Lucide Icons) importados de forma granular.
2. **Optimización de Fuentes:**
   - Carga de fuentes mediante `next/font/google` con `display: swap` y subconjunto latino exclusivo.
3. **Manejo de Estado Local Reactivo:**
   - Estado de pipeline e insumos manejado con store ligero (Zustand o Context API nativo) permitiendo interacción instantánea y fluida sin re-renderizado global.
