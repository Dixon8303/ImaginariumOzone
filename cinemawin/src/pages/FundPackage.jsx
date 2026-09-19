import { useState } from "react";
import { useOutletContext, Link } from "react-router-dom";
import { cw } from "@/api/client";
import { Loader2, Landmark, Crown, Lock, Mail, Check, ArrowRight, Coins, RefreshCw, ScrollText } from "lucide-react";
import SampleNotice from "@/components/SampleNotice";

const tagColor = {
  FACT: "bg-primary/15 text-primary",
  "VERIFIED CURRENT DATA": "bg-primary/15 text-primary",
  "INDUSTRY RANGE": "bg-accent/15 text-accent",
  "MODEL ASSUMPTION": "bg-muted text-muted-foreground",
  "PROJECT-SPECIFIC ASSUMPTION": "bg-accent/15 text-accent",
  SCENARIO: "bg-muted text-muted-foreground",
  UNKNOWN: "bg-destructive/15 text-destructive",
};

export default function FundPackage() {
  const { project, setProject } = useOutletContext();
  const [running, setRunning] = useState(false);
  const [pkg, setPkg] = useState(project.finance || null);
  const [error, setError] = useState("");
  const [email, setEmail] = useState("");
  const [captured, setCaptured] = useState(project.paywall_email_captured);
  const [isSample, setIsSample] = useState(!!project.finance?.demo);

  const runFinance = async () => {
    setRunning(true);
    setError("");
    try {
      const { data: res } = await cw.functions.invoke("buildFinance", {
        title: project.title,
        logline: project.logline,
        genre: project.genre,
        premise: project.premise,
        story_score: project.story_score,
        story_verdict: project.story_verdict,
      });
      setPkg(res);
      setIsSample(!!res.demo);
      const updated = await cw.entities.Project.update(project.id, {
        budget_ceiling: res.budget_ceiling,
        finance: res,
        current_module: "fund",
      });
      setProject(updated);
    } catch (e) {
      setError(e.message || "Couldn't build the package. Try again.");
    } finally {
      setRunning(false);
    }
  };

  const captureEmail = async () => {
    if (!email.trim()) return;
    try {
      const updated = await cw.entities.Project.update(project.id, {
        paywall_email: email.trim(),
        paywall_email_captured: true,
      });
      setProject(updated);
      setCaptured(true);
    } catch {
      /* non-critical */
    }
  };

  const fmt = (n) => (n != null ? `$${Number(n).toLocaleString()}` : "—");
  // The server decides this and withholds the content; the flag on the
  // response is authoritative over the one cached on the project.
  const unlocked = pkg?.deck_unlocked ?? project.pitch_deck_unlocked === true;

  return (
    <div className="space-y-6 pb-16">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wider text-primary">Fund & Package</p>
        <h1 className="mt-2 font-heading text-3xl font-semibold tracking-tight">Money that makes sense.</h1>
        <p className="mt-1 text-muted-foreground">A defendable budget, a clear capital stack, and a pitch deck you can actually present.</p>
      </div>

      {!pkg && (
        <div className="rounded-2xl border border-dashed border-border bg-card/40 p-10 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/12 ring-1 ring-primary/30">
            <Landmark className="h-7 w-7 text-primary" />
          </div>
          <h2 className="mt-5 font-heading text-xl font-semibold">Build your finance package</h2>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">We'll set a budget ceiling, map your capital stack, and draft a 12-slide pitch deck — all in plain language.</p>
          {project.story_score == null && (
            <p className="mx-auto mt-3 max-w-sm text-xs text-muted-foreground">
              Tip: run your{" "}
              <Link to={`/project/${project.id}/score`} className="text-primary hover:underline">
                Story Score
              </Link>{" "}
              first — the finance package uses it to size the budget.
            </p>
          )}
          <button onClick={runFinance} disabled={running} className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40">
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Coins className="h-4 w-4" />}
            {running ? "Crunching the numbers…" : "Build my package"}
          </button>
          {error && <p className="mt-4 text-sm text-destructive">{error}</p>}
        </div>
      )}

      {isSample && <SampleNotice />}

      {pkg && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-border/70 bg-card p-5">
              <p className="text-xs text-muted-foreground">Budget ceiling</p>
              <p className="mt-1 font-heading text-3xl font-semibold text-primary">{fmt(pkg.budget_ceiling)}</p>
              <p className="text-xs text-muted-foreground">{pkg.budget_tier}</p>
            </div>
            <div className="rounded-2xl border border-border/70 bg-card p-5">
              <p className="text-xs text-muted-foreground">Equity gap</p>
              <p className="mt-1 font-heading text-3xl font-semibold text-accent">{fmt(pkg.equity_gap)}</p>
              <p className="text-xs text-muted-foreground">{pkg.equity_gap_percent}% of budget</p>
            </div>
            <div className="rounded-2xl border border-border/70 bg-card p-5">
              <p className="text-xs text-muted-foreground">Soft-money offset</p>
              <p className="mt-1 font-heading text-3xl font-semibold text-primary">{100 - (pkg.equity_gap_percent || 0)}%</p>
              <p className="text-xs text-muted-foreground">de-risked before equity</p>
            </div>
          </div>

          {pkg.headline && <p className="text-sm leading-relaxed text-foreground/90">{pkg.headline}</p>}

          <div className="rounded-2xl border border-border/70 bg-card/50 p-6">
            <h2 className="font-heading text-lg font-semibold">Your 4-layer capital stack</h2>
            <p className="mt-1 text-sm text-muted-foreground">{pkg.budget_rationale}</p>
            <div className="mt-5 space-y-3">
              {(pkg.capital_stack || []).map((c, i) => (
                <div key={i} className="flex items-center gap-4">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">{i + 1}</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium">{c.layer}</span>
                      <span className="flex items-center gap-2 text-sm text-muted-foreground">
                        {c.evidence && <span className={`hidden rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider sm:inline ${tagColor[c.evidence] || "bg-muted text-muted-foreground"}`}>{c.evidence}</span>}
                        {c.percent}%
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {c.source} — {c.note}
                    </p>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${c.percent}%` }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {pkg.comps?.length > 0 && (
            <div className="rounded-2xl border border-border/70 bg-card/50 p-6">
              <h2 className="font-heading text-lg font-semibold">Market comparables</h2>
              <p className="mt-1 text-sm text-muted-foreground">Recent titles of similar genre, scale, and lane that anchor the budget ceiling.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {pkg.comps.map((c, i) => (
                  <div key={i} className="rounded-lg border border-border/60 bg-background/60 p-4">
                    <p className="font-medium">
                      {c.title} {c.year ? <span className="text-muted-foreground">({c.year})</span> : null}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">{c.budget_note}</p>
                    <p className="mt-1 text-xs text-foreground/80">{c.relevance}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="relative rounded-2xl border border-accent/30 bg-card p-6">
            <div className="flex items-center gap-2">
              <Crown className="h-5 w-5 text-accent" />
              <h2 className="font-heading text-lg font-semibold">Your 12-slide investor pitch deck</h2>
            </div>

            {!unlocked && (
              <>
                <div className="blur-paywall mt-4 grid gap-3 sm:grid-cols-2">
                  {(pkg.deck_slides || []).slice(0, 6).map((s, i) => (
                    <div key={i} className="rounded-lg border border-border/60 bg-background/60 p-4">
                      <p className="text-xs font-semibold text-muted-foreground">Slide {i + 1}</p>
                      <p className="mt-1 font-medium">{s.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{s.content}</p>
                    </div>
                  ))}
                </div>
                {!captured ? (
                  <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-background/75 backdrop-blur-sm">
                    <div className="w-full max-w-sm rounded-2xl border border-accent/40 bg-card p-6 text-center shadow-xl">
                      <Lock className="mx-auto h-7 w-7 text-accent" />
                      <h3 className="mt-3 font-heading text-lg font-semibold">Unlock the full pitch deck</h3>
                      <p className="mt-1 text-sm text-muted-foreground">Leave your email and we'll save it with this project so we can send the full deck when exports ship.</p>
                      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                        <input
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          type="email"
                          placeholder="you@email.com"
                          className="flex-1 rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                        />
                        <button onClick={captureEmail} className="inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-accent-foreground transition hover:opacity-90">
                          <Mail className="h-4 w-4" /> Send it
                        </button>
                      </div>
                      <Link to="/#pricing" className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-accent hover:underline">
                        Or go Premium for full exports <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  </div>
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-background/75 backdrop-blur-sm">
                    <div className="w-full max-w-sm rounded-2xl border border-primary/40 bg-card p-6 text-center shadow-xl">
                      <Check className="mx-auto h-7 w-7 text-primary" />
                      <h3 className="mt-3 font-heading text-lg font-semibold">Saved to this project</h3>
                      <p className="mt-1 text-sm text-muted-foreground">We've stored your email with this project. Upgrade to Premium to see the full deck now.</p>
                      <Link to="/#pricing" className="mt-4 inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-accent-foreground transition hover:opacity-90 glow-gold">
                        <Crown className="h-4 w-4" /> Go Premium — $29/mo
                      </Link>
                    </div>
                  </div>
                )}
              </>
            )}

            {unlocked && (
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {(pkg.deck_slides || []).map((s, i) => (
                  <div key={i} className="rounded-lg border border-border/60 bg-background/60 p-4">
                    <p className="text-xs font-semibold text-accent">Slide {i + 1}</p>
                    <p className="mt-1 font-medium">{s.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{s.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {unlocked && pkg.waterfall?.length > 0 && (
            <div className="rounded-2xl border border-border/70 bg-card/50 p-6">
              <h2 className="font-heading text-lg font-semibold">Investor recoupment waterfall</h2>
              <p className="mt-1 text-sm text-muted-foreground">Revenue flows in this order, top to bottom.</p>
              <ol className="mt-4 space-y-2">
                {pkg.waterfall.map((w, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs font-semibold text-accent">{i + 1}</span>
                    <span className="text-foreground/90">{w}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {pkg.assumptions?.length > 0 && (
            <div className="rounded-2xl border border-border/70 bg-card/40 p-6">
              <div className="flex items-center gap-2">
                <ScrollText className="h-5 w-5 text-muted-foreground" />
                <h2 className="font-heading text-lg font-semibold">How solid are these numbers?</h2>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">Every figure is tagged with how much evidence sits behind it. Nothing here is a promise.</p>
              <ul className="mt-4 space-y-2">
                {pkg.assumptions.map((a, i) => (
                  <li key={i} className="flex flex-col gap-1 rounded-lg border border-border/60 bg-background/50 p-3 sm:flex-row sm:items-start sm:gap-3">
                    <span className={`inline-flex w-fit shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${tagColor[a.tag] || "bg-muted text-muted-foreground"}`}>{a.tag}</span>
                    <span className="text-sm text-foreground/85">{a.claim}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex items-center gap-3">
            <button onClick={runFinance} disabled={running} className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-5 py-2.5 text-sm font-semibold transition hover:bg-card disabled:opacity-40">
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Rebuild package
            </button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        </>
      )}
    </div>
  );
}
