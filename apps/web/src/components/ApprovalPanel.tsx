"use client";
import { useState } from "react";
import { api } from "@/lib/client";
import { btnDanger, btnGhost, btnPrimary, input } from "./ui";

/** Approve / edit / reject. Posts to /approvals/{run_id}, which resumes the interrupted LangGraph thread. */
export default function ApprovalPanel({ runId, original, text, onDone, disabled }: { runId: string; original: string; text: string; onDone: () => void; disabled?: boolean }) {
  const [reason, setReason] = useState(""); const [rejecting, setRejecting] = useState(false);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const changed = text.trim() !== original.trim();
  async function send(body: { action: string; text?: string; reason?: string }) {
    setBusy(true); setErr("");
    try { await api(`/approvals/${encodeURIComponent(runId)}`, { body }); onDone(); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-2" aria-label="Approval">
      <div className="flex flex-wrap gap-2">
        {!changed && <button className={btnPrimary} disabled={busy || disabled} onClick={() => send({ action: "approve" })}>Approve &amp; send</button>}
        {changed && <button className={btnPrimary} disabled={busy || disabled} onClick={() => send({ action: "edit", text })}>Save edit &amp; approve</button>}
        <button className={btnGhost} disabled={busy} onClick={() => setRejecting(!rejecting)} aria-expanded={rejecting}>Reject…</button>
      </div>
      {rejecting && (
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex-1 text-sm"><span className="mb-1 block">Reason (required)</span>
            <input className={input} value={reason} onChange={(e) => setReason(e.target.value)} /></label>
          <button className={btnDanger} disabled={busy || !reason.trim()} onClick={() => send({ action: "reject", reason })}>Confirm reject</button>
        </div>
      )}
      {err && <p role="alert" className="text-sm text-red-600">{err}</p>}
      <p className="text-xs text-zinc-500">Nothing is sent until you approve. Edits are diffed, re-checked by Compliance and fed to style memory.</p>
    </div>
  );
}
