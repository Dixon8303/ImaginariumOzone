import { useState } from "react";
import { useOutletContext, Link } from "react-router-dom";
import { cw } from "@/api/client";
import { Loader2, Gauge, Lock, Crown, ArrowRight, Sparkles, RefreshCw } from "lucide-react";
import SampleNotice from "@/components/SampleNotice";

const categories = [
  ["Premise & Hook", 10],
  ["Story Architecture", 10],
  ["Character & Voice", 10],
  ["Dialogue & Subtext", 5],
  ["Thematic Depth", 5],
  ["Cinematic Potential", 10],
  ["Marketability & Comps", 10],
  ["Castability", 10],
  ["Production Feasibility", 10],
  ["Financial Viability", 10],
  ["Packaging Potential", 5],
  ["Distribution Viability", 5],
];

const verdictColor = { RECOMMEND: "bg-primary/15 text-primary", CONSIDER: "bg-accent/15 text-accent", PASS: "bg-destructive/15 text-destructive" };

export default function StoryScore() {
  const { project, setProject } = useOutletContext();
  const [running, setRunning] = useState(false);
  const [isSample, setIsSample] = useState(false);
  const [error, setError] = useState("");

  const runScore = async () => {
    setRunning(true);
    setError("");
    try {
      const { data: res } = await cw.functions.invoke("scoreStory", {
        title: project.title,
        logline: project.logline,
        premise: project.premise,
        protagonist: project.protagonist,
        central_question: project.central_question,
        theme: project.theme,
        genre: project.genre,
        track: project.track,
      });
      const updated = await cw.entities.Project.update(project.id, {
        story_score: res.total,
        story_verdict: res.verdict,
        story_verdict_label: res.verdict_label,
        story_headline: res.headline,
        score_breakdown: res.breakdown,
        top_fixes: res.top_fixes,
        current_module: "score",
      });
      setProject(updated);
      setIsSample(!!res.demo);
    } catch (e) {
      setError(e.message || "Couldn't run the score. Try again.");
    } finally {
      setRunning(false);
    }
  };

  const hasScore = project.story_score != null;
  const topFixes = project.top_fixes || [];
  // Derived server-side from the owner's plan (Entry → locked).
  const locked = project.score_locked !== false;

  return (
    <div className="space-y-6 pb-16">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wider text-primary">Story Score</p>
        <h1 className="mt-2 font-heading text-3xl font-semibold tracking-tight">How ready is your film?</h1>
        <p className="mt-1 text-muted-foreground">A clear, honest 100-point read — and the greenlight verdict behind it.</p>
      </div>

      {!hasScore && (
        <div className="rounded-2xl border border-dashed border-border bg-card/40 p-10 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/12 ring-1 ring-primary/30">
            <Gauge className="h-7 w-7 text-primary" />
          </div>
          <h2 className="mt-5 font-heading text-xl font-semibold">No score yet</h2>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">Run the scorecard to see your project's strengths, gaps, and greenlight verdict.</p>
          <button onClick={runScore} disabled={running} className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40">
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {running ? "Reading your project…" : "Run my Story Score"}
          </button>
          {error && <p className="mt-4 text-sm text-destructive">{error}</p>}
        </div>
      )}

      {isSample && <SampleNotice />}

      {hasScore && (
        <>
          <div className="rounded-2xl border border-border/70 bg-card p-7">
            <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Your Story Score</p>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="font-heading text-6xl font-semibold text-primary">{project.story_score}</span>
                  <span className="text-2xl text-muted-foreground">/ 100</span>
                </div>
                <span className={`mt-2 inline-block rounded-full px-3 py-1 text-sm font-semibold ${verdictColor[project.story_verdict] || "bg-muted text-muted-foreground"}`}>
                  {project.story_verdict_label || project.story_verdict}
                </span>
              </div>
              <div className="flex-1 sm:max-w-md">
                <p className="text-sm leading-relaxed text-foreground/90">
                  {project.story_headline || "Your project has a clear core. Here's what's working — and what to sharpen before you pitch."}
                </p>
                {!locked && topFixes.length > 0 && (
                  <ul className="mt-3 space-y-1.5 text-sm text-muted-foreground">
                    {topFixes.map((f, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-primary">→</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <button onClick={runScore} disabled={running} className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground disabled:opacity-40">
                  {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} Re-run after edits
                </button>
                {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
              </div>
            </div>
          </div>

          <div className="relative rounded-2xl border border-border/70 bg-card/50 p-6">
            <h2 className="font-heading text-lg font-semibold">Category breakdown</h2>
            {locked ? (
              <>
                <div className="blur-paywall mt-4 space-y-3">
                  {categories.map(([c, max]) => (
                    <div key={c} className="flex items-center gap-3">
                      <span className="w-44 shrink-0 text-sm text-muted-foreground">{c}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary/40" style={{ width: `${(max * 8) % 100}%` }} />
                      </div>
                      <span className="w-10 text-right text-sm text-muted-foreground">?/{max}</span>
                    </div>
                  ))}
                </div>
                <div className="absolute inset-0 flex flex-col items-center justify-center rounded-2xl bg-background/70 backdrop-blur-sm">
                  <div className="rounded-2xl border border-accent/40 bg-card p-6 text-center shadow-xl">
                    <Lock className="mx-auto h-7 w-7 text-accent" />
                    <h3 className="mt-3 font-heading text-lg font-semibold">Unlock your full breakdown</h3>
                    <p className="mx-auto mt-1 max-w-xs text-sm text-muted-foreground">See the score for every category — and the specific notes behind each one.</p>
                    <Link to="/#pricing" className="mt-4 inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-accent-foreground transition hover:opacity-90 glow-gold">
                      <Crown className="h-4 w-4" /> Unlock with Starter — $12/mo
                    </Link>
                  </div>
                </div>
              </>
            ) : (
              <div className="mt-4 space-y-4">
                {(project.score_breakdown || []).map((b, i) => (
                  <div key={i}>
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{b.category}</span>
                      <span className="text-muted-foreground">
                        {b.score}/{b.max}
                      </span>
                    </div>
                    <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-muted">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${(b.score / b.max) * 100}%` }} />
                    </div>
                    <p className="mt-1.5 text-sm text-muted-foreground">{b.note}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-border/70 bg-card/40 p-6">
            <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h3 className="font-heading text-lg font-semibold">Ready to fund & package?</h3>
                <p className="mt-1 text-sm text-muted-foreground">Turn this score into a budget, a capital stack, and a pitch deck.</p>
              </div>
              <Link to={`/project/${project.id}/fund`} className="inline-flex shrink-0 items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90">
                Fund & package <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
