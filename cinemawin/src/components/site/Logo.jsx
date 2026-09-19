import { Link } from "react-router-dom";
import { Film } from "lucide-react";

export default function Logo({ className = "" }) {
  return (
    <Link to="/" className={`flex items-center gap-2.5 group ${className}`}>
      <span className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-primary/15 ring-1 ring-primary/40 transition group-hover:bg-primary/25">
        <Film className="h-5 w-5 text-primary" strokeWidth={2.2} />
      </span>
      <span className="font-heading text-xl font-semibold tracking-tight text-foreground">
        Cinema<span className="text-primary">Win</span>
      </span>
    </Link>
  );
}
