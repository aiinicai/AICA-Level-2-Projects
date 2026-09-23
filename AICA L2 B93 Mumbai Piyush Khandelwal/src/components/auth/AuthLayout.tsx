import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <div className="flex items-center justify-center bg-background px-4 py-10">
        <div className="w-full max-w-sm space-y-5">
          <Link to="/" className="flex items-center gap-2 text-sm font-semibold">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
              D
            </span>
            The DASH
          </Link>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
            {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
          </div>
          {children}
          {footer && <p className="text-xs text-muted-foreground">{footer}</p>}
        </div>
      </div>

      <aside className="hidden flex-col justify-between bg-primary p-10 text-primary-foreground lg:flex">
        <p className="text-sm opacity-80">Business intelligence for Indian finance teams</p>
        <blockquote className="space-y-4">
          <p className="text-2xl font-semibold leading-snug">
            Every invoice, payment and ledger entry — in one dashboard your whole team can read.
          </p>
          <p className="text-sm opacity-80">
            GST-aware, ₹ formatted in lakhs and crores, and ready for Tally, Zoho, QuickBooks, Razorpay and more.
          </p>
        </blockquote>
        <p className="text-xs opacity-70">This workspace runs on clearly labelled demo data.</p>
      </aside>
    </main>
  );
}
