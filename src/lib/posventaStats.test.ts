import { describe, expect, it } from 'vitest';

import { INITIAL_CONSUMABLES, INITIAL_MAINTENANCE, INITIAL_TRAINING_BY_CLINIC } from '../data/mockData';

import { buildPosventaStats, monthlyUnits } from './posventaStats';

describe('buildPosventaStats con el mock', () => {
  const stats = buildPosventaStats(INITIAL_MAINTENANCE, INITIAL_CONSUMABLES, INITIAL_TRAINING_BY_CLINIC);

  it('cuenta los equipos instalados y la salud promedio', () => {
    expect(stats.installed).toBe(12);
    expect(stats.averageHealth).toBeGreaterThan(0);
    expect(stats.averageHealth).toBeLessThanOrEqual(100);
  });

  it('reparte los equipos en bandas de salud sin perder ninguno', () => {
    const total = stats.healthBands.reduce((sum, band) => sum + band.count, 0);
    expect(total).toBe(stats.installed);
  });

  it('cuenta insumos por estado y las unidades en riesgo', () => {
    const { agotado, reabastecer, al_dia } = stats.consumablesByStatus;
    expect(agotado + reabastecer + al_dia).toBe(INITIAL_CONSUMABLES.length);
    expect(stats.unitsAtRisk).toBeGreaterThan(0);
  });

  it('calcula la capacitación total y por clínica, de menor a mayor avance', () => {
    expect(stats.trainingPercent).toBeGreaterThan(0);
    const percents = stats.trainingByClinic.map((row) => row.percent);
    expect(percents).toEqual([...percents].sort((a, b) => a - b));
  });

  it('pone primero los equipos con alerta y el de menor salud', () => {
    expect(stats.priorityEquipment.length).toBeGreaterThan(0);
    expect(stats.priorityEquipment.every((item) => item.urgency !== 'low')).toBe(true);
    const health = stats.priorityEquipment.map((item) => item.healthPercent);
    expect(health).toEqual([...health].sort((a, b) => a - b));
  });

  it('agrupa modelos sin el prefijo de marca', () => {
    expect(stats.modelCounts.every((row) => !row.model.startsWith('SEDECAL'))).toBe(true);
    expect(stats.modelCounts.reduce((sum, row) => sum + row.count, 0)).toBe(stats.installed);
  });
});

describe('monthlyUnits', () => {
  it('extrae el número de "24 por mes"', () => {
    expect(monthlyUnits('24 por mes')).toBe(24);
    expect(monthlyUnits('sin cifra')).toBe(0);
  });
});
