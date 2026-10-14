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

export interface DigemidDossier {
  registryNumber: string;
  classification: string;
  calibrationCertificate: string;
  goodPracticesCertificate: string;
  informedConsentTemplate: string;
  verified: boolean;
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
  digemidDossier?: DigemidDossier;
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
  aiContent: OutboundDraft | RoiProposal | DigemidDossier | ConsumableItem['reminderDraft'];
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
