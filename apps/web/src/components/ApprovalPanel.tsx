"use client";
import { useState } from "react";
import { api } from "@/lib/client";
import { btnDanger, btnGhost, btnPrimary, input } from "./ui";

/** Approve / edit / reject. Posts to /approvals/{run_id}, which resumes the interrupted LangGraph thread. */
export default function ApprovalPanel({ runId, original, text, onDone, disabled, bid }: { runId: string; original: string; text: string; onDone: () => void; disabled?: boolean; bid?: number }) {
  const [reason, setReason] = useState(""); const [rejecting, setRejecting] = useState(false);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const [price, setPrice] = useState<string>(bid != null ? String(bid) : "");
  const priceNum = Number(price);
  const priceOk = price === "" || (Number.isFinite(priceNum) && priceNum > 0 && priceNum <= 100000);
  const priceChanged = bid != null && price !== "" && priceOk && priceNum !== bid;
  const changed = text.trim() !== original.trim();
  async function send(body: { action: string; text?: string; reason?: string; bid?: number }) {
    if (body.action !== "reject" && priceChanged) body = { ...body, bid: priceNum };
    setBusy(true); setErr("");
    try { await api(`/approvals/${encodeURIComponent(runId)}`, { body }); onDone(); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-2" aria-label="Approval">
      {bid != null && (
        <label className="block text-sm"><span className="mb-1 block">Bid price (USD) <span className="text-xs text-zinc-500">AI suggested ${bid}</span></span>
          <input type="number" min={1} max={100000} step="1" className={input} value={price} onChange={(e) => setPrice(e.target.value)} aria-label="Bid price" aria-invalid={!priceOk} />
          {!priceOk && <span role="alert" className="text-xs text-red-600">Enter a price between 1 and 100000.</span>}</label>
      )}
      <div className="flex flex-wrap gap-2">
        {!changed && <button className={btnPrimary} disabled={busy || disabled || !priceOk} onClick={() => send({ action: "approve" })}>Approve &amp; send</button>}
        {changed && <button className={btnPrimary} disabled={busy || disabled || !priceOk} onClick={() => send({ action: "edit", text })}>Save edit &amp; approve</button>}
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
