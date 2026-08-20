import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Field } from '@/components/common'
import { FullPageLoader } from '@/components/route-guards'
import { useAuth } from '@/components/auth-provider'
import { friendlyError, supabase } from '@/lib/supabase'
import { FIRM_INITIALS, FIRM_NAME, FIRM_TAGLINE } from '@/lib/constants'

type SignInErrors = { email?: string; password?: string }
type SignUpErrors = SignInErrors & { fullName?: string; confirm?: string }

export default function AuthPage() {
  const { session, loading } = useAuth()

  const [signInEmail, setSignInEmail] = useState('')
  const [signInPassword, setSignInPassword] = useState('')
  const [signInErrors, setSignInErrors] = useState<SignInErrors>({})
  const [signingIn, setSigningIn] = useState(false)

  const [fullName, setFullName] = useState('')
  const [signUpEmail, setSignUpEmail] = useState('')
  const [signUpPassword, setSignUpPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [signUpErrors, setSignUpErrors] = useState<SignUpErrors>({})
  const [signingUp, setSigningUp] = useState(false)

  const [forgotOpen, setForgotOpen] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotError, setForgotError] = useState<string | null>(null)
  const [forgotSending, setForgotSending] = useState(false)
  const [forgotSent, setForgotSent] = useState(false)

  if (loading) return <FullPageLoader />
  if (session) return <Navigate to="/" replace />

  async function handleSignIn(event: React.FormEvent) {
    event.preventDefault()
    const errors: SignInErrors = {}
    if (!signInEmail.trim()) errors.email = 'Email is required.'
    if (!signInPassword) errors.password = 'Password is required.'
    setSignInErrors(errors)
    if (Object.keys(errors).length) return

    setSigningIn(true)
    const { error } = await supabase.auth.signInWithPassword({
      email: signInEmail.trim().toLowerCase(),
      password: signInPassword,
    })
    setSigningIn(false)

    if (error) {
      const message = friendlyError(error)
      setSignInErrors({ password: message })
      toast.error(message)
      return
    }
    toast.success('Signed in')
  }

  async function handleForgotPassword(event: React.FormEvent) {
    event.preventDefault()
    const email = forgotEmail.trim().toLowerCase()
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setForgotError('Enter a valid email address.')
      return
    }
    setForgotError(null)
    setForgotSending(true)

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    setForgotSending(false)

    if (error) {
      setForgotError(friendlyError(error))
      return
    }
    // Deliberately not revealing whether the address exists.
    setForgotSent(true)
  }

  async function handleSignUp(event: React.FormEvent) {
    event.preventDefault()
    const email = signUpEmail.trim().toLowerCase()
    const errors: SignUpErrors = {}
    if (!fullName.trim()) errors.fullName = 'Full name is required.'
    if (!email) errors.email = 'Email is required.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Enter a valid email address.'
    if (signUpPassword.length < 8) errors.password = 'Password must be at least 8 characters.'
    if (signUpPassword !== confirmPassword) errors.confirm = 'Passwords do not match.'
    setSignUpErrors(errors)
    if (Object.keys(errors).length) return

    setSigningUp(true)

    // Ask the database whether this email is on the admin's invite list BEFORE
    // attempting signup, so the user sees a sentence instead of a trigger error.
    const { data: allowed, error: rpcError } = await supabase.rpc('is_email_allowed', {
      _email: email,
    })

    if (rpcError) {
      setSigningUp(false)
      toast.error(friendlyError(rpcError))
      return
    }

    if (!allowed) {
      setSigningUp(false)
      const message =
        'This email is not authorised. Please ask your firm administrator to add you first.'
      setSignUpErrors({ email: message })
      toast.error(message)
      return
    }

    const { error } = await supabase.auth.signUp({
      email,
      password: signUpPassword,
      options: { data: { full_name: fullName.trim() } },
    })
    setSigningUp(false)

    if (error) {
      const message = friendlyError(error)
      setSignUpErrors({ email: message })
      toast.error(message)
      return
    }
    toast.success('Account created. Signing you in…')
  }

  return (
    <div className="bg-primary flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <div className="mb-6 flex flex-col items-center gap-3 text-center">
        <div className="bg-accent text-accent-foreground grid size-12 place-items-center rounded-lg text-sm font-bold">
          {FIRM_INITIALS}
        </div>
        <div>
          <h1 className="text-primary-foreground text-2xl font-semibold tracking-tight">
            {FIRM_NAME}
          </h1>
          <p className="text-primary-foreground/70 mt-1 text-sm">{FIRM_TAGLINE}</p>
        </div>
      </div>

      <Card className="w-full max-w-md">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Welcome</CardTitle>
          <CardDescription>Sign in to your firm account to continue.</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="signin">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="signin">Sign In</TabsTrigger>
              <TabsTrigger value="signup">Sign Up</TabsTrigger>
            </TabsList>

            <TabsContent value="signin" className="mt-4">
              <form className="space-y-4" onSubmit={handleSignIn} noValidate>
                <Field label="Email" htmlFor="signin-email" error={signInErrors.email} required>
                  <Input
                    id="signin-email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@firm.in"
                    value={signInEmail}
                    onChange={(e) => setSignInEmail(e.target.value)}
                  />
                </Field>
                <Field
                  label="Password"
                  htmlFor="signin-password"
                  error={signInErrors.password}
                  required
                >
                  <Input
                    id="signin-password"
                    type="password"
                    autoComplete="current-password"
                    value={signInPassword}
                    onChange={(e) => setSignInPassword(e.target.value)}
                  />
                </Field>
                <div className="flex justify-end">
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-foreground text-xs underline underline-offset-2"
                    onClick={() => {
                      setForgotEmail(signInEmail.trim())
                      setForgotError(null)
                      setForgotSent(false)
                      setForgotOpen(true)
                    }}
                  >
                    Forgot password?
                  </button>
                </div>
                <Button type="submit" className="w-full" disabled={signingIn}>
                  {signingIn ? <Loader2 className="size-4 animate-spin" /> : null}
                  Sign In
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="signup" className="mt-4">
              <form className="space-y-4" onSubmit={handleSignUp} noValidate>
                <Field label="Full Name" htmlFor="signup-name" error={signUpErrors.fullName} required>
                  <Input
                    id="signup-name"
                    autoComplete="name"
                    placeholder="Ruchika Aggarwal"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </Field>
                <Field
                  label="Email"
                  htmlFor="signup-email"
                  error={signUpErrors.email}
                  hint="Use the exact email your administrator added for you."
                  required
                >
                  <Input
                    id="signup-email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@firm.in"
                    value={signUpEmail}
                    onChange={(e) => setSignUpEmail(e.target.value)}
                  />
                </Field>
                <Field
                  label="Password"
                  htmlFor="signup-password"
                  error={signUpErrors.password}
                  hint="Minimum 8 characters."
                  required
                >
                  <Input
                    id="signup-password"
                    type="password"
                    autoComplete="new-password"
                    value={signUpPassword}
                    onChange={(e) => setSignUpPassword(e.target.value)}
                  />
                </Field>
                <Field
                  label="Confirm Password"
                  htmlFor="signup-confirm"
                  error={signUpErrors.confirm}
                  required
                >
                  <Input
                    id="signup-confirm"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </Field>
                <Button type="submit" className="w-full" disabled={signingUp}>
                  {signingUp ? <Loader2 className="size-4 animate-spin" /> : null}
                  Create Account
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <p className="text-primary-foreground/50 mt-6 text-center text-xs">
        Access is restricted to staff of {FIRM_NAME}.
      </p>

      <Dialog open={forgotOpen} onOpenChange={setForgotOpen}>
        <DialogContent className="sm:max-w-md">
          {forgotSent ? (
            <>
              <DialogHeader>
                <DialogTitle>Check your email</DialogTitle>
                <DialogDescription>
                  If an account exists for that address, a reset link is on its way. The link works
                  once and expires shortly.
                </DialogDescription>
              </DialogHeader>
              <p className="text-muted-foreground text-sm">
                Nothing after a few minutes? Check the spam folder, then ask your administrator —
                they can reset it directly.
              </p>
              <DialogFooter>
                <Button onClick={() => setForgotOpen(false)}>Close</Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle>Reset your password</DialogTitle>
                <DialogDescription>
                  We will email you a link to choose a new one.
                </DialogDescription>
              </DialogHeader>
              <form className="space-y-4" onSubmit={handleForgotPassword} noValidate>
                <Field label="Email" htmlFor="forgot-email" error={forgotError} required>
                  <Input
                    id="forgot-email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@firm.in"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                  />
                </Field>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setForgotOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={forgotSending}>
                    {forgotSending ? <Loader2 className="size-4 animate-spin" /> : null}
                    Send reset link
                  </Button>
                </DialogFooter>
              </form>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
