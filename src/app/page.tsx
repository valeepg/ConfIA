'use client';

import React, { useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { MetricCards } from '@/components/MetricCards';
import { IntentAlertBanner } from '@/components/IntentAlertBanner';
import { KanbanBoard } from '@/components/KanbanBoard';
import { TableView } from '@/components/TableView';
import { LeadDetailDrawer } from '@/components/LeadDetailDrawer';
import { 
  RoiApprovalModal, 
  DossierModal, 
  OutboundDraftModal 
} from '@/components/HumanInTheLoopModals';
import { PosventaView } from '@/components/PosventaView';
import { OzonePediaModal } from '@/components/OzonePediaModal';
import { 
  INITIAL_LEADS, 
  INITIAL_CONSUMABLES, 
  INITIAL_MAINTENANCE, 
  INITIAL_TRAINING 
} from '@/data/mockData';
import { Lead, PipelineStatus, ConsumableItem } from '@/types';
import { 
  Users, 
  FileEdit, 
  Send, 
  CheckCircle2, 
  Search, 
  LayoutGrid, 
  List, 
  Plus, 
  SlidersHorizontal,
  Bell,
  Sparkles,
  ShieldCheck,
  Check
} from 'lucide-react';

export default function ConfiaCRM() {
  // Navigation & View state
  const [currentTab, setCurrentTab] = useState<'pipeline' | 'prospectos' | 'posventa' | 'documentos'>('pipeline');
  const [pipelineLayout, setPipelineLayout] = useState<'kanban' | 'table'>('kanban');
  const [searchQuery, setSearchQuery] = useState('');

  // Domain data state
  const [leads, setLeads] = useState<Lead[]>(INITIAL_LEADS);
  const [consumables, setConsumables] = useState<ConsumableItem[]>(INITIAL_CONSUMABLES);
  const [maintenance] = useState(INITIAL_MAINTENANCE);
  const [training] = useState(INITIAL_TRAINING);

  // Selected lead & Drawer state
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  // Alert banner state
  const [alertVisible, setAlertVisible] = useState(true);
  const [alertMessage, setAlertMessage] = useState(
    'Alerta nueva: Clínica Santa Rosa Sur está leyendo protocolos en la OzonePedia.'
  );

  // Modals state (RF-05 Human-in-the-Loop)
  const [roiModalOpen, setRoiModalOpen] = useState(false);
  const [dossierModalOpen, setDossierModalOpen] = useState(false);
  const [outboundModalOpen, setOutboundModalOpen] = useState(false);
  const [ozonePediaOpen, setOzonePediaOpen] = useState(false);
  const [modalLead, setModalLead] = useState<Lead | null>(null);

  // Success Toast notification
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // KPI Calculations
  const activeLeadsCount = leads.filter((l) => l.status !== 'cierre').length;
  const pendingDraftsCount = leads.filter((l) => l.hasAiDraft && !l.draftApproved).length;
  const proposalsSentCount = leads.filter((l) => l.status === 'propuesta_enviada').length;
  const activeClientsCount = leads.filter((l) => l.status === 'cierre').length;

  const pipelineMetrics = [
    {
      label: 'Prospectos Activos',
      value: activeLeadsCount,
      highlight: 'teal' as const,
      icon: <Users className="w-5 h-5 text-teal-600" />,
      subtitle: 'En pipeline',
    },
    {
      label: 'Borradores por Aprobar',
      value: pendingDraftsCount,
      highlight: 'amber' as const,
      icon: <FileEdit className="w-5 h-5 text-amber-500" />,
      subtitle: 'Human-in-the-Loop',
    },
    {
      label: 'Propuestas Enviadas',
      value: proposalsSentCount,
      highlight: 'default' as const,
      icon: <Send className="w-5 h-5 text-sky-600" />,
      subtitle: 'En evaluación',
    },
    {
      label: 'Clientes Activos',
      value: activeClientsCount,
      highlight: 'emerald' as const,
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
      subtitle: 'Comodato OaaS',
    },
  ];

  // Lead search filter
  const filteredLeads = leads.filter((l) => {
    const q = searchQuery.toLowerCase();
    return (
      l.name.toLowerCase().includes(q) ||
      l.district.toLowerCase().includes(q) ||
      l.specialty.toLowerCase().includes(q) ||
      l.directorMedico.toLowerCase().includes(q)
    );
  });

  // Stage transition handler
  const handleMoveLeadStatus = (leadId: string, newStatus: PipelineStatus) => {
    setLeads((prev) =>
      prev.map((l) => (l.id === leadId ? { ...l, status: newStatus } : l))
    );
    showToast(`Estado de prospecto actualizado a: ${newStatus.replace('_', ' ').toUpperCase()}`);
  };

  // RF-05 1-Click Approval Handlers
  const handleApproveRoi = (leadId: string) => {
    setLeads((prev) =>
      prev.map((l) =>
        l.id === leadId
          ? {
              ...l,
              draftApproved: true,
              status: 'propuesta_enviada',
              statusNote: 'Propuesta ROI enviada tras aprobación humana',
            }
          : l
      )
    );
    showToast('¡Propuesta ROI aprobada y enviada a la IPRESS (1 Clic)!');
    if (selectedLead?.id === leadId) {
      setSelectedLead((prev) => (prev ? { ...prev, draftApproved: true, status: 'propuesta_enviada' } : null));
    }
  };

  const handleAttachDossier = (leadId: string) => {
    setLeads((prev) =>
      prev.map((l) =>
        l.id === leadId
          ? {
              ...l,
              statusNote: 'Dossier técnico DIGEMID homologado y enviado',
            }
          : l
      )
    );
    showToast('Expediente técnico DIGEMID adjuntado exitosamente');
  };

  const handleApproveOutbound = (leadId: string) => {
    setLeads((prev) =>
      prev.map((l) =>
        l.id === leadId
          ? {
              ...l,
              draftApproved: true,
              status: 'contactado',
              statusNote: 'Primer contacto outbound enviado',
            }
          : l
      )
    );
    showToast('Mensaje de contacto outbound aprobado y despachado (1 Clic)');
  };

  const handleApproveReminder = (consumableId: string) => {
    setConsumables((prev) =>
      prev.map((c) =>
        c.id === consumableId
          ? { ...c, status: 'al_dia', urgentAiReminder: false, lastOrderText: 'Despacho generado hoy' }
          : c
      )
    );
    showToast('Recordatorio y pedido de kits de insumos despachado exitosamente');
  };

  // Telemetry Trigger from OzonePedia
  const handleTriggerTelemetry = (clinicName: string) => {
    setAlertMessage(`Alerta nueva: ${clinicName} está leyendo protocolos en la OzonePedia.`);
    setAlertVisible(true);
    setLeads((prev) =>
      prev.map((l) =>
        l.name.includes('Santa Rosa')
          ? {
              ...l,
              telemetryAlert: true,
              telemetryActivity: {
                ...l.telemetryActivity,
                lumbarMinutes: l.telemetryActivity.lumbarMinutes + 5,
                lastVisited: 'Hace 1 minuto',
              },
            }
          : l
      )
    );
    showToast(`Telemetría recibida: Lectura registrada desde ${clinicName}`);
  };

  return (
    <div className="flex min-h-screen bg-[#F7F5F0]">
      {/* Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={(tab) => setCurrentTab(tab as any)}
        onOpenOzonePedia={() => setOzonePediaOpen(true)}
      />

      {/* Main Content Workspace */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top App Bar */}
        <header className="bg-white border-b border-[#E5E7EB] px-8 py-4 sticky top-0 z-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="font-serif font-bold text-xl text-[#071C21]">
              {currentTab === 'pipeline' && 'Pipeline B2B'}
              {currentTab === 'prospectos' && 'Directorio de IPRESS Prospectadas'}
              {currentTab === 'posventa' && 'Posventa y Retención'}
              {currentTab === 'documentos' && 'Repositorio DIGEMID'}
            </h2>
            <span className="text-xs bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] font-medium px-2.5 py-0.5 rounded-full">
              Datos de ejemplo
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Search Input */}
            <div className="relative w-64 md:w-80">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar clínica o director médico..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-[#FAF9F5] text-xs text-[#071C21] rounded-xl border border-gray-300 focus:outline-hidden focus:border-[#059669] focus:bg-white transition-all"
              />
            </div>

            {/* Quick action button */}
            <button
              onClick={() => {
                const newLead: Lead = {
                  id: `lead-${Date.now()}`,
                  name: 'Clínica San Borja Salud',
                  district: 'San Borja',
                  specialty: 'Traumatología',
                  score: 79,
                  status: 'descubierto',
                  statusNote: 'Ingresada manualmente',
                  directorMedico: 'Dr. Carlos Mendoza',
                  doctorSpecialty: 'Traumatología',
                  hasAiDraft: false,
                  draftApproved: false,
                  telemetryActivity: { ahtmReads: 0, lumbarMinutes: 0 },
                  aiSuggestion: 'Nuevo prospecto. Generar borrador de prospección OaaS.',
                };
                setLeads([newLead, ...leads]);
                showToast('Nuevo prospecto registrado en Descubierto');
              }}
              className="px-4 py-2 bg-[#059669] hover:bg-[#047857] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-xs transition-all shrink-0"
            >
              <Plus className="w-4 h-4" />
              <span>Nuevo prospecto</span>
            </button>
          </div>
        </header>

        {/* Workspace Body */}
        <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Toast Notification */}
          {toastMessage && (
            <div className="fixed bottom-6 right-6 z-50 bg-[#071C21] text-white px-5 py-3 rounded-2xl shadow-2xl border border-[#0E2E33] flex items-center gap-3 text-xs animate-in slide-in-from-bottom duration-200">
              <div className="w-6 h-6 rounded-full bg-[#059669] flex items-center justify-center shrink-0">
                <Check className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="font-medium text-gray-100">{toastMessage}</span>
            </div>
          )}

          {/* VIEW: Pipeline B2B (RF-03) */}
          {(currentTab === 'pipeline' || currentTab === 'prospectos') && (
            <div>
              {/* Top KPI Cards */}
              <MetricCards metrics={pipelineMetrics} />

              {/* Real-time Telemetry Alert Banner */}
              {alertVisible && (
                <IntentAlertBanner
                  message={alertMessage}
                  onClick={() => {
                    const santaRosa = leads.find((l) => l.name.includes('Santa Rosa')) || leads[0];
                    setSelectedLead(santaRosa);
                  }}
                  onDismiss={() => setAlertVisible(false)}
                />
              )}

              {/* View Switcher Controls (Kanban / Table) */}
              <div className="flex items-center justify-between mb-4">
                <div className="text-xs text-gray-500 font-medium">
                  Mostrando <strong>{filteredLeads.length}</strong> clínicas en prospección
                </div>

                <div className="bg-[#EFECE6] p-1 rounded-xl flex items-center gap-1 border border-[#E2DDD3]">
                  <button
                    onClick={() => setPipelineLayout('kanban')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      pipelineLayout === 'kanban'
                        ? 'bg-white text-[#071C21] shadow-xs'
                        : 'text-gray-600 hover:text-black'
                    }`}
                  >
                    <LayoutGrid className="w-3.5 h-3.5" />
                    <span>Kanban</span>
                  </button>
                  <button
                    onClick={() => setPipelineLayout('table')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      pipelineLayout === 'table'
                        ? 'bg-white text-[#071C21] shadow-xs'
                        : 'text-gray-600 hover:text-black'
                    }`}
                  >
                    <List className="w-3.5 h-3.5" />
                    <span>Tabla</span>
                  </button>
                </div>
              </div>

              {/* Kanban or Table View */}
              {pipelineLayout === 'kanban' && currentTab === 'pipeline' ? (
                <KanbanBoard
                  leads={filteredLeads}
                  onSelectLead={(lead) => setSelectedLead(lead)}
                  onOpenDraftApproval={(lead) => {
                    setModalLead(lead);
                    if (lead.draftType === 'roi') setRoiModalOpen(true);
                    else setOutboundModalOpen(true);
                  }}
                  onMoveLeadStatus={handleMoveLeadStatus}
                />
              ) : (
                <TableView
                  leads={filteredLeads}
                  onSelectLead={(lead) => setSelectedLead(lead)}
                  onOpenDraftApproval={(lead) => {
                    setModalLead(lead);
                    if (lead.draftType === 'roi') setRoiModalOpen(true);
                    else setOutboundModalOpen(true);
                  }}
                  onMoveLeadStatus={handleMoveLeadStatus}
                />
              )}
            </div>
          )}

          {/* VIEW: Posventa y Retención (RF-04) */}
          {currentTab === 'posventa' && (
            <PosventaView
              consumables={consumables}
              maintenance={maintenance}
              training={training}
              onApproveReminder={handleApproveReminder}
            />
          )}

          {/* VIEW: Repositorio DIGEMID */}
          {currentTab === 'documentos' && (
            <div className="bg-white rounded-2xl p-6 border border-[#E5E7EB] shadow-xs space-y-4">
              <div className="border-b border-gray-100 pb-3">
                <h3 className="font-serif font-bold text-lg text-[#071C21]">
                  Carpeta Técnica Regulatoria DIGEMID
                </h3>
                <p className="text-xs text-gray-500">
                  Documentación oficial para homologación institucional en IPRESS públicas y privadas
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                  <ShieldCheck className="w-6 h-6 text-emerald-600 mb-2" />
                  <h4 className="font-bold text-sm text-gray-800">Registro Sanitario Clase IIb</h4>
                  <p className="text-xs text-gray-500 mt-1">Código DM-2024-O3-CLASE-IIB-7891 con fotómetro digital calibrado.</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                  <ShieldCheck className="w-6 h-6 text-teal-600 mb-2" />
                  <h4 className="font-bold text-sm text-gray-800">Certificación BPM Droguería</h4>
                  <p className="text-xs text-gray-500 mt-1">Buenas Prácticas de Manufactura y Almacenamiento certificadas.</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                  <ShieldCheck className="w-6 h-6 text-sky-600 mb-2" />
                  <h4 className="font-bold text-sm text-gray-800">Protocolo ISCO3 / Madrid</h4>
                  <p className="text-xs text-gray-500 mt-1">Guías clínicas universales y tabla de concentraciones 5-60 &micro;g/mL.</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Slid-in Lead Detail Drawer */}
      <LeadDetailDrawer
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
        onOpenRoiModal={(lead) => {
          setModalLead(lead);
          setRoiModalOpen(true);
        }}
        onOpenDossierModal={(lead) => {
          setModalLead(lead);
          setDossierModalOpen(true);
        }}
        onOpenOutboundModal={(lead) => {
          setModalLead(lead);
          setOutboundModalOpen(true);
        }}
      />

      {/* Human-in-the-Loop RF-05 Modals */}
      <RoiApprovalModal
        lead={modalLead}
        isOpen={roiModalOpen}
        onClose={() => setRoiModalOpen(false)}
        onApprove={handleApproveRoi}
      />

      <DossierModal
        lead={modalLead}
        isOpen={dossierModalOpen}
        onClose={() => setDossierModalOpen(false)}
        onAttach={handleAttachDossier}
      />

      <OutboundDraftModal
        lead={modalLead}
        isOpen={outboundModalOpen}
        onClose={() => setOutboundModalOpen(false)}
        onApprove={handleApproveOutbound}
      />

      {/* OzonePedia Wiki Preview & Live Telemetry Simulator */}
      <OzonePediaModal
        isOpen={ozonePediaOpen}
        onClose={() => setOzonePediaOpen(false)}
        onTriggerTelemetry={handleTriggerTelemetry}
      />
    </div>
  );
}
