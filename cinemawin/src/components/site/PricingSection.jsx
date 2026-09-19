import { Link } from "react-router-dom";
import { Check, Lock, Crown } from "lucide-react";

const tiers = [
  {
    name: "Entry",
    price: "$0",
    period: "free forever",
    tagline: "Explore and save your progress.",
    cta: "Start free",
    to: "/get-started",
    highlight: false,
    features: ["Guided idea intake", "Save unlimited projects", "Story Score preview (teased)", "Sample project access"],
  },
  {
    name: "Starter",
    price: "$12",
    period: "per month",
    tagline: "Your full Story Score, unlocked.",
    cta: "Choose Starter",
    to: "/get-started",
    highlight: true,
    badge: "Most popular",
    features: ["Everything in Entry", "Full Story Score & verdict", "Develop & refine your script", "Production footprint overview", "No exports"],
  },
  {
    name: "Premium",
    price: "$29",
    period: "per month",
    tagline: "Pitch decks, budgets, exports.",
    cta: "Go Premium",
    to: "/get-started",
    highlight: false,
    premium: true,
    features: ["Everything in Starter", "Export pitch deck & budget", "Full capital stack & waterfall", "Clearance & risk audit", "Unlimited project scale"],
  },
];

export default function PricingSection() {
  return (
    <section id="pricing" className="border-t border-border/60 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-5">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-wider text-primary">Pricing</p>
          <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight sm:text-4xl">Honest pricing that grows with you.</h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Start free. Unlock your full score for the price of a few coffees. Add exports when you're ready to pitch. Cancel anytime.
          </p>
        </div>
        <div className="mt-12 grid gap-5 lg:grid-cols-3">
          {tiers.map((t) => (
            <div
              key={t.name}
              className={`relative flex flex-col rounded-2xl border p-7 ${
                t.highlight ? "border-primary/50 bg-card glow-green" : t.premium ? "border-accent/40 bg-card" : "border-border/70 bg-card/50"
              }`}
            >
              {t.badge && (
                <span className="absolute -top-3 left-7 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">{t.badge}</span>
              )}
              <div className="flex items-center gap-2">
                {t.premium ? <Crown className="h-5 w-5 text-accent" /> : t.highlight ? <Check className="h-5 w-5 text-primary" /> : <Lock className="h-5 w-5 text-muted-foreground" />}
                <h3 className="font-heading text-xl font-semibold">{t.name}</h3>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{t.tagline}</p>
              <div className="mt-5 flex items-baseline gap-1.5">
                <span className="font-heading text-4xl font-semibold">{t.price}</span>
                <span className="text-sm text-muted-foreground">{t.period}</span>
              </div>
              <ul className="mt-6 flex-1 space-y-3">
                {t.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm">
                    <Check className={`mt-0.5 h-4 w-4 shrink-0 ${t.premium ? "text-accent" : "text-primary"}`} />
                    <span className="text-foreground/90">{f}</span>
                  </li>
                ))}
              </ul>
              <Link
                to={t.to}
                className={`mt-7 inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition ${
                  t.highlight
                    ? "bg-primary text-primary-foreground hover:opacity-90"
                    : t.premium
                    ? "bg-accent text-accent-foreground hover:opacity-90 glow-gold"
                    : "border border-border bg-card/50 text-foreground hover:bg-card"
                }`}
              >
                {t.cta}
              </Link>
            </div>
          ))}
        </div>
        <p className="mt-8 text-center text-sm text-muted-foreground">
          Every plan keeps your work private to you. Upgrade the moment a feature earns its place.
        </p>
      </div>
    </section>
  );
}
