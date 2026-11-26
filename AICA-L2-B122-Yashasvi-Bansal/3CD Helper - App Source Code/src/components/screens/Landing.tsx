import { Link } from "@tanstack/react-router";
import { ArrowRight, CheckCircle2, FileSpreadsheet, ShieldCheck, Users, Upload, Sparkles, Lock, Smartphone, FileDown, Check } from "lucide-react";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";

const FEATURES = [
  { icon: Upload, title: "Upload from any software", text: "Tally XML, Busy, Marg, Zoho, QuickBooks, SAP, Excel, CSV, TXT or GSTR-2B JSON. Smart column mapping remembers each client." },
  { icon: ShieldCheck, title: "GSTIN validation", text: "Format and checksum validation for every GSTIN. Invalid numbers are flagged for review, never silently dropped." },
  { icon: Sparkles, title: "Auto classification", text: "Exempt, composition, other registered and unregistered buckets from a reusable party master that carries forward every year." },
  { icon: FileSpreadsheet, title: "Clause 44 & Clause 31 reports", text: "Clause 44 in the Form 3CD layout with reconciliation to P&L. Clause 31 loans & deposits with Note-1 codes, maximum outstanding and a/c payee details." },
  { icon: Users, title: "Built for CA firms", text: "Partners, staff and viewers with roles. See who prepared, edited and reviewed every item, with full edit history." },
  { icon: Lock, title: "Private & secure", text: "Each firm's data is isolated with row-level security. Final years are locked against accidental changes." },
];

const PLANS = [
  { name: "Free", price: "₹0", period: "forever", features: ["5 clients", "1 user", "Clause 44 & 31 reports", "Excel export"], cta: "Start free" },
  { name: "Pro", price: "₹999", period: "per month", highlight: true, features: ["200 clients", "10 users", "All exports", "Email & client upload links", "GSTR-2B matching", "Priority support"], cta: "Start 14-day trial" },
  { name: "Enterprise", price: "Custom", period: "", features: ["Unlimited clients & users", "White-label branding", "Dedicated support", "Custom integrations"], cta: "Contact us" },
];

const FAQ = [
  ["Which clause does 3CD Helper prepare?", "Clause 44 – break-up of total expenditure of entities registered or not registered under GST, and Clause 31 – loans and deposits taken or accepted and repaid, with the official Note-1 codes."],
  ["How do I export data from Tally?", "Use the free 3CD Tally Connector for Chrome to bring data straight from TallyPrime, or export the Day Book as Excel or XML and upload it. 3CD Helper maps the columns automatically."],
  ["Does it file Form 3CD for me?", "No. It prepares the Clause 44 and Clause 31 tables and working papers. You review and enter the figures in the Income-tax e-filing utility."],
  ["Can my staff use it?", "Yes. Invite staff by email, assign client years to them, and review their work before marking it Final."],
];

export default function Landing() {
  const { session } = useAuth();
  return (
    <div className="bg-white">
      <header className="sticky top-0 z-30 border-b border-slate-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <Logo />
          <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
            <a href="#features" className="hover:text-navy-900">Features</a>
            <a href="#pricing" className="hover:text-navy-900">Pricing</a>
            <a href="#faq" className="hover:text-navy-900">FAQ</a>
          </nav>
          <div className="flex items-center gap-2">
            {session ? (
              <Link to="/app"><Button>Open app <ArrowRight className="h-4 w-4" /></Button></Link>
            ) : (
              <>
                <Link to="/login" className="hidden sm:block"><Button variant="ghost">Sign in</Button></Link>
                <Link to="/signup"><Button>Get started</Button></Link>
              </>
            )}
          </div>
        </div>
      </header>

      <section className="relative overflow-hidden bg-navy-950 text-white">
        <div className="pointer-events-none absolute -left-32 top-10 h-96 w-96 rounded-full bg-navy-600/30 blur-3xl" />
        <div className="pointer-events-none absolute -right-20 bottom-0 h-80 w-80 rounded-full bg-gold-400/10 blur-3xl" />
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 py-20 lg:grid-cols-2 lg:py-28">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-navy-100">
              <Sparkles className="h-3.5 w-3.5 text-gold-400" /> For tax audits u/s 44AB
            </div>
            <h1 className="mt-6 text-4xl font-extrabold leading-[1.1] tracking-tight sm:text-5xl">
              Form 3CD Clause 44 & 31,<br /><span className="text-gold-400">done right. In minutes.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg text-navy-100">
              Upload your client's ledgers from any accounting software. 3CD Helper validates GSTINs, classifies every rupee of expenditure and gives you the Clause 44 and Clause 31 tables in the prescribed format.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/signup"><Button variant="gold" size="lg">Start free trial <ArrowRight className="h-4 w-4" /></Button></Link>
              <a href="#features"><Button size="lg" variant="onDark">See features</Button></a>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-navy-200">
              <span className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-gold-400" />No card required</span>
              <span className="flex items-center gap-2"><Smartphone className="h-4 w-4 text-gold-400" />Works on phone & desktop</span>
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white p-5 text-slate-900 shadow-2xl">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Clause 44 · AY 2025-26</div>
                <div className="mt-0.5 font-semibold">Sharma Textiles Pvt Ltd</div>
              </div>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">Reconciled</span>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
              {[["Exempt supplies", "₹4,12,500", "bg-sky-50"], ["Composition", "₹1,86,000", "bg-amber-50"], ["Other registered", "₹2,48,96,350", "bg-emerald-50"], ["Unregistered", "₹18,42,900", "bg-slate-100"]].map(([l, v, c]) => (
                <div key={l} className={`rounded-xl p-3 ${c}`}><div className="text-xs text-slate-500">{l}</div><div className="mt-1 font-bold tabular-nums">{v}</div></div>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between rounded-xl bg-navy-950 p-4 text-white">
              <span className="text-sm">Total expenditure</span><span className="text-lg font-bold tabular-nums">₹2,73,37,750</span>
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-500"><FileDown className="h-4 w-4" />Excel · CSV · JSON · Print-ready PDF</div>
          </div>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-5 py-20">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-bold tracking-tight text-slate-900">Everything a CA firm needs for Clause 44 & 31</h2>
          <p className="mt-3 text-slate-600">From raw ledger to a reviewed, locked working paper – with a clear audit trail.</p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-2xl border border-slate-200 p-6 transition hover:shadow-lg">
              <div className="inline-flex rounded-xl bg-navy-50 p-3 text-navy-800"><f.icon className="h-6 w-6" /></div>
              <h3 className="mt-4 font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-[#f6f8fc] py-20">
        <div className="mx-auto max-w-7xl px-5">
          <h2 className="text-center text-3xl font-bold tracking-tight">How it works</h2>
          <div className="mt-12 grid gap-6 md:grid-cols-4">
            {["Add client & assessment year", "Upload ledger from any software", "Review flags, exclusions & party master", "Export the Clause 44 & 31 reports"].map((s, i) => (
              <div key={s} className="rounded-2xl bg-white p-6 shadow-card">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-navy-950 text-sm font-bold text-white">{i + 1}</div>
                <p className="mt-4 font-medium text-slate-800">{s}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="mx-auto max-w-7xl px-5 py-20">
        <h2 className="text-center text-3xl font-bold tracking-tight">Simple pricing</h2>
        <p className="mt-3 text-center text-slate-600">Start free. Upgrade when your practice grows.</p>
        <div className="mx-auto mt-12 grid max-w-5xl gap-6 md:grid-cols-3">
          {PLANS.map((p) => (
            <div key={p.name} className={`flex flex-col rounded-2xl border p-7 ${p.highlight ? "border-navy-900 bg-navy-950 text-white shadow-xl" : "border-slate-200"}`}>
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">{p.name}</h3>
                {p.highlight && <span className="rounded-full bg-gold-400 px-2 py-0.5 text-xs font-semibold text-navy-950">Popular</span>}
              </div>
              <div className="mt-4"><span className="text-4xl font-extrabold">{p.price}</span> <span className={p.highlight ? "text-navy-200" : "text-slate-500"}>{p.period}</span></div>
              <ul className="mt-6 flex-1 space-y-3 text-sm">
                {p.features.map((f) => <li key={f} className="flex gap-2"><Check className={`h-4 w-4 shrink-0 ${p.highlight ? "text-gold-400" : "text-emerald-600"}`} />{f}</li>)}
              </ul>
              <Link to="/signup" className="mt-8"><Button className="w-full" variant={p.highlight ? "gold" : "outline"}>{p.cta}</Button></Link>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-xs text-slate-500">Prices are indicative and exclusive of GST. Billing launches soon; all new accounts get a free Pro trial.</p>
      </section>

      <section id="faq" className="bg-[#f6f8fc] py-20">
        <div className="mx-auto max-w-3xl px-5">
          <h2 className="text-center text-3xl font-bold tracking-tight">Frequently asked questions</h2>
          <div className="mt-10 space-y-3">
            {FAQ.map(([q, a]) => (
              <details key={q} className="group rounded-xl border border-slate-200 bg-white p-5">
                <summary className="cursor-pointer list-none font-semibold text-slate-900">{q}</summary>
                <p className="mt-3 text-sm text-slate-600">{a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-200">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-5 py-8 text-sm text-slate-500 sm:flex-row">
          <Logo />
          <div className="flex gap-6"><Link to="/terms" className="hover:text-slate-900">Terms</Link><Link to="/privacy" className="hover:text-slate-900">Privacy</Link></div>
          <span>© {new Date().getFullYear()} 3CD Helper</span>
        </div>
      </footer>
    </div>
  );
}
