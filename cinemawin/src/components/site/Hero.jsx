import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, Play } from "lucide-react";

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-grain">
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent" />
      <div className="absolute -top-24 left-1/2 h-72 w-[36rem] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]" />
      <div className="relative mx-auto max-w-6xl px-5 pt-20 pb-24 md:pt-28 md:pb-32">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-medium text-primary">
            <Sparkles className="h-3.5 w-3.5" /> From spark to greenlight
          </span>
          <h1 className="mt-6 font-heading text-4xl font-semibold leading-[1.05] tracking-tight text-balance sm:text-5xl md:text-6xl">
            Turn your film idea into an <span className="italic text-accent">investor-ready</span> package.
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground text-balance">
            CinemaWin walks you from a one-line idea to a finished script, a shootable plan, and a finance-ready pitch — in one calm, guided workspace. No film-school degree required.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link to="/get-started" className="group inline-flex items-center gap-2 rounded-full bg-primary px-7 py-3.5 text-base font-semibold text-primary-foreground transition hover:opacity-90 glow-green">
              Start your project free
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </Link>
            <Link to="/sample" className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-7 py-3.5 text-base font-semibold text-foreground transition hover:bg-card">
              <Play className="h-4 w-4 text-accent" /> See a sample
            </Link>
          </div>
          <p className="mt-5 text-sm text-muted-foreground">No credit card. Save your progress instantly.</p>
        </div>

        <div className="mx-auto mt-16 max-w-4xl">
          <div className="rounded-2xl border border-border/70 bg-card/60 p-2 shadow-2xl backdrop-blur">
            <div className="flex items-center gap-1.5 px-3 py-2">
              <span className="h-2.5 w-2.5 rounded-full bg-destructive/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-accent/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-primary/70" />
              <span className="ml-3 text-xs text-muted-foreground">cinemawin.app — Story Workspace</span>
            </div>
            <div className="grid grid-cols-1 gap-3 p-3 sm:grid-cols-3">
              {[
                { k: "Story Score", v: "87", s: "RECOMMEND", c: "text-primary" },
                { k: "Budget Ceiling", v: "$4.2M", s: "Mid-tier", c: "text-accent" },
                { k: "Equity Gap", v: "$1.6M", s: "38% de-risked", c: "text-primary" },
              ].map((m) => (
                <div key={m.k} className="rounded-xl border border-border/60 bg-background/60 p-4">
                  <p className="text-xs text-muted-foreground">{m.k}</p>
                  <p className={`mt-1 font-heading text-2xl font-semibold ${m.c}`}>{m.v}</p>
                  <p className="text-xs text-muted-foreground">{m.s}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
