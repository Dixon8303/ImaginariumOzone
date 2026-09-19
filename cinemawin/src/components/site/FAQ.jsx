import { useState } from "react";
import { ChevronDown } from "lucide-react";

const faqs = [
  {
    q: "Do I need to know how films get made?",
    a: "No. CinemaWin is built for first-time filmmakers and seasoned producers alike. Every step uses plain language, and the guided questions do the heavy lifting — you just bring your idea and your instincts.",
  },
  {
    q: "Can I start with just a one-line idea?",
    a: "Absolutely. Most projects begin as a single sentence. The intake walks you from that spark into a premise, characters, and a structure — at your own pace.",
  },
  {
    q: "What's a Story Score?",
    a: "It's a clear 100-point read on your project across story, character, marketability, and finance. You get a greenlight verdict — Recommend, Consider, or Pass — plus the specific notes behind it. Free accounts see a teaser; paid plans unlock the full breakdown.",
  },
  {
    q: "Will it change my story to fit a formula?",
    a: "Never. CinemaWin treats structure as a diagnostic lens, not a rulebook. It protects your voice, your cultural specificity, and the creative risks that make your story yours.",
  },
  {
    q: "Can I export a pitch deck and budget?",
    a: "Yes — on Premium. You get a 12-slide investor pitch deck, a departmental budget top sheet, and a capital stack you can actually present. Free and Starter plans can preview these with a soft paywall so you know exactly what you're upgrading for.",
  },
  {
    q: "Is my work private?",
    a: "Yes. Your projects are yours alone. Nothing is shared, published, or used to train anything. You can delete a project anytime.",
  },
];

export default function FAQ() {
  const [open, setOpen] = useState(0);
  return (
    <section id="faq" className="border-t border-border/60 bg-sidebar/40 py-20 md:py-28">
      <div className="mx-auto max-w-3xl px-5">
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-primary">FAQ</p>
          <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight sm:text-4xl">Questions, answered plainly.</h2>
        </div>
        <div className="mt-10 space-y-3">
          {faqs.map((f, i) => (
            <div key={f.q} className="rounded-xl border border-border/70 bg-card/50 overflow-hidden">
              <button onClick={() => setOpen(open === i ? -1 : i)} className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left">
                <span className="font-medium text-foreground">{f.q}</span>
                <ChevronDown className={`h-5 w-5 shrink-0 text-muted-foreground transition ${open === i ? "rotate-180" : ""}`} />
              </button>
              {open === i && <div className="px-5 pb-5 text-sm leading-relaxed text-muted-foreground">{f.a}</div>}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
