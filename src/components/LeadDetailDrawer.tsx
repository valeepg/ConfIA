'use client';

import React from 'react';
import { Lead } from '@/types';
import { 
  X, 
  MapPin, 
  User, 
  Stethoscope, 
  BookOpen, 
  Clock, 
  Search, 
  Sparkles, 
  ShieldCheck, 
  FileSpreadsheet, 
  Send
} from 'lucide-react';

interface LeadDetailDrawerProps {
  lead: Lead | null;
  onClose: () => void;
  onOpenRoiModal: (lead: Lead) => void;
  onOpenDossierModal: (lead: Lead) => void;
  onOpenOutboundModal: (lead: Lead) => void;
}

export const LeadDetailDrawer: React.FC<LeadDetailDrawerProps> = ({
  lead,
  onClose,
  onOpenRoiModal,
  onOpenDossierModal,
  onOpenOutboundModal,
}) => {
  if (!lead) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-md bg-white shadow-2xl border-l border-gray-200 flex flex-col transition-all duration-300">
      {/* Drawer Header */}
      <div className="p-6 border-b border-gray-100 bg-[#FAF9F5] flex items-start justify-between">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider bg-[#0E2E33] text-[#34D399] px-2.5 py-0.5 rounded-full inline-block mb-2">
            Ficha de la Clínica
          </span>
          <h2 className="font-serif font-bold text-xl text-[#071C21] leading-tight">
            {lead.name}
          </h2>
          <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
            <MapPin className="w-3.5 h-3.5 text-gray-400" />
            <span>{lead.district}</span>
            <span>&middot;</span>
            <span className="font-semibold text-gray-700">{lead.specialty}</span>
          </div>
        </div>

        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-200/60 transition-colors"
          title="Cerrar panel"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Drawer Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Contact Info */}
        <div className="bg-gray-50 p-3.5 rounded-xl border border-gray-200/70 space-y-2">
          <div className="flex items-center gap-2 text-xs text-gray-700">
            <User className="w-4 h-4 text-[#0D9488]" />
            <span className="font-medium text-gray-500">Contacto principal:</span>
            <span className="font-semibold text-gray-900">{lead.directorMedico}</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-700">
            <Stethoscope className="w-4 h-4 text-[#0D9488]" />
            <span className="font-medium text-gray-500">Especialidad:</span>
            <span className="font-semibold text-gray-900">{lead.doctorSpecialty}</span>
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-gray-200 text-xs">
            <span className="text-gray-500 font-medium">Nivel de interés:</span>
            <span className="font-mono font-bold text-[#0D9488] bg-teal-50 px-2 py-0.5 rounded">
              {lead.score}%
            </span>
          </div>
        </div>

        {/* Section: What they've been reading */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-[#D97706]" />
              Interés y Consultas Clínicas
            </h3>
            {lead.telemetryActivity.lastVisited && (
              <span className="text-[11px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full font-medium">
                {lead.telemetryActivity.lastVisited}
              </span>
            )}
          </div>

          <div className="space-y-2">
            <div className="p-3 bg-[#FAF9F5] border border-[#EAE6DF] rounded-xl flex items-start gap-3">
              <div className="w-7 h-7 rounded-lg bg-teal-100 text-[#0D9488] flex items-center justify-center shrink-0 mt-0.5">
                <BookOpen className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <p className="font-semibold text-[#071C21]">
                  Autohemoterapia mayor (AHTm): cómo funciona
                </p>
                <p className="text-gray-500 mt-0.5 font-medium">
                  {lead.telemetryActivity.ahtmReads} consulta{lead.telemetryActivity.ahtmReads !== 1 ? 's' : ''} sobre protocolo
                </p>
              </div>
            </div>

            <div className="p-3 bg-[#FAF9F5] border border-[#EAE6DF] rounded-xl flex items-start gap-3">
              <div className="w-7 h-7 rounded-lg bg-amber-100 text-[#D97706] flex items-center justify-center shrink-0 mt-0.5">
                <Clock className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <p className="font-semibold text-[#071C21]">
                  Hernia discal lumbar: tratamiento con ozono
                </p>
                <p className="text-gray-500 mt-0.5 font-medium">
                  {lead.telemetryActivity.lumbarMinutes} minutos de revisión técnica
                </p>
              </div>
            </div>

            {lead.telemetryActivity.searchQuery && (
              <div className="p-3 bg-[#FAF9F5] border border-[#EAE6DF] rounded-xl flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-sky-100 text-[#0284C7] flex items-center justify-center shrink-0 mt-0.5">
                  <Search className="w-4 h-4" />
                </div>
                <div className="text-xs">
                  <p className="font-medium text-gray-500">Término consultado:</p>
                  <p className="font-semibold text-[#071C21] italic mt-0.5">
                    &ldquo;{lead.telemetryActivity.searchQuery}&rdquo;
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section: AI Suggestion */}
        <div className="bg-[#071C21] rounded-2xl p-5 text-white border border-[#0E2E33] shadow-md space-y-3.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#A7F3D0]">
              <Sparkles className="w-4 h-4 text-[#F59E0B]" />
              La IA sugiere
            </div>
            <span className="text-[10px] font-semibold bg-[#D97706] text-white px-2 py-0.5 rounded-full">
              Necesita tu aprobación
            </span>
          </div>

          <p className="text-sm font-sans text-gray-200 leading-relaxed">
            {lead.aiSuggestion}
          </p>

          <div className="pt-2 border-t border-[#0F2F38] space-y-2">
            <button
              onClick={() => onOpenRoiModal(lead)}
              className="w-full py-2.5 px-4 bg-[#059669] hover:bg-[#047857] text-white rounded-xl text-sm font-semibold transition-all flex items-center justify-center gap-2 shadow-sm"
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Ver cotización y ganancias</span>
            </button>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => onOpenDossierModal(lead)}
                className="py-2 px-3 bg-[#0E2E33] hover:bg-[#143B42] text-gray-200 border border-[#10B981]/30 rounded-xl text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-[#34D399]" />
                <span>Carpeta DIGEMID</span>
              </button>

              <button
                onClick={() => onOpenOutboundModal(lead)}
                className="py-2 px-3 bg-[#0E2E33] hover:bg-[#143B42] text-gray-200 border border-[#38BDF8]/30 rounded-xl text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5 text-[#38BDF8]" />
                <span>Mensaje sugerido</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Drawer Footer */}
      <div className="p-4 border-t border-gray-100 bg-gray-50 flex items-center justify-between text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          Tú apruebas todo antes de que se envíe
        </span>
        <button
          onClick={onClose}
          className="text-gray-600 hover:text-gray-900 font-semibold"
        >
          Cerrar
        </button>
      </div>
    </div>
  );
};
