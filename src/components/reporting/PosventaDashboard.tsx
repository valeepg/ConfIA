"use client";

import { useMemo } from "react";

import { buildPosventaStats, type TrainingRow } from "@/lib/posventaStats";
import type { ConsumableItem, MaintenanceItem } from "@/types";

import { BarList, ChartCard, Kpi, SEQUENTIAL } from "./ChartPrimitives";

type PosventaDashboardProps = {
  maintenance: MaintenanceItem[];
  consumables: ConsumableItem[];
  training: TrainingRow[];
};

const URGENCY_LABEL = { high: "Alta", medium: "Media", low: "Baja" } as const;

export function PosventaDashboard({ maintenance, consumables, training }: PosventaDashboardProps) {
  const stats = useMemo(
    () => buildPosventaStats(maintenance, consumables, training),
    [maintenance, consumables, training],
  );

  const alertCount = stats.urgency.high + stats.urgency.medium;

  return (
    <div className="space-y-6" data-tour="posventa-dashboard">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Equipos instalados" value={String(stats.installed)} hint="Parque activo de clientes" />
        <Kpi label="Salud promedio del parque" value={`${stats.averageHealth}%`} hint="Según la última revisión" />
        <Kpi label="Equipos con alerta" value={String(alertCount)} hint={`${stats.urgency.high} de prioridad alta`} />
        <Kpi label="Médicos capacitados" value={`${stats.trainingPercent}%`} hint="Del total de médicos de los clientes" />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <ChartCard title="Salud del parque" subtitle="Equipos por banda de salud">
          <BarList
            items={stats.healthBands.map((band, index) => ({
              label: band.label,
              value: band.count,
              color: [SEQUENTIAL[250], SEQUENTIAL[450], SEQUENTIAL[650]][index],
            }))}
          />
        </ChartCard>

        <ChartCard title="Alertas de mantenimiento" subtitle="Equipos por nivel de urgencia">
          <BarList
            items={(["high", "medium", "low"] as const).map((level) => ({
              label: `Urgencia ${URGENCY_LABEL[level].toLowerCase()}`,
              value: stats.urgency[level],
              color: { high: SEQUENTIAL[650], medium: SEQUENTIAL[450], low: SEQUENTIAL[250] }[level],
            }))}
          />
        </ChartCard>

        <ChartCard title="Insumos por reponer" subtitle="Clientes según el estado de su stock">
          <BarList
            items={[
              { label: "Agotado", value: stats.consumablesByStatus.agotado, color: SEQUENTIAL[650] },
              { label: "Reabastecer pronto", value: stats.consumablesByStatus.reabastecer, color: SEQUENTIAL[450] },
              { label: "Al día", value: stats.consumablesByStatus.al_dia, color: SEQUENTIAL[250] },
            ]}
          />
          <p className="mt-4 text-[11px] text-slate-500">
            Unidades mensuales en riesgo: <span className="font-semibold text-[#0B1528]">{stats.unitsAtRisk}</span>
          </p>
        </ChartCard>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <ChartCard title="Capacitación por clínica" subtitle="Porcentaje de médicos certificados, de menor a mayor avance">
          <BarList
            items={stats.trainingByClinic.map((row) => ({
              label: row.clinicName,
              value: row.percent,
              valueLabel: `${row.certified}/${row.total} · ${row.percent}%`,
              color: SEQUENTIAL[450],
            }))}
            emptyText="Sin clínicas registradas."
          />
        </ChartCard>

        <ChartCard title="Parque por modelo" subtitle="Equipos instalados por modelo">
          <BarList
            items={stats.modelCounts.map((row) => ({
              label: row.model,
              value: row.count,
              color: SEQUENTIAL[450],
            }))}
          />
        </ChartCard>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
        <h3 className="text-sm font-bold text-[#0B1528]">Acciones de mantenimiento prioritarias</h3>
        <p className="mb-4 text-[11px] text-slate-500">Equipos con alerta, del menor al mayor nivel de salud</p>
        {stats.priorityEquipment.length === 0 ? (
          <p className="text-xs text-slate-500">No hay equipos con alerta.</p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 font-semibold uppercase tracking-[0.12em] text-slate-500">
                <tr>
                  <th className="px-3.5 py-2.5">Cliente</th>
                  <th className="px-3.5 py-2.5">Equipo</th>
                  <th className="px-3.5 py-2.5">Salud</th>
                  <th className="px-3.5 py-2.5">Urgencia</th>
                  <th className="px-3.5 py-2.5">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white text-slate-700">
                {stats.priorityEquipment.map((item) => (
                  <tr key={item.id}>
                    <td className="px-3.5 py-3 font-medium text-[#071C21]">{item.clinicName}</td>
                    <td className="px-3.5 py-3">{item.equipmentModel.replace(/^SEDECAL\s+/i, "")}</td>
                    <td className="px-3.5 py-3">{item.healthPercent}%</td>
                    <td className="px-3.5 py-3">
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 font-semibold text-slate-800">
                        {URGENCY_LABEL[item.urgency]}
                      </span>
                    </td>
                    <td className="px-3.5 py-3">{item.task}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
