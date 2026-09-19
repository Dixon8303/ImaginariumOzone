import { ShieldCheck, Gauge, FileText, Compass, Eye, Coins } from "lucide-react";

const features = [
  { icon: Compass, title: "Guided story development", body: "Plain-language questions draw out your premise, characters, and theme — no outline templates to stare at." },
  { icon: Gauge, title: "Your Story Score", body: "A clear 100-point read on what's working and what isn't, with a greenlight verdict you can act on." },
  { icon: FileText, title: "Industry-standard script", body: "Generate and refine properly formatted scenes as your idea grows into a screenplay." },
  { icon: Eye, title: "Production footprint map", body: "See locations, cast, and schedule as a real shoot would — catch expensive problems early." },
  { icon: Coins, title: "Finance-ready capital stack", body: "A defendable budget, soft-money offsets, and an equity gap that investors can actually understand." },
  { icon: ShieldCheck, title: "Clearance & risk check", body: "Spot rights issues and clearance red flags before they cost you a deal." },
];

export default function Features() {
  return (
    <section id="features" className="border-t border-border/60 bg-sidebar/40 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-5">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-wider text-primary">Features</p>
          <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight sm:text-4xl">Everything a film needs. Nothing it doesn't.</h2>
          <p className="mt-4 text-lg text-muted-foreground">
            One workspace across story, production, and finance — so your creative choices and your numbers always agree.
          </p>
        </div>
        <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-border/70 bg-border/70 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="bg-card/60 p-7 transition hover:bg-card">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/12 ring-1 ring-primary/25">
                <f.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 font-heading text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
