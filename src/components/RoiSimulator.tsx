"use client";

import { useEffect, useState } from "react";

import { downloadApiFile, generateProforma, simulateRoi } from "@/lib/aiApi";
import type { Lead, RoiEvaluation, RoiOffer, RoiProforma, RoiZone } from "@/types";

const PRODUCT_OPTIONS = [
  { id: "ozonette", name: "Ozonette" },
  { id: "ozonette_dent", name: "Ozonette Dent" },
  { id: "ozonette_woman_care", name: "Ozonette Woman Care" },
  { id: "ozonette_vet", name: "Ozonette Vet" },
  { id: "ozonobaric_p", name: "Ozonobaric P" },
  { id: "om_302_d", name: "OM-302 D" },
];

// Propuesta inicial del procedimiento v0.3 (sección 6).
const DEFAULT_OFFER: RoiOffer = {
  productId: "ozonette",
  sessionPricePen: 120,
  sessionsPerMonth: 40,
  equipmentPriceUsd: 6500,
  installationIncluded: false,
  trainingIncludedSessions: 2,
  installments: 1,
  warrantyMonths: 12,
};

const ZONE_LABEL: Record<RoiZone, string> = {
  win_win: "Zona de acuerdo",
  clinic_only: "Requiere aprobación gerencial",
  tecnocare_only: "Sin recuperación para la clínica",
  none: "Sin acuerdo",
};

const SIMULATION_DELAY_MS = 300;

function usd(value: number) {
  return `USD ${value.toLocaleString("es-PE", { maximumFractionDigits: 0 })}`;
}

function months(value: number | null) {
  return value === null ? "n/a" : `${value.toFixed(1)} meses`;
}

function percent(value: number | null) {
  return value === null ? "n/a" : `${(value * 100).toFixed(1)}%`;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

type RoiSimulatorProps = {
  lead: Lead;
};

export function RoiSimulator({ lead }: RoiSimulatorProps) {
  const [offer, setOffer] = useState<RoiOffer>(DEFAULT_OFFER);
  const [evaluation, setEvaluation] = useState<RoiEvaluation | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationError, setSimulationError] = useState<string | null>(null);
  const [proformas, setProformas] = useState<RoiProforma[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Recalcula en vivo, con un pequeño retardo para no llamar a la API en cada tecla.
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      setIsSimulating(true);
      try {
        const result = await simulateRoi(offer);
        if (!cancelled) {
          setEvaluation(result);
          setSimulationError(null);
        }
      } catch (error: unknown) {
        if (!cancelled) setSimulationError(errorMessage(error, "No se pudo recalcular la oferta."));
      } finally {
        if (!cancelled) setIsSimulating(false);
      }
    }, SIMULATION_DELAY_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [offer]);

  const update = <K extends keyof RoiOffer>(key: K, value: RoiOffer[K]) => {
    setOffer((current) => ({ ...current, [key]: value }));
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setActionError(null);
    try {
      const created = await generateProforma(lead, offer);
      setProformas((current) => [created, ...current]);
    } catch (error: unknown) {
      setActionError(errorMessage(error, "No se pudo generar la propuesta."));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async (proforma: RoiProforma, kind: "pdf" | "params") => {
    const filename = kind === "pdf"
      ? `${proforma.leadId}-${proforma.versionLabel}-propuesta_comercial.pdf`
      : `${proforma.leadId}-${proforma.versionLabel}-parametros.json`;
    try {
      await downloadApiFile(proforma.downloadUrls[kind], filename);
    } catch (error: unknown) {
      setActionError(errorMessage(error, "No se pudo descargar el archivo."));
    }
  };

  const isGreen = evaluation?.status === "green";
  const inputClass = "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-[#071C21]";

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-xs font-semibold text-slate-600">
          Producto
          <select
            className={inputClass}
            value={offer.productId}
            onChange={(event) => update("productId", event.target.value)}
          >
            {PRODUCT_OPTIONS.map((product) => (
              <option key={product.id} value={product.id}>{product.name}</option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Precio por sesión que cobra la clínica (PEN)
          <input
            type="number"
            min={0}
            className={inputClass}
            value={offer.sessionPricePen}
            onChange={(event) => update("sessionPricePen", Number(event.target.value))}
          />
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Sesiones por mes
          <input
            type="number"
            min={0}
            className={inputClass}
            value={offer.sessionsPerMonth}
            onChange={(event) => update("sessionsPerMonth", Number(event.target.value))}
          />
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Precio del equipo (USD)
          <input
            type="number"
            min={0}
            className={inputClass}
            value={offer.equipmentPriceUsd}
            onChange={(event) => update("equipmentPriceUsd", Number(event.target.value))}
          />
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Capacitación incluida (sesiones)
          <input
            type="number"
            min={0}
            max={20}
            className={inputClass}
            value={offer.trainingIncludedSessions}
            onChange={(event) => update("trainingIncludedSessions", Number(event.target.value))}
          />
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Plazo de pago (cuotas)
          <input
            type="number"
            min={1}
            max={60}
            className={inputClass}
            value={offer.installments}
            onChange={(event) => update("installments", Number(event.target.value))}
          />
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Garantía (meses)
          <input
            type="number"
            min={0}
            className={inputClass}
            value={offer.warrantyMonths}
            onChange={(event) => update("warrantyMonths", Number(event.target.value))}
          />
        </label>
        <label className="flex items-center gap-2 pt-6 text-xs font-semibold text-slate-600">
          <input
            type="checkbox"
            checked={offer.installationIncluded}
            onChange={(event) => update("installationIncluded", event.target.checked)}
          />
          Instalación incluida
        </label>
      </div>

      {simulationError && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-xs text-red-800">{simulationError}</div>
      )}

      {evaluation && (
        <div className="space-y-4">
          <div
            className={`rounded-2xl border p-4 ${
              isGreen ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-red-200 bg-red-50 text-red-900"
            }`}
          >
            <p className="text-sm font-semibold">
              {isGreen ? "🟢" : "🔴"} {ZONE_LABEL[evaluation.zone]}
              {isSimulating && <span className="ml-2 text-xs font-normal">recalculando…</span>}
            </p>
            <p className="mt-1 text-xs">{evaluation.message}</p>
            {evaluation.violations.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-xs">
                {evaluation.violations.map((violation) => (
                  <li key={violation}>{violation}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <Metric label="Inversión" value={usd(evaluation.investmentUsd)} />
            <Metric label="Flujo neto mensual" value={usd(evaluation.monthlyFlowUsd)} />
            <Metric label="Recuperación" value={months(evaluation.recoveryMonths)} />
            <Metric label="Retorno a 24 meses" value={percent(evaluation.return24m)} />
            <Metric label="Margen Tecnocare (interno)" value={percent(evaluation.margin)} />
            <Metric
              label="Precio mínimo del equipo (interno)"
              value={evaluation.minEquipmentPriceUsd === null ? "n/a" : usd(evaluation.minEquipmentPriceUsd)}
            />
          </div>
          <p className="text-[11px] text-slate-500">
            Margen y precio mínimo son internos. No se incluyen en la propuesta que recibe la clínica.
          </p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={handleGenerate}
          disabled={!isGreen || isGenerating}
          className="rounded-full bg-[#0B6E4F] px-5 py-2.5 text-xs font-semibold text-white hover:bg-[#0A5F44] disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {isGenerating ? "Generando propuesta..." : "Generar propuesta ajustada"}
        </button>
        {!isGreen && evaluation && (
          <span className="text-xs text-slate-500">Solo se genera cuando la oferta está en zona de acuerdo.</span>
        )}
      </div>

      {actionError && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-xs text-red-800">{actionError}</div>
      )}

      {proformas.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Versiones generadas</p>
          {proformas.map((proforma) => (
            <div
              key={`${proforma.leadId}-${proforma.versionLabel}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200 bg-white p-3"
            >
              <div>
                <p className="text-sm font-semibold text-[#071C21]">
                  Propuesta {proforma.versionLabel} · {proforma.productName}
                </p>
                <p className="text-[11px] text-slate-500">Borrador: pendiente de aprobación antes de enviar.</p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleDownload(proforma, "pdf")}
                  className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold text-[#071C21] hover:bg-slate-100"
                >
                  PDF
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload(proforma, "params")}
                  className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold text-[#071C21] hover:bg-slate-100"
                >
                  Parámetros (interno)
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-[11px] text-slate-600">{label}</p>
      <p className="mt-1 font-semibold text-[#071C21]">{value}</p>
    </div>
  );
}
