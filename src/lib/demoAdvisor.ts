import type { Lead, PipelineStatus } from "@/types";

/**
 * Asesor de demostración. NO llama a ningún modelo: responde con reglas sobre el estado
 * real del pipeline. Sirve para mostrar el flujo de preguntas con contexto.
 */

export type AdvisorContext = {
  totalLeads: number;
  byStatus: Record<PipelineStatus, number>;
  averageScore: number;
  highScoreNotContacted: { name: string; score: number }[];
  topProspects: { name: string; score: number; status: PipelineStatus }[];
  pendingDrafts: number;
  proposalsSent: number;
  closed: number;
  potentialNetMonthlyUsd: number;
};

export type AdvisorAnswer = {
  topic: "prioridades" | "riesgos" | "cierre" | "resumen";
  text: string;
  bullets: string[];
};

export const SUGGESTED_QUESTIONS = [
  "¿A quién contacto primero?",
  "¿Qué riesgos tiene el pipeline?",
  "¿Cómo cierro más propuestas este trimestre?",
  "Dame un resumen del pipeline",
];

const HIGH_SCORE = 70;
const TOP_LIMIT = 3;

export function buildAdvisorContext(leads: Lead[]): AdvisorContext {
  const byStatus: Record<PipelineStatus, number> = {
    descubierto: 0,
    contactado: 0,
    propuesta_enviada: 0,
    cierre: 0,
  };
  for (const lead of leads) byStatus[lead.status] += 1;

  const totalScore = leads.reduce((sum, lead) => sum + lead.score, 0);
  const sortedByScore = [...leads].sort((a, b) => b.score - a.score);

  return {
    totalLeads: leads.length,
    byStatus,
    averageScore: leads.length === 0 ? 0 : Math.round(totalScore / leads.length),
    highScoreNotContacted: sortedByScore
      .filter((lead) => lead.status === "descubierto" && lead.score >= HIGH_SCORE)
      .slice(0, TOP_LIMIT)
      .map((lead) => ({ name: lead.name, score: lead.score })),
    topProspects: sortedByScore
      .filter((lead) => lead.status !== "cierre")
      .slice(0, TOP_LIMIT)
      .map((lead) => ({ name: lead.name, score: lead.score, status: lead.status })),
    pendingDrafts: leads.filter((lead) => lead.hasAiDraft && !lead.draftApproved).length,
    proposalsSent: byStatus.propuesta_enviada,
    closed: byStatus.cierre,
    potentialNetMonthlyUsd: leads.reduce((sum, lead) => sum + (lead.roiProposal?.estimatedNetMonthly ?? 0), 0),
  };
}

function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

export function detectTopic(question: string): AdvisorAnswer["topic"] {
  const q = normalize(question);
  if (/(prioridad|primero|contact|hoy|a quien)/.test(q)) return "prioridades";
  if (/(riesgo|atrasad|pendiente|bloque|borrador|problema)/.test(q)) return "riesgos";
  if (/(cierr|cierre|propuesta|trimestre|vender|venta)/.test(q)) return "cierre";
  return "resumen";
}

export function answerAdvisorQuestion(question: string, context: AdvisorContext): AdvisorAnswer {
  const topic = detectTopic(question);

  if (context.totalLeads === 0) {
    return {
      topic,
      text: "Todavía no hay prospectos en el pipeline. Busca nuevos clientes o agrega uno manualmente para empezar.",
      bullets: [],
    };
  }

  if (topic === "prioridades") {
    if (context.highScoreNotContacted.length === 0) {
      return {
        topic,
        text: "No hay prospectos de alta prioridad sin contactar. Revisa los que ya están en contacto para avanzar la propuesta.",
        bullets: context.topProspects.map((p) => `${p.name} (score ${p.score}, ${STATUS_LABEL[p.status]})`),
      };
    }
    return {
      topic,
      text: `Empieza por ${context.highScoreNotContacted.length} prospecto(s) con score ${HIGH_SCORE} o más que aún no contactas.`,
      bullets: context.highScoreNotContacted.map((p) => `${p.name} · score ${p.score}`),
    };
  }

  if (topic === "riesgos") {
    const risks: string[] = [];
    if (context.pendingDrafts > 0) {
      risks.push(`${context.pendingDrafts} borrador(es) de IA esperan tu revisión: no se envían solos.`);
    }
    if (context.highScoreNotContacted.length > 0) {
      risks.push(`${context.highScoreNotContacted.length} prospecto(s) de alto score sin contacto: riesgo de que se enfríen.`);
    }
    if (context.proposalsSent > 0 && context.closed === 0) {
      risks.push(`${context.proposalsSent} propuesta(s) enviada(s) y ningún cierre: conviene dar seguimiento.`);
    }
    return {
      topic,
      text: risks.length > 0 ? "Estos son los riesgos que veo en el pipeline:" : "No veo riesgos críticos en el pipeline actual.",
      bullets: risks,
    };
  }

  if (topic === "cierre") {
    const steps = [
      `Tienes ${context.proposalsSent} propuesta(s) enviada(s). Haz seguimiento en la cadencia acordada.`,
      "Ajusta la oferta en el simulador de contraofertas antes de bajar el precio: prioriza plazo y capacitación.",
    ];
    if (context.potentialNetMonthlyUsd > 0) {
      steps.push(
        `El ROI generado suma unos USD ${Math.round(context.potentialNetMonthlyUsd).toLocaleString("es-PE")} de ingreso neto mensual para las clínicas.`,
      );
    }
    return {
      topic,
      text: "Para cerrar más propuestas este trimestre, enfócate en lo siguiente:",
      bullets: steps,
    };
  }

  const b = context.byStatus;
  return {
    topic,
    text: `Pipeline con ${context.totalLeads} prospectos y score promedio de ${context.averageScore}.`,
    bullets: [
      `Descubiertos: ${b.descubierto} · Contactados: ${b.contactado}`,
      `Propuesta enviada: ${b.propuesta_enviada} · Cierre: ${b.cierre}`,
      `Borradores pendientes de revisión: ${context.pendingDrafts}`,
    ],
  };
}

const STATUS_LABEL: Record<PipelineStatus, string> = {
  descubierto: "Descubierto",
  contactado: "Contactado",
  propuesta_enviada: "Propuesta enviada",
  cierre: "Cierre",
};
