import { useState } from "react";
import { Link } from "react-router-dom";
import Navbar from "@/components/site/Navbar";
import Footer from "@/components/site/Footer";
import { cw } from "@/api/client";
import { useAuth } from "@/lib/AuthContext";
import { localPlan, setLocalPlan } from "@/lib/localStore";
import { Server, Check, Loader2, HardDrive, Crown, ExternalLink, AlertTriangle } from "lucide-react";

const PLANS = [
  { id: "entry", label: "Entry", detail: "Score teased, deck locked" },
  { id: "starter", label: "Starter", detail: "Full score breakdown" },
  { id: "premium", label: "Premium", detail: "Everything, including the deck" },
];

export default function Settings() {
  const { appPublicSettings, isLocalMode, refreshUser } = useAuth();
  const [url, setUrl] = useState(cw.getBackendUrl());
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState(null);
  const [plan, setPlan] = useState(localPlan());

  const connect = async () => {
    setChecking(true);
    setResult(null);
    const clean = url.trim().replace(/\/$/, "");
    try {
      if (!clean) {
        cw.setBackendUrl("");
        setResult({ ok: true, message: "Disconnected. CinemaWin is back to browser-only mode." });
        return;
      }
      const res = await fetch(`${clean}/api/health`);
      if (!res.ok) throw new Error(`The server answered ${res.status}.`);
      const health = await res.json();
      cw.setBackendUrl(clean);
      setResult({
        ok: true,
        message: health.demo_mode
          ? "Connected — but that server is in demo mode, so it will still return sample output."
          : `Connected. Provider: ${health.provider || "unknown"}.`,
      });
    } catch (e) {
      setResult({
        ok: false,
        message:
          `Couldn't reach ${clean}. Check the address, make sure the server is running, and make sure ` +
          "it allows this site (CINEMAWIN_CORS_ORIGINS).",
      });
    } finally {
      setChecking(false);
    }
  };

  const choosePlan = (id) => {
    setPlan(id);
    setLocalPlan(id);
    refreshUser();
  };

  const llm = appPublicSettings?.llm;

  return (
    <div className="min-h-screen bg-background bg-grain">
      <Navbar />
      <div className="mx-auto max-w-3xl px-5 py-10">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-muted-foreground">Where CinemaWin stores your work and where it gets its AI.</p>

        {/* Current state */}
        <div className="mt-8 rounded-2xl border border-border/70 bg-card p-6">
          <div className="flex items-start gap-3">
            {isLocalMode ? (
              <HardDrive className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
            ) : (
              <Server className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
            )}
            <div>
              <h2 className="font-heading text-lg font-semibold">
                {isLocalMode ? "Browser-only mode" : "Connected to a server"}
              </h2>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                {isLocalMode ? (
                  <>
                    Projects are saved in this browser's storage and the four story functions return
                    sample text. Nothing is sent anywhere. Clearing site data deletes your projects,
                    and they do not follow you to another device.
                  </>
                ) : (
                  <>
                    Projects are saved on the server and the story functions run on{" "}
                    <span className="text-foreground">{llm?.label || "the configured provider"}</span>
                    {llm?.craft_model ? ` (${llm.craft_model})` : ""}.
                    {appPublicSettings?.demo_mode && " That server is in demo mode, so output is still sample text."}
                  </>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Backend connection */}
        <div className="mt-6 rounded-2xl border border-border/70 bg-card/50 p-6">
          <h2 className="font-heading text-lg font-semibold">Connect a backend</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            To analyse your own story you need a CinemaWin backend running somewhere, holding an AI
            provider key. Several providers have a free tier. The README has a step-by-step guide,
            including a one-click free deploy.
          </p>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://your-backend.example.com"
              className="flex-1 rounded-lg border border-input bg-background px-4 py-2.5 text-sm focus:border-primary focus:outline-none"
            />
            <button
              onClick={connect}
              disabled={checking}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40"
            >
              {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Server className="h-4 w-4" />}
              {url.trim() ? "Connect" : "Disconnect"}
            </button>
          </div>
          {result && (
            <div
              className={`mt-3 flex items-start gap-2 rounded-lg border p-3 text-sm ${
                result.ok
                  ? "border-primary/40 bg-primary/10 text-foreground"
                  : "border-destructive/40 bg-destructive/10 text-foreground"
              }`}
            >
              {result.ok ? (
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              ) : (
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
              )}
              <span>{result.message}</span>
            </div>
          )}
          {result?.ok && (
            <button
              onClick={() => window.location.reload()}
              className="mt-3 text-sm font-semibold text-primary hover:underline"
            >
              Reload to apply
            </button>
          )}
        </div>

        {/* Plan, local mode only */}
        {isLocalMode && (
          <div className="mt-6 rounded-2xl border border-border/70 bg-card/50 p-6">
            <div className="flex items-center gap-2">
              <Crown className="h-5 w-5 text-accent" />
              <h2 className="font-heading text-lg font-semibold">Preview a plan</h2>
            </div>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              There is no billing in CinemaWin yet. In browser-only mode you can switch plans freely to
              see what each one unlocks. On a real server the operator sets this with{" "}
              <code className="rounded bg-muted px-1.5 py-0.5 text-xs">tools/set_plan.py</code>.
            </p>
            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              {PLANS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => choosePlan(p.id)}
                  className={`rounded-xl border p-4 text-left transition ${
                    plan === p.id ? "border-primary bg-primary/10" : "border-border bg-card/50 hover:bg-card"
                  }`}
                >
                  <span className="flex items-center justify-between">
                    <span className="font-semibold">{p.label}</span>
                    {plan === p.id && <Check className="h-4 w-4 text-primary" />}
                  </span>
                  <span className="mt-1 block text-xs text-muted-foreground">{p.detail}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Where to get a free key */}
        <div className="mt-6 rounded-2xl border border-border/70 bg-card/40 p-6">
          <h2 className="font-heading text-lg font-semibold">Free AI providers</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            These have a free tier with no credit card. You put the key in your backend's{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">.env</code>, never in this browser.
          </p>
          <ul className="mt-4 space-y-2 text-sm">
            {[
              ["Google Gemini", "https://aistudio.google.com/apikey", "Free tier, no card. Best quality of the free options."],
              ["Groq", "https://console.groq.com/keys", "Free tier, no card. Very fast."],
              ["Cerebras", "https://cloud.cerebras.ai/", "Free tier."],
              ["Ollama", "https://ollama.com/download", "Runs on your own machine. Unlimited, no key, no internet."],
            ].map(([name, href, note]) => (
              <li key={name} className="flex flex-col gap-0.5 rounded-lg border border-border/60 bg-background/50 p-3 sm:flex-row sm:items-center sm:gap-3">
                <a
                  href={href}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex shrink-0 items-center gap-1.5 font-semibold text-primary hover:underline"
                >
                  {name} <ExternalLink className="h-3.5 w-3.5" />
                </a>
                <span className="text-muted-foreground">{note}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="mt-8 text-center text-sm text-muted-foreground">
          <Link to="/workspace" className="text-primary hover:underline">
            Back to your projects
          </Link>
        </p>
      </div>
      <Footer />
    </div>
  );
}
