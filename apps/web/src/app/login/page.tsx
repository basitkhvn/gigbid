"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setSession, TokenOut } from "@/lib/client";
import { btnPrimary, Card, Field, input } from "@/components/ui";

export default function Login() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [persona, setPersona] = useState("ml");
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr("");
    try {
      const t = await api<TokenOut>(`/auth/${mode}`, { body: { email, password, persona } });
      setSession(t); router.replace(mode === "register" ? "/onboarding" : "/");
    } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  }
  return (
    <div className="mx-auto max-w-sm pt-8">
      <Card title={mode === "login" ? "Sign in" : "Create account"}>
        <form onSubmit={submit} className="space-y-3">
          <Field label="Email"><input className={input} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></Field>
          <Field label="Password (min 8 chars)"><input className={input} type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} /></Field>
          {mode === "register" && (
            <Field label="Persona">
              <select className={input} value={persona} onChange={(e) => setPersona(e.target.value)}>
                <option value="ml">AI/ML engineer</option><option value="web">Full-stack web developer</option><option value="data">Data analyst</option>
              </select>
            </Field>
          )}
          {err && <p role="alert" className="text-sm text-red-600">{err}</p>}
          <button className={`${btnPrimary} w-full`} disabled={busy}>{mode === "login" ? "Sign in" : "Register"}</button>
        </form>
        <button className="mt-3 text-sm text-indigo-600 underline" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
        </button>
      </Card>
    </div>
  );
}
