import { getFirebaseIdToken } from './auth';
import type {
  GeneratedDossier,
  Lead,
  OutboundDraft,
  RoiEvaluation,
  RoiOffer,
  RoiProforma,
  RoiProposal,
  RoiZone,
  LeadDocument,
  OutboundSendResult,
} from '@/types';

// Desarrollo local: sin NEXT_PUBLIC_AI_API_URL (p. ej. sin .env.local) se usa el backend en localhost.
const DEFAULT_AI_API_URL = 'http://localhost:8000';
const apiUrl = (process.env.NEXT_PUBLIC_AI_API_URL || DEFAULT_AI_API_URL).replace(/\/$/, '');

type ApiProspect = {
  name: string;
  district: string;
  specialty: string;
  director_medico: string;
  doctor_specialty: string;
  score: number;
  ai_suggestion: string;
};

type ApiRoiOutput = {
  summary: string;
  equipment_model: string;
  monthly_lease_cost: number;
  minimum_kits_per_month: number;
  cost_per_session: number;
  patient_price_avg: number;
  projected_sessions_month: number;
  estimated_net_monthly: number;
  assumptions: string[];
};

type ApiOutboundOutput = {
  recipient_name: string;
  recipient_role: string;
  subject: string;
  body: string;
  suggested_channel: OutboundDraft['suggestedChannel'];
  evidence_used: string[];
};

type ApiDossierOutput = {
  lead_id: string;
  version: number;
  version_label: string;
  product_line: string;
  product_name: string;
  catalog_match: 'explicit' | 'specialty' | 'default';
  regulatory_data: {
    registry_number: string;
    classification: string;
    calibration_certificate: string;
    good_practices_certificate: string;
    informed_consent_template: string;
  };
  markdown_path: string;
  pdf_path: string;
  download_urls: { markdown: string; pdf: string };
  generated_at: string;
  verification_required: true;
};

function prospectPayload(lead: Lead): ApiProspect {
  return {
    name: lead.name,
    district: lead.district,
    specialty: lead.specialty,
    director_medico: lead.directorMedico,
    doctor_specialty: lead.doctorSpecialty,
    score: lead.score,
    ai_suggestion: lead.aiSuggestion,
  };
}

/** Añade el token solo si hay sesión; sin sesión la petición sale sin encabezado de auth. */
async function authHeaders(): Promise<Record<string, string>> {
  const token = await getFirebaseIdToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function post<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    method: 'POST',
    headers: {
      ...(await authHeaders()),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = `Error HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the HTTP status when the API does not return JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export async function generateOutbound(lead: Lead): Promise<OutboundDraft> {
  const output = await post<ApiOutboundOutput>('/generate/outbound', prospectPayload(lead));
  return {
    recipientName: output.recipient_name,
    recipientRole: output.recipient_role,
    subject: output.subject,
    body: output.body,
    suggestedChannel: output.suggested_channel,
  };
}

export async function generateRoi(lead: Lead): Promise<RoiProposal> {
  const current = lead.roiProposal;
  if (!current) {
    throw new Error('Este prospecto no tiene parámetros ROI validados para generar una propuesta.');
  }

  const output = await post<ApiRoiOutput>('/generate/roi', {
    ...prospectPayload(lead),
    equipment_model: current.equipmentModel,
    monthly_lease_cost: current.monthlyLeaseCost,
    minimum_kits_per_month: current.minimumKitsPerMonth,
    cost_per_session: current.costPerSession,
    patient_price_avg: current.patientPriceAvg,
    projected_sessions_month: current.projectedSessionsMonth,
  });

  return {
    equipmentModel: output.equipment_model,
    monthlyLeaseCost: output.monthly_lease_cost,
    minimumKitsPerMonth: output.minimum_kits_per_month,
    costPerSession: output.cost_per_session,
    patientPriceAvg: output.patient_price_avg,
    projectedSessionsMonth: output.projected_sessions_month,
    estimatedNetMonthly: output.estimated_net_monthly,
  };
}

/**
 * El backend resuelve la línea de producto y adjunta los datos regulatorios oficiales
 * del catálogo maestro. El lead no aporta datos regulatorios.
 */
export async function generateDossier(lead: Lead): Promise<GeneratedDossier> {
  const output = await post<ApiDossierOutput>('/generate/dossier', {
    ...prospectPayload(lead),
    lead_id: lead.id,
  });

  return {
    leadId: output.lead_id,
    version: output.version,
    versionLabel: output.version_label,
    productLine: output.product_line,
    productName: output.product_name,
    catalogMatch: output.catalog_match,
    regulatory: {
      registryNumber: output.regulatory_data.registry_number,
      classification: output.regulatory_data.classification,
      calibrationCertificate: output.regulatory_data.calibration_certificate,
      goodPracticesCertificate: output.regulatory_data.good_practices_certificate,
      informedConsentTemplate: output.regulatory_data.informed_consent_template,
    },
    markdownPath: output.markdown_path,
    pdfPath: output.pdf_path,
    downloadUrls: output.download_urls,
    generatedAt: output.generated_at,
    verificationRequired: output.verification_required,
  };
}

/**
 * Descarga una versión del dossier. La ruta exige el token de Firebase, así que
 * no puede abrirse con un enlace directo: se pide con fetch y se entrega como archivo.
 */
type ApiEvaluation = {
  investment_usd: number;
  monthly_flow_usd: number;
  recovery_months: number | null;
  return_24m: number | null;
  margin: number | null;
  installation_charged_usd: number;
  training_charged_usd: number;
  clinic_viable: boolean;
  tecnocare_viable: boolean;
  zone: RoiZone;
  min_equipment_price_usd: number | null;
  violations: string[];
  status: 'green' | 'red';
  message: string;
  data_status: string;
};

type ApiProformaOutput = {
  lead_id: string;
  version: number;
  version_label: string;
  product_name: string;
  evaluation: ApiEvaluation;
  pdf_path: string;
  params_path: string;
  download_urls: { pdf: string; params: string };
  generated_at: string;
};

function offerPayload(offer: RoiOffer) {
  return {
    product_id: offer.productId,
    session_price_pen: offer.sessionPricePen,
    sessions_per_month: offer.sessionsPerMonth,
    equipment_price_usd: offer.equipmentPriceUsd,
    installation_included: offer.installationIncluded,
    training_included_sessions: offer.trainingIncludedSessions,
    installments: offer.installments,
    warranty_months: offer.warrantyMonths,
  };
}

function mapEvaluation(output: ApiEvaluation): RoiEvaluation {
  return {
    investmentUsd: output.investment_usd,
    monthlyFlowUsd: output.monthly_flow_usd,
    recoveryMonths: output.recovery_months,
    return24m: output.return_24m,
    margin: output.margin,
    installationChargedUsd: output.installation_charged_usd,
    trainingChargedUsd: output.training_charged_usd,
    clinicViable: output.clinic_viable,
    tecnocareViable: output.tecnocare_viable,
    zone: output.zone,
    minEquipmentPriceUsd: output.min_equipment_price_usd,
    violations: output.violations,
    status: output.status,
    message: output.message,
    dataStatus: output.data_status,
  };
}

/** Recalcula la oferta en el backend. No usa IA, así que puede llamarse en cada cambio del simulador. */
export async function simulateRoi(offer: RoiOffer): Promise<RoiEvaluation> {
  const output = await post<ApiEvaluation>('/roi/simulate', offerPayload(offer));
  return mapEvaluation(output);
}

/** Genera una nueva versión de la propuesta ajustada. El backend solo la acepta si hay acuerdo (RN-044). */
export async function generateProforma(lead: Lead, offer: RoiOffer): Promise<RoiProforma> {
  const output = await post<ApiProformaOutput>('/roi/proforma', {
    ...offerPayload(offer),
    lead_name: lead.name,
    lead_id: lead.id,
  });

  return {
    leadId: output.lead_id,
    version: output.version,
    versionLabel: output.version_label,
    productName: output.product_name,
    evaluation: mapEvaluation(output.evaluation),
    pdfPath: output.pdf_path,
    paramsPath: output.params_path,
    downloadUrls: output.download_urls,
    generatedAt: output.generated_at,
  };
}

/** Descarga un archivo versionado de la API con el token (si hay sesión) y lo entrega como archivo. */
export async function downloadApiFile(relativeUrl: string, filename: string): Promise<void> {
  const response = await fetch(`${apiUrl}${relativeUrl}`, {
    headers: await authHeaders(),
  });

  if (!response.ok) {
    throw new Error(`No se pudo descargar el documento (HTTP ${response.status}).`);
  }

  const objectUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export async function downloadDossier(
  dossier: GeneratedDossier,
  format: 'pdf' | 'markdown',
): Promise<void> {
  const extension = format === 'pdf' ? 'pdf' : 'md';
  await downloadApiFile(
    dossier.downloadUrls[format],
    `${dossier.leadId}-${dossier.versionLabel}.${extension}`,
  );
}

/* ── Outbound por Gmail ── */

/** El dueño debe vincular su cuenta de Gmail antes de enviar. */
export class GmailAuthRequiredError extends Error {
  readonly authUrl: string;

  constructor(message: string, authUrl: string) {
    super(message);
    this.name = 'GmailAuthRequiredError';
    this.authUrl = authUrl;
  }
}

/** URL que abre la pestaña de consentimiento de Google (el backend redirige). */
export function gmailConnectUrl(): string {
  return `${apiUrl}/gmail/auth/start`;
}

type ApiLeadDocument = {
  version: number;
  filename: LeadDocument['filename'];
  label: string;
  download_url: string;
};

export async function fetchLeadDocuments(leadId: string): Promise<LeadDocument[]> {
  const response = await fetch(`${apiUrl}/leads/${encodeURIComponent(leadId)}/documents`, {
    headers: await authHeaders(),
  });
  if (!response.ok) {
    throw new Error(`No se pudieron cargar los documentos del prospecto (HTTP ${response.status}).`);
  }

  const body = (await response.json()) as { files: ApiLeadDocument[] };
  return body.files.map((file) => ({
    version: file.version,
    filename: file.filename,
    label: file.label,
    downloadUrl: file.download_url,
  }));
}

export async function sendOutboundEmail(input: {
  lead: Lead;
  to: string;
  subject: string;
  body: string;
  attachments: LeadDocument[];
}): Promise<OutboundSendResult> {
  const response = await fetch(`${apiUrl}/outbound/send`, {
    method: 'POST',
    headers: {
      ...(await authHeaders()),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      lead_id: input.lead.id,
      lead_name: input.lead.name,
      to: input.to,
      subject: input.subject,
      body: input.body,
      attachments: input.attachments.map((file) => ({ version: file.version, filename: file.filename })),
    }),
  });

  if (!response.ok) {
    const failure = (await response.json().catch(() => ({}))) as {
      detail?: string | { code?: string; message?: string; auth_url?: string };
    };
    const detail = failure.detail;
    if (response.status === 401 && typeof detail === 'object' && detail.code === 'gmail_auth_required') {
      throw new GmailAuthRequiredError(detail.message ?? 'Vincula tu cuenta de Gmail.', detail.auth_url ?? '');
    }
    throw new Error(typeof detail === 'string' ? detail : `Error HTTP ${response.status}`);
  }

  const body = (await response.json()) as {
    status: 'contactado';
    message_id: string;
    sent_at: string;
    to: string;
    subject: string;
    attachments: string[];
  };
  return {
    status: body.status,
    messageId: body.message_id,
    sentAt: body.sent_at,
    to: body.to,
    subject: body.subject,
    attachments: body.attachments,
  };
}
