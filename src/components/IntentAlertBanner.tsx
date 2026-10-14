'use client';

import React from 'react';
import { Bell, ArrowRight, X } from 'lucide-react';

interface IntentAlertBannerProps {
  message: string;
  onClick: () => void;
  onDismiss?: () => void;
}

export const IntentAlertBanner: React.FC<IntentAlertBannerProps> = ({
  message,
  onClick,
  onDismiss,
}) => {
  return (
    <div className="mb-6 bg-gradient-to-r from-[#FEF3C7] via-[#FFFBEB] to-[#FEF3C7] border border-[#FDE68A] rounded-xl px-4 py-3 shadow-xs flex items-center justify-between gap-4 transition-all hover:border-[#F59E0B]">
      <div 
        onClick={onClick}
        className="flex items-center gap-3 cursor-pointer flex-1 group"
      >
        <div className="w-8 h-8 rounded-full bg-[#F59E0B]/20 text-[#B45309] flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
          <Bell className="w-4 h-4 animate-bounce" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#B45309] bg-[#FDE68A] px-2 py-0.5 rounded">
              Actividad detectada
            </span>
          </div>
          <p className="text-sm font-medium text-[#78350F] mt-0.5 group-hover:text-[#92400E] flex items-center gap-1.5">
            {message}
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-1 text-xs font-semibold text-[#B45309] group-hover:translate-x-1 transition-transform">
          <span>Ver detalle</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </div>
      </div>

      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-amber-600 hover:text-amber-800 p-1 rounded-md hover:bg-amber-100 transition-colors"
          title="Ocultar"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
