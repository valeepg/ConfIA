'use client';

import React, { useState } from 'react';
import { ConsumableItem, MaintenanceItem, TrainingProgress } from '@/types';
import { 
  MetricCards 
} from '@/components/MetricCards';
import { 
  Package, 
  Wrench, 
  GraduationCap, 
  Cpu, 
  AlertTriangle, 
  Sparkles, 
  Send, 
  Check, 
  ShieldCheck,
  FileText,
  X,
  Calendar
} from 'lucide-react';

interface PosventaViewProps {
  consumables: ConsumableItem[];
  maintenance: MaintenanceItem[];
  training: TrainingProgress;
  onApproveReminder: (consumableId: string) => void;
}

export const PosventaView: React.FC<PosventaViewProps> = ({
  consumables,
  maintenance,
  training,
  onApproveReminder,
}) => {
  const [selectedReminder, setSelectedReminder] = useState<ConsumableItem | null>(null);
  const [reminderModalOpen, setReminderModalOpen] = useState(false);
  const [notePrepared, setNotePrepared] = useState(false);

  const metrics = [
    {
      label: 'Equipos Instalados',
      value: 4,
      highlight: 'teal' as const,
      icon: <Cpu className="w-5 h-5" />,
      subtitle: 'SEDECAL activos',
    },
    {
      label: 'Insumos por Reponer',
      value: 2,
      highlight: 'amber' as const,
      icon: <Package className="w-5 h-5 text-amber-500" />,
      subtitle: 'Necesitan pedido',
    },
    {
      label: 'Revisiones Programadas',
      value: 3,
      highlight: 'default' as const,
      icon: <Wrench className="w-5 h-5" />,
      subtitle: 'Próximos meses',
    },
    {
      label: 'Médicos Capacitados',
      value: `${training.certifiedDoctors} de ${training.totalDoctors}`,
      highlight: 'emerald' as const,
      icon: <GraduationCap className="w-5 h-5 text-emerald-600" />,
      subtitle: '75% certificados',
    },
  ];

  const handleOpenReminderModal = (item: ConsumableItem) => {
    setSelectedReminder(item);
    setReminderModalOpen(true);
  };

  const handleSendReminder1Click = () => {
    if (selectedReminder) {
      onApproveReminder(selectedReminder.id);
      setReminderModalOpen(false);
      setSelectedReminder(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-serif font-bold text-2xl text-[#071C21]">
              Clientes y Equipos Instalados
            </h1>
            <span className="text-xs bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] font-medium px-2.5 py-0.5 rounded-full">
              Datos de ejemplo
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Control de insumos, revisiones técnicas de equipos SEDECAL y capacitación de médicos
          </p>
        </div>

        <button
          className="px-4 py-2 bg-[#059669] hover:bg-[#047857] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-xs transition-all w-max"
        >
          <Cpu className="w-4 h-4" />
          <span>+ Registrar equipo nuevo</span>
        </button>
      </div>

      {/* KPI Cards */}
      <MetricCards metrics={metrics} />

      {/* Main Grid: Consumables (Left) + Right Widgets */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Consumables Table & AI Box */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-xs overflow-hidden">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h2 className="font-serif font-bold text-base text-[#071C21]">
                  Insumos Médicos
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Kits de autohemoterapia, líneas de infusión y frascos de vacío
                </p>
              </div>
              <span className="text-[11px] font-semibold text-gray-500 bg-gray-100 px-2.5 py-1 rounded-full">
                4 Equipos Activos
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-[#0F2F38]">
                <thead className="bg-[#FAF9F5] font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-200">
                  <tr>
                    <th className="py-3 px-4">Clínica</th>
                    <th className="py-3 px-4">Insumo</th>
                    <th className="py-3 px-4">Consumo Mensual</th>
                    <th className="py-3 px-4">Último Pedido</th>
                    <th className="py-3 px-4">Estado</th>
                    <th className="py-3 px-4 text-right">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {consumables.map((item) => {
                    let statusBadge = (
                      <span className="px-2 py-0.5 rounded-full font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Al día
                      </span>
                    );

                    if (item.status === 'agotado') {
                      statusBadge = (
                        <span className="px-2 py-0.5 rounded-full font-semibold bg-red-50 text-red-700 border border-red-200 animate-pulse">
                          Se agotó
                        </span>
                      );
                    } else if (item.status === 'reabastecer') {
                      statusBadge = (
                        <span className="px-2 py-0.5 rounded-full font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                          Reponer pronto
                        </span>
                      );
                    }

                    return (
                      <tr key={item.id} className="hover:bg-gray-50/70 transition-colors">
                        <td className="py-3.5 px-4 font-serif font-bold text-[#071C21]">
                          {item.clinicName}
                        </td>
                        <td className="py-3.5 px-4 font-medium text-gray-700">
                          {item.consumableType}
                        </td>
                        <td className="py-3.5 px-4 text-gray-600 font-mono">
                          {item.estimatedMonthly}
                        </td>
                        <td className="py-3.5 px-4 text-gray-500">
                          {item.lastOrderText}
                        </td>
                        <td className="py-3.5 px-4">
                          {statusBadge}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          {item.urgentAiReminder ? (
                            <button
                              onClick={() => handleOpenReminderModal(item)}
                              className="px-2.5 py-1 bg-[#FEF3C7] hover:bg-[#FDE68A] text-[#92400E] border border-[#F59E0B] rounded-lg font-semibold text-[11px] transition-all"
                            >
                              Gestionar
                            </button>
                          ) : (
                            <span className="text-gray-400 text-[11px]">En orden</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* AI Suggestion Box */}
          <div className="bg-[#071C21] rounded-2xl p-5 text-white border border-[#0E2E33] shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#A7F3D0] bg-[#0E2E33] px-2.5 py-0.5 rounded-full border border-[#059669]/30">
                  La IA sugiere
                </span>
                <span className="text-xs bg-[#D97706] text-white px-2 py-0.5 rounded-full font-semibold">
                  Necesita tu aprobación
                </span>
              </div>
              <p className="text-xs text-gray-200 leading-relaxed font-sans">
                <strong>Clínica del Valle</strong> lleva 4 semanas sin pedir kits de autohemoterapia. ¿Quieres enviarles un recordatorio para coordinar la reposición?
              </p>
            </div>

            <button
              onClick={() => {
                const valle = consumables.find((c) => c.clinicName.includes('Valle')) || consumables[0];
                handleOpenReminderModal(valle);
              }}
              className="py-2.5 px-4 bg-[#059669] hover:bg-[#047857] text-white rounded-xl text-xs font-semibold shrink-0 transition-all shadow-sm flex items-center justify-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Revisar recordatorio</span>
            </button>
          </div>
        </div>

        {/* Right Column: Maintenance & Training */}
        <div className="space-y-6">
          {/* Revisiones Técnicas del Equipo */}
          <div className="bg-white rounded-2xl p-5 border border-[#E5E7EB] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-teal-50 text-[#0D9488] flex items-center justify-center">
                  <Wrench className="w-4 h-4" />
                </div>
                <h3 className="font-serif font-bold text-sm text-[#071C21]">
                  Revisiones Técnicas
                </h3>
              </div>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                SEDECAL
              </span>
            </div>

            <div className="space-y-3">
              {maintenance.map((m) => (
                <div key={m.id} className="p-3 bg-gray-50 rounded-xl border border-gray-200/80 text-xs space-y-1.5">
                  <div className="flex items-start justify-between gap-1">
                    <p className="font-serif font-bold text-[#071C21]">{m.clinicName}</p>
                    <span className="px-2 py-0.5 rounded font-medium text-[10px] bg-teal-50 text-teal-700">
                      {m.dueInText}
                    </span>
                  </div>
                  <p className="text-gray-600 text-[11px]">{m.task}</p>
                  {m.equipmentModel && (
                    <div className="flex items-center gap-1 text-[10px] text-gray-400 pt-1 border-t border-gray-100">
                      <Cpu className="w-3 h-3" />
                      <span>{m.equipmentModel} &middot; {m.installDate}</span>
                    </div>
                  )}
                  {m.nextMajorService && (
                    <p className="text-[10px] text-gray-400 italic">
                      {m.nextMajorService}
                    </p>
                  )}
                </div>
              ))}
            </div>

            <p className="text-[10px] text-gray-400 italic text-center pt-1 border-t border-gray-100">
              Los equipos SEDECAL tienen vida útil larga. El servicio mayor (lámpara UV) se estima cada ~6 años.
            </p>
          </div>

          {/* Capacitación */}
          <div className="bg-white rounded-2xl p-5 border border-[#E5E7EB] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-emerald-50 text-[#059669] flex items-center justify-center">
                  <GraduationCap className="w-4 h-4" />
                </div>
                <h3 className="font-serif font-bold text-sm text-[#071C21]">
                  Capacitación de Médicos
                </h3>
              </div>
              <span className="font-mono text-xs font-bold text-[#059669]">
                {training.certifiedDoctors} de {training.totalDoctors}
              </span>
            </div>

            {/* Progress bar */}
            <div>
              <div className="w-full bg-gray-100 h-2 rounded-full overflow-hidden mb-1">
                <div
                  className="h-full bg-gradient-to-r from-[#059669] to-[#10B981] rounded-full"
                  style={{ width: `${(training.certifiedDoctors / training.totalDoctors) * 100}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-gray-400 font-medium">
                <span>Capacitados en uso del equipo</span>
                <span>75%</span>
              </div>
            </div>

            {/* New protocol notification */}
            <div className="p-3.5 bg-emerald-50/50 rounded-xl border border-emerald-200/60 space-y-2">
              <p className="text-xs text-emerald-950 font-medium leading-snug">
                Nueva actualización en <strong>Guías Clínicas</strong>: {training.recentProtocolName}. ¿Enviar un resumen a los médicos de traumatología?
              </p>

              {notePrepared ? (
                <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-semibold pt-1">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Resumen enviado</span>
                </div>
              ) : (
                <button
                  onClick={() => setNotePrepared(true)}
                  className="text-xs font-semibold text-[#059669] hover:text-[#047857] hover:underline flex items-center gap-1 pt-1"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Preparar y enviar resumen</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Reminder Modal */}
      {reminderModalOpen && selectedReminder && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full border border-gray-200 shadow-2xl overflow-hidden animate-in fade-in duration-200">
            <div className="bg-[#071C21] p-5 text-white flex items-start justify-between border-b border-[#0E2E33]">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-500 text-black px-2 py-0.5 rounded-full inline-block mb-1">
                  Recordatorio sugerido por la IA
                </span>
                <h3 className="font-serif font-bold text-lg text-[#FAF9F5]">
                  Reposición de insumos
                </h3>
                <p className="text-xs text-gray-300">
                  {selectedReminder.clinicName} &middot; {selectedReminder.consumableType}
                </p>
              </div>
              <button
                onClick={() => setReminderModalOpen(false)}
                className="text-gray-400 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                <span>Último pedido: <strong>{selectedReminder.lastOrderText}</strong>. Estimamos que ya se agotaron.</span>
              </div>

              <p className="text-xs text-gray-500">
                La IA preparó este mensaje para enviar a la clínica. Revísalo y si está bien, apruébalo.
              </p>

              <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 text-xs text-gray-700 space-y-2 font-sans">
                <p className="font-semibold text-gray-900">
                  {selectedReminder.reminderDraft?.subject || 'Recordatorio de insumos'}
                </p>
                <p className="leading-relaxed whitespace-pre-line text-gray-600">
                  {selectedReminder.reminderDraft?.body || 'Estimado cliente, sugerimos renovar sus kits para no interrumpir las sesiones.'}
                </p>
              </div>
            </div>

            <div className="bg-gray-50 p-4 border-t border-gray-200 flex items-center justify-between">
              <button
                onClick={() => setReminderModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-gray-600 hover:text-gray-900"
              >
                Cancelar
              </button>
              <button
                onClick={handleSendReminder1Click}
                className="px-5 py-2.5 bg-[#059669] hover:bg-[#047857] text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-xs transition-all"
              >
                <Send className="w-4 h-4" />
                <span>Aprobar y enviar recordatorio</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
