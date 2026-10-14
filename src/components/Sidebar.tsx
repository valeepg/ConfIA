'use client';

import React from 'react';
import { 
  Kanban, 
  Users, 
  Repeat, 
  ShoppingBag, 
  Settings, 
  FileText, 
  ShieldCheck 
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
}) => {
  const navItems = [
    { id: 'pipeline', label: 'Seguimiento de Clientes', icon: Kanban },
    { id: 'prospectos', label: 'Directorio de Clientes', icon: Users },
    { id: 'posventa', label: 'Equipos y Mantenimiento', icon: Repeat },
    { id: 'catalogo', label: 'Catálogo de Equipos', icon: ShoppingBag },
    { id: 'configuracion', label: 'Configuración y Regulación', icon: Settings },
    { id: 'documentos', label: 'Esquema de Datos', icon: FileText },
  ];

  return (
    <aside className="w-64 bg-[#0B1528] text-white flex flex-col justify-between shrink-0 h-screen sticky top-0 border-r border-[#1E293B] select-none shadow-xl">
      <div>
        {/* Brand Header - Tecnocare Style */}
        <div className="p-5 border-b border-[#1E293B] flex items-center justify-between bg-[#080E1D]">
          <div className="flex items-center gap-3">
            {/* Tecnocare Swirl Icon Style */}
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center p-1.5 shadow-md shadow-sky-900/30">
              <svg viewBox="0 0 100 100" className="w-full h-full">
                <circle cx="50" cy="50" r="42" fill="none" stroke="#F97316" strokeWidth="8" strokeDasharray="60 180" strokeLinecap="round" transform="rotate(-45 50 50)" />
                <circle cx="50" cy="50" r="32" fill="none" stroke="#0284C7" strokeWidth="8" strokeDasharray="120 120" strokeLinecap="round" transform="rotate(45 50 50)" />
                <circle cx="50" cy="50" r="20" fill="none" stroke="#0F172A" strokeWidth="6" strokeDasharray="80 80" strokeLinecap="round" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h1 className="font-sans font-black text-base leading-tight text-white tracking-wider">
                  TECNO<span className="text-[#0284C7]">CARE</span>
                </h1>
              </div>
              <p className="text-[10px] text-[#38BDF8] font-sans font-bold uppercase tracking-widest mt-0.5">
                ConfIA · SEDECAL Perú
              </p>
            </div>
          </div>
          <span className="text-[10px] bg-[#0284C7]/20 text-[#38BDF8] px-2 py-0.5 rounded-full font-bold border border-[#0284C7]/40">
            v1.3
          </span>
        </div>

        {/* Navigation Menu */}
        <nav className="p-4 space-y-1.5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 font-bold px-3 mb-2 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#F97316]"></span>
            Panel de Gestión
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-[#0284C7]/25 to-transparent text-[#38BDF8] border-l-4 border-[#0284C7] shadow-sm'
                    : 'text-slate-300 hover:bg-[#132238] hover:text-white'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#38BDF8]' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Compliance & User Footer */}
      <div className="p-4 border-t border-[#1E293B] space-y-3 bg-[#080E1D]">
        <div className="flex items-center gap-2 px-2.5 py-2 bg-[#0F1D33] rounded-xl border border-[#1E3A5F]">
          <ShieldCheck className="w-4 h-4 text-[#38BDF8] shrink-0" />
          <div className="text-[11px] leading-tight">
            <p className="text-white font-bold">DIGEMID · Droguería</p>
            <p className="text-slate-400 text-[10px]">Tecnología Médica SEDECAL</p>
          </div>
        </div>

        <div className="flex items-center gap-3 px-2 pt-1">
          <div className="relative">
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-[#0284C7] to-[#38BDF8] flex items-center justify-center text-white font-bold text-xs shadow-md shadow-sky-500/20">
              TC
            </div>
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-[#F97316] rounded-full ring-2 ring-[#0B1528]"></span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-white truncate">Tecnocare Perú</p>
            <p className="text-[11px] text-slate-400 truncate">Soporte y Ventas Oficiales</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
