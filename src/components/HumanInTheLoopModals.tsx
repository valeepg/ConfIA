'use client';

import React, { useState } from 'react';
import { Lead, ConsumableItem } from '@/types';
import { 
  X, 
  Check, 
  ShieldCheck, 
  FileSpreadsheet, 
  Send, 
  FileText, 
  Sparkles, 
  AlertTriangle,
  ArrowRight,
  Download,
  Building,
  CheckCircle2
} from 'lucide-react';

interface RoiModalProps {
  lead: Lead | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (leadId: string) => void;
}

export const RoiApprovalModal: React.FC<RoiModalProps> = ({
  lead,
  isOpen,
  onClose,
  onApprove,
}) => {
  const [approved, setApproved] = useState(false);

  if (!isOpen || !lead) return null;

  const proposal = lead.roiProposal || {
    equipmentModel: 'Generador O3 Médico Sistémico OzoLife Digital Clase IIb',
    monthlyLeaseCost: 0,
    minimumKitsPerMonth: 25,
    costPerSession: 35,
    patientPriceAvg: 180,
    projectedSessionsMonth: 40,
    estimatedNetMonthly: 5800,
  };

  const handle1ClickApprove = () => {
    setApproved(true);
    setTimeout(() => {
      onApprove(lead.id);
      setApproved(false);
      onClose();
    }, 900);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full border border-gray-200 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="bg-[#071C21] p-6 text-white flex items-start justify-between border-b border-[#0E2E33]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider bg-[#059669] text-white px-2 py-0.5 rounded-full">
                Human-in-the-Loop RF-05
              </span>
              <span className="text-xs text-teal-300 font-mono">Modelo OaaS (OpEx)</span>
            </div>
            <h2 className="font-serif font-bold text-xl text-[#FAF9F5]">
              Propuesta Económica &amp; ROI Clínico
            </h2>
            <p className="text-xs text-gray-300 mt-0.5">
              Generada por Copiloto IA para: <strong className="text-white">{lead.name}</strong> ({lead.district})
            </p>
          </div>

          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {/* Clinical equipment & terms */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1">
                Tecnología Biomédica
              </span>
              <p className="font-bold text-sm text-[#071C21]">
                {proposal.equipmentModel}
              </p>
              <div className="mt-2 flex items-center gap-1.5 text-xs text-[#059669] font-medium">
                <ShieldCheck className="w-4 h-4" />
                <span>Registro Sanitario DIGEMID Clase IIb</span>
              </div>
            </div>

            <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-200">
              <span className="text-xs font-semibold text-emerald-800 uppercase tracking-wider block mb-1">
                Modalidad OaaS (Comodato)
              </span>
              <p className="font-bold text-sm text-emerald-950">
                Inversión Inicial CapEx: S/ 0.00
              </p>
              <p className="text-xs text-emerald-700 mt-1">
                Condicionado a consumo mínimo de <strong>{proposal.minimumKitsPerMonth} kits AHTm/mes</strong>.
              </p>
            </div>
          </div>

          {/* ROI Matrix */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
              Proyección de Rentabilidad para la IPRESS
            </h3>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-gray-50 p-3.5 rounded-xl border border-gray-200 text-center">
                <span className="text-[11px] text-gray-500 font-medium">Costo Insumo / Sesión</span>
                <p className="font-mono text-lg font-bold text-gray-800 mt-1">S/ {proposal.costPerSession}</p>
                <span className="text-[10px] text-gray-400">Kit estéril + línea</span>
              </div>

              <div className="bg-gray-50 p-3.5 rounded-xl border border-gray-200 text-center">
                <span className="text-[11px] text-gray-500 font-medium">Tarifa Promedio Paciente</span>
                <p className="font-mono text-lg font-bold text-teal-700 mt-1">S/ {proposal.patientPriceAvg}</p>
                <span className="text-[10px] text-gray-400">Arancel privado Lima</span>
              </div>

              <div className="bg-teal-50 p-3.5 rounded-xl border border-teal-200 text-center">
                <span className="text-[11px] text-teal-800 font-semibold">Margen Neto Estimado</span>
                <p className="font-mono text-xl font-bold text-[#0D9488] mt-1">S/ {proposal.estimatedNetMonthly}</p>
                <span className="text-[10px] text-teal-600 font-medium">/ mes (40 sesiones)</span>
              </div>
            </div>
          </div>

          {/* AI Guardrail notice */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 text-xs text-amber-800">
            <Sparkles className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <strong>Guardarraíl de Integridad:</strong> Las tarifas e insumos están calculados con base en las listas de precios vigentes. El texto regulatorio cita la Declaración de Madrid (ISCO3) y normativas DIGEMID Clase IIb.
            </div>
          </div>
        </div>

        {/* Footer with 1-click Approval button */}
        <div className="bg-gray-50 p-5 border-t border-gray-200 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-200"
          >
            Cancelar
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={handle1ClickApprove}
              disabled={approved}
              className={`px-5 py-2.5 rounded-xl text-sm font-semibold text-white shadow-md flex items-center gap-2 transition-all ${
                approved
                  ? 'bg-emerald-600 scale-95'
                  : 'bg-[#059669] hover:bg-[#047857] hover:shadow-lg'
              }`}
            >
              {approved ? (
                <>
                  <CheckCircle2 className="w-4 h-4 animate-spin" />
                  <span>¡Propuesta Aprobada y Registrada!</span>
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  <span>Aprobar y Enviar Propuesta (1 Clic)</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

interface DossierModalProps {
  lead: Lead | null;
  isOpen: boolean;
  onClose: () => void;
  onAttach: (leadId: string) => void;
}

export const DossierModal: React.FC<DossierModalProps> = ({
  lead,
  isOpen,
  onClose,
  onAttach,
}) => {
  if (!isOpen || !lead) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full border border-gray-200 shadow-2xl overflow-hidden animate-in fade-in duration-200">
        <div className="bg-[#071C21] p-6 text-white flex items-start justify-between border-b border-[#0E2E33]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider bg-teal-600 text-white px-2 py-0.5 rounded-full">
                Carpeta Regulatoria
              </span>
              <span className="text-xs text-teal-300">Normativa DIGEMID &middot; MINSA</span>
            </div>
            <h2 className="font-serif font-bold text-xl text-[#FAF9F5]">
              Dossier Técnico DIGEMID
            </h2>
            <p className="text-xs text-gray-300 mt-0.5">
              Destinatario: Dirección Técnica de {lead.name}
            </p>
          </div>

          <button onClick={onClose} className="text-gray-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
          <div className="space-y-3">
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-800">1. Registro Sanitario de Dispositivo Médico</p>
                <p className="text-[11px] text-gray-500 font-mono">Código: DM-2024-O3-CLASE-IIB-7891 (Vigente)</p>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded">Homologado</span>
            </div>

            <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-800">2. Certificado de Calibración de Fotómetro</p>
                <p className="text-[11px] text-gray-500">Laboratorio ISO/IEC 17025 &middot; ISCO3</p>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded">Válido 12m</span>
            </div>

            <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-800">3. Certificación BPM de Droguería Distribuidora</p>
                <p className="text-[11px] text-gray-500">Buenas Prácticas de Manufactura y Almacenamiento</p>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded">Certificado</span>
            </div>

            <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-800">4. Formato de Consentimiento Informado Paciente</p>
                <p className="text-[11px] text-gray-500">Alineado a Ley N° 29459 y Declaración de Madrid</p>
              </div>
              <span className="text-xs font-bold text-sky-700 bg-sky-50 px-2 py-1 rounded">Plantilla PDF</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 p-4 border-t border-gray-200 flex items-center justify-between">
          <button onClick={onClose} className="px-4 py-2 text-xs font-semibold text-gray-600 hover:text-gray-900">
            Cerrar
          </button>
          <button
            onClick={() => {
              onAttach(lead.id);
              onClose();
            }}
            className="px-5 py-2.5 bg-[#0D9488] hover:bg-[#0F766E] text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-xs"
          >
            <Check className="w-4 h-4" />
            <span>Aprobar y Adjuntar Expediente DIGEMID</span>
          </button>
        </div>
      </div>
    </div>
  );
};

interface OutboundDraftModalProps {
  lead: Lead | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (leadId: string) => void;
}

export const OutboundDraftModal: React.FC<OutboundDraftModalProps> = ({
  lead,
  isOpen,
  onClose,
  onApprove,
}) => {
  if (!isOpen || !lead) return null;

  const draft = lead.outboundDraft || {
    recipientName: lead.directorMedico,
    recipientRole: 'Director Médico',
    subject: `Incorporación de Ozonoterapia Sistémica en ${lead.name} sin inversión de capital`,
    body: `Estimado(a) ${lead.directorMedico},\n\nHemos identificado la especialidad de ${lead.name} en ${lead.specialty}. Ponemos a su consideración nuestro modelo de comodato OaaS con equipos certificados por DIGEMID (Clase IIb) y capacitaciones certificadas con base en la Declaración de Madrid de ISCO3.\n\nQuedamos a su disposición para compartir el dossier regulatorio.`,
    suggestedChannel: 'Email',
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full border border-gray-200 shadow-2xl overflow-hidden animate-in fade-in duration-200">
        <div className="bg-[#071C21] p-6 text-white flex items-start justify-between border-b border-[#0E2E33]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider bg-[#F59E0B] text-black px-2 py-0.5 rounded-full">
                Copiloto Outbound
              </span>
              <span className="text-xs text-teal-300">Canal: {draft.suggestedChannel}</span>
            </div>
            <h2 className="font-serif font-bold text-xl text-[#FAF9F5]">
              Borrador de Contacto Personalizado
            </h2>
          </div>

          <button onClick={onClose} className="text-gray-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-500 w-20">Destinatario:</span>
              <span className="font-bold text-gray-800">{draft.recipientName} ({draft.recipientRole})</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-500 w-20">Asunto:</span>
              <span className="font-bold text-gray-900 bg-gray-100 px-2 py-1 rounded w-full">{draft.subject}</span>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
            <p className="text-xs text-gray-700 whitespace-pre-line leading-relaxed font-sans">
              {draft.body}
            </p>
          </div>
        </div>

        <div className="bg-gray-50 p-4 border-t border-gray-200 flex items-center justify-between">
          <button onClick={onClose} className="px-4 py-2 text-xs font-semibold text-gray-600 hover:text-gray-900">
            Descartar
          </button>
          <button
            onClick={() => {
              onApprove(lead.id);
              onClose();
            }}
            className="px-5 py-2.5 bg-[#059669] hover:bg-[#047857] text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-xs"
          >
            <Send className="w-4 h-4" />
            <span>Aprobar y Enviar (1 Clic)</span>
          </button>
        </div>
      </div>
    </div>
  );
};
