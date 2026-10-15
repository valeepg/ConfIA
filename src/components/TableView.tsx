'use client';

import React from 'react';
import { Lead, PipelineStatus } from '@/types';
import { MapPin, Sparkles, ChevronRight } from 'lucide-react';

interface TableViewProps {
  leads: Lead[];
  onSelectLead: (lead: Lead) => void;
  onOpenDraftApproval: (lead: Lead) => void;
  onMoveLeadStatus: (leadId: string, newStatus: PipelineStatus) => void;
}

const STATUS_LABELS: Record<PipelineStatus, { label: string; badgeClass: string }> = {
  descubierto: { label: 'Identificada', badgeClass: 'bg-slate-100 text-slate-700 border-slate-300' },
  contactado: { label: 'En conversación', badgeClass: 'bg-amber-50 text-amber-800 border-amber-300' },
  propuesta_enviada: { label: 'Cotización enviada', badgeClass: 'bg-sky-50 text-sky-800 border-sky-300' },
  cierre: { label: 'Cliente activo', badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-300' },
};

export const TableView: React.FC<TableViewProps> = ({
  leads,
  onSelectLead,
  onOpenDraftApproval,
  onMoveLeadStatus,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-xs overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-[#0F2F38]">
          <thead className="bg-[#FAF9F5] text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">
            <tr>
              <th className="py-3.5 px-4">Clínica</th>
              <th className="py-3.5 px-4">Ubicación</th>
              <th className="py-3.5 px-4">Especialidad</th>
              <th className="py-3.5 px-4">Interés</th>
              <th className="py-3.5 px-4">Etapa</th>
              <th className="py-3.5 px-4">Interés Detectado</th>
              <th className="py-3.5 px-4">Asistente IA</th>
              <th className="py-3.5 px-4 text-right">Ver</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {leads.map((lead) => {
              const statusInfo = STATUS_LABELS[lead.status];
              const hasPendingAi = lead.hasAiDraft && !lead.draftApproved;

              return (
                <tr
                  key={lead.id}
                  onClick={() => onSelectLead(lead)}
                  className="hover:bg-[#FAF9F5]/70 transition-colors cursor-pointer group"
                >
                  <td className="py-3.5 px-4">
                    <div className="font-serif font-bold text-sm text-[#071C21] group-hover:text-[#059669]">
                      {lead.name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {lead.directorMedico}
                    </div>
                  </td>

                  <td className="py-3.5 px-4 text-gray-600">
                    <div className="flex items-center gap-1 text-xs">
                      <MapPin className="w-3 h-3 text-gray-400" />
                      <span>{lead.district}</span>
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <span className="text-xs font-medium text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
                      {lead.specialty}
                    </span>
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-gray-100 h-2 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#0D9488]"
                          style={{ width: `${lead.score}%` }}
                        />
                      </div>
                      <span className="font-mono text-xs font-bold text-[#0D9488]">
                        {lead.score}%
                      </span>
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium border ${statusInfo.badgeClass}`}>
                      {statusInfo.label}
                    </span>
                  </td>

                  <td className="py-3.5 px-4">
                    {lead.telemetryAlert ? (
                      <span className="text-[11px] font-bold text-[#B45309] bg-[#FEF3C7] px-2 py-0.5 rounded-full border border-[#FDE68A] flex items-center gap-1 w-max">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#D97706] animate-pulse"></span>
                        Leyendo ahora ({lead.telemetryActivity?.lumbarMinutes ?? 0} min)
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">
                        {lead.telemetryActivity?.ahtmReads > 0 ? `${lead.telemetryActivity?.ahtmReads} artículos` : 'Sin actividad'}
                      </span>
                    )}
                  </td>

                  <td className="py-3.5 px-4">
                    {hasPendingAi ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenDraftApproval(lead);
                        }}
                        className="text-xs bg-[#FEF3C7] hover:bg-[#FDE68A] text-[#92400E] border border-[#F59E0B] px-2.5 py-1 rounded-lg font-semibold flex items-center gap-1"
                      >
                        <Sparkles className="w-3 h-3 text-[#D97706]" />
                        Revisar
                      </button>
                    ) : (
                      <span className="text-xs text-gray-400">Al día</span>
                    )}
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectLead(lead);
                      }}
                      className="text-xs font-semibold text-[#059669] hover:text-[#047857] flex items-center gap-1 ml-auto"
                    >
                      <span>Ver ficha</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
