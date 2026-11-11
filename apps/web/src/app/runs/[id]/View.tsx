"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, streamRun } from "@/lib/client";
import { useApi, useAuthGuard } from "@/lib/hooks";
import RunTimeline from "@/components/RunTimeline";
import { Badge, btnGhost, btnPrimary, Card, ErrorState, Loading, Page } from "@/components/ui";

export default function RunView() {
  const ready = useAuthGuard(); const { id: raw } = useParams<{ id: string }>(); const id = decodeURIComponent(raw);
  const [events, setEvents] = useState<any[]>([]); const [status, setStatus] = useState("running");
  const run = useApi<any>(ready ? `/runs/${encodeURIComponent(id)}` : null);
  const trace = useApi<any>(ready ? `/runs/${encodeURIComponent(id)}/trace` : null, [status]);
  const hist = useApi<any[]>(ready ? `/runs/${encodeURIComponent(id)}/history` : null, [status]);
  useEffect(() => {
    if (!ready) return;
    const ac = new AbortController(); let stopped = false;
    streamRun(id, (e) => { setEvents((x) => [...x, e]); if (e.node === "__end__") setStatus(e.status ?? "done"); }, ac.signal).catch(async () => {
      // fallback: poll
      while (!stopped) { try { const r = await api(`/runs/${encodeURIComponent(id)}`); setEvents(r.events.map((x: any) => ({ node: x.node, ...x.data }))); setStatus(r.run.status); if (r.run.status !== "running") break; } catch { /* */ } await new Promise((r) => setTimeout(r, 1500)); }
    });
    return () => { stopped = true; ac.abort(); };
  }, [id, ready]);
  if (!ready) return null;
  if (run.loading && !run.data) return <Loading />;
  if (run.error) return <ErrorState error={run.error} retry={run.reload} />;
  const r = run.data?.run;
  const replay = async (cp: string) => { await api(`/runs/${encodeURIComponent(id)}/replay/${cp}`, { body: {} }); setEvents([]); setStatus("running"); };
  const interesting = (n: string) => !n.startsWith("__") || n === "__end__" || n === "__error__";
  return (
    <Page title={`Agent run — ${r?.title ?? id}`} actions={r?.kind === "bid" ? <Link className={btnPrimary} href={`/studio/${encodeURIComponent(id)}`}>Open proposal studio</Link> : <Link className={btnGhost} href="/messages">Messages</Link>}>
      <div className="flex gap-2"><Badge tone={status === "running" ? "amber" : "indigo"}>{status}</Badge>{status === "running" && <span role="status" className="text-sm text-zinc-500">streaming…</span>}</div>
      <div className="grid gap-4 md:grid-cols-3">
        <Card title="Live node progress" className="md:col-span-2"><RunTimeline events={events.filter((e) => interesting(e.node))} /></Card>
        <div className="space-y-4">
          <Card title="Trace">{trace.data ? <ul className="text-sm"><li>Trace id <code className="text-xs">{trace.data.summary.trace_id}</code></li><li>{trace.data.summary.spans} spans</li><li>tokens in/out {trace.data.summary.tokens_in}/{trace.data.summary.tokens_out}</li><li>cost ${trace.data.summary.usd}</li><li>latency {trace.data.summary.latency_s}s</li></ul> : <Loading />}</Card>
          <Card title="Checkpoint history (replay from any node)">
            <ul className="space-y-1 text-xs">{(hist.data ?? []).map((h) => <li key={h.checkpoint_id} className="flex items-center justify-between gap-2"><span>step {h.step} → {h.next.join(", ") || "end"}</span><button className={btnGhost} onClick={() => replay(h.checkpoint_id)}>Replay</button></li>)}</ul>
          </Card>
        </div>
      </div>
      <Card title="Tool & LLM spans"><div className="max-h-64 overflow-auto"><table className="w-full text-xs"><tbody>{(trace.data?.spans ?? []).map((s: any, i: number) => <tr key={i} className="border-t border-zinc-200 dark:border-zinc-700"><td className="py-0.5 pr-2">{s.kind}</td><td className="pr-2 font-mono">{s.name}</td><td>{s.latency_s}s</td></tr>)}</tbody></table></div></Card>
    </Page>
  );
}
