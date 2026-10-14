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
} from "lucide-react";

import { Sidebar } from "@/components/Sidebar";
import { DATASET_ALERTS, FIRESTORE_COLLECTIONS, INITIAL_CONSUMABLES, INITIAL_LEADS, INITIAL_MAINTENANCE, INITIAL_TRAINING } from "@/data/mockData";
import { getUserRole, signInWithGoogle, signOutUser, subscribeToAuth, type AppRole } from "@/lib/auth";
import { generateDossier, generateOutbound, generateRoi } from "@/lib/aiApi";
import { firebaseReady } from "@/lib/firebase";
import { getProspects, proposalId, saveProposal, saveProspect, seedInstalledBaseFromMocks, seedProspectsFromMocks } from "@/lib/firestore";
import type { Lead, PipelineStatus } from "@/types";

const STATUS_META: Record<PipelineStatus, { label: string; badge: string }> = {
  descubierto: { label: "Descubierto", badge: "bg-slate-100 text-slate-700" },
  contactado: { label: "Contactado", badge: "bg-amber-100 text-amber-700" },
  propuesta_enviada: { label: "Propuesta enviada", badge: "bg-emerald-100 text-emerald-700" },
  cierre: { label: "Cierre", badge: "bg-emerald-700 text-white" },
};

const STATUS_STYLES = {
  agotado: "bg-red-50 text-red-700 border border-red-200",
  reabastecer: "bg-amber-50 text-amber-700 border border-amber-200",
  al_dia: "bg-emerald-50 text-emerald-700 border border-emerald-200",
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("es-PE", {
    style: "currency",
    currency: "PEN",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function Home() {
  const [currentTab, setCurrentTab] = useState<"pipeline" | "prospectos" | "posventa" | "documentos">("pipeline");
  const [leads, setLeads] = useState<Lead[]>(INITIAL_LEADS);
  const [selectedLeadId, setSelectedLeadId] = useState<string>(INITIAL_LEADS[4].id);
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [approvalTarget, setApprovalTarget] = useState<{
    lead: Lead;
    type: "outbound" | "roi" | "dossier" | "consumibles";
  } | null>(null);
  const [dataMessage, setDataMessage] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [authUser, setAuthUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(firebaseReady);
  const [userRole, setUserRole] = useState<AppRole | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [generatingType, setGeneratingType] = useState<"outbound" | "roi" | "dossier" | null>(null);

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
          setDataMessage("Prospectos cargados desde Firestore.");
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setDataMessage(
            error instanceof Error
              ? `Firestore no disponible: ${error.message}`
              : "Firestore no disponible. Se mantienen los datos de demostración.",
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

  const alertLead = useMemo(
    () => leads.find((lead) => lead.telemetryAlert) ?? leads[0],
    [leads],
  );

  if (firebaseReady && authLoading) {
    return <FullScreenMessage title="Cargando sesión" body="Verificando tu identidad en Firebase..." />;
  }

  if (firebaseReady && !authUser) {
    return <LoginScreen error={authError} onSignIn={() => {
      setAuthError(null);
      signInWithGoogle().catch((error: unknown) => {
        setAuthError(error instanceof Error ? error.message : "No se pudo iniciar sesión.");
      });
    }} />;
  }

  if (firebaseReady && !userRole) {
    return (
      <FullScreenMessage
        title="Usuario pendiente de autorización"
        body={`Tu cuenta (${authUser?.email ?? "sin correo"}) inició sesión, pero todavía no tiene un documento users/{uid} con un rol válido.`}
        action={<button type="button" onClick={() => signOutUser()} className="rounded-full bg-[#0B6E4F] px-4 py-2 text-sm font-semibold text-white">Cerrar sesión</button>}
      />
    );
  }

  const handleApprove = async (leadId: string, type: "outbound" | "roi" | "dossier" | "consumibles") => {
    const currentLead = leads.find((lead) => lead.id === leadId);
    if (!currentLead) {
      return;
    }

    const nextLead: Lead = {
      ...currentLead,
      status: type === "roi" && currentLead.status === "contactado"
        ? "propuesta_enviada"
        : currentLead.status,
      hasAiDraft: false,
      draftApproved: true,
      statusNote: type === "roi" ? "Propuesta ROI aprobada y enviada" : "Borrador IA aprobado",
    };

    setLeads((current) =>
      current.map((lead) => {
        if (lead.id !== leadId) {
          return lead;
        }
        return nextLead;
      }),
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
        setDataMessage("Aprobación guardada en Firestore.");
      } catch (error: unknown) {
        setDataMessage(
          error instanceof Error
            ? `La aprobación quedó local, pero no se guardó en Firestore: ${error.message}`
            : "La aprobación quedó local, pero no se guardó en Firestore.",
        );
      }
    }

    setApprovalTarget(null);
  };

  const handleSyncMocks = async () => {
    setIsSyncing(true);
    try {
      await seedProspectsFromMocks();
      await seedInstalledBaseFromMocks();
      setDataMessage("Prospectos y parque instalado sincronizados en Firestore.");
    } catch (error: unknown) {
      setDataMessage(
        error instanceof Error
          ? `No se pudo sincronizar: ${error.message}`
          : "No se pudo sincronizar los prospectos.",
      );
    } finally {
      setIsSyncing(false);
    }
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
        statusNote: "Borrador IA pendiente de aprobación humana",
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
      if (firebaseReady && authUser) {
        await saveProspect(nextLead);
        await saveProposal({
          id: proposalId(nextLead.id, type),
          prospectId: nextLead.id,
          type,
          status: "pending_approval",
          createdBy: authUser.uid,
          aiContent: content,
        });
      }
      setApprovalTarget({ lead: nextLead, type });
      setDataMessage("Borrador generado y guardado como pendiente de aprobación.");
    } catch (error: unknown) {
      setDataMessage(error instanceof Error ? `No se pudo generar el borrador: ${error.message}` : "No se pudo generar el borrador.");
    } finally {
      setGeneratingType(null);
    }
  };

  const tabTitle = {
    pipeline: "Pipeline comercial outbound",
    prospectos: "Prospectos IPRESS",
    posventa: "Posventa y retención",
    documentos: "IA y modelo de base de datos",
  }[currentTab];

  return (
    <div className="min-h-screen bg-[#F7F5F0] text-[#0F2F38]">
      <div className="flex min-h-screen">
        <Sidebar
          currentTab={currentTab}
          onSelectTab={(tab) => setCurrentTab(tab as typeof currentTab)}
          onOpenOzonePedia={() => setCurrentTab("documentos")}
        />

        <main className="flex-1 p-5 lg:p-7">
          <div className="mx-auto max-w-[1600px]">
            <header className="mb-6 flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#0F766E]">ConfIA</p>
                <h1 className="mt-1 font-serif text-3xl font-bold text-[#071C21]">{tabTitle}</h1>
              </div>

              <div className="flex items-center gap-3 self-start lg:self-auto">
                {authUser && (
                  <button type="button" onClick={() => signOutUser()} className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700">
                    {authUser.displayName ?? authUser.email ?? "Salir"}
                  </button>
                )}
                <button className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300">
                  <Filter className="h-4 w-4 text-slate-500" />
                  Filtros
                </button>
                <button className="inline-flex items-center gap-2 rounded-full bg-[#0B6E4F] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#0A5F44]">
                  <Zap className="h-4 w-4" />
                  Nuevo lead
                </button>
              </div>
            </header>

            {dataMessage && (
              <div className="mb-5 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
                {dataMessage}
              </div>
            )}

            {currentTab === "pipeline" && (
              <>
                <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard label="Prospectos activos" value={metrics.openLeads.toString()} accent="emerald" />
                  <MetricCard label="Borradores por aprobar" value={metrics.pendingDrafts.toString()} accent="amber" />
                  <MetricCard label="Propuestas enviadas" value={metrics.proposalsSent.toString()} accent="teal" />
                  <MetricCard label="Clientes activos" value={metrics.activeClients.toString()} accent="green" />
                </section>

                <div className="mb-6 flex items-center justify-between rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 to-yellow-50 px-5 py-4 shadow-sm">
                  <div className="flex items-center gap-3">
                    <Bell className="h-5 w-5 text-amber-600" />
                    <div>
                      <p className="text-sm font-semibold text-amber-800">Alerta nueva</p>
                      <p className="text-sm text-amber-700">
                        {alertLead.name} está leyendo protocolos en la OzonePedia y requiere seguimiento comercial.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedLeadId(alertLead.id);
                      setDrawerOpen(true);
                    }}
                    className="inline-flex items-center gap-2 rounded-full bg-amber-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-amber-600"
                  >
                    Ver detalle
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>

                <section className="grid gap-4 xl:grid-cols-4">
                  {(["descubierto", "contactado", "propuesta_enviada", "cierre"] as PipelineStatus[]).map((stage) => {
                    const stageLeads = leads.filter((lead) => lead.status === stage);
                    return (
                      <div key={stage} className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
                        <div className="mb-3 flex items-center justify-between">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{STATUS_META[stage].label}</p>
                            <span className="mt-1 inline-flex rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                              {stageLeads.length}
                            </span>
                          </div>
                        </div>

                        <div className="space-y-3">
                          {stageLeads.length === 0 ? (
                            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-6 text-center text-sm text-slate-500">
                              Sin registros
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
                                className="w-full rounded-2xl border border-slate-200 bg-[#F9FAF7] p-3 text-left transition hover:-translate-y-0.5 hover:border-[#0B6E4F]/30 hover:shadow-md"
                              >
                                <div className="mb-2 flex items-center justify-between gap-2">
                                  <p className="font-semibold text-[#071C21]">{lead.name}</p>
                                  <span className="rounded-full bg-[#EAFBF4] px-2 py-1 text-xs font-bold text-[#0B6E4F]">
                                    {lead.score}
                                  </span>
                                </div>
                                <p className="text-xs text-slate-500">{lead.district} · {lead.specialty}</p>
                                <p className="mt-2 text-xs text-slate-600">{lead.statusNote}</p>
                                {lead.hasAiDraft && (
                                  <div className="mt-3 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-amber-800">
                                    <Sparkles className="h-3 w-3" />
                                    Borrador IA
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

            {currentTab === "prospectos" && (
              <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="font-serif text-2xl font-bold text-[#071C21]">Listado de prospectos</h2>
                    <button className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600">
                      <Filter className="h-4 w-4" />
                      Especialidad
                    </button>
                  </div>
                  <div className="space-y-3">
                    {leads.map((lead) => (
                      <button
                        key={lead.id}
                        type="button"
                        onClick={() => {
                          setSelectedLeadId(lead.id);
                          setDrawerOpen(true);
                        }}
                        className="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-[#F8FAF9] p-4 text-left transition hover:border-[#0B6E4F]/30"
                      >
                        <div>
                          <p className="font-semibold text-[#071C21]">{lead.name}</p>
                          <p className="text-sm text-slate-500">{lead.district} · {lead.specialty}</p>
                        </div>
                        <div className="text-right">
                          <span className="inline-flex rounded-full bg-emerald-100 px-2 py-1 text-xs font-bold text-emerald-700">
                            Score {lead.score}
                          </span>
                          <p className="mt-2 text-xs text-slate-500">{STATUS_META[lead.status].label}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Prioridad</p>
                    <div className="mt-4 space-y-4">
                      {leads.slice(0, 3).map((lead) => (
                        <div key={lead.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                          <div className="flex items-center justify-between">
                            <p className="font-semibold text-[#071C21]">{lead.name}</p>
                            <span className="text-sm font-bold text-[#0B6E4F]">{lead.score}</span>
                          </div>
                          <p className="mt-1 text-sm text-slate-500">{lead.directorMedico}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-[#071C21] p-5 text-white shadow-sm">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Métricas</p>
                    <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
                      <div className="rounded-xl bg-white/5 p-3">
                        <p className="text-xs text-slate-300">Leads con alerta</p>
                        <p className="mt-1 text-2xl font-bold">{leads.filter((lead) => lead.telemetryAlert).length}</p>
                      </div>
                      <div className="rounded-xl bg-white/5 p-3">
                        <p className="text-xs text-slate-300">Borradores IA</p>
                        <p className="mt-1 text-2xl font-bold">{leads.filter((lead) => lead.hasAiDraft).length}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {currentTab === "posventa" && (
              <section className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard label="Parque instalado" value="14 equipos" accent="deep" />
                  <MetricCard label="Consumo crítico" value="2 clínicas" accent="amber" />
                  <MetricCard label="Mantenimiento" value="3 alertas" accent="red" />
                  <MetricCard label="Capacitación" value="9/12 médicos" accent="teal" />
                </div>

                <div className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="mb-4 flex items-center justify-between">
                      <h2 className="font-serif text-2xl font-bold text-[#071C21]">Monitoreo de insumos</h2>
                      <button className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-600">
                        <Bot className="h-4 w-4 text-amber-600" />
                        Generar reminder
                      </button>
                    </div>

                    <div className="overflow-hidden rounded-xl border border-slate-200">
                      <table className="min-w-full divide-y divide-slate-200 text-left">
                        <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">
                          <tr>
                            <th className="px-4 py-3">Cliente</th>
                            <th className="px-4 py-3">Consumible</th>
                            <th className="px-4 py-3">Demanda</th>
                            <th className="px-4 py-3">Estado</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 bg-white text-sm text-slate-700">
                          {INITIAL_CONSUMABLES.map((item) => (
                            <tr key={item.id}>
                              <td className="px-4 py-3 font-medium text-[#071C21]">{item.clinicName}</td>
                              <td className="px-4 py-3">{item.consumableType}</td>
                              <td className="px-4 py-3">{item.estimatedMonthly}</td>
                              <td className="px-4 py-3">
                                <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${STATUS_STYLES[item.status]}`}>
                                  {item.status === "agotado" ? "Agotado" : item.status === "reabastecer" ? "Reabastecer" : "Al día"}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Alertas de mantenimiento</p>
                      <div className="mt-4 space-y-3">
                        {INITIAL_MAINTENANCE.map((alert) => (
                          <div key={alert.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                            <div className="flex items-center justify-between">
                              <p className="font-semibold text-[#071C21]">{alert.clinicName}</p>
                              <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${
                                alert.urgency === "high" ? "bg-red-100 text-red-700" : alert.urgency === "medium" ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
                              }`}>{alert.urgency}</span>
                            </div>
                            <p className="mt-2 text-sm text-slate-600">{alert.task}</p>
                            <p className="mt-2 text-xs text-slate-500">{alert.dueInText}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-200 bg-[#071C21] p-5 text-white shadow-sm">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Capacitación médica</p>
                      <div className="mt-4 rounded-xl bg-white/5 p-4">
                        <p className="text-3xl font-bold">{INITIAL_TRAINING.certifiedDoctors}/{INITIAL_TRAINING.totalDoctors}</p>
                        <p className="mt-2 text-sm text-slate-300">Médicos certificados</p>
                        <p className="mt-4 text-sm text-slate-100">{INITIAL_TRAINING.recentProtocolName}</p>
                        <p className="mt-2 text-xs text-slate-300">{INITIAL_TRAINING.targetDepartment}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {currentTab === "documentos" && (
              <section className="space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                  <div>
                    <p className="font-semibold text-emerald-900">
                      Firestore {firebaseReady ? "habilitado" : "en modo demo"}
                    </p>
                    <p className="mt-1 text-sm text-emerald-800">
                      Sincroniza los prospectos de demostración para validar la colección `prospects`.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleSyncMocks}
                    disabled={!firebaseReady || isSyncing}
                    className="rounded-full bg-[#0B6E4F] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#0A5F44] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isSyncing ? "Sincronizando..." : "Sincronizar datos demo"}
                  </button>
                </div>

                <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="font-serif text-2xl font-bold text-[#071C21]">Esquema Firestore</h2>
                    <span className="inline-flex items-center gap-2 rounded-full bg-[#ECFDF5] px-3 py-1 text-xs font-semibold text-emerald-700">
                      <ShieldCheck className="h-4 w-4" />
                      Security by role
                    </span>
                  </div>

                  <div className="space-y-4">
                    {FIRESTORE_COLLECTIONS.map((collection) => (
                      <div key={collection.name} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="flex items-center justify-between gap-4">
                          <div>
                            <p className="font-semibold uppercase tracking-[0.12em] text-[#0B6E4F]">{collection.name}</p>
                            <p className="mt-1 text-sm text-slate-600">{collection.purpose}</p>
                          </div>
                          <span className="rounded-full bg-slate-200 px-2 py-1 text-[10px] font-bold uppercase text-slate-700">
                            {collection.role}
                          </span>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {collection.fields.map((field) => (
                            <span key={field} className="rounded-full bg-white px-2 py-1 text-xs text-slate-600 ring-1 ring-slate-200">
                              {field}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="rounded-2xl border border-slate-200 bg-[#071C21] p-5 text-white shadow-sm">
                    <div className="flex items-center gap-2 text-[#D4F6E8]">
                      <Bot className="h-5 w-5" />
                      <p className="text-xs font-semibold uppercase tracking-[0.2em]">Structured outputs</p>
                    </div>
                    <p className="mt-4 text-sm text-slate-200">
                      Gemini Flash devolverá JSON validado con Pydantic para evitar inventar registros sanitarios, precios o procedimientos no validados.
                    </p>
                    <div className="mt-4 rounded-xl bg-white/5 p-3">
                      <p className="text-xs text-slate-300">Schema objetivo</p>
                      <p className="mt-1 font-mono text-sm text-emerald-200">proposal, roi, dossier, outboundDraft</p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Alertas de calidad</p>
                    <div className="mt-4 space-y-3">
                      {DATASET_ALERTS.map((alert) => (
                        <div key={alert.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                          <div className="flex items-center justify-between">
                            <p className="font-semibold text-[#071C21]">{alert.title}</p>
                            <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${
                              alert.risk === "alta" ? "bg-red-100 text-red-700" : alert.risk === "media" ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
                            }`}>{alert.risk}</span>
                          </div>
                          <p className="mt-2 text-sm text-slate-600">{alert.summary}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                </div>
              </section>
            )}
          </div>
        </main>
      </div>

      {drawerOpen && selectedLead && (
        <aside className="fixed right-0 top-0 h-screen w-full max-w-xl border-l border-slate-200 bg-white shadow-2xl shadow-slate-900/10">
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Lead</p>
                <h2 className="mt-1 font-serif text-2xl font-bold text-[#071C21]">{selectedLead.name}</h2>
              </div>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="rounded-full border border-slate-200 px-2.5 py-1.5 text-sm text-slate-600"
              >
                Cerrar
              </button>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto p-5">
              <div className="rounded-2xl bg-[#F8FAF9] p-4">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm text-slate-500">{selectedLead.district} · {selectedLead.specialty}</p>
                  <span className={`rounded-full px-2 py-1 text-xs font-semibold ${STATUS_META[selectedLead.status].badge}`}>
                    {STATUS_META[selectedLead.status].label}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-700">
                  Director médico: <span className="font-semibold text-[#071C21]">{selectedLead.directorMedico}</span>
                </p>
                <p className="mt-1 text-sm text-slate-700">Especialista: {selectedLead.doctorSpecialty}</p>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Actividad en OzonePedia</p>
                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between rounded-xl bg-slate-50 p-3">
                    <span className="text-sm text-slate-700">Autohemoterapia mayor (AHTm)</span>
                    <span className="font-bold text-[#071C21]">{selectedLead.telemetryActivity.ahtmReads}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl bg-slate-50 p-3">
                    <span className="text-sm text-slate-700">Tiempo lectura hernia lumbar</span>
                    <span className="font-bold text-[#071C21]">{selectedLead.telemetryActivity.lumbarMinutes} min</span>
                  </div>
                  {selectedLead.telemetryActivity.searchQuery && (
                    <div className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
                      Búsqueda reciente: “{selectedLead.telemetryActivity.searchQuery}”
                    </div>
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
                <div className="mb-2 flex items-center gap-2 text-amber-800">
                  <Bot className="h-4 w-4" />
                  <p className="text-xs font-semibold uppercase tracking-[0.18em]">Sugerencia de IA</p>
                </div>
                <p className="text-sm leading-6 text-amber-900">{selectedLead.aiSuggestion}</p>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Acciones</p>
                <div className="mt-4 grid gap-3">
                  <button
                    type="button"
                    onClick={() => setApprovalTarget({ lead: selectedLead, type: selectedLead.draftType ?? "roi" })}
                    className="inline-flex items-center justify-center gap-2 rounded-full bg-[#0B6E4F] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0A5F44]"
                  >
                    Revisar {selectedLead.draftType === "roi" ? "propuesta ROI" : selectedLead.draftType === "dossier" ? "dossier" : "borrador"}
                    <ChevronRight className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    disabled={generatingType !== null}
                    onClick={() => handleGenerate("outbound")}
                    className="inline-flex items-center justify-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-800 transition hover:border-emerald-300 disabled:cursor-wait disabled:opacity-60"
                  >
                    <Sparkles className="h-4 w-4" />
                    {generatingType === "outbound" ? "Generando..." : "Generar outbound con IA"}
                  </button>
                  {selectedLead.roiProposal && (
                    <button
                      type="button"
                      disabled={generatingType !== null}
                      onClick={() => handleGenerate("roi")}
                      className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300 disabled:cursor-wait disabled:opacity-60"
                    >
                      {generatingType === "roi" ? "Generando ROI..." : "Regenerar propuesta ROI"}
                    </button>
                  )}
                  {selectedLead.digemidDossier && (
                    <button
                      type="button"
                      disabled={generatingType !== null}
                      onClick={() => handleGenerate("dossier")}
                      className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300 disabled:cursor-wait disabled:opacity-60"
                    >
                      {generatingType === "dossier" ? "Generando dossier..." : "Regenerar dossier"}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setApprovalTarget({ lead: selectedLead, type: "dossier" })}
                    className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300"
                  >
                    Ver dossier DIGEMID
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:border-slate-300"
                  >
                    Posponer contacto
                  </button>
                </div>
              </div>
            </div>
          </div>
        </aside>
      )}

      {approvalTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Aprobación humana</p>
                <h3 className="mt-1 font-serif text-2xl font-bold text-[#071C21]">
                  {approvalTarget.type === "roi" ? "Propuesta ROI" : approvalTarget.type === "dossier" ? "Dossier DIGEMID" : approvalTarget.type === "outbound" ? "Borrador outbound" : "Recordatorio de consumibles"}
                </h3>
              </div>
              <button type="button" onClick={() => setApprovalTarget(null)} className="rounded-full border border-slate-200 px-3 py-1.5 text-sm text-slate-600">
                Cerrar
              </button>
            </div>

            {approvalTarget.type === "roi" && approvalTarget.lead.roiProposal ? (
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm text-slate-600">Equipo sugerido</p>
                  <p className="mt-2 font-semibold text-[#071C21]">{approvalTarget.lead.roiProposal.equipmentModel}</p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <InfoCard label="Costo por sesión" value={formatCurrency(approvalTarget.lead.roiProposal.costPerSession)} />
                  <InfoCard label="Ingreso neto mensual" value={formatCurrency(approvalTarget.lead.roiProposal.estimatedNetMonthly)} />
                  <InfoCard label="Kits mínimo" value={`${approvalTarget.lead.roiProposal.minimumKitsPerMonth} / mes`} />
                  <InfoCard label="Sesiones proyectadas" value={`${approvalTarget.lead.roiProposal.projectedSessionsMonth}`} />
                </div>
              </div>
            ) : approvalTarget.type === "dossier" && approvalTarget.lead.digemidDossier ? (
              <div className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <InfoCard label="Registro" value={approvalTarget.lead.digemidDossier.registryNumber} />
                  <InfoCard label="Clasificación" value={approvalTarget.lead.digemidDossier.classification} />
                  <InfoCard label="Calibración" value={approvalTarget.lead.digemidDossier.calibrationCertificate} />
                  <InfoCard label="Consentimiento" value={approvalTarget.lead.digemidDossier.informedConsentTemplate} />
                </div>
              </div>
            ) : approvalTarget.type === "outbound" && approvalTarget.lead.outboundDraft ? (
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm text-slate-600">Destinatario</p>
                  <p className="mt-2 font-semibold text-[#071C21]">{approvalTarget.lead.outboundDraft.recipientName}</p>
                  <p className="text-sm text-slate-500">{approvalTarget.lead.outboundDraft.recipientRole}</p>
                  <p className="mt-3 text-sm font-medium text-slate-700">Asunto: {approvalTarget.lead.outboundDraft.subject}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                  {approvalTarget.lead.outboundDraft.body}
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                Se preparó un recordatorio de reposición para asegurar continuidad operativa del equipo médico.
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => handleApprove(approvalTarget.lead.id, approvalTarget.type)}
                className="inline-flex items-center gap-2 rounded-full bg-[#0B6E4F] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#0A5F44]"
              >
                <CheckCircle2 className="h-4 w-4" />
                Aprobar y enviar
              </button>
              <button type="button" className="rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700">
                Editar variables
              </button>
              <button type="button" onClick={() => setApprovalTarget(null)} className="rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700">
                Descartar
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
  accent: "emerald" | "amber" | "teal" | "green" | "deep" | "red";
}) {
  const styles = {
    emerald: "bg-emerald-50 text-emerald-800 border border-emerald-100",
    amber: "bg-amber-50 text-amber-800 border border-amber-100",
    teal: "bg-teal-50 text-teal-800 border border-teal-100",
    green: "bg-emerald-100 text-emerald-900 border border-emerald-200",
    deep: "bg-slate-900 text-white border border-slate-800",
    red: "bg-red-50 text-red-700 border border-red-100",
  };

  return (
    <div className={`rounded-2xl p-4 shadow-sm ${styles[accent]}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] opacity-80">{label}</p>
      <div className="mt-3 flex items-end justify-between gap-2">
        <p className="font-serif text-3xl font-bold">{value}</p>
        <TrendingUp className="h-5 w-5 opacity-70" />
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-[#071C21]">{value}</p>
    </div>
  );
}

function FullScreenMessage({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F7F5F0] px-5 text-[#071C21]">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#0F766E]">ConfIA</p>
        <h1 className="mt-3 font-serif text-2xl font-bold">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">{body}</p>
        {action && <div className="mt-6">{action}</div>}
      </section>
    </main>
  );
}

function LoginScreen({ error, onSignIn }: { error: string | null; onSignIn: () => void }) {
  return (
    <FullScreenMessage
      title="Inicia sesión en ConfIA"
      body="Usa tu cuenta autorizada para consultar prospectos y aprobar contenido comercial."
      action={
        <div>
          <button type="button" onClick={onSignIn} className="inline-flex items-center gap-2 rounded-full bg-[#0B6E4F] px-5 py-3 text-sm font-semibold text-white hover:bg-[#0A5F44]">
            Continuar con Google
          </button>
          {error && <p className="mt-4 text-sm text-red-700">{error}</p>}
        </div>
      }
    />
  );
}
