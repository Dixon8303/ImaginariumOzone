import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { cw } from "@/api/client";
import { useAuth } from "@/lib/AuthContext";
import { stashIntake } from "@/lib/intake";
import { ArrowRight, ArrowLeft, Check, Sparkles, Loader2, PenLine, Clapperboard, Layers } from "lucide-react";
import Logo from "@/components/site/Logo";

const tracks = [
  { id: "Writer", icon: PenLine, title: "Writer", desc: "I'm focused on the story and the script." },
  { id: "Producer", icon: Clapperboard, title: "Producer", desc: "I'm focused on the shoot and the money." },
  { id: "Both", icon: Layers, title: "Both", desc: "I'm wearing every hat on this one." },
];

const genres = ["Drama", "Thriller", "Comedy", "Horror", "Historical", "Documentary-Fiction", "Sci-Fi", "Crime", "Romance", "Other"];

export default function GetStarted() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({ track: "", title: "", logline: "", genre: "" });
  const [loading, setLoading] = useState(false);
  const [developed, setDeveloped] = useState(null);
  const [error, setError] = useState("");

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const runDevelop = async () => {
    setLoading(true);
    setError("");
    try {
      const { data: res } = await cw.functions.invoke("developStory", {
        title: form.title,
        logline: form.logline,
        genre: form.genre,
        track: form.track,
      });
      setDeveloped(res);
      setStep(4);
    } catch (e) {
      setError(e.message || "Something went wrong developing your story. Please try again.");
      setStep(2);
    } finally {
      setLoading(false);
    }
  };

  const saveProject = async () => {
    setLoading(true);
    setError("");
    try {
      const authed = isAuthenticated || (await cw.auth.isAuthenticated());
      if (!authed) {
        // Park the developed story; Register/Login turn it into a project on success.
        stashIntake({ ...form, ...developed });
        navigate(`/register?returnTo=${encodeURIComponent("/workspace")}`);
        return;
      }
      const project = await cw.entities.Project.create({
        title: form.title,
        logline: form.logline,
        track: form.track,
        genre: form.genre,
        premise: developed?.premise,
        protagonist: developed?.protagonist,
        core_need: developed?.core_need,
        emotional_wound: developed?.emotional_wound,
        central_question: developed?.central_question,
        theme: developed?.theme,
        maturity_level: 1,
        current_module: "develop",
      });
      navigate(`/project/${project.id}/develop`);
    } catch (e) {
      setError(e.message || "We couldn't save your project. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const canNext = step === 0 ? !!form.track : step === 1 ? form.title.trim() && form.logline.trim() : step === 2 ? !!form.genre : false;

  return (
    <div className="min-h-screen bg-background bg-grain">
      <div className="mx-auto max-w-2xl px-5 py-10">
        <Logo />
        <div className="mt-10">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className={step >= 0 ? "text-primary" : ""}>Track</span>
            <span className="h-px w-4 bg-border" />
            <span className={step >= 1 ? "text-primary" : ""}>Idea</span>
            <span className="h-px w-4 bg-border" />
            <span className={step >= 2 ? "text-primary" : ""}>Genre</span>
            <span className="h-px w-4 bg-border" />
            <span className={step >= 3 ? "text-primary" : ""}>Develop</span>
          </div>

          {step === 0 && (
            <div className="mt-8">
              <h1 className="font-heading text-3xl font-semibold tracking-tight">First, what's your role on this film?</h1>
              <p className="mt-2 text-muted-foreground">This shapes which tools we put in front of you. You can change it anytime.</p>
              <div className="mt-6 space-y-3">
                {tracks.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => update("track", t.id)}
                    className={`flex w-full items-center gap-4 rounded-xl border p-4 text-left transition ${
                      form.track === t.id ? "border-primary bg-primary/10" : "border-border bg-card/50 hover:bg-card"
                    }`}
                  >
                    <span className={`flex h-11 w-11 items-center justify-center rounded-lg ${form.track === t.id ? "bg-primary/20" : "bg-muted"}`}>
                      <t.icon className={`h-5 w-5 ${form.track === t.id ? "text-primary" : "text-muted-foreground"}`} />
                    </span>
                    <span>
                      <span className="block font-semibold">{t.title}</span>
                      <span className="block text-sm text-muted-foreground">{t.desc}</span>
                    </span>
                    {form.track === t.id && <Check className="ml-auto h-5 w-5 text-primary" />}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="mt-8">
              <h1 className="font-heading text-3xl font-semibold tracking-tight">What's the film, in your own words?</h1>
              <p className="mt-2 text-muted-foreground">A working title and one line is plenty. We'll build from there together.</p>
              <div className="mt-6 space-y-4">
                <div>
                  <label className="text-sm font-medium" htmlFor="gs-title">Working title</label>
                  <input
                    id="gs-title"
                    value={form.title}
                    onChange={(e) => update("title", e.target.value)}
                    placeholder="e.g. The Last Archivist"
                    className="mt-1.5 w-full rounded-lg border border-input bg-background px-4 py-3 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium" htmlFor="gs-logline">One-line idea</label>
                  <textarea
                    id="gs-logline"
                    value={form.logline}
                    onChange={(e) => update("logline", e.target.value)}
                    rows={3}
                    placeholder="e.g. A disgraced archivist discovers a film reel that predicts tragedies, and has to decide whether to stop the next one."
                    className="mt-1.5 w-full rounded-lg border border-input bg-background px-4 py-3 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none resize-none"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="mt-8">
              <h1 className="font-heading text-3xl font-semibold tracking-tight">What kind of story is it?</h1>
              <p className="mt-2 text-muted-foreground">Pick the closest fit. We'll tune the craft to match.</p>
              <div className="mt-6 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                {genres.map((g) => (
                  <button
                    key={g}
                    onClick={() => update("genre", g)}
                    className={`rounded-lg border px-4 py-3 text-sm font-medium transition ${
                      form.genre === g ? "border-primary bg-primary/10 text-primary" : "border-border bg-card/50 hover:bg-card"
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="mt-8 flex flex-col items-center justify-center py-16 text-center">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <h1 className="mt-6 font-heading text-2xl font-semibold">Excavating your story…</h1>
              <p className="mt-2 text-muted-foreground">Finding the premise, the protagonist, and the dramatic engine beneath your idea.</p>
            </div>
          )}

          {step === 4 && developed && (
            <div className="mt-8">
              <div className="flex items-center gap-2 text-primary">
                <Sparkles className="h-5 w-5" />
                <span className="text-sm font-semibold uppercase tracking-wider">Your story, surfaced</span>
              </div>
              <h1 className="mt-3 font-heading text-3xl font-semibold tracking-tight">{form.title}</h1>
              <p className="mt-1 text-muted-foreground italic">"{form.logline}"</p>
              <div className="mt-6 space-y-4">
                {[
                  ["Premise", developed.premise],
                  ["Protagonist", developed.protagonist],
                  ["Deeper need", developed.core_need],
                  ["Emotional wound", developed.emotional_wound],
                  ["Central question", developed.central_question],
                  ["Theme", developed.theme],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-xl border border-border/70 bg-card/50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{k}</p>
                    <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">{v}</p>
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-xl border border-primary/30 bg-primary/10 p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-primary">Your next step</p>
                <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">{developed.first_step}</p>
              </div>
            </div>
          )}

          {error && <p className="mt-4 text-sm text-destructive">{error}</p>}

          <div className="mt-10 flex items-center justify-between">
            {step > 0 && step < 3 ? (
              <button onClick={() => setStep(step - 1)} className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
                <ArrowLeft className="h-4 w-4" /> Back
              </button>
            ) : (
              <span />
            )}
            {step < 2 && (
              <button
                disabled={!canNext}
                onClick={() => setStep(step + 1)}
                className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40"
              >
                Continue <ArrowRight className="h-4 w-4" />
              </button>
            )}
            {step === 2 && (
              <button
                disabled={!canNext || loading}
                onClick={() => {
                  setStep(3);
                  runDevelop();
                }}
                className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Develop my story
              </button>
            )}
            {step === 4 && (
              <button
                disabled={loading}
                onClick={saveProject}
                className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Save & open workspace
              </button>
            )}
          </div>
          <p className="mt-8 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
