import type { ReactNode } from "react";

// Un solo tono secuencial por gráfico (validado con scripts/validate_palette.js).
export const SEQUENTIAL = {
  100: "#cde2fb",
  250: "#86b6ef",
  350: "#5598e7",
  450: "#2a78d6",
  550: "#1c5cab",
  650: "#104281",
};

export function Kpi({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <p className="mt-2 font-sans text-3xl font-extrabold tracking-tight text-[#0B1528]">{value}</p>
      <p className="mt-1 text-[11px] text-slate-500">{hint}</p>
    </div>
  );
}

export function ChartCard({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
      <h3 className="text-sm font-bold text-[#0B1528]">{title}</h3>
      <p className="mb-4 text-[11px] text-slate-500">{subtitle}</p>
      {children}
    </div>
  );
}

export type BarItem = { label: string; value: number; valueLabel?: string; color: string };

/** Barras horizontales con etiqueta directa (una serie, sin leyenda). */
export function BarList({ items, emptyText = "Sin datos todavía." }: { items: BarItem[]; emptyText?: string }) {
  if (items.length === 0) return <p className="text-xs text-slate-500">{emptyText}</p>;
  const max = Math.max(1, ...items.map((item) => item.value));
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.label}>
          <div className="flex justify-between gap-2 text-xs text-slate-600">
            <span className="truncate">{item.label}</span>
            <span className="shrink-0 font-semibold text-[#0B1528]">{item.valueLabel ?? item.value}</span>
          </div>
          <div className="mt-1 h-3 rounded-full bg-slate-100" title={`${item.label}: ${item.valueLabel ?? item.value}`}>
            <div
              className="h-3 rounded-full transition-all"
              style={{
                width: `${(item.value / max) * 100}%`,
                backgroundColor: item.color,
                minWidth: item.value > 0 ? 8 : 0,
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
