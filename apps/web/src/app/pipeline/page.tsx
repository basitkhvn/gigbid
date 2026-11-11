"use client";
import Link from "next/link";
import { useApi, useAuthGuard, usePoll } from "@/lib/hooks";
import { Badge, Card, Empty, ErrorState, Loading, Page } from "@/components/ui";

export default function Pipeline() {
  const ready = useAuthGuard();
  const { data, error, loading, reload } = useApi<any>(ready ? "/pipeline" : null);
  usePoll(reload, 8000);
  if (!ready) return null;
  return (
    <Page title="Pipeline">
      {loading && !data && <Loading />}
      {error && <ErrorState error={error} retry={reload} />}
      {data?.unavailable && <p role="alert" className="rounded bg-amber-100 p-2 text-sm text-amber-900">Marketplace unavailable — showing local drafts only.</p>}
      {data && (
        <div className="flex gap-3 overflow-x-auto pb-2">
          {Object.entries<any[]>(data.columns).map(([col, cards]) => (
            <section key={col} aria-label={col} className="w-56 shrink-0 rounded-lg bg-zinc-100 p-2 dark:bg-zinc-900">
              <h2 className="mb-2 flex items-center justify-between text-xs font-semibold uppercase text-zinc-500">{col}<Badge>{cards.length}</Badge></h2>
              <ul className="space-y-2">{cards.length === 0 ? <li className="text-xs text-zinc-400">empty</li> : cards.map((c) => (
                <li key={c.id}><Card className="!p-2 text-sm">{c.run_id ? <Link className="text-indigo-700 hover:underline dark:text-indigo-300" href={`/studio/${encodeURIComponent(c.run_id)}`}>{c.title}</Link> : c.title}
                  {c.bid != null && <p className="text-xs text-zinc-500">${c.bid} · {c.connects} Connects</p>}</Card></li>))}</ul>
            </section>))}
        </div>
      )}
    </Page>
  );
}
