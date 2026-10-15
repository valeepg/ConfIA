import { describe, expect, it } from 'vitest';

import type { Lead } from '@/types';

import { answerAdvisorQuestion, buildAdvisorContext, detectTopic } from './demoAdvisor';

function lead(overrides: Partial<Lead> & Pick<Lead, 'id' | 'name' | 'score' | 'status'>): Lead {
  return {
    district: 'San Isidro',
    specialty: 'Traumatología',
    statusNote: '',
    directorMedico: 'Dr. Demo',
    doctorSpecialty: 'Traumatología',
    hasAiDraft: false,
    draftApproved: false,
    telemetryActivity: { ahtmReads: 0, lumbarMinutes: 0 },
    aiSuggestion: '',
    ...overrides,
  };
}

const PIPELINE: Lead[] = [
  lead({ id: 'a', name: 'Clínica Alfa', score: 91, status: 'descubierto' }),
  lead({ id: 'b', name: 'Clínica Beta', score: 74, status: 'descubierto' }),
  lead({ id: 'c', name: 'Clínica Gamma', score: 88, status: 'contactado', hasAiDraft: true, draftApproved: false }),
  lead({
    id: 'd',
    name: 'Clínica Delta',
    score: 60,
    status: 'propuesta_enviada',
    roiProposal: {
      equipmentModel: 'Ozonette',
      monthlyLeaseCost: 0,
      minimumKitsPerMonth: 1,
      costPerSession: 15,
      patientPriceAvg: 40,
      projectedSessionsMonth: 40,
      estimatedNetMonthly: 1000,
    },
  }),
  lead({ id: 'e', name: 'Clínica Épsilon', score: 40, status: 'cierre' }),
];

describe('buildAdvisorContext', () => {
  it('cuenta prospectos por etapa y calcula el score promedio', () => {
    const context = buildAdvisorContext(PIPELINE);

    expect(context.totalLeads).toBe(5);
    expect(context.byStatus).toEqual({ descubierto: 2, contactado: 1, propuesta_enviada: 1, cierre: 1 });
    expect(context.averageScore).toBe(71);
  });

  it('lista los de alto score sin contactar, de mayor a menor', () => {
    const context = buildAdvisorContext(PIPELINE);
    expect(context.highScoreNotContacted.map((p) => p.name)).toEqual(['Clínica Alfa', 'Clínica Beta']);
  });

  it('cuenta borradores pendientes y suma el ROI potencial', () => {
    const context = buildAdvisorContext(PIPELINE);
    expect(context.pendingDrafts).toBe(1);
    expect(context.potentialNetMonthlyUsd).toBe(1000);
  });
});

describe('detectTopic', () => {
  it('reconoce los temas con y sin tildes', () => {
    expect(detectTopic('¿A quién contacto primero?')).toBe('prioridades');
    expect(detectTopic('¿Qué riesgos tiene el pipeline?')).toBe('riesgos');
    expect(detectTopic('¿Cómo cierro más propuestas este trimestre?')).toBe('cierre');
    expect(detectTopic('Dame un resumen')).toBe('resumen');
  });
});

describe('answerAdvisorQuestion', () => {
  const context = buildAdvisorContext(PIPELINE);

  it('prioriza los prospectos de alto score sin contactar', () => {
    const answer = answerAdvisorQuestion('¿A quién contacto primero?', context);
    expect(answer.text).toContain('2 prospecto(s)');
    expect(answer.bullets[0]).toBe('Clínica Alfa · score 91');
  });

  it('señala los borradores pendientes como riesgo', () => {
    const answer = answerAdvisorQuestion('¿Qué riesgos tiene?', context);
    expect(answer.bullets.some((b) => b.includes('borrador'))).toBe(true);
  });

  it('responde con el resumen por defecto', () => {
    const answer = answerAdvisorQuestion('Dame un resumen', context);
    expect(answer.text).toContain('5 prospectos');
  });

  it('avisa cuando el pipeline está vacío', () => {
    const answer = answerAdvisorQuestion('resumen', buildAdvisorContext([]));
    expect(answer.bullets).toEqual([]);
    expect(answer.text).toContain('no hay prospectos');
  });
});
