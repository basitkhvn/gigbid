"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, getUser } from "@/lib/client";
import { useAuthGuard } from "@/lib/hooks";
import { btnGhost, btnPrimary, Card, Field, input, Page } from "@/components/ui";

export default function Onboarding() {
  const ready = useAuthGuard(); const router = useRouter();
  const [connected, setConnected] = useState(false);
  const [rate, setRate] = useState(45); const [floor, setFloor] = useState(30); const [budget, setBudget] = useState(120);
  const [title, setTitle] = useState(""); const [text, setText] = useState(""); const [uploaded, setUploaded] = useState("");
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  if (!ready) return null;
  const connect = async () => { try { await api("/auth/connect/gigsim", { body: {} }); setConnected(true); } catch (e: any) { setErr(e.message); } };
  const upload = async () => { try { const r = await api("/portfolio/items", { body: { title, text, type: "case_study", skills: [] } }); setUploaded(r.id); setTitle(""); setText(""); } catch (e: any) { setErr(e.message); } };
  const save = async () => {
    setErr("");
    try { await api("/settings", { method: "PUT", body: { rate, floor, weekly_connects_budget: budget, marketplace: "gigsim" } }); setMsg("Settings saved"); router.push("/"); }
    catch (e: any) { setErr(e.message); }
  };
  return (
    <Page title="Welcome to GigBid">
      <p className="text-sm text-zinc-600 dark:text-zinc-400">Persona: <b>{getUser()?.persona}</b> (portfolio corpus preloaded). Three quick steps.</p>
      <Card title="1. Connect a marketplace">
        <button className={btnGhost} onClick={connect}>Connect GigSim (simulator)</button>
        {connected && <span className="ml-3 text-sm text-green-600" role="status">GigSim connected</span>}
        <p className="mt-2 text-xs text-zinc-500">Live Upwork (OAuth) is configured in Settings; GigSim is the default for development.</p>
      </Card>
      <Card title="2. Add portfolio material (optional)">
        <div className="space-y-2">
          <Field label="Title"><input className={input} value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
          <Field label="Case study text (min 20 chars)"><textarea className={input} rows={4} value={text} onChange={(e) => setText(e.target.value)} /></Field>
          <button className={btnGhost} onClick={upload} disabled={title.length < 2 || text.length < 20}>Upload &amp; index</button>
          {uploaded && <span className="ml-3 text-sm text-green-600" role="status">Indexed {uploaded}</span>}
        </div>
      </Card>
      <Card title="3. Rates and budget">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Hourly rate (USD)"><input className={input} type="number" value={rate} onChange={(e) => setRate(+e.target.value)} /></Field>
          <Field label="Rate floor (USD/h)"><input className={input} type="number" value={floor} onChange={(e) => setFloor(+e.target.value)} /></Field>
          <Field label="Weekly Connects budget"><input className={input} type="number" value={budget} onChange={(e) => setBudget(+e.target.value)} /></Field>
        </div>
        <button className={`${btnPrimary} mt-3`} onClick={save}>Save and finish</button>
        {msg && <span className="ml-3 text-sm text-green-600" role="status">{msg}</span>}
      </Card>
      {err && <p role="alert" className="text-sm text-red-600">{err}</p>}
    </Page>
  );
}
