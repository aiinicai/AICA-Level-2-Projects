import { FIRM_INITIALS, FIRM_NAME } from '@/lib/constants'

/**
 * Shown instead of the app when the Supabase environment variables are absent.
 * Far better than a blank screen and a console stack trace on first deploy.
 */
export default function ConfigNotice() {
  return (
    <div className="bg-primary flex min-h-screen items-center justify-center px-4 py-10">
      <div className="bg-card w-full max-w-lg rounded-lg border p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-3">
          <div className="bg-primary text-primary-foreground grid size-10 shrink-0 place-items-center rounded-md text-xs font-bold">
            {FIRM_INITIALS}
          </div>
          <div>
            <h1 className="font-semibold">{FIRM_NAME}</h1>
            <p className="text-muted-foreground text-sm">Configuration required</p>
          </div>
        </div>

        <p className="text-sm">
          The app cannot reach Supabase because its connection details are missing. Set both
          variables below, then rebuild — Vite bakes them in at <strong>build</strong> time, so a
          restart alone will not pick them up.
        </p>

        <pre className="bg-muted mt-4 overflow-x-auto rounded-md p-3 text-xs">
          <code>{'VITE_SUPABASE_URL=https://<project-ref>.supabase.co\nVITE_SUPABASE_ANON_KEY=<anon public key>'}</code>
        </pre>

        <ul className="text-muted-foreground mt-4 space-y-1.5 text-sm">
          <li>
            <strong className="text-foreground">Locally:</strong> copy <code>.env.example</code> to{' '}
            <code>.env</code> and fill it in.
          </li>
          <li>
            <strong className="text-foreground">On Railway:</strong> add them under Service →
            Variables, then redeploy.
          </li>
          <li>
            Both values are safe to expose in the browser — the anon key is protected by row-level
            security.
          </li>
        </ul>
      </div>
    </div>
  )
}
