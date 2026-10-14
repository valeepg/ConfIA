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
    <aside className="w-64 bg-[#071C21] text-white flex flex-col justify-between shrink-0 h-screen sticky top-0 border-r border-[#0E2E33] select-none">
      <div>
        {/* Brand Header */}
        <div className="p-6 border-b border-[#0F2F38]/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[#059669] to-[#047857] flex items-center justify-center shadow-md shadow-[#059669]/20">
              <span className="font-bold text-lg text-white tracking-wider">O₃</span>
            </div>
            <div>
              <h1 className="font-serif font-bold text-lg leading-tight text-[#FAF9F5] tracking-wide">
                ConfIA
              </h1>
              <p className="text-[11px] text-[#93C5FD]/70 font-sans uppercase tracking-wider">
                Ozono Médico Perú
              </p>
            </div>
          </div>
          <span className="text-[10px] bg-[#0E2E33] text-[#34D399] px-2 py-0.5 rounded-full font-medium border border-[#059669]/30">
            v1.2
          </span>
        </div>

        {/* Navigation Menu */}
        <nav className="p-4 space-y-1.5">
          <div className="text-[11px] uppercase tracking-wider text-gray-400 font-semibold px-3 mb-2">
            Panel Principal
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-[#0E2E33] text-[#34D399] border-l-4 border-[#10B981] shadow-inner'
                    : 'text-gray-300 hover:bg-[#0A242B] hover:text-white'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#34D399]' : 'text-gray-400'}`} />
                  <span>{item.label}</span>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Compliance & User Footer */}
      <div className="p-4 border-t border-[#0F2F38]/60 space-y-3 bg-[#05161A]/50">
        <div className="flex items-center gap-2 px-2 py-1.5 bg-[#082228] rounded-md border border-[#0E3B43]">
          <ShieldCheck className="w-3.5 h-3.5 text-[#10B981] shrink-0" />
          <span className="text-[11px] text-gray-300 font-medium">DIGEMID &middot; Droguería Certificada</span>
        </div>

        <div className="flex items-center gap-3 px-2 pt-1">
          <div className="relative">
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-[#0D9488] to-[#14B8A6] flex items-center justify-center text-white font-bold text-xs shadow-sm">
              TC
            </div>
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-[#10B981] rounded-full ring-2 ring-[#071C21]"></span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white truncate">Tecnocare Perú</p>
            <p className="text-[11px] text-gray-400 truncate">Equipos &amp; Asistencia</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
