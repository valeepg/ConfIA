# Constitución del Sistema ConfIA (Ozonoterapia B2B Perú)

> **Versión:** 1.0.0  
> **Estado:** Activa e Invariable  
> **Ámbito de Aplicación:** Todos los módulos, agentes, desarrolladores y submódulos de ConfIA.

---

## Preámbulo y Propósito

ConfIA es un sistema de inteligencia comercial y posventa B2B diseñado para la distribución, capacitación y retención de equipos de ozonoterapia médica en el Perú bajo el modelo **Ozone-as-a-Service (OaaS)**. 

Este proyecto opera en el sector de salud institucional de alta complejidad (IPRESS, directores médicos, traumatólogos, anestesiólogos y comités de compra). Por tanto, la credibilidad clínica, la seguridad del paciente y el cumplimiento regulatorio estricto prevalecen sobre cualquier métrica de automatización o velocidad.

---

## 🏛️ Principios Constitucionales Fundamentales

### Artículo I: Human-in-the-Loop y Salvaguarda Clínica (No Negociable)
1. **La IA opera exclusivamente en el back-office:** En ningún caso un modelo de lenguaje (LLM) o agente autónomo se comunicará directamente con pacientes, ni emitirá diagnósticos, recomendaciones de dosificación o prescripciones clínicas de forma desatendida.
2. **Aprobación de 1 clic del Dueño/Operador:** Todo mensaje de prospección (outbound), propuesta económica de ROI, dossier regulatorio DIGEMID o recordatorio de insumo redactado por la IA es un **borrador preliminar**. Ningún contenido sale del sistema hacia una IPRESS o médico sin la aprobación humana explícita.
3. **Guardarraíl contra alucinaciones:** Los datos regulatorios (Registros Sanitarios DIGEMID), precios, concentraciones de gas permitidas (5 a 60 µg/mL según la Declaración de Madrid) y especificaciones técnicas deben inyectarse mediante plantillas estructuradas e inmutables, nunca redactadas libremente por el LLM.

### Artículo II: Rigor Regulatorio y Legal Peruano
1. **Marco DIGEMID / MINSA:** Los equipos comercializados se clasifican como Dispositivos Médicos Clase II o Clase III (Ley N° 29459, D.S. 016-2011-SA y 016-2013-SA). Solo se prospecta y vende a IPRESS registradas ante SUSALUD y profesionales de la salud colegiados (CMP).
2. **Protección de Datos Personales (Ley N° 29733):** La información extraída de padrones públicos y la telemetría de lectura se procesan bajo estricto principio de finalidad y confidencialidad. Los datos comerciales nunca se exponen al cliente público.
3. **Cero almacenamiento de secretos en cliente:** Credenciales, claves de API (Gemini, Firebase Admin, Cloud Run) y firmas deben residir exclusivamente en Google Secret Manager o variables de entorno del servidor.

### Artículo III: Separación Estricta de Dominios (OzonePedia vs. CRM)
1. **OzonePedia (Hub Abierto):** Debe residir en un dominio independiente del sitio comercial. Su misión es puramente científica y educativa (basada en la Declaración de Madrid de ISCO3). Nunca debe mostrar botones agresivos de compra para preservar la confianza médica.
2. **CRM ConfIA (Dashboard Interno):** Aplicación autenticada de uso exclusivo para el dueño y equipo comercial. Centraliza el pipeline B2B, radar de telemetría, gestión de insumos y aprobaciones.

### Artículo IV: Estética Premium y Experiencia de Usuario (UI/UX)
1. **Diseño de Autoridad Médica:** La interfaz debe proyectar sobriedad institucional y sofisticación tecnológica.
   - **Paleta de Identidad:** 
     - *Slate / Deep Teal* (`#071C21`, `#0E2E33`): Autoridad, tecnología y estructura.
     - *Warm Sand / Bone White* (`#F8F9FA`, `#F4EFE6`): Claridad clínica sin frialdad hospitalaria.
     - *Amber / Warm Gold* (`#D97706`, `#F59E0B`): Alertas de telemetría y badges "Borrador de IA por aprobar".
     - *Clinical Emerald* (`#059669`, `#10B981`): Confirmaciones, estado al día y acciones de alto impacto.
   - **Tipografía:** Combinación editorial serif para títulos institucionales (ej. *Merriweather* / *Playfair*) y tipografía sans-serif de alta legibilidad para métricas y datos (*Plus Jakarta Sans* / *Inter*).
2. **Prohibición de Diseños Genéricos:** Queda estrictamente vetado el uso de plantillas genéricas no estilizadas o componentes crudos tipo MVP básico.

### Artículo V: Presupuesto de Rendimiento (RNF-04)
1. **LCP < 1.5 Segundos:** El tiempo de carga (Largest Contentful Paint) del CRM en Vercel debe mantenerse estrictamente por debajo de 1.5 segundos en conexiones estándar.
2. **Arquitectura Ligera:** Minimizar dependencias externas pesadas. Preferir CSS nativo / Tailwind optimizado, componentes limpios y carga diferida (lazy loading) en modales y drawers.

---

## 🔒 Mecanismos de Aplicación
Cualquier Pull Request, commit o generación de código que viole estos principios (especialmente la exposición de la IA al cliente final sin supervisión humana o la violación del rendimiento LCP) será rechazado automáticamente por los agentes y revisores.
