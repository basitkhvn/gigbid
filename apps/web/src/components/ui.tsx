"use client";
import React from "react";

export const btn = "inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:opacity-50";
export const btnPrimary = `${btn} bg-indigo-600 text-white hover:bg-indigo-700`;
export const btnGhost = `${btn} border border-zinc-300 dark:border-zinc-600 hover:bg-zinc-100 dark:hover:bg-zinc-800`;
export const btnDanger = `${btn} bg-red-600 text-white hover:bg-red-700`;
export const input = "w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 px-3 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500";

export function Card({ title, children, className = "" }: { title?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-4 ${className}`}>
      {title && <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-500">{title}</h2>}
      {children}
    </section>
  );
}

export function Badge({ children, tone = "zinc" }: { children: React.ReactNode; tone?: "zinc" | "red" | "green" | "amber" | "indigo" }) {
  const t = { zinc: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300", red: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
    green: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300", amber: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
    indigo: "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300" }[tone];
  return <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${t}`}>{children}</span>;
}

export const actionTone = (a: string) => (a === "bid" ? "green" : a === "watch" ? "amber" : "zinc") as "green" | "amber" | "zinc";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <p role="status" className="py-6 text-center text-sm text-zinc-500">{label}</p>;
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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2"><h1 className="text-xl font-semibold">{title}</h1>{actions}</div>
      {children}
    </div>
  );
}
export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm"><span className="mb-1 block font-medium">{label}</span>{children}</label>;
}
