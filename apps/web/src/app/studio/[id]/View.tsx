"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/client";
import { useApi, useAuthGuard, usePoll, useRouteId } from "@/lib/hooks";
import ApprovalPanel from "@/components/ApprovalPanel";
import EvidenceHover from "@/components/EvidenceHover";
import { Badge, btnGhost, Card, ErrorState, input, Loading, Page } from "@/components/ui";

export default function Studio() {
  const ready = useAuthGuard(); const id = useRouteId();
  const { data, error, loading, reload } = useApi<any>(ready ? `/proposals/${encodeURIComponent(id)}` : null);
  const [text, setText] = useState(""); const [orig, setOrig] = useState("");
  // keep the editor in sync with the server draft (e.g. after an approved edit was sanitised), but never clobber unsaved typing while pending
  const serverText: string | undefined = data?.draft?.cover_letter;
  useEffect(() => {
    if (serverText !== undefined && serverText !== orig && (text === orig || !data?.pending)) { setText(serverText); setOrig(serverText); }
  }, [serverText, orig, text, data?.pending]);
  usePoll(() => { if (data && !data.pending && data.run.status === "running") reload(); }, 1500);
  if (!ready) return null;
  if (loading && !data) return <Loading />;
  if (error) return <ErrorState error={error} retry={reload} />;
  if (!data) return null;
  const evidence = data.evidence ?? [];
  const paras = text.split(/\n\n+/);
  const regen = async (i: number) => {
    const r = await api(`/proposals/${encodeURIComponent(id)}/regenerate`, { body: { paragraph: paras[i] } });
    const p = [...paras]; p[i] = r.paragraph; setText(p.join("\n\n"));
  };
  const status = data.run.status;
  const critique = (data.critiques ?? []).slice(-1)[0];
  return (
    <Page title={`Proposal studio — ${data.run.title}`} actions={<Link className={btnGhost} href={`/runs/${encodeURIComponent(id)}`}>Agent run</Link>}>
      <div className="flex flex-wrap items-center gap-2"><Badge tone={status === "submitted" ? "green" : "indigo"}>{status}</Badge>
        {data.claim_stats && <Badge>claims unsupported {data.claim_stats.unsupported_before} → {data.claim_stats.unsupported_after} of {data.claim_stats.claims_before}</Badge>}</div>
      {status === "submitted" && <p role="status" data-testid="submitted" className="rounded bg-green-100 p-3 text-sm text-green-900 dark:bg-green-950 dark:text-green-200">Submitted — {data.submission?.connects_spent} Connects spent (proposal {data.submission?.proposal_id}).</p>}
      {status === "rejected" && <p role="status" className="rounded bg-zinc-200 p-3 text-sm dark:bg-zinc-800">Rejected: {data.approval?.reason}</p>}
      {status === "blocked_by_compliance" && <p role="alert" className="rounded bg-red-100 p-3 text-sm text-red-900">Blocked by Compliance: {data.compliance?.reason}</p>}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card title="Draft (claims show their evidence on hover/focus)">
            <div data-testid="draft-preview" className="space-y-3 text-sm leading-relaxed">
              {paras.map((p, i) => (
                <div key={i} className="group"><EvidenceHover text={p} evidence={evidence} />
                  <button className="ml-2 text-xs text-indigo-600 underline opacity-70 focus:opacity-100 group-hover:opacity-100" onClick={() => regen(i)}>Regenerate paragraph</button></div>))}
            </div>
          </Card>
          <Card title="Edit">
            <label className="block text-sm"><span className="sr-only">Cover letter</span>
              <textarea aria-label="Cover letter editor" className={input} rows={9} value={text} onChange={(e) => setText(e.target.value)} disabled={!data.pending} /></label>
            <h3 className="mt-3 text-xs font-semibold uppercase text-zinc-500">Claims</h3>
            <ul className="space-y-1 text-xs">{(data.draft?.claims ?? []).filter((c: any) => c.verdict !== "not_a_claim").map((c: any, i: number) => (
              <li key={i}><Badge tone={c.verdict === "supported" ? "green" : "red"}>{c.verdict}</Badge> {c.text}</li>))}</ul>
          </Card>
          {data.pending && <Card title="Decision"><ApprovalPanel runId={id} original={orig} text={text} bid={data.price_quote?.bid} onDone={() => { setTimeout(reload, 800); }} /></Card>}
        </div>
        <div className="space-y-4">
          <Card title="Critic">{critique ? <><p className="text-sm">{critique.ok ? "No serious issues." : critique.issues.join("; ")}</p><p className="text-xs text-zinc-500">score {critique.score} · {(data.critiques ?? []).length} pass(es)</p></> : <p className="text-sm text-zinc-500">—</p>}</Card>
          <Card title="Compliance">{data.compliance ? <><Badge tone={data.compliance.passed ? "green" : "red"}>{data.compliance.passed ? "passed" : "blocked"}</Badge>{data.compliance.violations.length > 0 && <ul className="mt-1 list-disc pl-4 text-xs">{data.compliance.violations.map((v: string, i: number) => <li key={i}>{v}</li>)}</ul>}</> : "—"}</Card>
          <Card title="Dry-run preview (what will be sent)">
            {data.preview ? <><p className="text-sm">Bid ${data.preview.would_send?.bid} · Connects cost <b>{data.preview.connects_cost}</b> (balance {data.preview.connects_balance})</p>
              {data.preview.warnings?.map((w: string, i: number) => <p key={i} className="text-xs text-red-600">{w}</p>)}</> : <p className="text-sm text-zinc-500">Not available.</p>}
          </Card>
          <Card title="Price rationale"><p className="text-xs">{data.price_quote?.rationale}</p></Card>
          <Card title="Evidence"><ol className="space-y-1 text-xs">{evidence.map((e: any, i: number) => <li key={e.id}><b>[E{i + 1}]</b> {e.title} <span className="text-zinc-500">({e.type})</span></li>)}</ol></Card>
        </div>
      </div>
    </Page>
  );
}
