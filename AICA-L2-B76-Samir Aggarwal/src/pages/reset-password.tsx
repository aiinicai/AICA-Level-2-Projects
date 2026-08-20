import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { CheckCircle2, Loader2, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Field } from '@/components/common'
import { friendlyError, supabase } from '@/lib/supabase'
import { FIRM_INITIALS, FIRM_NAME } from '@/lib/constants'

type Phase = 'checking' | 'ready' | 'invalid' | 'done'

/**
 * Landing page for the link in a password-reset email.
 *
 * Supabase hands us a short-lived recovery session (the client exchanges the
 * code in the URL because detectSessionInUrl is on). That session is enough to
 * call updateUser, and nothing else — so this route sits outside the guards.
 */
export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>('checking')
  const [linkError, setLinkError] = useState<string | null>(null)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<{ password?: string; confirm?: string }>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true

    // An expired or already-used link comes back as an error in the URL hash
    // rather than as a session, so check that before waiting on anything.
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const query = new URLSearchParams(window.location.search)
    const urlError =
      hash.get('error_description') ??
      hash.get('error') ??
      query.get('error_description') ??
      query.get('error')

    if (urlError) {
      setLinkError(urlError.replace(/\+/g, ' '))
      setPhase('invalid')
      return
    }

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active && session) setPhase('ready')
    })

    void supabase.auth.getSession().then(({ data }) => {
      if (!active) return
      if (data.session) {
        setPhase('ready')
      } else {
        // Give the client a moment to exchange the code in the URL.
        setTimeout(() => {
          if (!active) return
          void supabase.auth.getSession().then(({ data: retry }) => {
            if (!active) return
            setPhase(retry.session ? 'ready' : 'invalid')
          })
        }, 1200)
      }
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [])

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const next: { password?: string; confirm?: string } = {}
    if (password.length < 8) next.password = 'Password must be at least 8 characters.'
    if (password !== confirm) next.confirm = 'Passwords do not match.'
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    const { error } = await supabase.auth.updateUser({ password })
    setSaving(false)

    if (error) {
      toast.error(friendlyError(error))
      return
    }
    setPhase('done')
    toast.success('Password updated')
    setTimeout(() => navigate('/', { replace: true }), 1500)
  }

  return (
    <div className="bg-primary flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <div className="mb-6 flex flex-col items-center gap-3 text-center">
        <div className="bg-accent text-accent-foreground grid size-12 place-items-center rounded-lg text-sm font-bold">
          {FIRM_INITIALS}
        </div>
        <h1 className="text-primary-foreground text-2xl font-semibold tracking-tight">
          {FIRM_NAME}
        </h1>
      </div>

      <Card className="w-full max-w-md">
        {phase === 'checking' ? (
          <CardContent className="flex flex-col items-center gap-3 py-10">
            <Loader2 className="text-muted-foreground size-5 animate-spin" />
            <p className="text-muted-foreground text-sm">Checking your reset link…</p>
          </CardContent>
        ) : phase === 'invalid' ? (
          <>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TriangleAlert className="text-destructive size-5" />
                Link expired or already used
              </CardTitle>
              <CardDescription>
                Reset links are single-use and time-limited. Request a fresh one from the login
                page.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {linkError ? (
                <p className="bg-muted text-muted-foreground rounded-md px-3 py-2 text-xs">
                  {linkError}
                </p>
              ) : null}
              <Button asChild className="w-full">
                <Link to="/auth">Back to sign in</Link>
              </Button>
            </CardContent>
          </>
        ) : phase === 'done' ? (
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <CheckCircle2 className="text-success size-8" />
            <div>
              <p className="font-medium">Password updated</p>
              <p className="text-muted-foreground mt-1 text-sm">Taking you to your workspace…</p>
            </div>
          </CardContent>
        ) : (
          <>
            <CardHeader>
              <CardTitle className="text-lg">Set a new password</CardTitle>
              <CardDescription>
                Choose something you have not used elsewhere. Minimum 8 characters.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleSubmit} noValidate>
                <Field label="New Password" htmlFor="new-password" error={errors.password} required>
                  <Input
                    id="new-password"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </Field>
                <Field
                  label="Confirm New Password"
                  htmlFor="confirm-password"
                  error={errors.confirm}
                  required
                >
                  <Input
                    id="confirm-password"
                    type="password"
                    autoComplete="new-password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                  />
                </Field>
                <Button type="submit" className="w-full" disabled={saving}>
                  {saving ? <Loader2 className="size-4 animate-spin" /> : null}
                  Update password
                </Button>
              </form>
            </CardContent>
          </>
        )}
      </Card>
    </div>
  )
}
