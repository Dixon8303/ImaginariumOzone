import { Link, useNavigate, Outlet, useParams, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { cw } from "@/api/client";
import { useAuth } from "@/lib/AuthContext";
import Logo from "@/components/site/Logo";
import { PenLine, Gauge, Landmark, Loader2, LayoutGrid, Crown } from "lucide-react";

const modules = [
  { id: "develop", label: "Develop Story", to: "develop", icon: PenLine },
  { id: "score", label: "Story Score", to: "score", icon: Gauge },
  { id: "fund", label: "Fund & Package", to: "fund", icon: Landmark },
];

const planLabel = { entry: "Entry", starter: "Starter", premium: "Premium" };

export default function ProjectLayout() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const p = await cw.entities.Project.get(id);
        if (!cancelled) setProject(p);
      } catch {
        if (!cancelled) navigate("/workspace", { replace: true });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, navigate]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }
  if (!project) return null;

  const plan = user?.plan || "entry";

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5">
          <div className="flex items-center gap-4">
            <Logo />
            <span className="hidden h-5 w-px bg-border sm:block" />
            <span className="hidden font-heading text-lg font-semibold sm:block">{project.title}</span>
          </div>
          <div className="flex items-center gap-4">
            <span
              className={`hidden items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold sm:inline-flex ${
                plan === "premium" ? "bg-accent/15 text-accent" : plan === "starter" ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
              }`}
              title="Your plan decides which sections are unlocked"
            >
              {plan === "premium" && <Crown className="h-3.5 w-3.5" />}
              {planLabel[plan] || plan} plan
            </span>
            <Link to="/workspace" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
              <LayoutGrid className="h-4 w-4" /> All projects
            </Link>
          </div>
        </div>
      </header>
      <div className="mx-auto flex max-w-7xl gap-6 px-5 py-6">
        <aside className="hidden w-56 shrink-0 md:block">
          <nav className="sticky top-24 space-y-1">
            <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Modules</p>
            {modules.map((m) => {
              const active = location.pathname.endsWith(`/${m.to}`);
              return (
                <Link
                  key={m.id}
                  to={`/project/${id}/${m.to}`}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    active ? "bg-primary/15 text-primary" : "text-muted-foreground hover:bg-card hover:text-foreground"
                  }`}
                >
                  <m.icon className="h-4 w-4" /> {m.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <main className="min-w-0 flex-1">
          <div className="mb-5 flex gap-2 overflow-x-auto md:hidden">
            {modules.map((m) => {
              const active = location.pathname.endsWith(`/${m.to}`);
              return (
                <Link
                  key={m.id}
                  to={`/project/${id}/${m.to}`}
                  className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-semibold ${
                    active ? "border-primary/40 bg-primary/15 text-primary" : "border-border bg-card/50 text-muted-foreground"
                  }`}
                >
                  <m.icon className="h-3.5 w-3.5" /> {m.label}
                </Link>
              );
            })}
          </div>
          <Outlet context={{ project, setProject }} />
        </main>
      </div>
    </div>
  );
}
