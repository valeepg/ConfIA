"use client";

import { useEffect, useRef, useState } from "react";

import { DEMO_USER, initials } from "@/lib/demoSession";

import { useDemoSession } from "./DemoSessionGate";

export function AccountMenu() {
  const { session, logout, requestTutorial } = useDemoSession();
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Cierra el panel al hacer clic fuera o con Escape.
  useEffect(() => {
    if (!open) return;
    const handlePointer = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) setOpen(false);
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handlePointer);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handlePointer);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const startedAt = new Date(session.startedAt).toLocaleString("es-PE", { dateStyle: "medium", timeStyle: "short" });

  return (
    <div ref={wrapperRef} className="relative" data-tour="account">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white py-1.5 pl-1.5 pr-3 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#0B1528] text-[11px] font-bold text-white">
          {initials(session.name)}
        </span>
        <span className="hidden sm:inline">{session.name}</span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-40 mt-2 w-72 rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl"
        >
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#0B1528] text-sm font-bold text-white">
              {initials(session.name)}
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-[#0B1528]">{session.name}</p>
              <p className="truncate text-xs text-slate-500">{session.email}</p>
            </div>
          </div>

          <dl className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-xs">
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Rol</dt>
              <dd className="text-right font-semibold text-slate-800">{DEMO_USER.role}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Empresa</dt>
              <dd className="text-right font-semibold text-slate-800">{DEMO_USER.company}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Sesión iniciada</dt>
              <dd className="text-right text-slate-700">{startedAt}</dd>
            </div>
          </dl>

          <div className="mt-4 space-y-2">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                requestTutorial();
              }}
              className="w-full rounded-xl bg-sky-50 px-3 py-2.5 text-xs font-bold text-[#0369A1] hover:bg-sky-100"
            >
              Repetir tutorial
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={logout}
              className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
