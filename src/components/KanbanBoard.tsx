'use client';

import React from 'react';
import { Lead, PipelineStatus } from '@/types';
import { 
  MapPin, 
  Sparkles, 
  CheckCircle, 
  ChevronRight, 
  ChevronLeft
} from 'lucide-react';

interface KanbanBoardProps {
  leads: Lead[];
  onSelectLead: (lead: Lead) => void;
  onOpenDraftApproval: (lead: Lead) => void;
  onMoveLeadStatus: (leadId: string, newStatus: PipelineStatus) => void;
}

const COLUMNS: { id: PipelineStatus; label: string; description: string }[] = [
  { id: 'descubierto', label: 'Identificada', description: 'Clínica detectada, sin contacto previo' },
  { id: 'contactado', label: 'En conversación', description: 'Ya se hizo el primer contacto' },
  { id: 'propuesta_enviada', label: 'Cotización enviada', description: 'Se envió la cotización o la carpeta DIGEMID' },
  { id: 'cierre', label: 'Cliente activo', description: 'Equipo instalado y operando' },
];

export const KanbanBoard: React.FC<KanbanBoardProps> = ({
  leads,
  onSelectLead,
  onOpenDraftApproval,
  onMoveLeadStatus,
}) => {
  const getNextStatus = (current: PipelineStatus): PipelineStatus | null => {
    if (current === 'descubierto') return 'contactado';
    if (current === 'contactado') return 'propuesta_enviada';
    if (current === 'propuesta_enviada') return 'cierre';
    return null;
  };

  const getPrevStatus = (current: PipelineStatus): PipelineStatus | null => {
    if (current === 'cierre') return 'propuesta_enviada';
    if (current === 'propuesta_enviada') return 'contactado';
    if (current === 'contactado') return 'descubierto';
    return null;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 items-start">
      {COLUMNS.map((col) => {
        const columnLeads = leads.filter((l) => l.status === col.id);

        return (
          <div
            key={col.id}
            className="bg-[#EFECE6]/80 rounded-2xl p-3 border border-[#E2DDD3] flex flex-col min-h-[500px]"
          >
            {/* Column Header */}
            <div className="flex items-center justify-between pb-3 px-1 border-b border-[#E2DDD3] mb-3">
              <div className="flex items-center gap-2">
                <h3 className="font-serif font-bold text-base text-[#071C21]">
                  {col.label}
                </h3>
                <span className="w-5 h-5 rounded-full bg-white border border-[#D5CEBF] text-xs font-semibold text-[#071C21] flex items-center justify-center shadow-xs">
                  {columnLeads.length}
                </span>
              </div>
            </div>

            {/* Column Cards */}
            <div className="space-y-3 flex-1">
              {columnLeads.length === 0 ? (
                <div className="h-32 border-2 border-dashed border-[#D5CEBF] rounded-xl flex items-center justify-center text-xs text-gray-400">
                  Sin clínicas en esta etapa
                </div>
              ) : (
                columnLeads.map((lead) => {
                  const hasPendingAi = lead.hasAiDraft && !lead.draftApproved;
                  const nextStatus = getNextStatus(lead.status);
                  const prevStatus = getPrevStatus(lead.status);

                  return (
                    <div
                      key={lead.id}
                      className={`bg-white rounded-xl p-4 border transition-all duration-200 cursor-pointer shadow-xs hover:shadow-md ${
                        lead.telemetryAlert
                          ? 'border-[#F59E0B] ring-2 ring-[#FDE68A]/60'
                          : 'border-[#E5E7EB] hover:border-[#0D9488]/40'
                      }`}
                      onClick={() => onSelectLead(lead)}
                    >
                      {/* Clinic Info */}
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <h4 className="font-serif font-bold text-sm text-[#071C21] hover:text-[#059669] transition-colors leading-snug">
                          {lead.name}
                        </h4>
                        {lead.telemetryAlert && (
                          <span className="shrink-0 text-[10px] font-bold uppercase tracking-wider bg-[#FEF3C7] text-[#B45309] px-2 py-0.5 rounded-full border border-[#FDE68A]">
                            Leyendo
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-3">
                        <MapPin className="w-3 h-3 shrink-0 text-gray-400" />
                        <span>{lead.district}</span>
                        <span>&middot;</span>
                        <span className="font-medium text-gray-700">{lead.specialty}</span>
                      </div>

                      {/* Interest Level Bar */}
                      <div className="mb-3">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-medium text-gray-500">Nivel de interés</span>
                          <span className="font-bold text-[#0D9488] font-mono">{lead.score === null ? '—' : `${lead.score}%`}</span>
                        </div>
                        <div className="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              lead.score !== null && lead.score >= 85
                                ? 'bg-gradient-to-r from-[#0D9488] to-[#10B981]'
                                : lead.score !== null && lead.score >= 70
                                ? 'bg-[#0D9488]'
                                : 'bg-[#F59E0B]'
                            }`}
                            style={{ width: `${lead.score ?? 0}%` }}
                          />
                        </div>
                      </div>

                      {/* Status Note or AI Draft Badge */}
                      <div className="space-y-2">
                        {lead.statusNote && (
                          <p className="text-[11px] text-gray-600 line-clamp-1 italic bg-gray-50 px-2 py-1 rounded">
                            {lead.statusNote}
                          </p>
                        )}

                        {hasPendingAi && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpenDraftApproval(lead);
                            }}
                            className="w-full flex items-center justify-center gap-1.5 py-1.5 px-2 bg-[#FEF3C7] hover:bg-[#FDE68A] text-[#92400E] border border-[#F59E0B] rounded-lg text-xs font-semibold transition-all shadow-xs"
                          >
                            <Sparkles className="w-3.5 h-3.5 text-[#D97706]" />
                            <span>Sugerencia de IA — revisar</span>
                          </button>
                        )}
                      </div>

                      {/* Stage Controls */}
                      <div className="mt-3 pt-2.5 border-t border-gray-100 flex items-center justify-between">
                        <div>
                          {prevStatus ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onMoveLeadStatus(lead.id, prevStatus);
                              }}
                              className="text-gray-400 hover:text-gray-700 p-1 rounded hover:bg-gray-100 text-[11px] flex items-center gap-0.5"
                              title="Mover a la etapa anterior"
                            >
                              <ChevronLeft className="w-3.5 h-3.5" />
                              <span className="hidden sm:inline">Atrás</span>
                            </button>
                          ) : (
                            <span className="text-[10px] text-gray-400">Inicio</span>
                          )}
                        </div>

                        <div className="text-[11px] font-medium text-gray-500 truncate max-w-[100px]">
                          {lead.directorMedico}
                        </div>

                        <div>
                          {nextStatus ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onMoveLeadStatus(lead.id, nextStatus);
                              }}
                              className="text-[#059669] hover:text-[#047857] hover:bg-[#ECFDF5] px-1.5 py-1 rounded text-[11px] font-semibold flex items-center gap-0.5 transition-colors"
                              title="Avanzar a la siguiente etapa"
                            >
                              <span>Avanzar</span>
                              <ChevronRight className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <span className="text-[10px] font-bold text-[#059669] flex items-center gap-0.5">
                              <CheckCircle className="w-3 h-3" />
                              Activo
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
