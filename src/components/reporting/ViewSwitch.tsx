"use client";

export type ViewOption<T extends string> = { value: T; label: string };

/** Interruptor de dos vistas, con estado accesible (aria-pressed). */
export function ViewSwitch<T extends string>({
  value,
  options,
  onChange,
  dataTour,
}: {
  value: T;
  options: ViewOption<T>[];
  onChange: (value: T) => void;
  dataTour?: string;
}) {
  return (
    <div data-tour={dataTour} className="mb-5 inline-flex rounded-xl border border-slate-200 bg-white p-1 shadow-xs">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
          className={`rounded-lg px-4 py-2 text-xs font-bold transition ${
            value === option.value ? "bg-[#0B1528] text-white" : "text-slate-600 hover:bg-slate-50"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
