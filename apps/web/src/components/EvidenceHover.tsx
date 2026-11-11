"use client";
import React, { useState } from "react";

export type Evidence = { id: string; type: string; title?: string; text?: string; snippet?: string; outcome?: string | null; date?: string | null; industry?: string | null };

/** Renders text; every [E#] citation is a focusable control that reveals the evidence item behind the claim (hover or focus). */
export default function EvidenceHover({ text, evidence, verdicts }: { text: string; evidence: Evidence[]; verdicts?: Record<string, string> }) {
  const parts = text.split(/(\[E\d+\])/g);
  return (
    <span>
      {parts.map((p, i) => {
        const m = p.match(/^\[E(\d+)\]$/);
        if (!m) return <React.Fragment key={i}>{p}</React.Fragment>;
        const ev = evidence[+m[1] - 1];
        return <Cite key={i} label={p} ev={ev} />;
      })}
    </span>
  );
}

function Cite({ label, ev }: { label: string; ev?: Evidence }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-block" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" aria-label={`Evidence ${label}`} aria-expanded={open} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}
        className="mx-0.5 rounded bg-indigo-100 px-1 text-xs font-semibold text-indigo-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 dark:bg-indigo-950 dark:text-indigo-200">{label}</button>
      {open && (
        <span role="tooltip" data-testid="evidence-tooltip" className="absolute left-0 top-full z-20 mt-1 w-72 rounded-md border border-zinc-300 bg-white p-2 text-xs text-zinc-800 shadow-lg dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100">
          {ev ? (<><b>{ev.title ?? ev.id}</b> <span className="text-zinc-500">({ev.type}{ev.industry ? `, ${ev.industry}` : ""})</span><br />{(ev.text ?? ev.snippet ?? "").slice(0, 320)}</>) : "No evidence item found for this citation."}
        </span>
      )}
    </span>
  );
}
