export type TutorialTab = "pipeline" | "prospectos" | "posventa" | "catalogo" | "configuracion" | "documentos";
export type PipelineView = "kanban" | "dashboard";

export type TutorialNavigation = {
  tab?: TutorialTab;
  pipelineView?: PipelineView;
};

export type TutorialStep = {
  id: string;
  title: string;
  body: string;
  /** Valor de data-tour del elemento a señalar. Sin valor, el paso es un mensaje general. */
  target?: string;
  /** Navegación previa al paso para que el elemento exista en pantalla. */
  go?: TutorialNavigation;
};

export const TUTORIAL_STEPS: TutorialStep[] = [
  {
    id: "bienvenida",
    title: "Hola, soy Zonito",
    body: "Te guío por ConfIA en un minuto. Puedes saltar el recorrido en cualquier momento y repetirlo desde tu perfil.",
    go: { tab: "pipeline", pipelineView: "kanban" },
  },
  {
    id: "navegacion",
    title: "Menú principal",
    body: "Aquí navegas entre el seguimiento de clientes, el directorio, los equipos instalados, el catálogo y la configuración de la IA.",
    target: "sidebar",
    go: { tab: "pipeline" },
  },
  {
    id: "kanban",
    title: "Seguimiento de clientes",
    body: "Cada tarjeta es un prospecto. Se mueve entre Descubierto, Contactado, Propuesta enviada y Cierre según avanza la negociación.",
    target: "kanban",
    go: { tab: "pipeline", pipelineView: "kanban" },
  },
  {
    id: "vista-impacto",
    title: "Dashboard",
    body: "Con este interruptor cambias del tablero Kanban al dashboard: indicadores clave, embudo y prospectos prioritarios.",
    target: "report-switch",
    go: { tab: "pipeline", pipelineView: "kanban" },
  },
  {
    id: "asesor-ia",
    title: "Asesor IA con contexto",
    body: "Pregúntale por prioridades, riesgos o el cierre del trimestre. Responde con los datos del CRM. En la demo las respuestas son simuladas, sin llamadas a un modelo.",
    target: "advisor",
    go: { tab: "pipeline", pipelineView: "dashboard" },
  },
  {
    id: "revision-humana",
    title: "Nada sale sin tu aprobación",
    body: "Los borradores de la IA llegan a una pantalla de revisión. Editas el texto, eliges adjuntos y apruebas con un clic. Solo entonces se envía.",
    target: "kanban",
    go: { tab: "pipeline", pipelineView: "kanban" },
  },
  {
    id: "posventa",
    title: "Equipos y mantenimiento",
    body: "Seguimiento de equipos instalados, consumibles, alertas de mantenimiento y capacitación de los médicos. El interruptor te muestra la vista operativa o el dashboard de salud del parque.",
    target: "posventa",
    go: { tab: "posventa" },
  },
  {
    id: "catalogo",
    title: "Catálogo de equipos",
    body: "Modelos, registros sanitarios y precios de referencia. La IA solo usa datos verificados de este catálogo.",
    target: "catalogo",
    go: { tab: "catalogo" },
  },
  {
    id: "cuenta",
    title: "Tu cuenta",
    body: "Desde tu perfil ves tus datos, cierras sesión y puedes repetir este tutorial cuando quieras.",
    target: "account",
    go: { tab: "pipeline", pipelineView: "kanban" },
  },
];
