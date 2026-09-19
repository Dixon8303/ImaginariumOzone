import { Link } from "react-router-dom";
import Navbar from "@/components/site/Navbar";
import Footer from "@/components/site/Footer";
import { ArrowRight, Sparkles, Gauge, Landmark, PenLine, Lock } from "lucide-react";

const sample = {
  title: "The Last Archivist",
  logline: "A disgraced film archivist discovers a reel that predicts tragedies — and must decide whether to stop the next one or let it play.",
  genre: "Thriller",
  track: "Both",
  score: 87,
  verdict: "RECOMMEND",
  premise:
    "In a city that's demolishing its own history, a fallen archivist finds a forgotten reel that seems to foretell disasters. As she races to decode it, she's forced to choose between protecting herself and intervening in a tragedy she may not be able to stop.",
  protagonist: "Maren Cole, 40s — a once-respected archivist who lost her credibility after publicly misattributing a reel.",
  core_need: "To trust her own eyes again, and to believe that preserving something matters even when no one's watching.",
  emotional_wound: "She was publicly humiliated for a mistake she still isn't sure was a mistake.",
  central_question: "If you could see a tragedy coming, and no one would believe you, would you still try to stop it?",
  theme: "Memory is an act of faith — in the past, and in the people who'll inherit it.",
  budget: 4200000,
  tier: "Mid-tier indie / streamer buyout",
  equityGap: 1600000,
  equityPercent: 38,
  stack: [
    { layer: "Tax incentives (Georgia)", percent: 30 },
    { layer: "Foreign pre-sales & MGs", percent: 22 },
    { layer: "Brand integration & grants", percent: 10 },
    { layer: "Equity gap", percent: 38 },
  ],
};

const cats = [
  ["Premise & Hook", 9, 10],
  ["Story Architecture", 8, 10],
  ["Character & Voice", 9, 10],
  ["Marketability", 8, 10],
  ["Castability", 8, 10],
  ["Production Feasibility", 9, 10],
];

export default function Sample() {
  return (
    <div className="min-h-screen bg-background bg-grain">
      <Navbar />
      <article className="mx-auto max-w-4xl px-5 py-12">
        <div className="text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-1.5 text-xs font-medium text-accent">
            <Sparkles className="h-3.5 w-3.5" /> Sample project
          </span>
          <h1 className="mt-5 font-heading text-4xl font-semibold tracking-tight">{sample.title}</h1>
          <p className="mx-auto mt-3 max-w-2xl text-lg italic text-muted-foreground">"{sample.logline}"</p>
          <div className="mt-4 flex items-center justify-center gap-3 text-sm text-muted-foreground">
            <span className="rounded-full bg-muted px-3 py-1">{sample.genre}</span>
            <span className="rounded-full bg-muted px-3 py-1">{sample.track}</span>
          </div>
        </div>

        <div className="mt-12 grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-border/70 bg-card p-5 text-center">
            <PenLine className="mx-auto h-6 w-6 text-primary" />
            <p className="mt-2 text-xs text-muted-foreground">Story developed</p>
            <p className="font-heading text-lg font-semibold">8 sequences</p>
          </div>
          <div className="rounded-2xl border border-primary/40 bg-card p-5 text-center glow-green">
            <Gauge className="mx-auto h-6 w-6 text-primary" />
            <p className="mt-2 text-xs text-muted-foreground">Story Score</p>
            <p className="font-heading text-2xl font-semibold text-primary">
              {sample.score} <span className="text-sm text-muted-foreground">/ 100</span>
            </p>
            <p className="text-xs font-semibold text-primary">{sample.verdict}</p>
          </div>
          <div className="rounded-2xl border border-border/70 bg-card p-5 text-center">
            <Landmark className="mx-auto h-6 w-6 text-accent" />
            <p className="mt-2 text-xs text-muted-foreground">Budget ceiling</p>
            <p className="font-heading text-lg font-semibold">${(sample.budget / 1e6).toFixed(1)}M</p>
          </div>
        </div>

        <section className="mt-12">
          <h2 className="font-heading text-2xl font-semibold">The story, surfaced</h2>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {[
              ["Premise", sample.premise],
              ["Protagonist", sample.protagonist],
              ["Deeper need", sample.core_need],
              ["Emotional wound", sample.emotional_wound],
              ["Central question", sample.central_question],
              ["Theme", sample.theme],
            ].map(([k, v]) => (
              <div key={k} className="rounded-xl border border-border/70 bg-card/50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{k}</p>
                <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">{v}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-12">
          <h2 className="font-heading text-2xl font-semibold">Score breakdown (teaser)</h2>
          <div className="mt-5 space-y-3">
            {cats.map(([c, s, max]) => (
              <div key={c} className="flex items-center gap-3">
                <span className="w-40 shrink-0 text-sm text-muted-foreground">{c}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${(s / max) * 100}%` }} />
                </div>
                <span className="w-10 text-right text-sm text-muted-foreground">
                  {s}/{max}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-accent/30 bg-accent/5 p-3 text-sm text-muted-foreground">
            <Lock className="h-4 w-4 text-accent" /> 6 more categories unlock with a paid plan.
          </div>
        </section>

        <section className="mt-12">
          <h2 className="font-heading text-2xl font-semibold">The capital stack</h2>
          <div className="mt-5 space-y-3">
            {sample.stack.map((c, i) => (
              <div key={i} className="flex items-center gap-4">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">{i + 1}</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{c.layer}</span>
                    <span className="text-sm text-muted-foreground">{c.percent}%</span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${c.percent}%` }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-14 rounded-2xl border border-primary/30 bg-primary/5 p-8 text-center">
          <h2 className="font-heading text-2xl font-semibold">This could be your film.</h2>
          <p className="mx-auto mt-2 max-w-md text-muted-foreground">Start free and run your own idea through the same guided path — story, score, and finance.</p>
          <Link to="/get-started" className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-7 py-3.5 text-base font-semibold text-primary-foreground transition hover:opacity-90 glow-green">
            Start your project free <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </article>
      <Footer />
    </div>
  );
}
