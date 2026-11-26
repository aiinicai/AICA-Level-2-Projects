import { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { Logo } from "@/components/Logo";

function LegalShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-slate-200"><div className="mx-auto max-w-3xl px-5 py-4"><Link to="/"><Logo /></Link></div></header>
      <main className="mx-auto max-w-3xl px-5 py-10">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-slate-500">Template text – have it reviewed by your legal adviser before commercial launch.</p>
        <div className="mt-8 space-y-5 text-sm leading-relaxed text-slate-700 [&_h2]:mt-8 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-slate-900">{children}</div>
      </main>
    </div>
  );
}

export function Terms() {
  return (
    <LegalShell title="Terms of Service">
      <p>3CD Helper is a working-paper tool for Chartered Accountants. It helps prepare information for Form 3CD under the Income-tax Act, 1961. The auditor remains solely responsible for the contents of the tax audit report and must verify every figure before filing.</p>
      <h2>Accounts</h2><p>You are responsible for activity under your account and your firm workspace, including access given to staff members.</p>
      <h2>Your data</h2><p>Data you upload belongs to you and your clients. We process it only to provide the service. You can export or delete it at any time.</p>
      <h2>Acceptable use</h2><p>Do not upload data you are not authorised to process, attempt to access other firms' data, or disrupt the service.</p>
      <h2>Plans and billing</h2><p>Paid plans, where applicable, renew automatically until cancelled. Prices include or exclude GST as shown on the pricing page.</p>
      <h2>Limitation of liability</h2><p>The service is provided "as is". We are not liable for penalties, interest or losses arising from reliance on outputs without professional verification.</p>
    </LegalShell>
  );
}

export function Privacy() {
  return (
    <LegalShell title="Privacy Policy">
      <p>This policy explains how 3CD Helper processes personal data in line with the Digital Personal Data Protection Act, 2023.</p>
      <h2>What we collect</h2><p>Account details (name, email), firm details, and the accounting data you upload for your clients, plus basic usage logs (sign-in time and device).</p>
      <h2>Why</h2><p>To provide the service, secure your account, keep an audit trail for your firm, and support you.</p>
      <h2>Where it is stored</h2><p>Data is stored in a managed cloud database with row-level security so each firm can access only its own data. Uploaded files are kept in private storage.</p>
      <h2>Your rights</h2><p>You may access, correct, export or delete your data, and withdraw consent, from within the app or by contacting us.</p>
      <h2>Retention</h2><p>Data is kept while your account is active and deleted on request, subject to legal retention obligations.</p>
    </LegalShell>
  );
}
