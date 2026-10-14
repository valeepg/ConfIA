'use client';

import React, { useState } from 'react';
import { 
  X, 
  Search, 
  BookOpen, 
  ShieldCheck, 
  Sparkles, 
  Check, 
  ExternalLink,
  ChevronRight,
  FileText,
  AlertCircle
} from 'lucide-react';

interface OzonePediaModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTriggerTelemetry: (clinicName: string) => void;
}

export const OzonePediaModal: React.FC<OzonePediaModalProps> = ({
  isOpen,
  onClose,
  onTriggerTelemetry,
}) => {
  const [activeSpecialty, setActiveSpecialty] = useState('Hernia discal lumbar');
  const [telemetryFired, setTelemetryFired] = useState(false);

  if (!isOpen) return null;

  const specialties = [
    { category: 'Traumatología', items: ['Hernia discal lumbar', 'Artrosis de rodilla', 'Tendinopatías'] },
    { category: 'Otras Áreas', items: ['Medicina del dolor', 'Dermatología', 'Odontología', 'Pie diabético', 'Autohemoterapia mayor'] },
  ];

  const handleSimulateRead = () => {
    onTriggerTelemetry('Clínica Santa Rosa Sur');
    setTelemetryFired(true);
    setTimeout(() => setTelemetryFired(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4">
      <div className="bg-[#FAF9F5] rounded-2xl max-w-5xl w-full h-[90vh] border border-[#E2DDD3] shadow-2xl flex flex-col overflow-hidden animate-in fade-in duration-200">
        {/* Top Hub Nav */}
        <div className="bg-[#071C21] text-white px-6 py-3.5 flex items-center justify-between border-b border-[#0E2E33]">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-[#059669] flex items-center justify-center text-white font-bold text-xs">
                O₃
              </div>
              <span className="font-serif font-bold text-lg text-white">OzonePedia</span>
            </div>
            <div className="hidden md:flex items-center gap-4 text-xs text-gray-300">
              <span className="hover:text-white cursor-pointer">Especialidades</span>
              <span className="hover:text-white cursor-pointer">Protocolos</span>
              <span className="hover:text-white cursor-pointer">Evidencia (ISCO3)</span>
              <span className="hover:text-white cursor-pointer">Comité Científico</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[11px] text-gray-400 hidden sm:inline italic">
              Patrocinado por [Empresa Médica]
            </span>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white p-1 rounded-md"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Hero Banner */}
        <div className="bg-[#0B282F] text-white p-6 border-b border-[#0F363F]">
          <div className="max-w-3xl">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#34D399] bg-[#0E3B43] px-2 py-0.5 rounded-full inline-block mb-2">
              Hub Abierto de Evidencia Clínica
            </span>
            <h1 className="font-serif font-bold text-2xl text-[#FAF9F5]">
              Evidencia y protocolos de ozonoterapia médica
            </h1>
            <p className="text-xs text-gray-300 mt-1 leading-relaxed">
              Información abierta, revisada por un comité médico y basada en la Declaración de Madrid (ISCO3), organizada por especialidad clínica.
            </p>

            {/* Search Bar */}
            <div className="mt-4 flex gap-2 max-w-xl">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar protocolo, patología o estudio..."
                  defaultValue="Hernia discal lumbar"
                  className="w-full pl-9 pr-3 py-2 bg-white/10 text-white placeholder-gray-400 text-xs rounded-xl border border-white/20 focus:outline-hidden focus:border-[#34D399]"
                />
              </div>
              <button className="px-4 py-2 bg-[#059669] hover:bg-[#047857] text-white text-xs font-semibold rounded-xl transition-all">
                Buscar
              </button>
            </div>
          </div>
        </div>

        {/* Main Content Split */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Categories Sidebar */}
          <div className="w-56 bg-[#F3EFE6] border-r border-[#E2DDD3] p-4 overflow-y-auto hidden sm:block">
            <div className="space-y-4">
              {specialties.map((group, idx) => (
                <div key={idx}>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1.5 px-2">
                    {group.category}
                  </p>
                  <div className="space-y-0.5">
                    {group.items.map((item) => (
                      <button
                        key={item}
                        onClick={() => setActiveSpecialty(item)}
                        className={`w-full text-left text-xs px-2.5 py-1.5 rounded-lg font-medium transition-colors ${
                          activeSpecialty === item
                            ? 'bg-[#0E2E33] text-white font-semibold'
                            : 'text-gray-700 hover:bg-[#EAE5DA]'
                        }`}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Center Article */}
          <div className="flex-1 p-6 overflow-y-auto bg-white space-y-6">
            <div className="border-b border-gray-100 pb-4">
              <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-1">
                <span>Especialidades</span>
                <span>/</span>
                <span>Traumatología</span>
                <span>/</span>
                <span className="text-gray-700 font-medium">Hernia discal lumbar</span>
              </div>
              <h2 className="font-serif font-bold text-2xl text-[#071C21]">
                Hernia discal lumbar: protocolo de ozonoterapia
              </h2>

              <div className="flex flex-wrap items-center gap-2 mt-2">
                <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  Revisado por comité médico
                </span>
                <span className="text-[11px] text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                  Actualizado: Dic 2025
                </span>
                <span className="text-[11px] text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                  Nivel de evidencia: Grado A / IB
                </span>
              </div>
            </div>

            {/* Resumen clínico */}
            <div className="bg-[#FAF9F5] p-4 rounded-xl border border-[#EAE6DF] space-y-2">
              <h3 className="font-serif font-bold text-sm text-[#071C21]">
                Resumen clínico
              </h3>
              <p className="text-xs text-gray-700 leading-relaxed">
                La aplicación de ozono médico para conflicto disco-radicular lumbar actúa reduciendo el volumen de la hernia mediante degradación de proteoglicanos y disminuyendo mediadores inflamatorios (PGE2, TNF-alfa). Protocolo homologado según la Declaración de Madrid (ISCO3, 4.ª edición).
              </p>
            </div>

            {/* Tabla de protocolo de aplicación */}
            <div className="space-y-2">
              <h3 className="font-serif font-bold text-sm text-[#071C21]">
                Protocolo de aplicación recomendado
              </h3>
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#FAF9F5] text-gray-600 font-semibold uppercase text-[10px] border-b border-gray-200">
                    <tr>
                      <th className="py-2.5 px-3">Vía de administración</th>
                      <th className="py-2.5 px-3">Concentración</th>
                      <th className="py-2.5 px-3">Frecuencia</th>
                      <th className="py-2.5 px-3">Fuente</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    <tr>
                      <td className="py-2.5 px-3 font-semibold text-gray-800">Paravertebral profunda</td>
                      <td className="py-2.5 px-3 font-mono text-[#0D9488]">15 - 20 &micro;g/mL</td>
                      <td className="py-2.5 px-3 text-gray-600">2 veces por semana (8 a 10 sesiones)</td>
                      <td className="py-2.5 px-3 text-gray-500">ISCO3 / Madrid</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-3 font-semibold text-gray-800">Intradiscal guiada (Fluroscopía)</td>
                      <td className="py-2.5 px-3 font-mono text-[#0D9488]">25 - 35 &micro;g/mL</td>
                      <td className="py-2.5 px-3 text-gray-600">Sesión única ambulatoria</td>
                      <td className="py-2.5 px-3 text-gray-500">Consenso Europeo</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-3 font-semibold text-gray-800">Autohemoterapia Mayor (AHTm) coadyuvante</td>
                      <td className="py-2.5 px-3 font-mono text-[#0D9488]">30 - 40 &micro;g/mL</td>
                      <td className="py-2.5 px-3 text-gray-600">Semanal (10 sesiones)</td>
                      <td className="py-2.5 px-3 text-gray-500">Declaración de Madrid</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Interactive Telemetry Trigger Banner */}
            <div className="p-4 bg-gradient-to-r from-[#FEF3C7] to-[#FFFBEB] border border-[#FDE68A] rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="text-xs text-amber-900">
                <span className="font-bold flex items-center gap-1.5 text-amber-800">
                  <Sparkles className="w-4 h-4 text-amber-600" />
                  Prueba de Radar de Intención (Telemetría de Lectura)
                </span>
                <p className="text-[11px] text-amber-700 mt-0.5">
                  Simula la visita de un director médico a este protocolo para enviar telemetría en tiempo real al CRM de ConfIA.
                </p>
              </div>

              <button
                onClick={handleSimulateRead}
                disabled={telemetryFired}
                className={`px-4 py-2 rounded-xl text-xs font-semibold text-white shadow-xs transition-all shrink-0 ${
                  telemetryFired
                    ? 'bg-emerald-600'
                    : 'bg-[#B45309] hover:bg-[#92400E]'
                }`}
              >
                {telemetryFired ? (
                  <span className="flex items-center gap-1">
                    <Check className="w-3.5 h-3.5" />
                    ¡Telemetría enviada al CRM!
                  </span>
                ) : (
                  <span>Simular lectura médica</span>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
