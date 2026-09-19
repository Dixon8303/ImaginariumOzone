import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X, LayoutGrid, LogOut } from "lucide-react";
import Logo from "./Logo";
import { useAuth } from "@/lib/AuthContext";

const links = [
  { label: "How it works", to: "/#how" },
  { label: "Features", to: "/#features" },
  { label: "Pricing", to: "/#pricing" },
  { label: "Sample", to: "/sample" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const { isAuthenticated, logout } = useAuth();

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Logo />
        <nav className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <Link key={l.label} to={l.to} className="text-sm font-medium text-muted-foreground transition hover:text-foreground">
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          {isAuthenticated ? (
            <>
              <Link to="/workspace" className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition hover:text-foreground">
                <LayoutGrid className="h-4 w-4" /> Your projects
              </Link>
              <button
                onClick={() => logout(true)}
                className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-card"
              >
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm font-medium text-muted-foreground transition hover:text-foreground">
                Sign in
              </Link>
              <Link to="/get-started" className="rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90 glow-green">
                Start free
              </Link>
            </>
          )}
        </div>
        <button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>
      {open && (
        <div className="border-t border-border/60 px-5 py-4 md:hidden">
          <div className="flex flex-col gap-3">
            {links.map((l) => (
              <Link key={l.label} to={l.to} onClick={() => setOpen(false)} className="text-sm font-medium text-muted-foreground">
                {l.label}
              </Link>
            ))}
            {isAuthenticated ? (
              <>
                <Link to="/workspace" onClick={() => setOpen(false)} className="text-sm font-medium text-muted-foreground">
                  Your projects
                </Link>
                <button onClick={() => logout(true)} className="mt-2 rounded-full border border-border px-5 py-2 text-center text-sm font-semibold text-foreground">
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" onClick={() => setOpen(false)} className="text-sm font-medium text-muted-foreground">
                  Sign in
                </Link>
                <Link to="/get-started" onClick={() => setOpen(false)} className="mt-2 rounded-full bg-primary px-5 py-2 text-center text-sm font-semibold text-primary-foreground">
                  Start free
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
