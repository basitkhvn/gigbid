"use client";
import { useApi, useAuthGuard } from "@/lib/hooks";
import { Card, Empty, ErrorState, Loading, Page } from "@/components/ui";

function Bar({ label, a, b, max }: { label: string; a: number; b: number; max: number }) {
  return (
    <div className="space-y-0.5 text-xs"><div>{label}</div>
      <div className="h-3 rounded bg-zinc-200 dark:bg-zinc-800" title={`sent ${a}`}><div className="h-3 rounded bg-indigo-500" style={{ width: `${(a / Math.max(max, 1)) * 100}%` }} /></div>
      <div className="h-3 rounded bg-zinc-200 dark:bg-zinc-800" title={`replied ${b}`}><div className="h-3 rounded bg-green-500" style={{ width: `${(b / Math.max(max, 1)) * 100}%` }} /></div></div>
  );
}
export default function Analytics() {
  const ready = useAuthGuard();
  const { data, error, loading, reload } = useApi<any>(ready ? "/analytics" : null);
  if (!ready) return null;
  if (loading && !data) return <Loading />;
  if (error) return <ErrorState error={error} retry={reload} />;
  const cats = Object.entries<any>(data.by_category); const max = Math.max(0, ...cats.map(([, c]) => c.sent));
  const t = data.totals;
  return (
    <Page title="Analytics">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[["Proposals sent", t.sent], ["Connects spent", t.connects_spent], ["Avg $ / run", t.avg_usd_per_run], ["p95 latency (s)", t.p95_latency_s]].map(([l, v]) => (
          <Card key={l as string}><p className="text-xs text-zinc-500">{l}</p><p className="text-2xl font-semibold">{v}</p></Card>))}
      </div>
      <Card title="Reply & hire rate by category (blue = sent, green = replied)">
        {cats.length === 0 ? <Empty>No submitted proposals yet.</Empty> : <div className="space-y-3">{cats.map(([k, c]) => (
          <div key={k}><Bar label={`${k} — reply ${c.sent ? Math.round((100 * c.replied) / c.sent) : 0}% · hire ${c.sent ? Math.round((100 * c.hired) / c.sent) : 0}% · ${c.connects} Connects`} a={c.sent} b={c.replied} max={max} /></div>))}</div>}
      </Card>
      <Card title="Top rejection / skip reasons">{data.top_reasons.length === 0 ? <Empty>Nothing yet.</Empty> : <ul className="text-sm">{data.top_reasons.map(([r, n]: [string, number]) => <li key={r}>{n}× {r}</li>)}</ul>}</Card>
    </Page>
  );
}
