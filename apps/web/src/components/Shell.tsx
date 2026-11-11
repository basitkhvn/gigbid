"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken, getUser, setSession } from "@/lib/client";
import { usePoll } from "@/lib/hooks";
import { btnGhost } from "./ui";

const NAV = [["/", "Inbox"], ["/pipeline", "Pipeline"], ["/messages", "Messages"], ["/analytics", "Analytics"], ["/settings", "Settings"]];

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname(); const router = useRouter();
  const [down, setDown] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => { setAuthed(!!getToken()); }, [path]);
  const check = async () => {
    if (!getToken()) return;
    try { const h = await api("/health/tools"); setDown(h.marketplace?.ok === false); } catch { /* api unreachable */ }
  };
  useEffect(() => { check(); }, [path]);
  usePoll(check, 5000);
  const toggle = async () => { const h = await api(`/admin/chaos/marketplace/${down ? "up" : "down"}`, { method: "POST", body: {} }); setDown(h.marketplace?.ok === false); };
  const logout = () => { setSession(null); router.replace("/login"); };
  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:bg-white focus:p-2 focus:text-black">Skip to content</a>
      <header className="border-b border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2">
          <Link href="/" className="font-bold text-indigo-600">GigBid</Link>
          {authed && (
            <>
              <button className="ml-auto md:hidden rounded border px-2 py-1 text-sm" aria-expanded={open} aria-controls="nav" onClick={() => setOpen(!open)}>Menu</button>
              <nav id="nav" aria-label="Main" className={`${open ? "flex" : "hidden"} absolute left-0 right-0 top-12 z-10 flex-col gap-1 border-b bg-white p-3 dark:bg-zinc-900 md:static md:ml-2 md:flex md:flex-1 md:flex-row md:items-center md:border-0 md:p-0`}>
                {NAV.map(([h, l]) => (
                  <Link key={h} href={h} onClick={() => setOpen(false)} aria-current={path === h ? "page" : undefined}
                    className={`rounded px-2 py-1 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${path === h ? "bg-indigo-100 font-semibold text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200" : "hover:bg-zinc-100 dark:hover:bg-zinc-800"}`}>{l}</Link>
                ))}
                <span className="flex-1" />
                <button className={btnGhost} onClick={toggle} data-testid="chaos-toggle">{down ? "Restore marketplace" : "Simulate marketplace outage"}</button>
                <span className="text-xs text-zinc-500">{getUser()?.email}</span>
                <button className={btnGhost} onClick={logout}>Sign out</button>
              </nav>
            </>
          )}
        </div>
      </header>
      {down && (
        <div role="alert" data-testid="degraded-banner" className="bg-amber-500 px-4 py-2 text-center text-sm font-medium text-black">
          Marketplace unavailable — work is queued and will resume
        </div>
      )}
      <main id="main" className="mx-auto max-w-6xl px-4 py-4">{children}</main>
    </>
  );
}
