"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/client";
import { useApi, useAuthGuard } from "@/lib/hooks";
import { actionTone, Badge, btnGhost, btnPrimary, Card, Empty, ErrorState, input, Loading, Page } from "@/components/ui";

export default function Inbox() {
  const ready = useAuthGuard(); const router = useRouter();
  const [action, setAction] = useState(""); const [minFit, setMinFit] = useState(0);
  const { data, error, loading, reload } = useApi<any>(ready ? `/jobs?limit=6&action=${action}&min_fit=${minFit}` : null);
  const [busy, setBusy] = useState("");
  if (!ready) return null;
  const draft = async (id: string) => { setBusy(id); try { const r = await api(`/jobs/${id}/draft`, { body: {} }); router.push(`/runs/${encodeURIComponent(r.run_id)}`); } catch (e: any) { alert(e.message); } finally { setBusy(""); } };
  const skip = async (id: string) => { await api(`/jobs/${id}/skip`, { body: {} }); reload(); };
  return (
    <Page title="Job inbox" actions={
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-sm">Action <select aria-label="Filter by action" className={input} value={action} onChange={(e) => setAction(e.target.value)}><option value="">all</option><option value="bid">bid</option><option value="watch">watch</option><option value="skip">skip</option></select></label>
        <label className="text-sm">Min fit {minFit.toFixed(1)} <input aria-label="Minimum fit" type="range" min={0} max={1} step={0.1} value={minFit} onChange={(e) => setMinFit(+e.target.value)} /></label>
      </div>}>
      {loading && !data && <Loading label="Triaging jobs…" />}
      {error && <ErrorState error={error} retry={reload} />}
      {data && data.jobs.length === 0 && <Empty>No jobs match these filters.</Empty>}
      <ul className="space-y-3">
        {data?.jobs.map((j: any) => (
          <li key={j.job_id}>
            <Card>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <Link href={`/jobs/${encodeURIComponent(j.job_id)}`} className="font-medium text-indigo-700 hover:underline dark:text-indigo-300">{j.title}</Link>
                  <p className="text-xs text-zinc-500">{j.job_id} · {j.skills.join(", ")}</p>
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  <Badge tone={actionTone(j.action)}>{j.action}</Badge>
                  <Badge tone="indigo">fit {j.fit.toFixed(2)}</Badge>
                  {j.flags.map((f: string) => <Badge key={f} tone="red">{f}</Badge>)}
                  {j.run && <Badge>{j.run.status}</Badge>}
                </div>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
                <span>Budget ${j.budget.max}</span>
                <span>Connects {j.connects_cost}</span>
                {j.price && <span>Suggested bid <b>${j.price.bid}</b>{!j.price.worth_connects && " (not worth Connects)"}</span>}
                <span className="flex-1" />
                {j.run?.status === "awaiting_approval" || j.run?.status === "submitted"
                  ? <Link className={btnGhost} href={`/studio/${encodeURIComponent(j.run.id)}`}>Open studio</Link>
                  : j.action === "bid" && <button className={btnPrimary} disabled={busy === j.job_id} onClick={() => draft(j.job_id)}>Draft proposal</button>}
                <button className={btnGhost} onClick={() => skip(j.job_id)}>Skip</button>
              </div>
            </Card>
          </li>
        ))}
      </ul>
    </Page>
  );
}
