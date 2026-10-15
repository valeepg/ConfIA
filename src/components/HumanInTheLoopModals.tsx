'use client';

import React, { useState } from 'react';
import { Lead } from '@/types';
import { 
  X, 
  Check, 
  ShieldCheck, 
  Send, 
  Sparkles, 
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
    equipmentModel: 'Ozonette — Generador SEDECAL (Clase IIb, marcado CE)',
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
                Necesita tu aprobación
              </span>
              <span className="text-xs text-teal-300">Alquiler con insumos</span>
            </div>
            <h2 className="font-serif font-bold text-xl text-[#FAF9F5]">
              Cotización y ganancia estimada
            </h2>
            <p className="text-xs text-gray-300 mt-0.5">
              Preparada por la IA para: <strong className="text-white">{lead.name}</strong> ({lead.district})
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
          {/* Equipment & Terms */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1">
                Equipo Médico
              </span>
              <p className="font-bold text-sm text-[#071C21]">
                {proposal.equipmentModel}
              </p>
              <div className="mt-2 flex items-center gap-1.5 text-xs text-[#059669] font-medium">
                <ShieldCheck className="w-4 h-4" />
                <span>Registro DIGEMID DM-14820-E</span>
              </div>
            </div>

            <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-200">
              <span className="text-xs font-semibold text-emerald-800 uppercase tracking-wider block mb-1">
                Modelo de Alquiler
              </span>
              <p className="font-bold text-sm text-emerald-950">
                Sin inversión inicial: S/ 0.00
              </p>
              <p className="text-xs text-emerald-700 mt-1">
                La clínica solo compra un mínimo de <strong>{proposal.minimumKitsPerMonth} kits de insumos al mes</strong>.
              </p>
            </div>
          </div>

          {/* Revenue Projection */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
              ¿Cuánto puede ganar la clínica?
            </h3>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-gray-50 p-3.5 rounded-xl border border-gray-200 text-center">
                <span className="text-[11px] text-gray-500 font-medium">Costo de insumos por sesión</span>
                <p className="font-mono text-lg font-bold text-gray-800 mt-1">S/ {proposal.costPerSession}</p>
                <span className="text-[10px] text-gray-400">Kit + línea estéril</span>
              </div>

              <div className="bg-gray-50 p-3.5 rounded-xl border border-gray-200 text-center">
                <span className="text-[11px] text-gray-500 font-medium">Le cobran al paciente</span>
                <p className="font-mono text-lg font-bold text-teal-700 mt-1">S/ {proposal.patientPriceAvg}</p>
                <span className="text-[10px] text-gray-400">Precio promedio Lima</span>
              </div>

              <div className="bg-teal-50 p-3.5 rounded-xl border border-teal-200 text-center">
                <span className="text-[11px] text-teal-800 font-semibold">Ganancia estimada</span>
                <p className="font-mono text-xl font-bold text-[#0D9488] mt-1">S/ {proposal.estimatedNetMonthly}</p>
                <span className="text-[10px] text-teal-600 font-medium">al mes ({proposal.projectedSessionsMonth} sesiones)</span>
              </div>
            </div>
          </div>

          {/* AI Guardrail notice */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 text-xs text-amber-800">
            <Sparkles className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <strong>Nota:</strong> Los precios e insumos están basados en las listas de precios vigentes de Tecnocare. Los datos regulatorios se toman de la Declaración de Madrid (ISCO3) y de los registros DIGEMID del equipo SEDECAL.
            </div>
          </div>
        </div>

        {/* Footer */}
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
                  <span>¡Cotización aprobada y enviada!</span>
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  <span>Aprobar y enviar cotización</span>
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
              <span className="text-xs text-teal-300">DIGEMID &middot; Droguería Autorizada</span>
            </div>
            <h2 className="font-serif font-bold text-xl text-[#FAF9F5]">
              Documentos del equipo para {lead.name}
            </h2>
          </div>

          <button onClick={onClose} className="text-gray-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
          <p className="text-xs text-gray-600 mb-2">
            Estos documentos se envían a la clínica para que su equipo técnico o de compras pueda verificar que el generador es legal y certificado.
          </p>

          <div className="space-y-3">
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-800">1. Registro Sanitario DIGEMID</p>
                <p className="text-[11px] text-gray-500 font-mono">Código: DM-14820-E — Ozonette (SEDECAL)</p>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded">Vigente</span>
            </div>

            <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-800">2. Certificado de calibración de fábrica</p>
                <p className="text-[11px] text-gray-500">SEDECAL — ISO 13485 / ISO 17025</p>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded">Válido</span>
            </div>

            <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-800">3. Autorización de droguería importadora</p>
                <p className="text-[11px] text-gray-500">Tecnology Care SRL — Droguería Autorizada DIGEMID</p>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded">Certificada</span>
            </div>

            <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-800">4. Formato de consentimiento informado</p>
                <p className="text-[11px] text-gray-500">Para que el paciente firme antes de cada sesión</p>
              </div>
              <span className="text-xs font-bold text-sky-700 bg-sky-50 px-2 py-1 rounded">PDF listo</span>
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
            <span>Aprobar y enviar carpeta</span>
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
    subject: `Equipo de ozono médico SEDECAL para ${lead.name}`,
    body: `Estimado(a) ${lead.directorMedico},\n\nHemos identificado a ${lead.name} como un centro especializado en ${lead.specialty}. Ofrecemos generadores de ozono médico SEDECAL con registro DIGEMID, instalación, capacitación y soporte técnico local.\n\nEl equipo se puede adquirir o alquilar con un consumo mínimo de insumos, sin inversión inicial.\n\nQuedamos a su disposición para compartir la documentación técnica.`,
    suggestedChannel: 'Email',
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full border border-gray-200 shadow-2xl overflow-hidden animate-in fade-in duration-200">
        <div className="bg-[#071C21] p-6 text-white flex items-start justify-between border-b border-[#0E2E33]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider bg-[#F59E0B] text-black px-2 py-0.5 rounded-full">
                Mensaje sugerido por la IA
              </span>
              <span className="text-xs text-teal-300">Por {draft.suggestedChannel}</span>
            </div>
            <h2 className="font-serif font-bold text-xl text-[#FAF9F5]">
              Mensaje para {lead.name}
            </h2>
          </div>

          <button onClick={onClose} className="text-gray-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <p className="text-xs text-gray-500">
            La IA preparó este mensaje. Revísalo y si te parece bien, apruébalo para enviarlo.
          </p>

          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-500 w-20">Para:</span>
              <span className="font-bold text-gray-800">{draft.recipientName} ({draft.recipientRole})</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="font-semibold text-gray-500 w-20 shrink-0">Asunto:</span>
              <span className="font-bold text-gray-900 bg-gray-100 px-2 py-1 rounded">{draft.subject}</span>
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
            <span>Aprobar y enviar</span>
          </button>
        </div>
      </div>
    </div>
  );
};
