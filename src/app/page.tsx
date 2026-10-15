"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { User } from "firebase/auth";
import {
  ArrowRight,
  Bell,
  Bot,
  CheckCircle2,
  ChevronRight,
  FileText,
  Filter,
  HandCoins,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Zap,
  ShoppingBag,
  Settings,
  Upload,
  Globe,
  RefreshCw,
  Sliders,
  DollarSign,
  Calendar,
  AlertTriangle,
  Award,
  Layers,
  Search,
  Check,
  FileCheck
} from "lucide-react";

import { Sidebar } from "@/components/Sidebar";
import {
  DATASET_ALERTS,
  FIRESTORE_COLLECTIONS,
  INITIAL_CONSUMABLES,
  INITIAL_LEADS,
  INITIAL_MAINTENANCE,
  INITIAL_TRAINING,
  INITIAL_EQUIPMENT,
  INITIAL_REGULATORY_FILES
} from "@/data/mockData";
import { getUserRole, signInWithGoogle, signOutUser, subscribeToAuth, type AppRole } from "@/lib/auth";
import { generateDossier, generateOutbound, generateRoi } from "@/lib/aiApi";
import { firebaseReady } from "@/lib/firebase";
import { getProspects, proposalId, saveProposal, saveProspect, seedInstalledBaseFromMocks, seedProspectsFromMocks } from "@/lib/firestore";
import type { Lead, PipelineStatus, EquipmentItem, RegulatoryFile } from "@/types";

const STATUS_META: Record<PipelineStatus, { label: string; badge: string }> = {
  descubierto: { label: "Descubierto", badge: "bg-slate-100 text-slate-700 border-slate-200" },
  contactado: { label: "Contactado", badge: "bg-sky-50 text-sky-800 border-sky-200" },
  propuesta_enviada: { label: "Propuesta enviada", badge: "bg-orange-50 text-orange-800 border-orange-200" },
  cierre: { label: "Cliente cerrado", badge: "bg-[#0B1528] text-white border-[#0B1528]" },
};

const STATUS_STYLES = {
  agotado: "bg-red-50 text-red-700 border border-red-200",
  reabastecer: "bg-orange-50 text-orange-700 border border-orange-200",
  al_dia: "bg-sky-50 text-sky-700 border border-sky-200",
};

const CLIENT_TYPE_META: Record<string, { label: string; badge: string }> = {
  "Clinica": { label: "Clínica Privada", badge: "bg-sky-50 text-[#0369A1] border-sky-200" },
  "Hospital Publico": { label: "Hospital Público", badge: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  "Consultorio Privado": { label: "Consultorio Privado", badge: "bg-cyan-50 text-cyan-800 border-cyan-200" },
  "Medico Independiente": { label: "Médico Independiente", badge: "bg-orange-50 text-orange-800 border-orange-200" },
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("es-PE", {
    style: "currency",
    currency: "PEN",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatUSD(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function Home() {
  const [currentTab, setCurrentTab] = useState<"pipeline" | "prospectos" | "posventa" | "catalogo" | "configuracion" | "documentos">("pipeline");
  const [leads, setLeads] = useState<Lead[]>(INITIAL_LEADS);
  const [selectedLeadId, setSelectedLeadId] = useState<string>(INITIAL_LEADS[0].id);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [approvalTarget, setApprovalTarget] = useState<{
    lead: Lead;
    type: "outbound" | "roi" | "dossier" | "consumibles";
  } | null>(null);
  const [dataMessage, setDataMessage] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isScraping, setIsScraping] = useState(false);
  const [isReprioritizing, setIsReprioritizing] = useState(false);

  // Auth states
  const [authUser, setAuthUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(firebaseReady);
  const [userRole, setUserRole] = useState<AppRole | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [generatingType, setGeneratingType] = useState<"outbound" | "roi" | "dossier" | null>(null);

  // Catalog & Regulatory files state
  const [equipmentList, setEquipmentList] = useState<EquipmentItem[]>(INITIAL_EQUIPMENT);
  const [regulatoryFiles, setRegulatoryFiles] = useState<RegulatoryFile[]>(INITIAL_REGULATORY_FILES);
  const [minScoreThreshold, setMinScoreThreshold] = useState<number>(65);

  useEffect(() => {
    if (!firebaseReady) {
      return;
    }

    return subscribeToAuth((user) => {
      setAuthUser(user);
      setAuthLoading(false);
      setUserRole(null);
      if (!user) {
        return;
      }

      getUserRole(user.uid)
        .then(setUserRole)
        .catch((error: unknown) => {
          setAuthError(error instanceof Error ? error.message : "No se pudo leer el rol del usuario.");
        });
    });
  }, []);

  useEffect(() => {
    if (!firebaseReady || !authUser || !userRole) {
      return;
    }

    let cancelled = false;
    getProspects()
      .then((remoteLeads) => {
        if (!cancelled && remoteLeads.length > 0) {
          setLeads(remoteLeads);
          setSelectedLeadId(remoteLeads[0].id);
          setDataMessage("Clínicas cargadas desde la nube.");
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setDataMessage(
            error instanceof Error
              ? `Base de datos no disponible: ${error.message}`
              : "Base de datos no disponible. Se mantienen datos de demostración.",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [authUser, userRole]);

  const selectedLead = useMemo(
    () => leads.find((lead) => lead.id === selectedLeadId) ?? leads[0],
    [leads, selectedLeadId],
  );

  const metrics = useMemo(() => {
    const openLeads = leads.filter((lead) => lead.status !== "cierre").length;
    const pendingDrafts = leads.filter((lead) => lead.hasAiDraft && !lead.draftApproved).length;
    const proposalsSent = leads.filter((lead) => ["propuesta_enviada", "cierre"].includes(lead.status)).length;
    const activeClients = leads.filter((lead) => lead.status === "cierre").length;

    return {
      openLeads,
      pendingDrafts,
      proposalsSent,
      activeClients,
    };
  }, [leads]);

  // Scraping handler
  const handleScrapeIpress = () => {
    setIsScraping(true);
    setDataMessage("Buscando nuevos clientes (hospitales públicos, consultorios privados y especialistas) en SUSALUD / CMP...");
    setTimeout(() => {
      const newClient: Lead = {
        id: `lead-scrape-${Date.now()}`,
        name: "Hospital Nacional Cayetano Heredia (Servicio de Fisiatría)",
        district: "San Martín de Porres, Lima",
        specialty: "Medicina de Rehabilitación y Dolor",
        score: 88,
        status: "descubierto",
        statusNote: "Hospital público con necesidad de unidad de dolor articular",
        directorMedico: "Dr. Víctor Cárdenas",
        doctorSpecialty: "Médico Fisiatra y Rehabilitador",
        clientType: "Hospital Publico",
        hasAiDraft: false,
        draftApproved: false,
        telemetryActivity: {
          ahtmReads: 0,
          lumbarMinutes: 0,
        },
        aiSuggestion: "Hospital docente de referencia. Presentar paquete institucional con generador SEDECAL y kits certificados sin PVC.",
      };
      setLeads((prev) => [newClient, ...prev]);
      setIsScraping(false);
      setDataMessage("¡Scraping finalizado! 1 nuevo cliente institucional agregado con puntaje 88.");
    }, 1500);
  };

  // Re-prioritize leads by score
  const handleReprioritize = () => {
    setIsReprioritizing(true);
    setDataMessage("Reordenando clientes por orden de mayor interés y afinidad médica...");
    setTimeout(() => {
      // `score` puede ser `null` (los prospectos de búsqueda no tienen puntaje del padrón): van al
      // final, no primero, porque `null` no es 0.
      setLeads((prev) => [...prev].sort((a, b) => (b.score ?? -1) - (a.score ?? -1)));
      setIsReprioritizing(false);
      setDataMessage(`¡Priorización actualizada! Clientes ordenados con umbral activo de ${minScoreThreshold} pts.`);
    }, 600);
  };

  const handleApprove = async (leadId: string, type: "outbound" | "roi" | "dossier" | "consumibles") => {
    const currentLead = leads.find((lead) => lead.id === leadId);
    if (!currentLead) return;

    const nextLead: Lead = {
      ...currentLead,
      status: type === "roi" && currentLead.status === "contactado"
        ? "propuesta_enviada"
        : currentLead.status,
      hasAiDraft: false,
      draftApproved: true,
      statusNote: type === "roi" ? "Propuesta económica aprobada y enviada" : "Borrador de comunicación aprobado",
    };

    setLeads((current) =>
      current.map((lead) => (lead.id !== leadId ? lead : nextLead))
    );

    if (firebaseReady) {
      try {
        await saveProspect(nextLead);
        const aiContent = type === "outbound"
          ? nextLead.outboundDraft
          : type === "roi"
            ? nextLead.roiProposal
            : type === "dossier"
              ? nextLead.digemidDossier
              : undefined;

        if (aiContent && authUser) {
          await saveProposal({
            id: proposalId(nextLead.id, type),
            prospectId: nextLead.id,
            type,
            status: "approved",
            createdBy: authUser.uid,
            approvedBy: authUser.uid,
            aiContent,
          });
        }
        setDataMessage("Aprobación guardada correctamente.");
      } catch (error: unknown) {
        setDataMessage(
          error instanceof Error
            ? `Aprobación local guardada, error al sincronizar: ${error.message}`
            : "Aprobación guardada localmente.",
        );
      }
    }

    setApprovalTarget(null);
  };

  const handleGenerate = async (type: "outbound" | "roi" | "dossier") => {
    if (!selectedLead) return;
    setGeneratingType(type);
    setDataMessage(null);

    try {
      const content = type === "outbound"
        ? await generateOutbound(selectedLead)
        : type === "roi"
          ? await generateRoi(selectedLead)
          : await generateDossier(selectedLead);

      const baseLead = {
        ...selectedLead,
        hasAiDraft: true,
        draftType: type,
        draftApproved: false,
        statusNote: "Borrador de IA listo para revisión humana",
      };

      let nextLead: Lead;
      if (type === "outbound") {
        nextLead = { ...baseLead, outboundDraft: content as Awaited<ReturnType<typeof generateOutbound>> };
      } else if (type === "roi") {
        nextLead = { ...baseLead, roiProposal: content as Awaited<ReturnType<typeof generateRoi>> };
      } else {
        nextLead = { ...baseLead, digemidDossier: content as Awaited<ReturnType<typeof generateDossier>> };
      }

      setLeads((current) => current.map((lead) => lead.id === nextLead.id ? nextLead : lead));
      setApprovalTarget({ lead: nextLead, type });
      setDataMessage("Borrador generado con éxito. Listo para revisión.");
    } catch (error: unknown) {
      setDataMessage(error instanceof Error ? `No se pudo generar: ${error.message}` : "Error al generar.");
    } finally {
      setGeneratingType(null);
    }
  };

  const tabTitle = {
    pipeline: "Seguimiento de Clientes",
    prospectos: "Directorio de Clientes",
    posventa: "Clientes, Equipos y Mantenimiento",
    catalogo: "Catálogo Oficial de Equipos",
    configuracion: "Configuración y Documentos de la IA",
    documentos: "Estructura y Esquema de Datos",
  }[currentTab];

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A]">
      <div className="flex min-h-screen">
        <Sidebar
          currentTab={currentTab}
          onSelectTab={(tab) => setCurrentTab(tab as typeof currentTab)}
        />

        <main className="flex-1 p-5 lg:p-7">
          <div className="mx-auto max-w-[1600px]">
            {/* Top Navigation & Action Controls Header - Tecnocare style */}
            <header className="mb-6 flex flex-col gap-4 border-b border-slate-200/80 bg-white p-5 rounded-2xl shadow-xs lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#F97316]"></span>
                  <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#0284C7]">TECNOCARE · OZONO MÉDICO PERÚ</p>
                </div>
                <h1 className="mt-1 font-sans text-2xl lg:text-3xl font-extrabold text-[#0B1528] tracking-tight">{tabTitle}</h1>
                <p className="text-xs text-slate-500 mt-0.5">Equipos SEDECAL con marcado CE y registro sanitario DIGEMID</p>
              </div>

              {/* Action Buttons with Tecnocare Navy and Orange accents */}
              <div className="flex flex-wrap items-center gap-2.5 self-start lg:self-auto">
                {authUser && (
                  <button type="button" onClick={() => signOutUser()} className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                    {authUser.displayName ?? authUser.email ?? "Salir"}
                  </button>
                )}

                {/* Scraping Button */}
                <button
                  type="button"
                  onClick={handleScrapeIpress}
                  disabled={isScraping}
                  className="inline-flex items-center gap-2 rounded-xl border border-sky-300 bg-sky-50/70 px-3.5 py-2 text-xs font-bold text-[#0369A1] shadow-xs transition hover:bg-sky-100 disabled:opacity-50"
                  title="Buscar automáticamente hospitales, consultorios y clínicas en SUSALUD y colegios médicos"
                >
                  <Globe className={`h-3.5 w-3.5 text-[#0284C7] ${isScraping ? "animate-spin" : ""}`} />
                  {isScraping ? "Buscando clientes..." : "Buscar nuevos clientes (Scraping)"}
                </button>

                {/* Reprioritize Button */}
                <button
                  type="button"
                  onClick={handleReprioritize}
                  disabled={isReprioritizing}
                  className="inline-flex items-center gap-2 rounded-xl border border-orange-200 bg-orange-50/70 px-3.5 py-2 text-xs font-bold text-orange-800 shadow-xs transition hover:bg-orange-100 disabled:opacity-50"
                  title="Reorganizar clientes por su nivel de interés"
                >
                  <RefreshCw className={`h-3.5 w-3.5 text-[#F97316] ${isReprioritizing ? "animate-spin" : ""}`} />
                  {isReprioritizing ? "Reordenando..." : "Actualizar priorización"}
                </button>

                {/* Main Action Button - Tecnocare Orange */}
                <button
                  type="button"
                  onClick={() => {
                    const sampleLead: Lead = {
                      id: `lead-manual-${Date.now()}`,
                      name: "Consultorio Dr. Juan Pérez (Medicina Física)",
                      district: "Surco, Lima",
                      specialty: "Medicina Física y Rehabilitación",
                      score: 75,
                      status: "descubierto",
                      statusNote: "Médico en proceso de equipar consultorio",
                      directorMedico: "Dr. Juan Pérez",
                      doctorSpecialty: "Fisiatra",
                      clientType: "Medico Independiente",
                      hasAiDraft: false,
                      draftApproved: false,
                      telemetryActivity: { ahtmReads: 0, lumbarMinutes: 0 },
                      aiSuggestion: "Interés en infiltraciones articulares con equipo Ozonette.",
                    };
                    setLeads((prev) => [sampleLead, ...prev]);
                    setDataMessage("Nuevo cliente agregado manualmente.");
                  }}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#F97316] px-4 py-2 text-xs font-bold text-white shadow-sm shadow-orange-500/20 transition hover:bg-[#EA580C]"
                >
                  <Zap className="h-3.5 w-3.5" />
                  Nuevo cliente
                </button>
              </div>
            </header>

            {/* Notification message */}
            {dataMessage && (
              <div className="mb-5 flex items-center justify-between rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-[#0369A1] shadow-xs">
                <span>{dataMessage}</span>
                <button type="button" onClick={() => setDataMessage(null)} className="text-sky-700 hover:text-sky-950 font-bold ml-4">✕</button>
              </div>
            )}

            {/* TAB: SEGUIMIENTO (KANBAN) */}
            {currentTab === "pipeline" && (
              <>
                <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard label="Clientes en contacto" value={metrics.openLeads.toString()} accent="sky" />
                  <MetricCard label="Propuestas por revisar" value={metrics.pendingDrafts.toString()} accent="orange" />
                  <MetricCard label="Propuestas enviadas" value={metrics.proposalsSent.toString()} accent="blue" />
                  <MetricCard label="Clientes cerrados" value={metrics.activeClients.toString()} accent="deep" />
                </section>

                <section className="grid gap-4 xl:grid-cols-4">
                  {(["descubierto", "contactado", "propuesta_enviada", "cierre"] as PipelineStatus[]).map((stage) => {
                    const stageLeads = leads.filter((lead) => lead.status === stage);
                    return (
                      <div key={stage} className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
                        <div className="mb-3 flex items-center justify-between">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{STATUS_META[stage].label}</p>
                            <span className="mt-1 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                              {stageLeads.length} clientes
                            </span>
                          </div>
                        </div>

                        <div className="space-y-3">
                          {stageLeads.length === 0 ? (
                            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-6 text-center text-sm text-slate-500">
                              No hay clientes en esta etapa
                            </div>
                          ) : (
                            stageLeads.map((lead) => (
                              <button
                                key={lead.id}
                                type="button"
                                onClick={() => {
                                  setSelectedLeadId(lead.id);
                                  setDrawerOpen(true);
                                }}
                                className="w-full rounded-2xl border border-slate-200 bg-[#F9FAF7] p-3.5 text-left transition hover:-translate-y-0.5 hover:border-[#0B6E4F]/40 hover:shadow-md"
                              >
                                <div className="mb-2 flex items-center justify-between gap-2">
                                  <p className="font-semibold text-[#071C21] text-sm leading-snug">{lead.name}</p>
                                  <span className="rounded-full bg-[#EAFBF4] px-2 py-0.5 text-xs font-bold text-[#0B6E4F] shrink-0">
                                    {lead.score === null ? 'Sin puntaje' : `${lead.score} pts`}
                                  </span>
                                </div>
                                
                                {lead.clientType && CLIENT_TYPE_META[lead.clientType] && (
                                  <div className="mb-2">
                                    <span className={`inline-block rounded-md border px-2 py-0.5 text-[10px] font-semibold ${CLIENT_TYPE_META[lead.clientType].badge}`}>
                                      {CLIENT_TYPE_META[lead.clientType].label}
                                    </span>
                                  </div>
                                )}

                                <p className="text-xs text-slate-500">{lead.district} · {lead.specialty}</p>
                                <p className="mt-2 text-xs text-slate-600 line-clamp-2">{lead.statusNote}</p>
                                {lead.hasAiDraft && (
                                  <div className="mt-2.5 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.1em] text-amber-800">
                                    <Sparkles className="h-3 w-3" />
                                    Borrador listo
                                  </div>
                                )}
                              </button>
                            ))
                          )}
                        </div>
                      </div>
                    );
                  })}
                </section>
              </>
            )}

            {/* TAB: DIRECTORIO DE CLIENTES */}
            {currentTab === "prospectos" && (
              <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
                    <div>
                      <h2 className="font-serif text-2xl font-bold text-[#071C21]">Directorio de Clientes</h2>
                      <p className="text-xs text-slate-500 mt-0.5">Hospitales públicos, clínicas privadas, consultorios y médicos independientes</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                        {leads.length} registros
                      </span>
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1">
                        <Award className="h-3.5 w-3.5 text-amber-600" />
                        {leads.filter((l) => (l.score ?? 0) >= minScoreThreshold).length} alta prioridad
                      </span>
                    </div>
                  </div>

                  {/* Listado con diferenciación visual dorada para clientes de alto interés */}
                  <div className="space-y-3">
                    {leads.map((lead) => {
                      const isHighPriority = (lead.score ?? 0) >= minScoreThreshold;
                      return (
                        <button
                          key={lead.id}
                          type="button"
                          onClick={() => {
                            setSelectedLeadId(lead.id);
                            setDrawerOpen(true);
                          }}
                          className={`flex w-full items-center justify-between rounded-2xl border p-4 text-left transition-all hover:shadow-md ${
                            isHighPriority
                              ? "bg-gradient-to-r from-amber-50/70 via-yellow-50/40 to-white border-amber-300 shadow-sm ring-1 ring-amber-200/60 hover:border-amber-400"
                              : "bg-[#F8FAF9] border-slate-200 hover:border-[#0B6E4F]/30 hover:bg-white"
                          }`}
                        >
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              {isHighPriority && (
                                <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-amber-500 to-yellow-500 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white shadow-xs">
                                  <Award className="h-3 w-3" />
                                  Prioridad Alta
                                </span>
                              )}
                              <p className={`font-semibold text-sm ${isHighPriority ? "text-[#071C21] font-bold" : "text-[#071C21]"}`}>{lead.name}</p>
                              {lead.clientType && CLIENT_TYPE_META[lead.clientType] && (
                                <span className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold ${CLIENT_TYPE_META[lead.clientType].badge}`}>
                                  {CLIENT_TYPE_META[lead.clientType].label}
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-500 mt-1.5">{lead.district} · {lead.specialty}</p>
                            <p className="text-xs text-slate-600 mt-0.5">Responsable: <strong className="text-slate-800">{lead.directorMedico ?? 'Sin identificar'}</strong> ({lead.doctorSpecialty ?? '—'})</p>
                          </div>

                          <div className="text-right shrink-0 ml-4">
                            {isHighPriority ? (
                              <div className="inline-flex flex-col items-end">
                                <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-amber-100 to-yellow-100 border border-amber-300 px-3 py-1 text-xs font-extrabold text-amber-900 shadow-xs">
                                  <Sparkles className="h-3.5 w-3.5 text-amber-600" />
                                  {lead.score === null ? 'Sin puntaje' : `${lead.score} pts`}
                                </span>
                                <span className="text-[10px] font-bold text-amber-700 mt-1 uppercase tracking-wider">Interés Máximo</span>
                              </div>
                            ) : (
                              <div className="inline-flex flex-col items-end">
                                <span className="inline-flex rounded-full bg-slate-100 border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700">
                                  {lead.score === null ? 'Sin puntaje' : `${lead.score} pts`}
                                </span>
                                <p className="mt-1 text-xs text-slate-500">{STATUS_META[lead.status].label}</p>
                              </div>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="space-y-6">
                  {/* Panel de Criterios de Priorización Mejorado */}
                  <div className="rounded-2xl border-2 border-amber-300 bg-gradient-to-b from-amber-50/80 to-white p-5 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-amber-900">
                        <Sliders className="h-5 w-5 text-amber-600" />
                        <h3 className="font-semibold text-sm uppercase tracking-[0.18em]">Criterios de Priorización</h3>
                      </div>
                      <span className="rounded-full bg-amber-200/80 px-2.5 py-0.5 text-xs font-bold text-amber-900">
                        Control Interactivo
                      </span>
                    </div>

                    <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                      Filtra y destaca en dorado automáticamente los clientes con mayor probabilidad de adopción según su afinidad médica y volumen de pacientes.
                    </p>

                    <div className="mt-4 rounded-xl bg-white p-4 border border-amber-200 shadow-xs space-y-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-700 font-semibold">Umbral para Destacar en Dorado:</span>
                        <span className="font-mono text-sm font-bold text-amber-800 bg-amber-100 px-2.5 py-0.5 rounded-full border border-amber-300">
                          ≥ {minScoreThreshold} puntos
                        </span>
                      </div>

                      <input
                        type="range"
                        min="50"
                        max="90"
                        step="5"
                        value={minScoreThreshold}
                        onChange={(e) => setMinScoreThreshold(Number(e.target.value))}
                        className="w-full accent-amber-500 cursor-pointer"
                      />

                      <div className="flex justify-between text-[10px] text-slate-400 font-medium">
                        <span>50 pts (Más permisivo)</span>
                        <span>70 pts (Recomendado)</span>
                        <span>90 pts (Solo líderes)</span>
                      </div>
                    </div>

                    {/* Presets rápidos */}
                    <div className="mt-3 flex items-center gap-1.5">
                      <span className="text-[11px] text-slate-500 font-medium">Presets:</span>
                      <button
                        type="button"
                        onClick={() => setMinScoreThreshold(70)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                          minScoreThreshold === 70 ? "bg-amber-600 text-white" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        Interés Alto (≥70)
                      </button>
                      <button
                        type="button"
                        onClick={() => setMinScoreThreshold(80)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                          minScoreThreshold === 80 ? "bg-amber-600 text-white" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        Muy Alto (≥80)
                      </button>
                      <button
                        type="button"
                        onClick={() => setMinScoreThreshold(90)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                          minScoreThreshold === 90 ? "bg-amber-600 text-white" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        Top VIP (≥90)
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={handleReprioritize}
                      disabled={isReprioritizing}
                      className="mt-4 w-full rounded-xl bg-gradient-to-r from-amber-600 to-yellow-600 py-2.5 text-xs font-bold text-white shadow-sm transition hover:from-amber-700 hover:to-yellow-700 flex items-center justify-center gap-2"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${isReprioritizing ? "animate-spin" : ""}`} />
                      {isReprioritizing ? "Reordenando..." : "Reordenar directorio por puntaje"}
                    </button>
                  </div>

                  {/* Cuadro destacado de los Top Clientes */}
                  <div className="rounded-2xl border border-amber-200 bg-white p-5 shadow-sm">
                    <div className="flex items-center gap-2 text-amber-900 mb-3">
                      <Award className="h-4 w-4 text-amber-600" />
                      <p className="text-xs font-bold uppercase tracking-[0.18em]">Clientes Más Interesados ({leads.filter((l) => (l.score ?? 0) >= minScoreThreshold).length})</p>
                    </div>
                    <div className="space-y-2.5">
                      {leads
                        .filter((l) => (l.score ?? 0) >= minScoreThreshold)
                        .slice(0, 4)
                        .map((lead) => (
                          <div
                            key={lead.id}
                            onClick={() => {
                              setSelectedLeadId(lead.id);
                              setDrawerOpen(true);
                            }}
                            className="cursor-pointer rounded-xl border border-amber-200/80 bg-gradient-to-r from-amber-50 to-yellow-50/50 p-3 transition hover:shadow-xs hover:border-amber-400"
                          >
                            <div className="flex items-center justify-between">
                              <p className="font-semibold text-[#071C21] text-xs truncate max-w-[200px]">{lead.name}</p>
                              <span className="text-xs font-extrabold text-amber-900 bg-amber-200/80 px-2 py-0.5 rounded-full">
                                {lead.score} pts
                              </span>
                            </div>
                            <p className="mt-1 text-[11px] text-slate-600 truncate">{lead.directorMedico} · {lead.specialty}</p>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* TAB: CLIENTES Y EQUIPOS (POSVENTA) */}
            {currentTab === "posventa" && (
              <section className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard label="Equipos instalados" value="14 unidades" accent="deep" />
                  <MetricCard label="Insumos por reponer" value="2 clientes" accent="orange" />
                  <MetricCard label="Ciclo de Mantenimiento" value="Cada 5 años" accent="sky" />
                  <MetricCard label="Médicos capacitados" value="9 de 12" accent="blue" />
                </div>

                <div className="grid gap-6 xl:grid-cols-[1fr_1.3fr]">
                  {/* Consumibles Table */}
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col justify-between">
                    <div>
                      <div className="mb-4 flex items-center justify-between">
                        <div>
                          <h2 className="font-serif text-2xl font-bold text-[#071C21]">Consumo de Insumos</h2>
                          <p className="text-xs text-slate-500 mt-0.5">Kits descartables AHTm y accesorios sin PVC</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setDataMessage("Recordatorio de reposición preparado para clientes con stock bajo.")}
                          className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
                        >
                          <Bot className="h-3.5 w-3.5 text-emerald-700" />
                          Recordar stock
                        </button>
                      </div>

                      <div className="overflow-hidden rounded-xl border border-slate-200">
                        <table className="min-w-full divide-y divide-slate-200 text-left">
                          <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                            <tr>
                              <th className="px-3.5 py-2.5">Cliente</th>
                              <th className="px-3.5 py-2.5">Insumo</th>
                              <th className="px-3.5 py-2.5">Estado</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200 bg-white text-xs text-slate-700">
                            {INITIAL_CONSUMABLES.map((item) => (
                              <tr key={item.id}>
                                <td className="px-3.5 py-3 font-medium text-[#071C21]">{item.clinicName}</td>
                                <td className="px-3.5 py-3 text-slate-600">{item.consumableType}</td>
                                <td className="px-3.5 py-3">
                                  <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLES[item.status]}`}>
                                    {item.status === "agotado" ? "Agotado" : item.status === "reabastecer" ? "Pedir pronto" : "Al día"}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Capacitacion Banner */}
                    <div className="mt-5 rounded-2xl border border-slate-200 bg-[#071C21] p-4 text-white">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Capacitación Médica Continua</p>
                      <div className="mt-2 flex items-center justify-between">
                        <div>
                          <p className="text-2xl font-bold">{INITIAL_TRAINING.certifiedDoctors}/{INITIAL_TRAINING.totalDoctors}</p>
                          <p className="text-xs text-slate-300 mt-0.5">Médicos acreditados en ozonoterapia</p>
                        </div>
                        <span className="text-xs bg-emerald-900/60 border border-emerald-500/40 text-emerald-200 px-3 py-1 rounded-full font-medium">
                          Vigente 2026
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Enhanced Maintenance & Lifecycle View */}
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
                      <div>
                        <h2 className="font-serif text-2xl font-bold text-[#071C21]">Parque de Equipos y Mantenimiento</h2>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Tecnología de alta durabilidad: los equipos médicos requieren mantenimiento mayor <strong>cada 5 años</strong>.
                        </p>
                      </div>
                      <span className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-xs font-semibold text-emerald-800">
                        <ShieldCheck className="h-4 w-4 text-emerald-600" />
                        Ciclos de 5 Años
                      </span>
                    </div>

                    <div className="space-y-3.5">
                      {INITIAL_MAINTENANCE.map((item) => (
                        <div key={item.id} className="rounded-2xl border border-slate-200 bg-[#FAF9F6] p-4 transition hover:border-[#0B6E4F]/40 hover:bg-white">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <div className="flex items-center gap-2">
                                <h3 className="font-semibold text-sm text-[#071C21]">{item.clinicName}</h3>
                                {item.clientType && CLIENT_TYPE_META[item.clientType] && (
                                  <span className={`rounded-md border px-1.5 py-0.5 text-[9px] font-semibold ${CLIENT_TYPE_META[item.clientType].badge}`}>
                                    {CLIENT_TYPE_META[item.clientType].label}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs font-medium text-[#059669] mt-0.5">{item.equipmentModel} · Serie: <span className="font-mono text-slate-700">{item.serialNumber}</span></p>
                            </div>

                            <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                              item.urgency === 'high' ? 'bg-red-100 text-red-700 border border-red-200' :
                              item.urgency === 'medium' ? 'bg-amber-100 text-amber-800 border border-amber-200' :
                              'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            }`}>
                              {item.urgency === 'high' ? 'Mantenimiento 5 Años Cumplido' :
                               item.urgency === 'medium' ? 'Revisión Próxima (Año 4)' :
                               'Operativo / Al día'}
                            </span>
                          </div>

                          {/* 5-Year Lifespan Progress Bar */}
                          <div className="mt-3.5 rounded-xl bg-white border border-slate-200/80 p-3">
                            <div className="flex items-center justify-between text-xs mb-1.5">
                              <span className="text-slate-600 font-medium">Ciclo Quinquenal:</span>
                              <span className="font-bold text-[#071C21]">
                                Año {item.currentYearOfUse} de {item.expectedLifespanYears} (Instalado {item.installYear})
                              </span>
                            </div>

                            {/* Visual Progress Bar (5 segments for 5 years) */}
                            <div className="grid grid-cols-5 gap-1.5">
                              {[1, 2, 3, 4, 5].map((year) => {
                                const isPassed = year < item.currentYearOfUse;
                                const isCurrent = year === item.currentYearOfUse;
                                return (
                                  <div key={year} className="flex flex-col items-center">
                                    <div
                                      className={`h-2.5 w-full rounded-sm transition-all ${
                                        isPassed
                                          ? 'bg-[#0B6E4F]'
                                          : isCurrent
                                          ? item.urgency === 'high' ? 'bg-red-500' : 'bg-amber-500 animate-pulse'
                                          : 'bg-slate-200'
                                      }`}
                                    />
                                    <span className="text-[9px] text-slate-400 mt-1 font-mono">Año {year}</span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>

                          <div className="mt-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs">
                            <p className="text-slate-700 font-medium">
                              📅 {item.dueInText}
                            </p>
                            <span className="text-slate-500 text-[11px]">
                              {item.nextMajorService}
                            </span>
                          </div>

                          <p className="mt-2 text-xs text-slate-600 bg-white/60 rounded-lg p-2 border border-slate-100">
                            {item.statusNote}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* TAB: CATÁLOGO DE EQUIPOS */}
            {currentTab === "catalogo" && (
              <section className="space-y-6">
                <div className="flex flex-col gap-2 rounded-2xl bg-gradient-to-r from-[#0B1528] via-[#0F294D] to-[#0284C7] p-6 text-white shadow-md md:flex-row md:items-center md:justify-between">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-widest text-[#38BDF8]">TECNOCARE · DISTRIBUIDOR OFICIAL</span>
                    <h2 className="font-sans text-2xl lg:text-3xl font-black text-white mt-1">Generadores de Ozono Médico SEDECAL España</h2>
                    <p className="text-xs text-sky-100/90 mt-1">Equipos europeos de alta precisión con marcado CE y registro sanitario DIGEMID en el Perú.</p>
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-xl bg-white/10 backdrop-blur-xs border border-white/20 px-4 py-2 text-xs font-bold text-white shrink-0">
                    <span className="w-2 h-2 rounded-full bg-[#F97316] animate-pulse"></span>
                    Mantenimiento Mayor Cada 5 Años
                  </div>
                </div>

                <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                  {equipmentList.map((eq) => (
                    <div key={eq.id} className="flex flex-col justify-between rounded-3xl border border-slate-200/90 bg-white p-6 shadow-xs transition hover:shadow-lg hover:border-[#0284C7]/50 group">
                      <div>
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="text-[10px] font-black uppercase tracking-widest text-[#F97316]">{eq.brand} · ESPAÑA</span>
                            <h3 className="font-sans text-2xl font-black text-[#0B1528] mt-0.5 tracking-tight group-hover:text-[#0284C7] transition-colors">{eq.model}</h3>
                          </div>
                          <span className="rounded-full bg-sky-50 border border-sky-100 px-3 py-1 text-xs font-bold text-[#0369A1]">
                            {eq.category}
                          </span>
                        </div>

                        <p className="mt-3 text-xs text-slate-600 leading-relaxed">{eq.description}</p>

                        <div className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="text-slate-500 font-medium">Registro DIGEMID:</span>
                            <span className="font-mono font-bold text-[#0B1528] bg-slate-100 px-2 py-0.5 rounded">{eq.registroDiGEMID}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-500 font-medium">Garantía / Calibración:</span>
                            <span className="font-bold text-[#0284C7]">Cada {eq.maintenanceCycleYears > 0 ? `${eq.maintenanceCycleYears} años` : "Uso único"}</span>
                          </div>
                        </div>

                        <div className="mt-3.5 flex flex-wrap gap-1.5">
                          {eq.certifications.map((c) => (
                            <span key={c} className="rounded-md bg-slate-50 border border-slate-200 px-2 py-0.5 text-[10px] text-slate-600 font-bold">
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="mt-6 border-t border-slate-100 pt-4 flex items-center justify-between">
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Precio de Referencia</p>
                          <p className="text-2xl font-black text-[#0B1528]">{formatUSD(eq.priceUSD)}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            setDataMessage(`Equipo ${eq.model} seleccionado como base para la propuesta comercial.`);
                          }}
                          className="rounded-xl bg-[#0B1528] px-4 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-[#0284C7] flex items-center gap-1.5"
                        >
                          Usar en cotización
                          <ArrowRight className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* TAB: CONFIGURACIÓN Y DOCUMENTOS REGULATORIOS PARA LA IA */}
            {currentTab === "configuracion" && (
              <section className="space-y-6">
                <div>
                  <h2 className="font-sans text-2xl font-black text-[#0B1528] tracking-tight">Configuración y Archivos de la IA</h2>
                  <p className="text-xs text-slate-500 mt-1">
                    Sube documentos normativos, certificados DIGEMID y guías clínicas para que la IA responda siempre con base legal verificada.
                  </p>
                </div>

                <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                  {/* Lista de archivos que alimentan a la IA */}
                  <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <FileCheck className="h-5 w-5 text-[#0284C7]" />
                        <h3 className="font-bold text-sm text-[#0B1528]">Archivos que guían a la IA</h3>
                      </div>
                      <span className="text-xs font-bold text-[#0369A1] bg-sky-50 border border-sky-200 px-3 py-1 rounded-full">
                        {regulatoryFiles.filter((f) => f.feedsAI).length} activos
                      </span>
                    </div>

                    <div className="space-y-3">
                      {regulatoryFiles.map((file) => (
                        <div key={file.id} className="rounded-2xl border border-slate-200 bg-[#F8FAFC] p-4 flex items-start justify-between gap-4 transition hover:bg-white hover:border-sky-300">
                          <div className="flex items-start gap-3">
                            <div className="p-2.5 rounded-xl bg-sky-100/70 text-[#0284C7] shrink-0 mt-0.5">
                              <FileText className="h-5 w-5" />
                            </div>
                            <div>
                              <p className="font-bold text-sm text-[#0B1528]">{file.name}</p>
                              <p className="text-xs text-slate-600 mt-1">{file.description}</p>
                              <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                                <span>{file.sizeKB} KB</span>
                                <span>•</span>
                                <span>Subido el {file.uploadedAt}</span>
                              </div>
                            </div>
                          </div>

                          <label className="flex items-center gap-2 cursor-pointer shrink-0 mt-1">
                            <input
                              type="checkbox"
                              checked={file.feedsAI}
                              onChange={() => {
                                setRegulatoryFiles((prev) =>
                                  prev.map((f) => (f.id === file.id ? { ...f, feedsAI: !f.feedsAI } : f))
                                );
                              }}
                              className="h-4 w-4 rounded accent-[#0284C7]"
                            />
                            <span className="text-xs text-slate-700 font-bold">Usar en IA</span>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Panel de Carga de nuevos archivos */}
                  <div className="space-y-6">
                    <div className="rounded-2xl border-2 border-dashed border-sky-300 bg-white p-6 text-center shadow-xs">
                      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-50 text-[#0284C7]">
                        <Upload className="h-6 w-6" />
                      </div>
                      <h4 className="mt-3 font-bold text-sm text-[#0B1528]">Subir nuevo documento legal</h4>
                      <p className="mt-1 text-xs text-slate-500">PDF, Word o Texto de Resoluciones DIGEMID, fichas técnicas o consentimientos (máx 20MB)</p>

                      <div className="mt-4">
                        <button
                          type="button"
                          onClick={() => {
                            const newFile: RegulatoryFile = {
                              id: `reg-${Date.now()}`,
                              name: "Resolucion_Directoral_DIGEMID_2026.pdf",
                              type: "registro_sanitario",
                              description: "Resolución oficial de droguería y comercialización de equipos de ozono en Perú.",
                              uploadedAt: "Hoy",
                              sizeKB: 1840,
                              feedsAI: true
                            };
                            setRegulatoryFiles((prev) => [newFile, ...prev]);
                            setDataMessage("Documento regulatorio subido y activado para entrenamiento del agente IA.");
                          }}
                          className="rounded-xl bg-[#0B1528] px-5 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-[#0284C7]"
                        >
                          Simular subida de archivo
                        </button>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-orange-200 bg-orange-50/70 p-5 text-orange-950 shadow-xs">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-[#F97316]" />
                        <p className="text-xs font-black uppercase tracking-wider text-orange-900">Regla de Cumplimiento Médico SEDECAL</p>
                      </div>
                      <p className="mt-2 text-xs leading-relaxed text-orange-900/90">
                        Todo texto redactado por la IA citará la <strong>Declaración de Madrid</strong> y el número oficial de Registro Sanitario DIGEMID para respaldar con rigor científico y normativo cada cotización.
                      </p>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* TAB: ESQUEMA DE DATOS Y BASES */}
            {currentTab === "documentos" && (
              <section className="space-y-6">
                <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                  <div className="mb-4 flex items-center justify-between">
                    <div>
                      <h2 className="font-serif text-2xl font-bold text-[#071C21]">Esquema de Base de Datos</h2>
                      <p className="text-xs text-slate-500 mt-1">Estructura organizada en la nube para clínicas, insumos y propuestas</p>
                    </div>
                    <span className="inline-flex items-center gap-2 rounded-full bg-[#ECFDF5] px-3 py-1 text-xs font-semibold text-emerald-700">
                      <ShieldCheck className="h-4 w-4" />
                      Seguridad por Perfil
                    </span>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    {FIRESTORE_COLLECTIONS.map((collection) => (
                      <div key={collection.name} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="flex items-center justify-between gap-4">
                          <div>
                            <p className="font-semibold uppercase tracking-[0.12em] text-[#0B6E4F] text-sm">{collection.name}</p>
                            <p className="mt-1 text-xs text-slate-600">{collection.purpose}</p>
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {collection.fields.map((field) => (
                            <span key={field} className="rounded-md bg-white px-2 py-0.5 text-[11px] text-slate-600 border border-slate-200">
                              {field}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}
          </div>
        </main>
      </div>

      {/* DRAWER LATERAL: DETALLE DE LA CLÍNICA */}
      {drawerOpen && selectedLead && (
        <aside className="fixed right-0 top-0 h-screen w-full max-w-xl border-l border-slate-200 bg-white shadow-2xl z-40">
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Ficha del Cliente</p>
                <h2 className="mt-1 font-serif text-2xl font-bold text-[#071C21]">{selectedLead.name}</h2>
              </div>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
              >
                Cerrar
              </button>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto p-6">
              <div className="rounded-2xl bg-[#F8FAF9] p-4">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs text-slate-500">{selectedLead.district} · {selectedLead.specialty}</p>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_META[selectedLead.status].badge}`}>
                    {STATUS_META[selectedLead.status].label}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-700">
                  Responsable médico: <span className="font-semibold text-[#071C21]">{selectedLead.directorMedico}</span>
                </p>
                <p className="mt-1 text-xs text-slate-500">Especialidad: {selectedLead.doctorSpecialty}</p>
              </div>

              {/* Sugerencia de la IA */}
              <div className="rounded-2xl border border-sky-200 bg-sky-50/60 p-4">
                <div className="mb-2 flex items-center gap-2 text-[#0369A1]">
                  <Bot className="h-4 w-4 text-[#0284C7]" />
                  <p className="text-xs font-black uppercase tracking-[0.18em]">Sugerencia Comercial SEDECAL</p>
                </div>
                <p className="text-xs leading-relaxed text-slate-700">{selectedLead.aiSuggestion}</p>
              </div>

              {/* Botones de Acción */}
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Acciones Recomendadas</p>
                <div className="mt-4 grid gap-2.5">
                  <button
                    type="button"
                    disabled={generatingType !== null}
                    onClick={() => handleGenerate("outbound")}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#F97316] px-4 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-[#EA580C] disabled:opacity-60"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    {generatingType === "outbound" ? "Redactando mensaje..." : "Redactar mensaje de contacto"}
                  </button>

                  <button
                    type="button"
                    disabled={generatingType !== null}
                    onClick={() => handleGenerate("roi")}
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-2.5 text-xs font-bold text-[#0369A1] transition hover:bg-sky-100 disabled:opacity-60"
                  >
                    <DollarSign className="h-3.5 w-3.5 text-[#0284C7]" />
                    {generatingType === "roi" ? "Calculando retorno..." : "Generar propuesta económica (Retorno)"}
                  </button>

                  <button
                    type="button"
                    disabled={generatingType !== null}
                    onClick={() => handleGenerate("dossier")}
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
                  >
                    <ShieldCheck className="h-3.5 w-3.5 text-[#0284C7]" />
                    {generatingType === "dossier" ? "Preparando documentos..." : "Ver carpeta regulatoria DIGEMID"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </aside>
      )}

      {/* MODAL DE APROBACIÓN HUMANA */}
      {approvalTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Revisión antes del envío</p>
                <h3 className="mt-1 font-serif text-2xl font-bold text-[#071C21]">
                  {approvalTarget.type === "roi" ? "Propuesta Económica" : approvalTarget.type === "dossier" ? "Carpeta Regulatoria DIGEMID" : "Mensaje de Contacto"}
                </h3>
              </div>
              <button type="button" onClick={() => setApprovalTarget(null)} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600">
                ✕
              </button>
            </div>

            {approvalTarget.type === "roi" && approvalTarget.lead.roiProposal ? (
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs text-slate-600">Modelo recomendado</p>
                  <p className="mt-1 font-semibold text-[#071C21]">{approvalTarget.lead.roiProposal.equipmentModel}</p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <InfoCard label="Costo por sesión" value={formatCurrency(approvalTarget.lead.roiProposal.costPerSession)} />
                  <InfoCard label="Ingreso neto estimado" value={formatCurrency(approvalTarget.lead.roiProposal.estimatedNetMonthly)} />
                  <InfoCard label="Kits por mes" value={`${approvalTarget.lead.roiProposal.minimumKitsPerMonth} kits`} />
                  <InfoCard label="Sesiones proyectadas" value={`${approvalTarget.lead.roiProposal.projectedSessionsMonth} al mes`} />
                </div>
              </div>
            ) : approvalTarget.type === "dossier" && approvalTarget.lead.digemidDossier ? (
              <div className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <InfoCard label="Registro Sanitario" value={approvalTarget.lead.digemidDossier.registryNumber} />
                  <InfoCard label="Clasificación" value={approvalTarget.lead.digemidDossier.classification} />
                  <InfoCard label="Certificado Calibración" value={approvalTarget.lead.digemidDossier.calibrationCertificate} />
                  <InfoCard label="Consentimiento Legal" value={approvalTarget.lead.digemidDossier.informedConsentTemplate} />
                </div>
              </div>
            ) : approvalTarget.type === "outbound" && approvalTarget.lead.outboundDraft ? (
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs text-slate-500">Dirigido a: <strong className="text-slate-800">{approvalTarget.lead.outboundDraft.recipientName}</strong> ({approvalTarget.lead.outboundDraft.recipientRole})</p>
                  <p className="mt-2 text-xs font-semibold text-[#071C21]">Asunto: {approvalTarget.lead.outboundDraft.subject}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-4 text-xs leading-relaxed text-slate-700 whitespace-pre-line border-l-4 border-l-[#0B6E4F]">
                  {approvalTarget.lead.outboundDraft.body}
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs leading-relaxed text-slate-700">
                Información preparada lista para aprobación.
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => handleApprove(approvalTarget.lead.id, approvalTarget.type)}
                className="inline-flex items-center gap-2 rounded-full bg-[#0B6E4F] px-5 py-2.5 text-xs font-semibold text-white hover:bg-[#0A5F44]"
              >
                <CheckCircle2 className="h-4 w-4" />
                Aprobar y Enviar (1 Clic)
              </button>
              <button
                type="button"
                onClick={() => setApprovalTarget(null)}
                className="rounded-full border border-slate-200 bg-white px-4 py-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Cerrar sin enviar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "sky" | "orange" | "blue" | "deep";
}) {
  const styles = {
    sky: "bg-white text-[#0B1528] border-l-4 border-l-[#0284C7] shadow-sm",
    orange: "bg-white text-[#0B1528] border-l-4 border-l-[#F97316] shadow-sm",
    blue: "bg-white text-[#0B1528] border-l-4 border-l-[#1E40AF] shadow-sm",
    deep: "bg-[#0B1528] text-white border-l-4 border-l-[#38BDF8] shadow-md",
  };

  const badgeIconStyles = {
    sky: "text-[#0284C7] bg-sky-50",
    orange: "text-[#F97316] bg-orange-50",
    blue: "text-[#1E40AF] bg-blue-50",
    deep: "text-[#38BDF8] bg-white/10",
  };

  return (
    <div className={`rounded-2xl p-5 border border-slate-200/80 ${styles[accent]}`}>
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{label}</p>
        <span className={`p-1.5 rounded-lg ${badgeIconStyles[accent]}`}>
          <TrendingUp className="h-4 w-4" />
        </span>
      </div>
      <div className="mt-3 flex items-baseline justify-between gap-2">
        <p className="font-sans text-3xl font-black tracking-tight">{value}</p>
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">{label}</p>
      <p className="mt-1.5 text-xs font-semibold text-[#071C21]">{value}</p>
    </div>
  );
}
