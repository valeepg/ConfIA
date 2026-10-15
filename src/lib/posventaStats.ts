import type { ConsumableItem, MaintenanceItem } from "@/types";

export type TrainingRow = { clinicName: string; certifiedDoctors: number; totalDoctors: number };

export type PosventaStats = {
  installed: number;
  averageHealth: number;
  healthBands: { label: string; count: number }[];
  urgency: { high: number; medium: number; low: number };
  consumablesByStatus: { agotado: number; reabastecer: number; al_dia: number };
  unitsAtRisk: number;
  trainingPercent: number;
  trainingByClinic: { clinicName: string; percent: number; certified: number; total: number }[];
  modelCounts: { model: string; count: number }[];
  priorityEquipment: MaintenanceItem[];
};

/** Extrae el número de "24 por mes" o "40 por mes". */
export function monthlyUnits(text: string): number {
  const match = text.match(/\d+/);
  return match ? Number(match[0]) : 0;
}

function cleanModel(model: string): string {
  return model.replace(/^SEDECAL\s+/i, "");
}

export function buildPosventaStats(
  maintenance: MaintenanceItem[],
  consumables: ConsumableItem[],
  training: TrainingRow[],
): PosventaStats {
  const installed = maintenance.length;
  const averageHealth = installed === 0
    ? 0
    : Math.round(maintenance.reduce((sum, item) => sum + item.healthPercent, 0) / installed);

  const bandDefs = [
    { label: "Crítico (menos de 60%)", min: 0, max: 59 },
    { label: "Atención (60–79%)", min: 60, max: 79 },
    { label: "Estable (80–100%)", min: 80, max: 100 },
  ];
  const healthBands = bandDefs.map((band) => ({
    label: band.label,
    count: maintenance.filter((item) => item.healthPercent >= band.min && item.healthPercent <= band.max).length,
  }));

  const urgency = {
    high: maintenance.filter((item) => item.urgency === "high").length,
    medium: maintenance.filter((item) => item.urgency === "medium").length,
    low: maintenance.filter((item) => item.urgency === "low").length,
  };

  const consumablesByStatus = {
    agotado: consumables.filter((item) => item.status === "agotado").length,
    reabastecer: consumables.filter((item) => item.status === "reabastecer").length,
    al_dia: consumables.filter((item) => item.status === "al_dia").length,
  };
  const unitsAtRisk = consumables
    .filter((item) => item.status !== "al_dia")
    .reduce((sum, item) => sum + monthlyUnits(item.estimatedMonthly), 0);

  const certified = training.reduce((sum, row) => sum + row.certifiedDoctors, 0);
  const total = training.reduce((sum, row) => sum + row.totalDoctors, 0);
  const trainingByClinic = training
    .map((row) => ({
      clinicName: row.clinicName,
      certified: row.certifiedDoctors,
      total: row.totalDoctors,
      percent: row.totalDoctors === 0 ? 0 : Math.round((row.certifiedDoctors / row.totalDoctors) * 100),
    }))
    .sort((a, b) => a.percent - b.percent || a.clinicName.localeCompare(b.clinicName));

  const modelMap = new Map<string, number>();
  for (const item of maintenance) {
    const model = cleanModel(item.equipmentModel);
    modelMap.set(model, (modelMap.get(model) ?? 0) + 1);
  }
  const modelCounts = [...modelMap.entries()]
    .map(([model, count]) => ({ model, count }))
    .sort((a, b) => b.count - a.count || a.model.localeCompare(b.model));

  const priorityEquipment = maintenance
    .filter((item) => item.urgency !== "low")
    .sort((a, b) => a.healthPercent - b.healthPercent);

  return {
    installed,
    averageHealth,
    healthBands,
    urgency,
    consumablesByStatus,
    unitsAtRisk,
    trainingPercent: total === 0 ? 0 : Math.round((certified / total) * 100),
    trainingByClinic,
    modelCounts,
    priorityEquipment,
  };
}
