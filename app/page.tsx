'use client';

import { ArrowRight, KeyRound, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { signIn } from "next-auth/react";
import TarotCommandCenter from "@/components/TarotCommandCenter";
import TarotSceneDemo from "@/components/3d/TarotSceneDemo";

export default function Home() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    setIsAuthenticated(window.sessionStorage.getItem("charttestui-authenticated") === "true");
  }, []);

  async function handleAuthenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.includes("@")) {
      setError("Enter a valid observer email.");
      return;
    }
    if (password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    setError("");
    setIsAuthenticating(true);
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiBaseUrl}/api/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password }),
      });
      if (!response.ok) throw new Error("Authentication failed");
      const token = await response.json() as { access_token: string };
      const sessionResult = await signIn("observer-credentials", { email, password, redirect: false });
      if (sessionResult?.error) throw new Error("Auth.js session could not be created");
      window.sessionStorage.setItem("charttestui-authenticated", "true");
      window.sessionStorage.setItem("charttestui-access-token", token.access_token);
      router.push("/gallery");
    } catch {
      setError("Authentication service unavailable or credentials rejected.");
      setIsAuthenticating(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#090b0f]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(56,189,248,0.13),transparent_28%),radial-gradient(circle_at_80%_80%,rgba(245,158,11,0.1),transparent_28%),linear-gradient(145deg,#030712_0%,#111827_48%,#090b0f_100%)]" />
      <div className="relative">
        <TarotCommandCenter />
        <TarotSceneDemo />
      </div>

      {!isAuthenticated && <div className="absolute bottom-4 right-4 z-20 w-[min(24rem,calc(100%-2rem))] p-2 sm:bottom-8 sm:right-8">
        <section className="border border-cyan-200/20 bg-[#080d16]/95 p-6 text-stone-100 shadow-[0_0_80px_rgba(34,211,238,0.12)] sm:p-8" aria-labelledby="auth-title">
          <div className="mb-8 flex items-start justify-between">
            <div>
              <div className="mb-5 flex items-center gap-3 text-cyan-200"><LockKeyhole className="h-5 w-5" /><span className="font-mono text-[10px] uppercase tracking-[0.34em]">Secure observatory</span></div>
              <h1 id="auth-title" className="text-3xl font-medium tracking-[-0.03em]">Enter the arcana field</h1>
              <p className="mt-3 font-mono text-xs leading-5 text-stone-500">Authenticate your observer identity to access the living gallery.</p>
            </div>
            <ShieldCheck className="h-5 w-5 text-emerald-300/70" aria-label="Secure connection" />
          </div>

          <form onSubmit={handleAuthenticate} className="space-y-5">
            <label className="block">
              <span className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-stone-500"><Mail className="h-3 w-3" /> Email address</span>
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="observer@example.com" autoComplete="email" required className="w-full border border-white/15 bg-white/[0.04] px-3 py-3 font-mono text-sm text-stone-100 outline-none transition-colors placeholder:text-stone-700 focus:border-cyan-200/70" />
            </label>
            <label className="block">
              <span className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-stone-500"><KeyRound className="h-3 w-3" /> Password</span>
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" autoComplete="current-password" required className="w-full border border-white/15 bg-white/[0.04] px-3 py-3 font-mono text-sm text-stone-100 outline-none transition-colors placeholder:text-stone-700 focus:border-cyan-200/70" />
            </label>
            {error && <p role="alert" className="font-mono text-xs text-red-300">{error}</p>}
            <button type="submit" disabled={isAuthenticating} className="flex w-full items-center justify-between border border-cyan-200/50 bg-cyan-100 px-4 py-3 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-950 transition-colors hover:bg-white disabled:cursor-wait disabled:opacity-60">
              <span>{isAuthenticating ? "Opening field..." : "Authenticate observer"}</span><ArrowRight className="h-4 w-4" />
            </button>
          </form>
          <p className="mt-6 border-t border-white/10 pt-4 font-mono text-[9px] uppercase tracking-[0.18em] text-stone-600">Demo gateway / credentials are local only</p>
        </section>
      </div>}
    </main>
  );
}
