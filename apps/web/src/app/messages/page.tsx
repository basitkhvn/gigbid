"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/client";
import { useApi, useAuthGuard } from "@/lib/hooks";
import ApprovalPanel from "@/components/ApprovalPanel";
import { Badge, btnPrimary, Card, Empty, ErrorState, Loading, Page } from "@/components/ui";

export default function Messages() {
  const ready = useAuthGuard();
  const threads = useApi<any[]>(ready ? "/messages" : null);
  const pending = useApi<any[]>(ready ? "/approvals" : null);
  const [busy, setBusy] = useState(""); const [err, setErr] = useState("");
  if (!ready) return null;
  const suggest = async (pid: string) => {
    setBusy(pid); setErr("");
    try {
      const r = await api(`/messages/${pid}/suggest`, { body: {} });
      for (let i = 0; i < 40; i++) { const x = await api(`/runs/${encodeURIComponent(r.run_id)}`); if (x.run.status !== "running") break; await new Promise((s) => setTimeout(s, 500)); }
      await pending.reload(); await threads.reload();
    } catch (e: any) { setErr(`Could not draft a reply: ${e.message}`); } finally { setBusy(""); }
  };
  const msgPending = (pending.data ?? []).filter((p) => p.kind === "conv");
  return (
    <Page title="Messages">
      {err && <p role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">{err}</p>}
      {threads.loading && !threads.data && <Loading />}
      {threads.error && <ErrorState error={threads.error} retry={threads.reload} />}
      {threads.data?.length === 0 && <Empty>No client replies yet. Approved proposals that get a reply appear here.</Empty>}
      <ul className="space-y-3">
        {threads.data?.map((t) => {
          const ap = msgPending.find((p) => p.payload.proposal_id === t.proposal_id);
          return (
            <li key={t.proposal_id}>
              <Card title={`Proposal ${t.proposal_id}`}>
                <ul className="space-y-2 text-sm">{t.messages.map((m: any, i: number) => <li key={i} className={m.from === "client" ? "flex" : "flex justify-end"}><span className={`max-w-[80%] rounded-2xl px-3 py-2 ${m.from === "client" ? "rounded-bl-sm bg-zinc-100 dark:bg-zinc-800" : "rounded-br-sm bg-indigo-600 text-white"}`}><b className="mr-1 text-xs uppercase opacity-70">{m.from}</b>{m.text}</span></li>)}</ul>
                {!ap && <button className={`${btnPrimary} mt-3`} onClick={() => suggest(t.proposal_id)} disabled={busy === t.proposal_id}>{busy === t.proposal_id ? "Drafting reply…" : "Suggest reply"}</button>}
                {ap && <Suggested ap={ap} onDone={() => { pending.reload(); setTimeout(threads.reload, 1000); }} />}
              </Card>
            </li>);
        })}
      </ul>
    </Page>
  );
}

function Suggested({ ap, onDone }: { ap: any; onDone: () => void }) {
  const [text, setText] = useState<string>(ap.payload.reply.reply);
  return (
    <div className="mt-3 space-y-2 rounded border border-indigo-300 p-3 dark:border-indigo-700" data-testid="suggested-reply">
      <p className="text-xs"><Badge tone={ap.payload.intent === "scam_signal" ? "red" : "indigo"}>{ap.payload.intent}</Badge> {ap.payload.risk_flags.map((f: string) => <Badge key={f} tone="red">{f}</Badge>)}</p>
      <textarea aria-label="Suggested reply" className="w-full rounded border p-2 text-sm dark:bg-zinc-900" rows={3} value={text} onChange={(e) => setText(e.target.value)} />
      {ap.payload.slots.length > 0 && <p className="text-xs">Interview slots offered: {ap.payload.slots.join(" · ")}</p>}
      <ApprovalPanel runId={ap.run_id} original={ap.payload.reply.reply} text={text} onDone={onDone} />
    </div>
  );
}
