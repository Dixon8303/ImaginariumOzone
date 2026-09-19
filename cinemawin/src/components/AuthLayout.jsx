import React from "react";
import Logo from "@/components/site/Logo";

export default function AuthLayout({ icon: Icon, title, subtitle, footer, children }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background bg-grain px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/15 ring-1 ring-primary/40 mb-4">
            <Icon className="w-7 h-7 text-primary" aria-hidden="true" />
          </div>
          <h1 className="font-heading text-3xl font-semibold tracking-tight text-foreground">{title}</h1>
          {subtitle && <p className="text-muted-foreground mt-2">{subtitle}</p>}
        </div>
        <div className="bg-card rounded-2xl shadow-sm border border-border p-8">{children}</div>
        {footer && <p className="text-center text-sm text-muted-foreground mt-6">{footer}</p>}
      </div>
    </div>
  );
}
