import { Link, useLocation } from "react-router-dom";
import { Film, Home } from "lucide-react";

export default function PageNotFound() {
  const location = useLocation();
  const pageName = location.pathname.substring(1);

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-background bg-grain">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/12 ring-1 ring-primary/30">
          <Film className="h-7 w-7 text-primary" />
        </div>
        <div className="space-y-2">
          <h1 className="font-heading text-7xl font-light text-muted-foreground/60">404</h1>
          <div className="h-0.5 w-16 bg-border mx-auto" />
        </div>
        <div className="space-y-3">
          <h2 className="font-heading text-2xl font-semibold">That scene isn't in the script.</h2>
          <p className="text-muted-foreground leading-relaxed">
            The page <span className="font-medium text-foreground">"{pageName || "/"}"</span> could not be found.
          </p>
        </div>
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-5 py-2.5 text-sm font-semibold text-foreground transition hover:bg-card"
        >
          <Home className="h-4 w-4" /> Go home
        </Link>
      </div>
    </div>
  );
}
