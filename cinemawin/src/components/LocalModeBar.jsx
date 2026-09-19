import { Link } from "react-router-dom";
import { HardDrive } from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

// A persistent strip in browser-only mode. Two facts the user must not be
// surprised by later: their work is in this browser alone, and the AI output
// is sample text.
export default function LocalModeBar() {
  const { isLocalMode } = useAuth();
  if (!isLocalMode) return null;

  return (
    <div className="border-b border-accent/30 bg-accent/10">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-2 gap-y-1 px-5 py-2 text-xs">
        <HardDrive className="h-3.5 w-3.5 shrink-0 text-accent" />
        <span className="font-semibold text-foreground">Browser-only mode.</span>
        <span className="text-muted-foreground">
          Projects are saved in this browser and AI output is sample text.
        </span>
        <Link to="/settings" className="font-semibold text-accent hover:underline">
          Set up real AI
        </Link>
      </div>
    </div>
  );
}
