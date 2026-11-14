// Thin fetch wrapper over the OpenAPI-generated types in ./api/schema.d.ts (generated; do not hand-edit).
import type { components } from "./api/schema";

export type Creds = components["schemas"]["Creds"];
export type TokenOut = components["schemas"]["TokenOut"];
export type Decision = components["schemas"]["Decision"];
export type SettingsIn = components["schemas"]["SettingsIn"];
export type ItemIn = components["schemas"]["ItemIn"];

export const API = process.env.NEXT_PUBLIC_API_URL ?? "";

export function getToken(): string | null {
  try { return localStorage.getItem("gigbid_token"); } catch { return null; }
}
export function setSession(t: TokenOut | null) {
  try {
    if (t) { localStorage.setItem("gigbid_token", t.token); localStorage.setItem("gigbid_user", JSON.stringify(t)); }
    else { localStorage.removeItem("gigbid_token"); localStorage.removeItem("gigbid_user"); }
  } catch { /* storage unavailable */ }
}
export function getUser(): TokenOut | null {
  try { const s = localStorage.getItem("gigbid_user"); return s ? JSON.parse(s) : null; } catch { return null; }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const tok = getToken();
  const r = await fetch(API + path, {
    cache: "no-store", // never replay a cached ngrok interstitial/HTML page as an API answer
    method: opts.method ?? (opts.body !== undefined ? "POST" : "GET"),
    headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "1", ...(tok ? { Authorization: `Bearer ${tok}` } : {}) },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j); } catch { /* */ }
    // Stale/invalid session (e.g. server restarted with a new secret): drop it and go to login instead of showing errors.
    if (r.status === 401 && tok && typeof window !== "undefined" && !path.startsWith("/auth/")) {
      setSession(null);
      if (!window.location.pathname.startsWith("/login")) window.location.replace("/login/");
    }
    throw new ApiError(r.status, msg);
  }
  return r.json();
}

/** SSE over fetch() so the Authorization header can be sent (EventSource cannot). */
export async function streamRun(runId: string, onEvent: (e: any) => void, signal: AbortSignal) {
  const tok = getToken();
  const r = await fetch(`${API}/runs/${encodeURIComponent(runId)}/stream`, { cache: "no-store", headers: { "ngrok-skip-browser-warning": "1", ...(tok ? { Authorization: `Bearer ${tok}` } : {}) }, signal });
  if (!r.ok || !r.body) throw new ApiError(r.status, "stream failed");
  const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.search(/\r?\n\r?\n/)) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i).replace(/^\r?\n\r?\n/, "");
      const data = block.split(/\r?\n/).filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim()).join("");
      if (data) { try { onEvent(JSON.parse(data)); } catch { /* ignore */ } }
    }
  }
}
