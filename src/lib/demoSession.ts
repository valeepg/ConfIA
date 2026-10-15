/**
 * Sesión simulada para la demo. No es autenticación real: un único usuario ficticio
 * y una contraseña de demostración. La sesión vive en localStorage (solo por visitante).
 */

export const DEMO_USER = {
  name: "Lucía Mendoza",
  email: "lucia.mendoza@confia-demo.test",
  password: "confia2026",
  role: "Dueña · Administradora",
  company: "Tecnocare Perú (demo)",
} as const;

const SESSION_KEY = "confia.demo.session";
const TUTORIAL_KEY = "confia.tutorial.completed";

export type DemoSession = {
  email: string;
  name: string;
  startedAt: string;
};

function readItem(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    // Navegador privado o almacenamiento bloqueado: la demo sigue funcionando sin persistir.
    return null;
  }
}

function writeItem(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // Sin almacenamiento disponible: se ignora.
  }
}

export function checkDemoCredentials(email: string, password: string): boolean {
  return email.trim().toLowerCase() === DEMO_USER.email && password === DEMO_USER.password;
}

export function loadDemoSession(): DemoSession | null {
  const raw = readItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as DemoSession;
    return parsed.email === DEMO_USER.email ? parsed : null;
  } catch {
    return null;
  }
}

const SESSION_EVENT = "confia-demo-session";

/** Suscripción para useSyncExternalStore: avisa cuando cambia la sesión en esta pestaña. */
export function subscribeDemoSession(callback: () => void): () => void {
  window.addEventListener(SESSION_EVENT, callback);
  return () => window.removeEventListener(SESSION_EVENT, callback);
}

/** Valor crudo de la sesión (string estable para comparar); null si no hay sesión. */
export function readDemoSessionRaw(): string | null {
  return readItem(SESSION_KEY);
}

export function parseDemoSession(raw: string | null): DemoSession | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as DemoSession;
    return parsed.email === DEMO_USER.email ? parsed : null;
  } catch {
    return null;
  }
}

function notifySessionChange(): void {
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function startDemoSession(): DemoSession {
  const session: DemoSession = {
    email: DEMO_USER.email,
    name: DEMO_USER.name,
    startedAt: new Date().toISOString(),
  };
  writeItem(SESSION_KEY, JSON.stringify(session));
  notifySessionChange();
  return session;
}

export function endDemoSession(): void {
  writeItem(SESSION_KEY, null);
  notifySessionChange();
}

export function isTutorialCompleted(): boolean {
  return readItem(TUTORIAL_KEY) === "true";
}

export function setTutorialCompleted(completed: boolean): void {
  writeItem(TUTORIAL_KEY, completed ? "true" : null);
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
