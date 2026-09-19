import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

export default function CTASection() {
  return (
    <section className="relative overflow-hidden border-t border-border/60 py-24">
      <div className="absolute -top-20 left-1/2 h-64 w-[40rem] -translate-x-1/2 rounded-full bg-primary/15 blur-[120px]" />
      <div className="relative mx-auto max-w-3xl px-5 text-center">
        <h2 className="font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">Your film deserves a clear path to the screen.</h2>
        <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground text-balance">
          Start free. See your Story Score. Upgrade only when you're ready to pitch. There's nothing to lose and a whole film to gain.
        </p>
        <Link to="/get-started" className="group mt-8 inline-flex items-center gap-2 rounded-full bg-primary px-8 py-4 text-base font-semibold text-primary-foreground transition hover:opacity-90 glow-green">
          Start your project free
          <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
        </Link>
      </div>
    </section>
  );
}
