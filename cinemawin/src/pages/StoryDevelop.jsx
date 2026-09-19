import { useState } from "react";
import { useOutletContext, Link } from "react-router-dom";
import { cw } from "@/api/client";
import { Loader2, Sparkles, Save, Layers, ArrowRight, Check } from "lucide-react";
import SampleNotice from "@/components/SampleNotice";

const fields = [
  ["premise", "Premise"],
  ["protagonist", "Protagonist"],
  ["core_need", "Deeper need"],
  ["emotional_wound", "Emotional wound"],
  ["central_question", "Central question"],
  ["theme", "Theme"],
];

export default function StoryDevelop() {
  const { project, setProject } = useOutletContext();
  const [draft, setDraft] = useState(project);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [building, setBuilding] = useState(false);
  const [structure, setStructure] = useState(project.structure || null);
  const [isSample, setIsSample] = useState(false);
  const [error, setError] = useState("");

  const update = (k, v) => {
    setSaved(false);
    setDraft((d) => ({ ...d, [k]: v }));
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const updated = await cw.entities.Project.update(project.id, {
        premise: draft.premise,
        protagonist: draft.protagonist,
        core_need: draft.core_need,
        emotional_wound: draft.emotional_wound,
        central_question: draft.central_question,
        theme: draft.theme,
        logline: draft.logline,
      });
      setProject(updated);
      setSaved(true);
    } catch (e) {
      setError(e.message || "Couldn't save. Try again.");
    } finally {
      setSaving(false);
    }
  };

  const buildStructure = async () => {
    setBuilding(true);
    setError("");
    try {
      // Build from what is actually stored, not from unsaved edits — otherwise
      // the saved structure describes text that was never written down.
      if (!saved) await save();
      const { data: res } = await cw.functions.invoke("buildStructure", {
        title: draft.title,
        logline: draft.logline,
        premise: draft.premise,
        protagonist: draft.protagonist,
        central_question: draft.central_question,
        theme: draft.theme,
        genre: draft.genre,
      });
      setStructure(res.sequences);
      setIsSample(!!res.demo);
      // Persist so the structure survives a reload.
      try {
        const updated = await cw.entities.Project.update(project.id, { structure: res.sequences, maturity_level: Math.max(project.maturity_level || 0, 1) });
        setProject(updated);
      } catch {
        /* the structure is still shown; saving it is best-effort */
      }
    } catch (e) {
      setError(e.message || "Couldn't build the structure. Try again.");
    } finally {
      setBuilding(false);
    }
  };

  return (
    <div className="space-y-6 pb-16">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wider text-primary">Develop your story</p>
        <h1 className="mt-2 font-heading text-3xl font-semibold tracking-tight">{draft.title}</h1>
        <p className="mt-1 text-muted-foreground italic">{draft.logline}</p>
      </div>

      <div className="rounded-lg border border-input bg-background p-3">
        <label className="px-1 text-xs font-medium text-muted-foreground" htmlFor="logline">Logline</label>
        <textarea id="logline" value={draft.logline || ""} onChange={(e) => update("logline", e.target.value)} rows={2} className="w-full resize-none bg-transparent px-1 py-1 text-sm focus:outline-none" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {fields.map(([k, label]) => (
          <div key={k} className="rounded-xl border border-border/70 bg-card/50 p-4">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground" htmlFor={`field-${k}`}>{label}</label>
            <textarea
              id={`field-${k}`}
              value={draft[k] || ""}
              onChange={(e) => update(k, e.target.value)}
              rows={3}
              placeholder={`Add the ${label.toLowerCase()}…`}
              className="mt-2 w-full resize-none bg-transparent text-sm leading-relaxed text-foreground/90 placeholder:text-muted-foreground/60 focus:outline-none"
            />
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button onClick={save} disabled={saving} className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : saved ? <Check className="h-4 w-4" /> : <Save className="h-4 w-4" />} {saved ? "Saved" : "Save changes"}
        </button>
        <button onClick={buildStructure} disabled={building} className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-5 py-2.5 text-sm font-semibold transition hover:bg-card disabled:opacity-40">
          {building ? <Loader2 className="h-4 w-4 animate-spin" /> : <Layers className="h-4 w-4 text-accent" />} {structure ? "Rebuild story structure" : "Build story structure"}
        </button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {isSample && <SampleNotice />}

      {structure && (
        <div className="rounded-2xl border border-accent/30 bg-card p-6">
          <div className="flex items-center gap-2 text-accent">
            <Sparkles className="h-5 w-5" />
            <h2 className="font-heading text-xl font-semibold">Your 8-sequence structure</h2>
          </div>
          <div className="mt-5 space-y-4">
            {structure.map((s, i) => (
              <div key={i} className="relative pl-8">
                <span className="absolute left-0 top-0 flex h-6 w-6 items-center justify-center rounded-full bg-accent/15 text-xs font-semibold text-accent">{i + 1}</span>
                <h3 className="font-semibold">{s.name}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{s.summary}</p>
                <p className="mt-1 text-sm text-foreground/80">
                  <span className="font-medium text-primary">Turn:</span> {s.turn}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-border/70 bg-card/40 p-6">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h3 className="font-heading text-lg font-semibold">Ready to see how it scores?</h3>
            <p className="mt-1 text-sm text-muted-foreground">Get your Story Score — a clear read on what's working and what to fix next.</p>
          </div>
          <Link to={`/project/${project.id}/score`} className="inline-flex shrink-0 items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90">
            View score <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
