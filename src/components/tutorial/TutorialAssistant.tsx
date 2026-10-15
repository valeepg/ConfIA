"use client";

import { useCallback, useEffect, useState } from "react";

import { isTutorialCompleted, setTutorialCompleted } from "@/lib/demoSession";
import { TUTORIAL_STEPS, type TutorialNavigation } from "@/lib/tutorialSteps";

const AUTO_OPEN_DELAY_MS = 1200;
const MEASURE_DELAY_MS = 180;
const SPOTLIGHT_PADDING = 8;

type Rect = { top: number; left: number; width: number; height: number };

type TutorialAssistantProps = {
  onNavigate: (navigation: TutorialNavigation) => void;
  /** Abre el tutorial desde el paso 1 al montarse (lo usa "Repetir tutorial" con una key nueva). */
  startOpen?: boolean;
};

export function TutorialAssistant({ onNavigate, startOpen = false }: TutorialAssistantProps) {
  const [open, setOpen] = useState(startOpen);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);

  const step = TUTORIAL_STEPS[index];
  const isLast = index === TUTORIAL_STEPS.length - 1;

  const finish = useCallback((completed: boolean) => {
    setTutorialCompleted(completed);
    setOpen(false);
    setRect(null);
  }, []);

  // Primera visita: el asistente se presenta solo, una vez.
  useEffect(() => {
    if (startOpen || isTutorialCompleted()) return;
    const timer = setTimeout(() => setOpen(true), AUTO_OPEN_DELAY_MS);
    return () => clearTimeout(timer);
  }, [startOpen]);

  // Al cambiar de paso, lleva a la pestaña o vista necesaria.
  useEffect(() => {
    if (!open || !step.go) return;
    onNavigate(step.go);
  }, [open, step, onNavigate]);

  // Mide el elemento señalado después de que la vista cambie.
  useEffect(() => {
    if (!open) return;

    const measure = () => {
      if (!step.target) {
        setRect(null);
        return;
      }
      const element = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
      if (!element) {
        setRect(null);
        return;
      }
      const box = element.getBoundingClientRect();
      setRect({ top: box.top, left: box.left, width: box.width, height: box.height });
    };

    const timer = setTimeout(() => {
      document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`)?.scrollIntoView({
        block: "center",
        behavior: "smooth",
      });
      measure();
    }, MEASURE_DELAY_MS);

    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [open, step]);

  // Teclado: flechas para avanzar o retroceder, Escape para saltar.
  useEffect(() => {
    if (!open) return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") finish(true);
      if (event.key === "ArrowRight") setIndex((current) => Math.min(current + 1, TUTORIAL_STEPS.length - 1));
      if (event.key === "ArrowLeft") setIndex((current) => Math.max(current - 1, 0));
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, finish]);

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => {
            setIndex(0);
            setOpen(true);
          }}
          aria-label="Abrir el tutorial con Zonito"
          className="fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-white shadow-xl shadow-orange-500/20 ring-1 ring-orange-200 transition hover:scale-105"
        >
          <ZonitoMascot className="h-9 w-9 animate-[bob_3s_ease-in-out_infinite]" />
        </button>
      )}

      {open && (
        <>
          {rect ? (
            <div
              aria-hidden
              className="pointer-events-none fixed z-40 rounded-2xl ring-4 ring-[#F97316] transition-all duration-300"
              style={{
                top: rect.top - SPOTLIGHT_PADDING,
                left: rect.left - SPOTLIGHT_PADDING,
                width: rect.width + SPOTLIGHT_PADDING * 2,
                height: rect.height + SPOTLIGHT_PADDING * 2,
                boxShadow: "0 0 0 9999px rgba(11, 21, 40, 0.55)",
              }}
            />
          ) : (
            <div aria-hidden className="fixed inset-0 z-40 bg-[#0B1528]/55" />
          )}

          <div
            role="dialog"
            aria-modal="false"
            aria-label="Tutorial de ConfIA"
            className="fixed bottom-5 right-5 z-50 w-[22rem] max-w-[calc(100vw-2.5rem)] rounded-3xl bg-white p-5 shadow-2xl"
          >
            <div className="flex items-start gap-3">
              <ZonitoMascot className="h-11 w-11 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#0284C7]">
                  Paso {index + 1} de {TUTORIAL_STEPS.length}
                </p>
                <h2 className="mt-0.5 text-base font-extrabold text-[#0B1528]">{step.title}</h2>
              </div>
              <button
                type="button"
                onClick={() => finish(true)}
                className="text-xs font-semibold text-slate-400 hover:text-slate-700"
              >
                Saltar
              </button>
            </div>

            <p className="mt-3 text-sm leading-relaxed text-slate-700">{step.body}</p>

            <div className="mt-4 flex items-center justify-center gap-1.5" aria-hidden>
              {TUTORIAL_STEPS.map((item, position) => (
                <span
                  key={item.id}
                  className={`h-1.5 rounded-full transition-all ${
                    position === index ? "w-5 bg-[#F97316]" : "w-1.5 bg-slate-200"
                  }`}
                />
              ))}
            </div>

            <div className="mt-4 flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setIndex((current) => Math.max(current - 1, 0))}
                disabled={index === 0}
                className="rounded-xl border border-slate-200 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"
              >
                Anterior
              </button>
              {isLast ? (
                <button
                  type="button"
                  onClick={() => finish(true)}
                  className="rounded-xl bg-[#F97316] px-4 py-2 text-xs font-bold text-white hover:bg-[#EA580C]"
                >
                  Terminar
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setIndex((current) => Math.min(current + 1, TUTORIAL_STEPS.length - 1))}
                  className="rounded-xl bg-[#0B1528] px-4 py-2 text-xs font-bold text-white hover:bg-[#1E293B]"
                >
                  Siguiente
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}

/**
 * Zonito: la mascota de ConfIA. Es una molécula de O₃ (ozono): tres átomos de oxígeno
 * en ángulo, con cara. Es un SVG propio, no un logotipo de terceros.
 */
export function ZonitoMascot({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} role="img" aria-label="Zonito, la mascota de ConfIA">
      <circle cx="32" cy="32" r="31" fill="#E6F4FA" />
      {/* Enlaces O–O del ozono */}
      <path d="M16 40 L32 22 L48 40" stroke="#0369A1" strokeWidth="3" fill="none" strokeLinejoin="round" />
      {/* Átomos de oxígeno: el central es mayor, como en la molécula bent de O₃ */}
      <circle cx="16" cy="42" r="9" fill="#38BDF8" stroke="#FFFFFF" strokeWidth="2" />
      <circle cx="48" cy="42" r="9" fill="#38BDF8" stroke="#FFFFFF" strokeWidth="2" />
      <circle cx="32" cy="24" r="11" fill="#0284C7" stroke="#FFFFFF" strokeWidth="2" />
      {/* Cara de Zonito */}
      <circle cx="28" cy="22" r="1.8" fill="#FFFFFF" />
      <circle cx="36" cy="22" r="1.8" fill="#FFFFFF" />
      <path d="M28 26 Q32 29 36 26" stroke="#FFFFFF" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <circle cx="16" cy="42" r="1.4" fill="#0B1528" />
      <circle cx="48" cy="42" r="1.4" fill="#0B1528" />
    </svg>
  );
}
