"use client";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, getToken } from "./client";

export function useAuthGuard() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  useEffect(() => { if (!getToken()) router.replace("/login"); else setReady(true); }, [router]);
  return ready;
}

export function useApi<T = any>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(!!path);
  const reload = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    try { setData(await api<T>(path)); setError(null); } catch (e) { setError(e as ApiError); } finally { setLoading(false); }
  }, [path]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, [reload, ...deps]);
  // the first render after `path` flips from null to a URL has data=null and loading=false: report it as loading so pages never dereference null data
  return { data, error, loading: loading || (!!path && data === null && error === null), reload, setData };
}

export function usePoll(fn: () => void, ms: number) {
  const ref = useRef(fn); ref.current = fn;
  useEffect(() => { const t = setInterval(() => ref.current(), ms); return () => clearInterval(t); }, [ms]);
}

/** Real id from the browser URL (/jobs/<id>/, /studio/<id>/, /runs/<id>/). Needed because in the static export a fresh page load only knows the prerendered placeholder param "_". */
export function useRouteId(): string {
  const path = usePathname();
  const seg = (path || "").split("/").filter(Boolean)[1] || "";
  try { return decodeURIComponent(seg); } catch { return seg; }
}
