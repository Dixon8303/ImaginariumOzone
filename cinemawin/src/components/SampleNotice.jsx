import { Link } from "react-router-dom";
import { FlaskConical, ArrowRight } from "lucide-react";

// Shown wherever demo output is displayed. Sample text is specific and
// confident enough to be mistaken for a real read of the user's film, so it
// must never appear without this.
export default function SampleNotice({ className = "" }) {
  return (
    <div className={`rounded-xl border border-accent/40 bg-accent/10 p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <FlaskConical className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">This is sample output, not a reading of your film.</p>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            CinemaWin has no AI provider connected, so it is showing example text to demonstrate the
            workflow. The wording below is the same for every project.
          </p>
          <Link
            to="/settings"
            className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-accent hover:underline"
          >
            Connect a provider to analyse your own story <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}
