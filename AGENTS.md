# Guía Operativa para Agentes de Desarrollo (AGENTS.md)

> **Proyecto:** ConfIA (Ozonoterapia B2B Perú)  
> **Propósito:** Definir los roles, contratos de interfaz, estándares de código y flujos de trabajo de los agentes de IA y desarrolladores.  
> **Documento Vinculante:** Todos los agentes deben respetar la [constitution.md](file:///d:/Proyectos/Confia/constitution.md).

---

## 👥 Matriz de Roles y Responsabilidades

### 1. `Frontend Engineer (UI/UX)` — *Rol Principal para Módulo 2*
- **Dominio:** Frontend en Vercel (Next.js / React / TypeScript).
- **Módulos a cargo:**
  - **RF-03:** Dashboard de Pipeline Comercial Outbound (Kanban / Tabla interactiva).
  - **RF-04:** Módulo de Posventa y Retención (Parque instalado, insumos AHTm/PVC, mantenimiento DIGEMID, capacitación).
  - **RF-05:** Interfaz de Aprobación del Copiloto (Human-in-the-Loop de 1 clic).
  - **RNF-04:** Presupuesto de Rendimiento (LCP < 1.5s).
- **Directrices de UI:**
  - Seguir fielmente la paleta y layouts de los mockups de diseño (`#071C21`, `#0E2E33`, `#F4EFE6`, `#D97706`, `#059669`).
  - Implementar microinteracciones fluidas, estados de carga accesibles y componentes desacoplados.

### 2. `Backend & Intelligence Engineer`
- **Dominio:** FastAPI en Google Cloud Run + Firebase Firestore / Auth.
- **Módulos a cargo:**
  - Scraping e ingesta de IPRESS (SUSALUD / CMP).
  - Algoritmo de Lead Scoring y telemetría de lectura desde OzonePedia.
  - Copiloto Gemini Flash con salida JSON estructurada (Pydantic) y variables pre-validadas.

### 3. `Compliance & Medical Content Guardian`
- **Dominio:** Plantillas documentales y consistencia regulatoria.
- **Supervisión:**
  - Vigilar que ningún texto generado afirme propiedades terapéuticas sin cita de la Declaración de Madrid.
  - Asegurar que los datos de Registro Sanitario DIGEMID (Clase II/III) se manejen como plantillas estáticas y jamás sean inventados por la IA.

---

## 🛠️ Reglas de Código y Arquitectura Frontend (Módulo 2)

### 1. Stack Tecnológico Estándar
- **Framework:** Next.js 14+ (App Router) o Vite con React + TypeScript.
- **Estilos:** Tailwind CSS con tokens semánticos corporativos (definidos en `tailwind.config.ts`) o CSS Modules limpios.
- **Iconografía:** Lucide React (ligero, tree-shakeable).
- **Tipografía:**
  - Títulos: Serif institucional (*Playfair Display* o *Merriweather*).
  - Interfaz y datos: Sans-serif moderna (*Plus Jakarta Sans* o *Inter*).

### 2. Guardarraíles de Desarrollo
- **No Hardcodear Secretos:** Ningún token de API ni clave privada en el cliente (`process.env.NEXT_PUBLIC_...` solo para URLs públicas o credenciales anónimas seguras).
- **Componentes Atómicos y Reutilizables:**
  - `MetricCard`: Tarjetas de KPI superior (Prospectos activos, Borradores, Propuestas, Clientes).
  - `KanbanColumn` & `LeadCard`: Columnas y tarjetas de prospectos con badge de Score y badges de estado.
  - `LeadDetailDrawer`: Drawer lateral con actividad en OzonePedia, sugerencia IA y botones de acción.
  - `ApprovalModal`: Modal o panel de confirmación con vista previa de mensaje, ROI o dossier con 1 clic de aprobación.
  - `PosventaTable`: Tabla de consumo de insumos con badges de urgencia (`Agotado`, `Reabastecer pronto`, `Al día`).
  - `MaintenanceWidget`: Alertas de calibración y revisión técnica DIGEMID.
- **Rendimiento RNF-04:**
  - Zero imágenes pesadas sin optimizar.
  - Evitar librerías excesivas para animaciones; usar transiciones CSS nativas.
  - Mantener el First Load JS por debajo de 85 KB por ruta.

---

## 📋 Protocolo de Validación y Quality Gates

Antes de considerar una tarea terminada, el agente debe validar:
1. **Compilación sin errores:** `npm run build` o `npx tsc --noEmit` debe pasar con 0 errores y 0 warnings críticos.
2. **Fidelidad Visual:** El resultado debe coincidir con las referencias gráficas (Header oscuro, Kanban organizado, Drawer lateral reactivo, badges claros).
3. **Flujo Human-in-the-Loop:** Verificar que la interfaz requiera un clic humano consciente para marcar una propuesta o mensaje como "Aprobado / Enviado".
4. **Commits Semánticos:** Seguir convención en español o inglés estructurado:
   - `feat(crm): implement pipeline kanban board (RF-03)`
   - `feat(posventa): add consumables tracking and digemid maintenance alerts (RF-04)`
   - `feat(copilot): add 1-click human-in-the-loop approval interface (RF-05)`
   - `perf(crm): optimize critical css and font loading for LCP < 1.5s (RNF-04)`
