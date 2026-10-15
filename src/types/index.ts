export type PipelineStatus = 'descubierto' | 'contactado' | 'propuesta_enviada' | 'cierre';

export interface TelemetryActivity {
  ahtmReads: number;
  lumbarMinutes: number;
  searchQuery?: string;
  lastVisited?: string;
}

export interface RoiProposal {
  equipmentModel: string;
  monthlyLeaseCost: number;
  minimumKitsPerMonth: number;
  costPerSession: number;
  patientPriceAvg: number;
  projectedSessionsMonth: number;
  estimatedNetMonthly: number;
}

/** Datos regulatorios oficiales de ConfIA (catálogo maestro). Los asigna el backend, nunca el lead ni la IA. */
export interface DigemidDossier {
  registryNumber: string;
  classification: string;
  calibrationCertificate: string;
  goodPracticesCertificate: string;
  informedConsentTemplate: string;
}

/** Documento generado por el backend (Markdown + PDF) con versionado local. */
export interface GeneratedDossier {
  leadId: string;
  version: number;
  versionLabel: string;
  productLine: string;
  productName: string;
  catalogMatch: 'explicit' | 'specialty' | 'default';
  regulatory: DigemidDossier;
  markdownPath: string;
  pdfPath: string;
  downloadUrls: {
    markdown: string;
    pdf: string;
  };
  generatedAt: string;
  verificationRequired: true;
}

export interface OutboundDraft {
  recipientName: string;
  recipientRole: string;
  subject: string;
  body: string;
  suggestedChannel: 'Email' | 'LinkedIn' | 'WhatsApp Directo';
}

export interface Lead {
  id: string;
  name: string;
  district: string;
  specialty: string;
  score: number;
  status: PipelineStatus;
  statusNote: string;
  directorMedico: string;
  doctorSpecialty: string;
  hasAiDraft: boolean;
  draftType?: 'outbound' | 'roi' | 'dossier' | 'consumibles';
  draftApproved: boolean;
  telemetryAlert?: boolean;
  telemetryActivity: TelemetryActivity;
  aiSuggestion: string;
  clientType?: 'Clinica' | 'Hospital Publico' | 'Consultorio Privado' | 'Medico Independiente';
  outboundDraft?: OutboundDraft;
  roiProposal?: RoiProposal;
  dossierDocument?: GeneratedDossier;
  lastOutboundSentAt?: string;
}

export type ConsumableStatus = 'agotado' | 'reabastecer' | 'al_dia';

export interface ConsumableItem {
  id: string;
  clinicName: string;
  consumableType: string;
  estimatedMonthly: string;
  lastOrderText: string;
  status: ConsumableStatus;
  urgentAiReminder: boolean;
  reminderDraft?: {
    subject: string;
    body: string;
  };
}

export interface MaintenanceItem {
  id: string;
  clinicName: string;
  clientType?: string;
  equipmentModel: string;
  serialNumber?: string;
  installYear: number;
  expectedLifespanYears: number; // e.g. 5 to 6 years
  currentYearOfUse: number; // e.g. Año 2 de 5
  task: string;
  dueInText: string;
  urgency: 'high' | 'medium' | 'low';
  installDate?: string;
  nextMajorService?: string;
  healthPercent: number; // 0 to 100%
  statusNote: string;
}

export interface TrainingProgress {
  certifiedDoctors: number;
  totalDoctors: number;
  recentProtocolName: string;
  targetDepartment: string;
}

export interface FirestoreCollectionDefinition {
  name: string;
  purpose: string;
  fields: string[];
  role: 'admin' | 'sales' | 'medical' | 'support';
}

export interface DatasetAlert {
  id: string;
  title: string;
  summary: string;
  risk: 'alta' | 'media' | 'baja';
}

export type ProposalType = 'outbound' | 'roi' | 'dossier' | 'consumibles';

export interface ProposalDocument {
  id: string;
  prospectId: string;
  type: ProposalType;
  status: 'pending_approval' | 'approved' | 'discarded';
  createdBy: string;
  approvedBy?: string;
  aiContent: OutboundDraft | RoiProposal | GeneratedDossier | ConsumableItem['reminderDraft'];
}

export interface InstalledBaseRecord {
  id: string;
  clinicName: string;
  equipmentModel: string;
  installationDate: string;
  consumableStatus: ConsumableStatus;
  lastOrderText: string;
  maintenanceTask?: string;
  maintenanceDueInText?: string;
  maintenanceUrgency?: MaintenanceItem['urgency'];
  trainingProgress: TrainingProgress;
}

/* ── Equipment Catalog ──────────────────────────────── */

export interface EquipmentItem {
  id: string;
  model: string;
  brand: string;
  category: string;
  description: string;
  priceUSD: number;
  registroDiGEMID?: string;
  certifications: string[];
  maintenanceCycleYears: number;
  imageUrl?: string;
  applications: string[];
}

/* ── Regulatory Files for AI ─────────────────────────── */

export interface RegulatoryFile {
  id: string;
  name: string;
  type: 'declaracion_madrid' | 'registro_sanitario' | 'calibracion' | 'buenas_practicas' | 'consentimiento' | 'protocolo' | 'otro';
  description: string;
  uploadedAt: string;
  sizeKB: number;
  feedsAI: boolean;
}

/* ── Simulador de contraofertas (procedimiento v0.3) ── */

/** Parámetros que ajusta el dueño. Las cifras del catálogo (lista, costos) las resuelve el backend. */
export interface RoiOffer {
  productId: string;
  sessionPricePen: number;
  sessionsPerMonth: number;
  equipmentPriceUsd: number;
  installationIncluded: boolean;
  trainingIncludedSessions: number;
  installments: number;
  warrantyMonths: number;
}

export type RoiZone = 'win_win' | 'clinic_only' | 'tecnocare_only' | 'none';

/** Resultado del cálculo. El margen y el precio mínimo son internos: no se muestran a la clínica. */
export interface RoiEvaluation {
  investmentUsd: number;
  monthlyFlowUsd: number;
  recoveryMonths: number | null;
  return24m: number | null;
  margin: number | null;
  installationChargedUsd: number;
  trainingChargedUsd: number;
  clinicViable: boolean;
  tecnocareViable: boolean;
  zone: RoiZone;
  minEquipmentPriceUsd: number | null;
  violations: string[];
  status: 'green' | 'red';
  message: string;
  dataStatus: string;
}

export interface RoiProforma {
  leadId: string;
  version: number;
  versionLabel: string;
  productName: string;
  evaluation: RoiEvaluation;
  pdfPath: string;
  paramsPath: string;
  downloadUrls: {
    pdf: string;
    params: string;
  };
  generatedAt: string;
}

/* ── Envío de outbound por Gmail ── */

/** Documento versionado del lead que puede adjuntarse al correo. */
export interface LeadDocument {
  version: number;
  filename: 'document.pdf' | 'propuesta_comercial.pdf';
  label: string;
  downloadUrl: string;
}

export interface OutboundSendResult {
  status: 'contactado';
  messageId: string;
  sentAt: string;
  to: string;
  subject: string;
  attachments: string[];
}
