import { Link } from "react-router-dom";
import Logo from "./Logo";

export default function Footer() {
  return (
    <footer className="border-t border-border/60 bg-sidebar">
      <div className="mx-auto max-w-6xl px-5 py-12">
        <div className="flex flex-col items-start justify-between gap-8 md:flex-row">
          <div className="max-w-xs">
            <Logo />
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              The calm, guided workspace that takes a film from first spark to investor-ready package — without the jargon.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-10 sm:grid-cols-3">
            <div>
              <p className="text-sm font-semibold text-foreground">Product</p>
              <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                <li><Link to="/#how" className="hover:text-foreground">How it works</Link></li>
                <li><Link to="/#pricing" className="hover:text-foreground">Pricing</Link></li>
                <li><Link to="/sample" className="hover:text-foreground">Sample project</Link></li>
              </ul>
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">Company</p>
              <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                <li><Link to="/#faq" className="hover:text-foreground">FAQ</Link></li>
                <li><Link to="/get-started" className="hover:text-foreground">Get started</Link></li>
              </ul>
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">Legal</p>
              <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                <li><span className="hover:text-foreground cursor-pointer">Terms</span></li>
                <li><span className="hover:text-foreground cursor-pointer">Privacy</span></li>
              </ul>
            </div>
          </div>
        </div>
        <div className="mt-10 border-t border-border/60 pt-6 text-sm text-muted-foreground">
          © {new Date().getFullYear()} CinemaWin. Crafted for storytellers.
        </div>
      </div>
    </footer>
  );
}
