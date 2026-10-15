"use client";

import { useEffect, useState } from "react";

import {
  GmailAuthRequiredError,
  fetchLeadDocuments,
  gmailConnectUrl,
  sendOutboundEmail,
} from "@/lib/aiApi";
import type { Lead, LeadDocument, OutboundDraft, OutboundSendResult } from "@/types";

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type OutboundApprovalModalProps = {
  lead: Lead;
  draft: OutboundDraft;
  onClose: () => void;
  onSent: (result: OutboundSendResult) => void;
};

export function OutboundApprovalModal({ lead, draft, onClose, onSent }: OutboundApprovalModalProps) {
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [documents, setDocuments] = useState<LeadDocument[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [authUrl, setAuthUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchLeadDocuments(lead.id)
      .then((files) => {
        if (cancelled) return;
        setDocuments(files);
        // Por defecto, se adjunta la versión más reciente de cada documento.
        const latest = new Map<string, LeadDocument>();
        for (const file of files) {
          if (!latest.has(file.filename) || file.version > (latest.get(file.filename)?.version ?? 0)) {
            latest.set(file.filename, file);
          }
        }
        setSelected(new Set([...latest.values()].map(documentKey)));
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setDocumentsError(error instanceof Error ? error.message : "No se pudieron cargar los documentos.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [lead.id]);

  const toggleDocument = (file: LeadDocument) => {
    setSelected((current) => {
      const next = new Set(current);
      const key = documentKey(file);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const canSend = EMAIL_PATTERN.test(to.trim()) && subject.trim() !== "" && body.trim() !== "" && !isSending;

  const handleSend = async () => {
    setIsSending(true);
    setSendError(null);
    setAuthUrl(null);
    try {
      const result = await sendOutboundEmail({
        lead,
        to: to.trim(),
        subject: subject.trim(),
        body,
        attachments: documents.filter((file) => selected.has(documentKey(file))),
      });
      onSent(result);
    } catch (error: unknown) {
      if (error instanceof GmailAuthRequiredError) {
        setAuthUrl(error.authUrl);
        setSendError("Tu cuenta de Gmail no está vinculada. Vincúlala y vuelve a enviar.");
      } else {
        setSendError(error instanceof Error ? error.message : "No se pudo enviar el correo.");
      }
    } finally {
      setIsSending(false);
    }
  };

  const inputClass = "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-[#071C21]";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-3xl bg-white shadow-2xl">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-6 pb-4 pt-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Revisión antes del envío</p>
            <h3 className="mt-1 font-serif text-2xl font-bold text-[#071C21]">Correo de contacto</h3>
            <p className="mt-1 text-xs text-slate-500">
              Canal sugerido: {draft.suggestedChannel}. Se enviará por Gmail, con tu cuenta.
            </p>
          </div>
          <button type="button" onClick={onClose} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600">
            ✕
          </button>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-5">
          <label className="block text-xs font-semibold text-slate-600">
            Correo del destinatario ({draft.recipientName}, {draft.recipientRole})
            <input
              type="email"
              className={inputClass}
              placeholder="director@clinica.pe"
              value={to}
              onChange={(event) => setTo(event.target.value)}
            />
          </label>

          <label className="block text-xs font-semibold text-slate-600">
            Asunto
            <input className={inputClass} value={subject} onChange={(event) => setSubject(event.target.value)} />
          </label>

          <label className="block text-xs font-semibold text-slate-600">
            Mensaje
            <textarea
              className={`${inputClass} min-h-[180px] leading-relaxed`}
              value={body}
              onChange={(event) => setBody(event.target.value)}
            />
          </label>

          <div>
            <p className="text-xs font-semibold text-slate-600">Adjuntar documentos generados</p>
            {documentsError && <p className="mt-1 text-xs text-red-700">{documentsError}</p>}
            {!documentsError && documents.length === 0 && (
              <p className="mt-1 text-xs text-slate-500">Este prospecto aún no tiene documentos generados.</p>
            )}
            <div className="mt-2 space-y-2">
              {documents.map((file) => (
                <label
                  key={documentKey(file)}
                  className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 text-xs text-[#071C21]"
                >
                  <input type="checkbox" checked={selected.has(documentKey(file))} onChange={() => toggleDocument(file)} />
                  {file.label}
                </label>
              ))}
            </div>
          </div>

          {sendError && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-xs text-red-800">
              <p>{sendError}</p>
              {authUrl !== null && (
                <button
                  type="button"
                  onClick={() => window.open(gmailConnectUrl(), "_blank", "noopener")}
                  className="mt-2 rounded-full border border-red-300 bg-white px-3 py-1.5 font-semibold text-red-800 hover:bg-red-100"
                >
                  Vincular cuenta de Gmail
                </button>
              )}
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-wrap gap-3 border-t border-slate-200 bg-white px-6 py-4">
          <button
            type="button"
            onClick={handleSend}
            disabled={!canSend}
            className="inline-flex items-center gap-2 rounded-full bg-[#0B6E4F] px-5 py-2.5 text-xs font-semibold text-white hover:bg-[#0A5F44] disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isSending ? "Enviando correo..." : "Aprobar y Enviar Correo"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-200 bg-white px-4 py-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Cerrar sin enviar
          </button>
        </div>
      </div>
    </div>
  );
}

function documentKey(file: LeadDocument) {
  return `${file.version}:${file.filename}`;
}
