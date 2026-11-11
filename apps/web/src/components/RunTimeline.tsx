"use client";
const ICON: Record<string, string> = { __end__: "■", __error__: "!", __resume__: "▶" };
export default function RunTimeline({ events }: { events: any[] }) {
  if (!events.length) return <p className="text-sm text-zinc-500">Waiting for the first node…</p>;
  return (
    <ol aria-label="Run timeline" className="space-y-1">
      {events.map((e, i) => (
        <li key={i} className="flex gap-2 text-sm" data-testid="timeline-node">
          <span className="w-5 text-center text-indigo-600">{ICON[e.node] ?? "●"}</span>
          <span className="w-36 shrink-0 font-mono text-xs">{e.node}</span>
          <span className="text-zinc-600 dark:text-zinc-400">{e.summary || e.status || (e.keys ? e.keys.join(", ") : "") || e.error || ""}</span>
        </li>
      ))}
    </ol>
  );
}
