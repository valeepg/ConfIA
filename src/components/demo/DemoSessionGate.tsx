"use client";

import {
  createContext,
  useContext,
  useState,
  useSyncExternalStore,
  type FormEvent,
  type ReactNode,
} from "react";

import {
  DEMO_USER,
  checkDemoCredentials,
  endDemoSession,
  parseDemoSession,
  readDemoSessionRaw,
  startDemoSession,
  subscribeDemoSession,
  type DemoSession,
} from "@/lib/demoSession";

type DemoContextValue = {
  session: DemoSession;
  logout: () => void;
  /** Se incrementa para pedir al asistente que abra el tutorial desde el inicio. */
  tutorialRequest: number;
  requestTutorial: () => void;
};

const DemoContext = createContext<DemoContextValue | null>(null);

export function useDemoSession(): DemoContextValue {
  const value = useContext(DemoContext);
  if (!value) throw new Error("useDemoSession debe usarse dentro de DemoSessionGate.");
  return value;
}

export function DemoSessionGate({ children }: { children: ReactNode }) {
  const [tutorialRequest, setTutorialRequest] = useState(0);
  // Undefined solo durante el render del servidor: así no se mezcla HTML con sesión local.
  const raw = useSyncExternalStore(subscribeDemoSession, readDemoSessionRaw, () => undefined);

  if (raw === undefined) return null;

  const session = parseDemoSession(raw);
  if (!session) {
    return <LoginScreen onLogin={() => startDemoSession()} />;
  }

  const value: DemoContextValue = {
    session,
    logout: () => endDemoSession(),
    tutorialRequest,
    requestTutorial: () => setTutorialRequest((count) => count + 1),
  };

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState<string>(DEMO_USER.email);
  const [password, setPassword] = useState<string>(DEMO_USER.password);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!checkDemoCredentials(email, password)) {
      setError("Correo o contraseña incorrectos. Usa la cuenta de demostración indicada abajo.");
      return;
    }
    setError(null);
    onLogin();
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0B1528] p-5">
      <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#0B1528] text-lg font-extrabold text-white">
            C
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#0284C7]">TECNOCARE · OZONO MÉDICO PERÚ</p>
            <h1 className="font-sans text-xl font-extrabold text-[#0B1528]">Acceso al CRM ConfIA</h1>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-7 space-y-4">
          <label className="block text-xs font-semibold text-slate-600">
            Correo corporativo
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-[#0B1528]"
            />
          </label>
          <label className="block text-xs font-semibold text-slate-600">
            Contraseña
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-[#0B1528]"
            />
          </label>

          {error && <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800">{error}</p>}

          <button
            type="submit"
            className="w-full rounded-xl bg-[#F97316] px-4 py-3 text-sm font-bold text-white shadow-sm shadow-orange-500/20 hover:bg-[#EA580C]"
          >
            Ingresar
          </button>
        </form>

        <div className="mt-6 rounded-2xl border border-sky-100 bg-sky-50/60 p-4 text-xs text-slate-700">
          <p className="font-semibold text-[#0369A1]">Cuenta de demostración</p>
          <p className="mt-1">
            {DEMO_USER.name} · {DEMO_USER.role}
          </p>
          <p>{DEMO_USER.email}</p>
          <p className="mt-1 text-slate-500">Contraseña: {DEMO_USER.password}</p>
        </div>
        <p className="mt-4 text-center text-[11px] text-slate-400">
          Autenticación simulada para la demostración. No se conecta a ningún proveedor real.
        </p>
      </div>
    </div>
  );
}
