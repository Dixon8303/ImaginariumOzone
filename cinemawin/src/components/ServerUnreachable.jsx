import { AlertTriangle, RefreshCw } from "lucide-react";

// Shown in place of server-backed screens when the FastAPI backend can't be
// reached. The marketing pages never show this — they don't need the server.
export default function ServerUnreachable({ message, onRetry }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background bg-grain px-5">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-8 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/12 ring-1 ring-destructive/30">
          <AlertTriangle className="h-7 w-7 text-destructive" />
        </div>
        <h1 className="mt-5 font-heading text-2xl font-semibold">The server is offline</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {message || "Can't reach the CinemaWin server."} Start the backend with{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 text-xs">./start.sh</code> and try again.
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
          >
            <RefreshCw className="h-4 w-4" /> Retry
          </button>
        )}
      </div>
    </div>
  );
}
