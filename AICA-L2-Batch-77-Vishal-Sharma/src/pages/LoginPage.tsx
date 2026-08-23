import { useAuth } from '../auth/AuthProvider'
import ecooLogo from '../assets/ecoo-logo.png'

export function LoginPage() {
  const { signInWithGoogle } = useAuth()

  return (
    <div className="min-h-full flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <img src={ecooLogo} alt="Ecoo" className="h-14 w-auto mx-auto mb-3" />
          <p className="font-serif text-lg font-semibold text-ink">
            <span className="text-amber">Delegation</span>
          </p>
          <p className="text-sm text-ink-soft">Task delegation &amp; tracking</p>
        </div>
        <div className="bg-paper-raised border border-line rounded-lg shadow-sm p-8 flex flex-col items-center gap-5">
          <p className="text-sm text-ink-soft text-center">
            Sign in with the Google account your Admin registered for you.
          </p>
          <button
            onClick={signInWithGoogle}
            className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-bark-gradient text-white text-sm font-medium py-2.5 transition-colors"
          >
            Continue with Google
          </button>
        </div>
      </div>
    </div>
  )
}
