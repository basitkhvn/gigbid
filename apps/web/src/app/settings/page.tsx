"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/client";
import { useApi, useAuthGuard } from "@/lib/hooks";
import { Badge, btnDanger, btnGhost, btnPrimary, Card, Empty, ErrorState, Field, input, Loading, Page } from "@/components/ui";

export default function Settings() {
  const ready = useAuthGuard();
  const s = useApi<any>(ready ? "/settings" : null);
  const ss = useApi<any[]>(ready ? "/saved-searches" : null);
  const mem = useApi<any>(ready ? "/memory" : null);
  const [f, setF] = useState<any>(null); const [msg, setMsg] = useState("");
  const [q, setQ] = useState(""); const [skill, setSkill] = useState("");
  useEffect(() => { if (s.data) setF(s.data); }, [s.data]);
  if (!ready) return null;
  if (s.error) return <ErrorState error={s.error} retry={s.reload} />;
  if (!f) return <Loading />;
  const save = async () => { await api("/settings", { method: "PUT", body: { rate: +f.rate, floor: +f.floor, autonomy: f.autonomy, weekly_connects_budget: +f.weekly_connects_budget, marketplace: f.marketplace } }); setMsg("Saved"); };
  const addSearch = async () => { await api("/saved-searches", { body: { q, skill, interval_min: 240 } }); setQ(""); setSkill(""); ss.reload(); };
  const forget = async (kind: string, key: string) => { await api(`/memory/${kind}/${encodeURIComponent(key)}`, { method: "DELETE" }); mem.reload(); };
  return (
    <Page title="Settings">
      <Card title="Autonomy & budgets">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Autonomy"><select className={input} value={f.autonomy} onChange={(e) => setF({ ...f, autonomy: e.target.value })}><option value="ask_always">Ask always</option><option value="auto_skip">Auto-skip low-fit jobs (never auto-send)</option></select></Field>
          <Field label="Weekly Connects budget"><input className={input} type="number" value={f.weekly_connects_budget} onChange={(e) => setF({ ...f, weekly_connects_budget: e.target.value })} /></Field>
          <Field label="Hourly rate"><input className={input} type="number" value={f.rate} onChange={(e) => setF({ ...f, rate: e.target.value })} /></Field>
          <Field label="Rate floor"><input className={input} type="number" value={f.floor} onChange={(e) => setF({ ...f, floor: e.target.value })} /></Field>
        </div>
        <button className={`${btnPrimary} mt-3`} onClick={save}>Save settings</button>{msg && <span role="status" className="ml-3 text-sm text-green-600">{msg}</span>}
      </Card>
      <Card title="Connected accounts"><p className="text-sm">GigSim <Badge tone="green">connected</Badge> · Upwork (live): <Badge>{f.marketplace === "upwork_live" ? "selected" : "not connected"}</Badge></p><p className="mt-1 text-xs text-zinc-500">Live mode never submits without your confirmation on Upwork. OAuth tokens are stored encrypted.</p></Card>
      <Card title="Saved searches">
        <div className="flex flex-wrap items-end gap-2"><Field label="Text"><input className={input} value={q} onChange={(e) => setQ(e.target.value)} /></Field><Field label="Skill"><input className={input} value={skill} onChange={(e) => setSkill(e.target.value)} /></Field><button className={btnGhost} onClick={addSearch}>Add</button></div>
        {ss.data?.length === 0 ? <Empty>No saved searches.</Empty> : <ul className="mt-2 text-sm">{ss.data?.map((x) => <li key={x.id} className="flex items-center justify-between border-t py-1 dark:border-zinc-700"><span>{x.q || "(any)"} {x.skill && `· ${x.skill}`} · every {x.interval_min} min</span><button className={btnGhost} onClick={async () => { await api(`/saved-searches/${x.id}`, { method: "DELETE" }); ss.reload(); }}>Delete</button></li>)}</ul>}
      </Card>
      <Card title="What GigBid has learned (memory viewer)">
        {!mem.data ? <Loading /> : (["style", "outcome", "style_candidates"] as const).map((k) => (
          <div key={k} className="mb-3"><h3 className="text-xs font-semibold uppercase text-zinc-500">{k === "style_candidates" ? "Not yet promoted (candidates)" : k + " memory"}</h3>
            {mem.data[k].length === 0 ? <p className="text-sm text-zinc-500">Nothing yet.</p> : <ul className="text-sm">{mem.data[k].map((m: any) => <li key={m.key} className="flex items-center justify-between gap-2 border-t py-1 dark:border-zinc-700"><span>{m.rule ?? m.insight ?? `${m.key} (${m.jobs?.length ?? 0} jobs)`} {m.promoted_by && <span className="text-xs text-zinc-500">— {m.promoted_by}</span>}</span><button className={btnDanger} aria-label={`Delete ${m.key}`} onClick={() => forget(k, m.key)}>Delete</button></li>)}</ul>}</div>))}
      </Card>
    </Page>
  );
}
