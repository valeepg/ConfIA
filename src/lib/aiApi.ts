import { getFirebaseIdToken } from './auth';
import type { DigemidDossier, Lead, OutboundDraft, RoiProposal } from '@/types';

const apiUrl = process.env.NEXT_PUBLIC_AI_API_URL?.replace(/\/$/, '');

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
  title: string;
  summary: string;
  registry_number: string;
  classification: string;
  calibration_certificate: string;
  good_practices_certificate: string;
  informed_consent_template: string;
  verification_required: boolean;
  warnings: string[];
};

function requireApiUrl() {
  if (!apiUrl) {
    throw new Error('NEXT_PUBLIC_AI_API_URL no está configurada.');
  }
  return apiUrl;
}

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

async function post<T>(path: string, payload: unknown): Promise<T> {
  const token = await getFirebaseIdToken();
  const response = await fetch(`${requireApiUrl()}${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
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

export async function generateDossier(lead: Lead): Promise<DigemidDossier> {
  const current = lead.digemidDossier;
  if (!current) {
    throw new Error('Este prospecto no tiene datos regulatorios validados para generar un dossier.');
  }

  const output = await post<ApiDossierOutput>('/generate/dossier', {
    ...prospectPayload(lead),
    validated_regulatory_data: {
      registry_number: current.registryNumber,
      classification: current.classification,
      calibration_certificate: current.calibrationCertificate,
      good_practices_certificate: current.goodPracticesCertificate,
      informed_consent_template: current.informedConsentTemplate,
    },
  });

  return {
    registryNumber: output.registry_number,
    classification: output.classification,
    calibrationCertificate: output.calibration_certificate,
    goodPracticesCertificate: output.good_practices_certificate,
    informedConsentTemplate: output.informed_consent_template,
    verified: !output.verification_required,
  };
}
