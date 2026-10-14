'use client';

import React from 'react';
import { Users, FileEdit, Send, CheckCircle2, Cpu, Package, Wrench, GraduationCap } from 'lucide-react';

interface MetricItem {
  label: string;
  value: string | number;
  highlight?: 'emerald' | 'amber' | 'teal' | 'default';
  icon?: React.ReactNode;
  subtitle?: string;
}

interface MetricCardsProps {
  metrics: MetricItem[];
}

export const MetricCards: React.FC<MetricCardsProps> = ({ metrics }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {metrics.map((m, idx) => {
        let valueColor = 'text-[#0F2F38]';
        let borderColor = 'border-[#E5E7EB]';
        let bgTag = '';

        if (m.highlight === 'emerald') {
          valueColor = 'text-[#059669]';
          borderColor = 'border-[#A7F3D0]/60';
        } else if (m.highlight === 'amber') {
          valueColor = 'text-[#D97706]';
          borderColor = 'border-[#FDE68A]';
          bgTag = 'bg-[#FEF3C7] text-[#92400E]';
        } else if (m.highlight === 'teal') {
          valueColor = 'text-[#0D9488]';
          borderColor = 'border-[#99F6E4]/60';
        }

        return (
          <div
            key={idx}
            className={`bg-white rounded-xl p-5 border ${borderColor} shadow-xs transition-all hover:shadow-md flex flex-col justify-between`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                {m.label}
              </span>
              {m.icon && (
                <div className="text-gray-400">
                  {m.icon}
                </div>
              )}
            </div>

            <div className="flex items-baseline justify-between mt-1">
              <div className={`font-serif text-3xl font-bold tracking-tight ${valueColor}`}>
                {m.value}
              </div>
              {m.subtitle && (
                <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${bgTag || 'bg-gray-100 text-gray-600'}`}>
                  {m.subtitle}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
