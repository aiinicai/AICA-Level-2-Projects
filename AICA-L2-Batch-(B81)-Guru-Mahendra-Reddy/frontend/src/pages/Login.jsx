import React, { useState } from 'react'
import { useApp } from '../lib/store'
import { Icon } from '../components/ui'

export default function Login() {
  const { signIn } = useApp()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function submit(e) {
    e.preventDefault()
    setBusy(true); setError(null)
    try { await signIn(email.trim(), password) }
    catch (err) { setError(err.message || 'Could not sign you in.'); setBusy(false) }
  }

  return (
    <div className="min-h-full grid lg:grid-cols-[1.05fr_1fr]">
      {/* Left — what the tool is for */}
      <div className="hidden lg:flex flex-col justify-between bg-navy-700 text-white p-10 xl:p-14">
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-lg bg-white/15 grid place-items-center">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="white"
                 strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 17l6-6 4 4 8-8" /><path d="M15 6h6v6" />
            </svg>
          </span>
          <span className="font-semibold text-[17px] tracking-tight">Cash Runway</span>
        </div>

        <div className="max-w-md">
          <h1 className="text-[30px] xl:text-[34px] font-semibold leading-tight tracking-tight">
            Cash command for founders and CFOs.
          </h1>
          <p className="mt-4 text-navy-100 leading-relaxed text-[14px]">
            Twelve screens, one question each. Every number carries its basis and
            its as-on date, and every figure is traceable to the entries behind it.
          </p>
          <ul className="mt-8 space-y-3">
            {[
              'Runway, burn and the cash-out date, on one screen',
              'A 13-week calendar built from named invoices and named payments',
              'Statutory dues tracked separately — they are first charge',
              'Alerts by SMS before a problem becomes a crisis',
            ].map((t) => (
              <li key={t} className="flex items-start gap-2.5 text-[13px] text-navy-100">
                <span className="mt-0.5 w-4 h-4 rounded-full bg-white/15 grid place-items-center shrink-0">
                  <Icon name="check" size={11} strokeWidth={3} />
                </span>
                {t}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-2xs text-navy-200">
          Runs locally against your own accounting data. Nothing leaves your network.
        </p>
      </div>

      {/* Right — the gate */}
      <div className="flex items-center justify-center p-6 sm:p-10 bg-canvas">
        <div className="w-full max-w-[380px]">
          <div className="lg:hidden flex items-center gap-2.5 mb-8">
            <span className="w-8 h-8 rounded-lg bg-navy-700 grid place-items-center">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="white"
                   strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 17l6-6 4 4 8-8" /><path d="M15 6h6v6" />
              </svg>
            </span>
            <span className="font-semibold text-[17px] tracking-tight">Cash Runway</span>
          </div>

          <h2 className="text-[22px] font-semibold tracking-tight">Sign in</h2>
          <p className="text-[13px] text-ink-muted mt-1">
            Your role decides what you can change. Board access is read-only.
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            <label className="block">
              <span className="label block mb-1.5">Email</span>
              <input type="email" required autoFocus autoComplete="username"
                     value={email} onChange={(e) => setEmail(e.target.value)}
                     placeholder="you@company.in" className="input" />
            </label>
            <label className="block">
              <span className="label block mb-1.5">Password</span>
              <input type="password" required autoComplete="current-password"
                     value={password} onChange={(e) => setPassword(e.target.value)}
                     placeholder="••••••••" className="input" />
            </label>

            {error && (
              <div className="rounded-lg border border-red-line bg-red-bg px-3 py-2.5
                              flex items-start gap-2 text-[13px] text-red">
                <Icon name="alert" size={15} className="mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button type="submit" disabled={busy} className="btn-primary w-full justify-center py-2.5">
              {busy ? 'Signing in…' : 'Sign in'}
              {!busy && <Icon name="chevronRight" size={15} />}
            </button>
          </form>

          <div className="mt-8 rounded-lg border border-line bg-white px-4 py-3">
            <p className="label mb-2">Demonstration sign-in</p>
            <div className="space-y-1.5 text-2xs text-ink-muted">
              <p><span className="font-semibold text-ink-soft">guru@northwindrobotics.in</span> — CFO</p>
              <p><span className="font-semibold text-ink-soft">rohan@northstarventures.in</span> — Board, read-only</p>
              <p className="pt-1">Password for both: <span className="font-semibold text-ink-soft">cashrunway</span></p>
            </div>
            <button type="button"
                    onClick={() => { setEmail('guru@northwindrobotics.in'); setPassword('cashrunway') }}
                    className="btn-ghost btn-sm mt-3 w-full justify-center">
              Fill in the CFO account
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
