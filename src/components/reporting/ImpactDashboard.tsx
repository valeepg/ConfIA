"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { SUGGESTED_QUESTIONS, answerAdvisorQuestion, buildAdvisorContext } from "@/lib/demoAdvisor";
import type { Lead, PipelineStatus } from "@/types";

import { ChartCard, Kpi } from "./ChartPrimitives";

// Escala secuencial de un solo tono (validada con scripts/validate_palette.js --ordinal).
// Las etapas del embudo van de la más clara (inicio) a la más oscura (cierre).
const FUNNEL_STAGES: { status: PipelineStatus; label: string; color: string }[] = [
  { status: "descubierto", label: "Descubierto", color: "#86b6ef" },
  { status: "contactado", label: "Contactado", color: "#5598e7" },
  { status: "propuesta_enviada", label: "Propuesta enviada", color: "#2a78d6" },
  { status: "cierre", label: "Cierre", color: "#184f95" },
];
const BAR_COLOR = "#2a78d6";
const ANSWER_DELAY_MS = 650;

const SCORE_BANDS = [
  { label: "Bajo (0–39)", min: 0, max: 39, color: "#9ec5f4" },
  { label: "Medio (40–69)", min: 40, max: 69, color: "#3987e5" },
  { label: "Alto (70–100)", min: 70, max: 100, color: "#184f95" },
];

type ChatMessage = { id: number; role: "user" | "assistant"; text: string; bullets?: string[] };

export function ImpactDashboard({ leads }: { leads: Lead[] }) {
  const context = useMemo(() => buildAdvisorContext(leads), [leads]);

  const funnelMax = Math.max(1, ...FUNNEL_STAGES.map((stage) => context.byStatus[stage.status]));
  const bandCounts = SCORE_BANDS.map((band) => ({
    ...band,
    count: leads.filter((lead) => lead.score >= band.min && lead.score <= band.max).length,
  }));
  const bandMax = Math.max(1, ...bandCounts.map((band) => band.count));
  const topLeads = [...leads].sort((a, b) => b.score - a.score).slice(0, 5);

  const contactedShare = context.totalLeads === 0
    ? 0
    : Math.round(((context.totalLeads - context.byStatus.descubierto) / context.totalLeads) * 100);

  return (
    <div className="space-y-6" data-tour="impact-dashboard">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Prospectos en pipeline" value={String(context.totalLeads)} hint="Total activo" />
        <Kpi label="Score promedio" value={String(context.averageScore)} hint="Escala 0 a 100" />
        <Kpi label="Ya contactados" value={`${contactedShare}%`} hint="Fuera de Descubierto" />
        <Kpi
          label="Ingreso neto potencial"
          value={`USD ${Math.round(context.potentialNetMonthlyUsd).toLocaleString("es-PE")}`}
          hint="Mensual, según ROI generado"
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <ChartCard title="Embudo comercial" subtitle="Prospectos por etapa">
          <ul className="space-y-3">
            {FUNNEL_STAGES.map((stage) => {
              const count = context.byStatus[stage.status];
              return (
                <li key={stage.status}>
                  <div className="flex justify-between text-xs text-slate-600">
                    <span>{stage.label}</span>
                    <span className="font-semibold text-[#0B1528]">{count}</span>
                  </div>
                  <div className="mt-1 h-3 rounded-full bg-slate-100" title={`${stage.label}: ${count}`}>
                    <div
                      className="h-3 rounded-full transition-all"
                      style={{ width: `${(count / funnelMax) * 100}%`, backgroundColor: stage.color, minWidth: count > 0 ? 8 : 0 }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </ChartCard>

        <ChartCard title="Distribución de score" subtitle="Cuántos prospectos caen en cada banda">
          <ul className="space-y-3">
            {bandCounts.map((band) => (
              <li key={band.label}>
                <div className="flex justify-between text-xs text-slate-600">
                  <span>{band.label}</span>
                  <span className="font-semibold text-[#0B1528]">{band.count}</span>
                </div>
                <div className="mt-1 h-3 rounded-full bg-slate-100" title={`${band.label}: ${band.count}`}>
                  <div
                    className="h-3 rounded-full transition-all"
                    style={{ width: `${(band.count / bandMax) * 100}%`, backgroundColor: band.color, minWidth: band.count > 0 ? 8 : 0 }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </ChartCard>

        <ChartCard title="Prospectos prioritarios" subtitle="Top 5 por score">
          {topLeads.length === 0 ? (
            <p className="text-xs text-slate-500">Sin prospectos todavía.</p>
          ) : (
            <ul className="space-y-3">
              {topLeads.map((lead) => (
                <li key={lead.id}>
                  <div className="flex justify-between gap-2 text-xs text-slate-600">
                    <span className="truncate">{lead.name}</span>
                    <span className="shrink-0 font-semibold text-[#0B1528]">{lead.score}</span>
                  </div>
                  <div className="mt-1 h-2.5 rounded-full bg-slate-100" title={`${lead.name}: score ${lead.score}`}>
                    <div
                      className="h-2.5 rounded-full"
                      style={{ width: `${lead.score}%`, backgroundColor: BAR_COLOR }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </ChartCard>
      </section>

      <AdvisorChat context={context} />
    </div>
  );
}

type AdvisorContextValue = ReturnType<typeof buildAdvisorContext>;

function AdvisorChat({ context }: { context: AdvisorContextValue }) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 0,
      role: "assistant",
      text: "Soy el asesor de ConfIA. Conozco tu pipeline actual. Pregúntame por prioridades, riesgos o cómo cerrar más propuestas.",
    },
  ]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const nextId = useRef(1);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const ask = (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || thinking) return;

    const userMessage: ChatMessage = { id: nextId.current++, role: "user", text: trimmed };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setThinking(true);

    timer.current = setTimeout(() => {
      const answer = answerAdvisorQuestion(trimmed, context);
      setMessages((current) => [
        ...current,
        { id: nextId.current++, role: "assistant", text: answer.text, bullets: answer.bullets },
      ]);
      setThinking(false);
    }, ANSWER_DELAY_MS);
  };

  return (
    <section data-tour="advisor" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-[#0B1528]">Asesor IA con contexto</h3>
          <p className="text-[11px] text-slate-500">
            Demostración: las respuestas se generan con reglas sobre tu pipeline. No llaman a un modelo.
          </p>
        </div>
        <span className="rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-[#0369A1]">Simulado</span>
      </div>

      <div className="max-h-80 space-y-3 overflow-y-auto rounded-xl bg-slate-50 p-4" aria-live="polite">
        {messages.map((message) => (
          <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                message.role === "user" ? "bg-[#0B1528] text-white" : "bg-white text-slate-800 shadow-xs"
              }`}
            >
              <p>{message.text}</p>
              {message.bullets && message.bullets.length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-700">
                  {message.bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ))}
        {thinking && <p className="text-xs italic text-slate-500">El asesor está revisando el pipeline…</p>}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {SUGGESTED_QUESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => ask(question)}
            disabled={thinking}
            className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs font-semibold text-[#0369A1] hover:bg-sky-100 disabled:opacity-50"
          >
            {question}
          </button>
        ))}
      </div>

      <form
        className="mt-3 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          ask(draft);
        }}
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Pregunta al asesor, por ejemplo: ¿qué hago esta semana?"
          className="flex-1 rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-[#0B1528]"
        />
        <button
          type="submit"
          disabled={thinking || draft.trim() === ""}
          className="rounded-xl bg-[#F97316] px-4 py-2.5 text-xs font-bold text-white hover:bg-[#EA580C] disabled:opacity-50"
        >
          Enviar
        </button>
      </form>
    </section>
  );
}
