import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { getFirebaseIdToken } from './auth';
import type { GeneratedDossier, Lead } from '@/types';

vi.mock('./auth', () => ({
  getFirebaseIdToken: vi.fn(async () => 'token-demo'),
}));

type AiApi = typeof import('./aiApi');
let api: AiApi;

const fetchMock = vi.fn();

beforeAll(async () => {
  vi.stubEnv('NEXT_PUBLIC_AI_API_URL', 'https://api.test/');
  api = await import('./aiApi');
});

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Lead tal como llega del scraper en frío: sin ningún dato regulatorio. */
function buildLead(overrides: Partial<Lead> = {}): Lead {
  return {
    id: 'lead-001',
    name: 'Clínica San Gabriel',
    district: 'San Isidro',
    specialty: 'Traumatología y Quemados',
    score: 82,
    status: 'descubierto',
    statusNote: '',
    directorMedico: 'Dra. Ana Torres',
    doctorSpecialty: 'Traumatología',
    hasAiDraft: false,
    draftApproved: false,
    telemetryActivity: { ahtmReads: 3, lumbarMinutes: 12 },
    aiSuggestion: 'Ofrecer demo del modelo OaaS',
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

const official = {
  registry_number: 'DM-14820-E',
  classification: 'Dispositivo Médico Clase IIb (SEDECAL, España)',
  calibration_certificate: 'Calibración de fábrica — SEDECAL ISO 13485',
  good_practices_certificate: 'Droguería Autorizada Tecnology Care SRL — DIGEMID',
  informed_consent_template: 'Formato de consentimiento informado para autohemoterapia mayor (AHTm)',
};

const apiDossierResponse = {
  lead_id: 'clinica-san-gabriel',
  version: 2,
  version_label: 'v2',
  product_line: 'ozonette_infiltracion',
  product_name: 'Ozonette — Generador compacto para infiltración y dolor',
  catalog_match: 'specialty',
  regulatory_data: official,
  markdown_path: 'output/leads/clinica-san-gabriel/v2/document.md',
  pdf_path: 'output/leads/clinica-san-gabriel/v2/document.pdf',
  download_urls: {
    markdown: '/documents/leads/clinica-san-gabriel/versions/2/document.md',
    pdf: '/documents/leads/clinica-san-gabriel/versions/2/document.pdf',
  },
  generated_at: '2026-10-15T02:00:00+00:00',
  verification_required: true,
} as const;

const generatedDossier: GeneratedDossier = {
  leadId: 'clinica-san-gabriel',
  version: 2,
  versionLabel: 'v2',
  productLine: 'ozonette_infiltracion',
  productName: 'Ozonette — Generador compacto para infiltración y dolor',
  catalogMatch: 'specialty',
  regulatory: {
    registryNumber: 'DM-14820-E',
    classification: official.classification,
    calibrationCertificate: official.calibration_certificate,
    goodPracticesCertificate: official.good_practices_certificate,
    informedConsentTemplate: official.informed_consent_template,
  },
  markdownPath: apiDossierResponse.markdown_path,
  pdfPath: apiDossierResponse.pdf_path,
  downloadUrls: apiDossierResponse.download_urls,
  generatedAt: '2026-10-15T02:00:00+00:00',
  verificationRequired: true,
};

describe('generateDossier', () => {
  it('envía solo la identidad del lead y la especialidad, sin datos regulatorios', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(apiDossierResponse));

    await api.generateDossier(buildLead());

    const [url, init] = fetchMock.mock.calls[0];
    const body = JSON.parse(init.body);

    expect(url).toBe('https://api.test/generate/dossier');
    expect(init.headers.Authorization).toBe('Bearer token-demo');
    expect(body.lead_id).toBe('lead-001');
    expect(body.specialty).toBe('Traumatología y Quemados');
    expect(body).not.toHaveProperty('validated_regulatory_data');
    expect(body).not.toHaveProperty('registry_number');
  });

  it('funciona con un lead nuevo que no trae ningún dato regulatorio', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(apiDossierResponse));

    await expect(api.generateDossier(buildLead())).resolves.toBeDefined();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('genera sin sesión: la petición sale sin encabezado Authorization', async () => {
    vi.mocked(getFirebaseIdToken).mockResolvedValueOnce(null);
    fetchMock.mockResolvedValueOnce(jsonResponse(apiDossierResponse));

    await expect(api.generateDossier(buildLead())).resolves.toBeDefined();

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers).not.toHaveProperty('Authorization');
  });

  it('mapea la respuesta, incluidos los datos oficiales del catálogo', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(apiDossierResponse));

    const dossier = await api.generateDossier(buildLead());

    expect(dossier).toEqual(generatedDossier);
  });

  it('muestra el detalle de error que devuelve el backend', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ detail: 'Gemini no devolvió una respuesta estructurada válida.' }, 502),
    );

    await expect(api.generateDossier(buildLead())).rejects.toThrow(
      'Gemini no devolvió una respuesta estructurada válida.',
    );
  });
});

describe('downloadDossier', () => {
  it('descarga el PDF con el token y lo entrega como archivo con nombre de versión', async () => {
    const link = { href: '', download: '', click: vi.fn(), remove: vi.fn() };
    vi.stubGlobal('document', {
      createElement: vi.fn(() => link),
      body: { appendChild: vi.fn() },
    });
    const createObjectURL = vi.fn(() => 'blob:demo');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL, revokeObjectURL }));
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => new Blob(['%PDF-1.4']),
    });

    await api.downloadDossier(generatedDossier, 'pdf');

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(
      'https://api.test/documents/leads/clinica-san-gabriel/versions/2/document.pdf',
    );
    expect(init.headers.Authorization).toBe('Bearer token-demo');
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(link.href).toBe('blob:demo');
    expect(link.download).toBe('clinica-san-gabriel-v2.pdf');
    expect(link.click).toHaveBeenCalledTimes(1);
  });

  it('lanza error si la descarga falla', async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 404, blob: async () => new Blob() });

    await expect(api.downloadDossier(generatedDossier, 'markdown')).rejects.toThrow('HTTP 404');
  });
});

describe('URL base de la API', () => {
  it('usa http://localhost:8000 cuando NEXT_PUBLIC_AI_API_URL no está definida', async () => {
    vi.stubEnv('NEXT_PUBLIC_AI_API_URL', '');
    vi.resetModules();
    const localApi = await import('./aiApi');
    fetchMock.mockResolvedValueOnce(jsonResponse(apiDossierResponse));

    await localApi.generateDossier(buildLead());

    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/generate/dossier');
  });
});

describe('simulador de contraofertas', () => {
  const offer = {
    productId: 'ozonette',
    sessionPricePen: 120,
    sessionsPerMonth: 40,
    equipmentPriceUsd: 6500,
    installationIncluded: false,
    trainingIncludedSessions: 2,
    installments: 1,
    warrantyMonths: 12,
  };

  const apiEvaluation = {
    investment_usd: 6900,
    monthly_flow_usd: 680,
    recovery_months: 10.15,
    return_24m: 1.365,
    margin: 0.338,
    installation_charged_usd: 400,
    training_charged_usd: 0,
    clinic_viable: true,
    tecnocare_viable: true,
    zone: 'win_win',
    min_equipment_price_usd: 5693.33,
    violations: [],
    status: 'green',
    message: 'Zona de acuerdo: margen aceptable y recuperación dentro del umbral.',
    data_status: 'mock',
  };

  it('simulateRoi envía la oferta en snake_case y mapea el resultado', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(apiEvaluation));

    const result = await api.simulateRoi(offer);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('https://api.test/roi/simulate');
    expect(JSON.parse(init.body)).toEqual({
      product_id: 'ozonette',
      session_price_pen: 120,
      sessions_per_month: 40,
      equipment_price_usd: 6500,
      installation_included: false,
      training_included_sessions: 2,
      installments: 1,
      warranty_months: 12,
    });
    expect(result.zone).toBe('win_win');
    expect(result.recoveryMonths).toBeCloseTo(10.15);
    expect(result.minEquipmentPriceUsd).toBeCloseTo(5693.33);
    expect(result.dataStatus).toBe('mock');
  });

  it('generateProforma envía el lead y la oferta, y devuelve la versión creada', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        lead_id: 'lead-001',
        version: 1,
        version_label: 'v1',
        product_name: 'Ozonette',
        evaluation: apiEvaluation,
        pdf_path: 'output/leads/lead-001/v1/propuesta_comercial.pdf',
        params_path: 'output/leads/lead-001/v1/parametros.json',
        download_urls: {
          pdf: '/documents/leads/lead-001/versions/1/propuesta_comercial.pdf',
          params: '/documents/leads/lead-001/versions/1/parametros.json',
        },
        generated_at: '2026-10-15T18:00:00+00:00',
      }),
    );

    const proforma = await api.generateProforma(buildLead(), offer);

    const [url, init] = fetchMock.mock.calls[0];
    const body = JSON.parse(init.body);
    expect(url).toBe('https://api.test/roi/proforma');
    expect(body.lead_name).toBe('Clínica San Gabriel');
    expect(body.lead_id).toBe('lead-001');
    expect(body.product_id).toBe('ozonette');
    expect(proforma.versionLabel).toBe('v1');
    expect(proforma.downloadUrls.pdf).toContain('propuesta_comercial.pdf');
    expect(proforma.evaluation.status).toBe('green');
  });

  it('generateProforma muestra el motivo cuando el backend lo rechaza', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ detail: 'No se genera la propuesta: La clínica no recupera.' }, 422),
    );

    await expect(api.generateProforma(buildLead(), offer)).rejects.toThrow('No se genera la propuesta');
  });

  it('downloadApiFile usa el token y el nombre de archivo indicado', async () => {
    const link = { href: '', download: '', click: vi.fn(), remove: vi.fn() };
    vi.stubGlobal('document', { createElement: vi.fn(() => link), body: { appendChild: vi.fn() } });
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() }));
    fetchMock.mockResolvedValueOnce({ ok: true, status: 200, blob: async () => new Blob(['{}']) });

    await api.downloadApiFile('/documents/leads/lead-001/versions/1/parametros.json', 'lead-001-v1-parametros.json');

    expect(fetchMock.mock.calls[0][0]).toBe('https://api.test/documents/leads/lead-001/versions/1/parametros.json');
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer token-demo');
    expect(link.download).toBe('lead-001-v1-parametros.json');
  });
});

describe('envío de outbound por Gmail', () => {
  const attachments = [
    { version: 1, filename: 'propuesta_comercial.pdf' as const, label: 'Propuesta comercial (PDF) · v1', downloadUrl: '/x' },
  ];

  it('fetchLeadDocuments devuelve los archivos adjuntables del lead', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        lead_id: 'lead-001',
        files: [
          {
            version: 2,
            filename: 'document.pdf',
            label: 'Dossier regulatorio (PDF) · v2',
            download_url: '/documents/leads/lead-001/versions/2/document.pdf',
          },
        ],
      }),
    );

    const files = await api.fetchLeadDocuments('lead-001');

    expect(fetchMock.mock.calls[0][0]).toBe('https://api.test/leads/lead-001/documents');
    expect(files).toEqual([
      {
        version: 2,
        filename: 'document.pdf',
        label: 'Dossier regulatorio (PDF) · v2',
        downloadUrl: '/documents/leads/lead-001/versions/2/document.pdf',
      },
    ]);
  });

  it('sendOutboundEmail envía el cuerpo editado y los adjuntos por referencia', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        status: 'contactado',
        message_id: 'msg-1',
        sent_at: '2026-10-15T20:00:00+00:00',
        to: 'director@clinica.pe',
        subject: 'Asunto editado',
        attachments: ['propuesta-comercial-v1.pdf'],
      }),
    );

    const result = await api.sendOutboundEmail({
      lead: buildLead(),
      to: 'director@clinica.pe',
      subject: 'Asunto editado',
      body: 'Cuerpo editado',
      attachments,
    });

    const [url, init] = fetchMock.mock.calls[0];
    const body = JSON.parse(init.body);
    expect(url).toBe('https://api.test/outbound/send');
    expect(body.body).toBe('Cuerpo editado');
    expect(body.attachments).toEqual([{ version: 1, filename: 'propuesta_comercial.pdf' }]);
    expect(result.status).toBe('contactado');
    expect(result.messageId).toBe('msg-1');
  });

  it('sendOutboundEmail lanza GmailAuthRequiredError cuando la cuenta no está vinculada', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        { detail: { code: 'gmail_auth_required', message: 'Vincula Gmail', auth_url: '/gmail/auth/start' } },
        401,
      ),
    );

    await expect(
      api.sendOutboundEmail({ lead: buildLead(), to: 'a@b.pe', subject: 's', body: 'b', attachments: [] }),
    ).rejects.toBeInstanceOf(api.GmailAuthRequiredError);
  });

  it('gmailConnectUrl apunta al inicio de OAuth del backend', () => {
    expect(api.gmailConnectUrl()).toBe('https://api.test/gmail/auth/start');
  });
});
