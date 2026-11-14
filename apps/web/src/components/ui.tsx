"use client";
import React from "react";

export const btn = "inline-flex items-center justify-center rounded-lg px-3.5 py-1.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50";
export const btnPrimary = `${btn} bg-gradient-to-b from-indigo-500 to-indigo-600 text-white shadow-sm shadow-indigo-500/30 hover:from-indigo-600 hover:to-indigo-700`;
export const btnGhost = `${btn} border border-zinc-300 bg-white/60 hover:bg-zinc-100 dark:border-zinc-600 dark:bg-transparent dark:hover:bg-zinc-800`;
export const btnDanger = `${btn} bg-red-600 text-white hover:bg-red-700`;
export const input = "w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 px-3 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500";

export function Card({ title, children, className = "" }: { title?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-zinc-200 bg-white p-4 shadow-sm transition hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900 ${className}`}>
      {title && <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-500">{title}</h2>}
      {children}
    </section>
  );
}

export function Badge({ children, tone = "zinc" }: { children: React.ReactNode; tone?: "zinc" | "red" | "green" | "amber" | "indigo" }) {
  const t = { zinc: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300", red: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
    green: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300", amber: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
    indigo: "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300" }[tone];
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ring-black/5 dark:ring-white/10 ${t}`}>{children}</span>;
}

export const actionTone = (a: string) => (a === "bid" ? "green" : a === "watch" ? "amber" : "zinc") as "green" | "amber" | "zinc";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <p role="status" className="flex items-center justify-center gap-2 py-8 text-sm text-zinc-500"><span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" aria-hidden="true" />{label}</p>;
}
export function ErrorState({ error, retry }: { error: { status?: number; message: string }; retry?: () => void }) {
  const down = error.status === 503;
  return (
    <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
      <p className="font-medium">{down ? "Marketplace unavailable" : "Something went wrong"}</p>
      <p>{down ? "The marketplace server cannot be reached. Work is queued and will resume automatically." : error.message}</p>
      {retry && <button className={`${btnGhost} mt-2`} onClick={retry}>Retry</button>}
    </div>
  );
}
export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-md border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-500 dark:border-zinc-700">{children}</p>;
}
export function Page({ title, children, actions }: { title: string; children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3"><h1 className="text-2xl font-semibold tracking-tight">{title}</h1>{actions}</div>
      {children}
    </div>
  );
}
export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm"><span className="mb-1 block font-medium">{label}</span>{children}</label>;
}

export function FitBar({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const color = value >= 0.7 ? "bg-green-500" : value >= 0.4 ? "bg-amber-500" : "bg-zinc-400";
  return <span className="inline-flex items-center gap-2 text-xs text-zinc-500" title={`fit ${value.toFixed(2)}`}><span className="h-1.5 w-16 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700"><span className={`block h-full ${color}`} style={{ width: `${pct}%` }} /></span>{pct}% match</span>;
}
