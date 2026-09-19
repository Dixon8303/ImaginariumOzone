import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { cw } from "@/api/client";
import Navbar from "@/components/site/Navbar";
import { Plus, Loader2, ArrowRight, PenLine, Gauge, Landmark, Sparkles } from "lucide-react";

export default function Workspace() {
  const [projects, setProjects] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await cw.entities.Project.list("-updated_date", 50);
        if (!cancelled) setProjects(list);
      } catch (e) {
        if (!cancelled) {
          setError(e.message || "Couldn't load your projects.");
          setProjects([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (projects === null) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background bg-grain">
      <Navbar />
      <div className="mx-auto max-w-6xl px-5 py-10">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="font-heading text-3xl font-semibold tracking-tight">Your projects</h1>
            <p className="mt-1 text-muted-foreground">Pick up where you left off, or start something new.</p>
          </div>
          <Link to="/get-started" className="inline-flex items-center gap-2 self-start rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 glow-green">
            <Plus className="h-4 w-4" /> New project
          </Link>
        </div>

        {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

        {projects.length === 0 ? (
          <div className="mt-12 rounded-2xl border border-dashed border-border bg-card/40 p-12 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/12 ring-1 ring-primary/30">
              <Sparkles className="h-7 w-7 text-primary" />
            </div>
            <h2 className="mt-5 font-heading text-xl font-semibold">No projects yet</h2>
            <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">Start with a single sentence. We'll help you turn it into a story worth telling.</p>
            <Link to="/get-started" className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition hover:opacity-90">
              Start your first project <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        ) : (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <Link key={p.id} to={`/project/${p.id}/develop`} className="group rounded-2xl border border-border/70 bg-card/50 p-5 transition hover:border-primary/40 hover:bg-card">
                <div className="flex items-center justify-between">
                  <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">{p.track || "Writer"}</span>
                  {p.story_score != null && <span className="font-heading text-lg font-semibold text-primary">{p.story_score}</span>}
                </div>
                <h3 className="mt-3 font-heading text-lg font-semibold leading-tight">{p.title}</h3>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{p.logline || "No logline yet"}</p>
                <div className="mt-4 flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <PenLine className="h-3.5 w-3.5" /> Develop
                  </span>
                  <span className="flex items-center gap-1">
                    <Gauge className="h-3.5 w-3.5" /> Score
                  </span>
                  <span className="flex items-center gap-1">
                    <Landmark className="h-3.5 w-3.5" /> Fund
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
