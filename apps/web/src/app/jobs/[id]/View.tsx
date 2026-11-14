"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/client";
import { useApi, useAuthGuard, useRouteId } from "@/lib/hooks";
import { actionTone, Badge, btnPrimary, Card, ErrorState, Loading, Page } from "@/components/ui";

export default function JobDetail() {
  const ready = useAuthGuard(); const id = useRouteId(); const router = useRouter();
  const { data, error, loading, reload } = useApi<any>(ready ? `/jobs/${id}` : null);
  const [busy, setBusy] = useState(false);
  if (!ready) return null;
  if (loading && !data) return <Loading />;
  if (error) return <ErrorState error={error} retry={reload} />;
  if (!data) return null;
  const { job, client, triage: t, run } = data;
  const draft = async () => { setBusy(true); try { const r = await api(`/jobs/${id}/draft`, { body: {} }); router.push(`/runs/${encodeURIComponent(r.run_id)}`); } finally { setBusy(false); } };
  return (
    <Page title={job.title} actions={t.action === "bid" ? (run ? <Link className={btnPrimary} href={`/runs/${encodeURIComponent(run.id)}`}>Open run</Link> : <button className={btnPrimary} onClick={draft} disabled={busy}>Draft proposal</button>) : undefined}>
      <div className="flex flex-wrap gap-1"><Badge tone={actionTone(t.action)}>{t.action}</Badge><Badge tone="indigo">fit {t.fit}</Badge><Badge tone={t.risk >= 0.5 ? "red" : "zinc"}>risk {t.risk}</Badge>{t.flags.map((f: string) => <Badge key={f} tone="red">{f}</Badge>)}</div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Job post (untrusted data)"><p className="whitespace-pre-wrap text-sm">{job.description}</p></Card>
        <Card title="JobSpec">
          <dl className="space-y-1 text-sm">
            <div><dt className="inline font-medium">Required skills: </dt><dd className="inline">{t.job_spec.required_skills.join(", ")}</dd></div>
            <div><dt className="inline font-medium">Budget: </dt><dd className="inline">${t.job_spec.budget_max ?? "n/a"}</dd></div>
            <div><dt className="inline font-medium">Screening: </dt><dd className="inline">{t.job_spec.screening_questions.join(" / ") || "none"}</dd></div>
          </dl>
        </Card>
        <Card title="Risk report"><p className="text-sm">{t.risk_report.explanation}</p><p className="text-xs text-zinc-500">client quality {t.risk_report.client_quality}{t.risk_report.injection_detected && " · injected instruction detected and removed"}</p></Card>
        <Card title="Client history">{client ? <ul className="text-sm"><li>Total spent ${client.total_spent}</li><li>Hire rate {client.hire_rate}</li><li>Rating {client.avg_rating}</li><li>Payment verified: {String(client.payment_verified)}</li></ul> : <p className="text-sm text-zinc-500">Unavailable.</p>}</Card>
      </div>
      <Card title="Requirement → evidence matrix">
        <div className="overflow-x-auto">
          <table className="w-full text-sm"><thead><tr className="text-left text-xs uppercase text-zinc-500"><th className="py-1">Requirement</th><th>Supported</th><th>Evidence</th><th>Score</th></tr></thead>
            <tbody>{t.matches.map((m: any) => (
              <tr key={m.requirement} className="border-t border-zinc-200 dark:border-zinc-700"><td className="py-1">{m.requirement}</td>
                <td>{m.supported ? <Badge tone="green">yes</Badge> : <Badge tone="red">no evidence</Badge>}</td>
                <td className="font-mono text-xs">{m.evidence_ids.join(", ") || "—"}</td><td>{m.best_score.toFixed(1)}</td></tr>))}</tbody></table>
        </div>
      </Card>
      <Card title="Bid-or-skip reasoning"><ul className="list-disc pl-5 text-sm">{t.reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul></Card>
      {t.price && <Card title="Price rationale"><p className="text-sm">Suggested bid <b>${t.price.bid}</b> (range ${t.price.low}–${t.price.high}); Connects {t.price.connects_cost}; worth it: {String(t.price.worth_connects)}.</p><p className="mt-1 text-xs text-zinc-500">{t.price.rationale}</p></Card>}
    </Page>
  );
}
