import { PenLine, Clapperboard, Landmark, ArrowRight } from "lucide-react";

const steps = [
  {
    icon: PenLine,
    title: "Develop your story",
    body: "Answer a few calm questions about your idea. CinemaWin uncovers the premise, the characters, and the dramatic engine — then helps you shape a structure that holds.",
  },
  {
    icon: Clapperboard,
    title: "Plan your shoot",
    body: "See your script as a production footprint: locations, cast, schedule, and a realistic budget ceiling — before you spend a dollar on the wrong thing.",
  },
  {
    icon: Landmark,
    title: "Fund & package",
    body: "Get a finance-ready capital stack, a 12-slide pitch deck, and a clear investor path — so you can walk into a room with numbers that hold up.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how" className="border-t border-border/60 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-5">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-wider text-primary">How it works</p>
          <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight sm:text-4xl">Three calm steps. One clear path.</h2>
          <p className="mt-4 text-lg text-muted-foreground">
            You bring the idea. CinemaWin brings the structure, the questions, and the numbers — meeting you wherever your project is today.
          </p>
        </div>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {steps.map((s, i) => (
            <div key={s.title} className="group relative rounded-2xl border border-border/70 bg-card/50 p-7 transition hover:border-primary/40 hover:bg-card">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/12 ring-1 ring-primary/30">
                <s.icon className="h-6 w-6 text-primary" />
              </div>
              <div className="mt-5 flex items-center gap-2">
                <span className="text-xs font-semibold text-muted-foreground">0{i + 1}</span>
                <h3 className="font-heading text-xl font-semibold">{s.title}</h3>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              {i < steps.length - 1 && <ArrowRight className="absolute -right-3 top-1/2 hidden h-5 w-5 text-border md:block" />}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
