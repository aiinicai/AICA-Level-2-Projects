import { Component } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Button } from './ui/button'

interface Props {
  children: React.ReactNode
  /** When this value changes (e.g. the route), a previous error is cleared. */
  resetKey?: string
}

interface State {
  error: Error | null
}

/** Catches unexpected screen errors and shows a friendly message instead of a blank window. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidUpdate(prev: Props): void {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null })
  }

  render(): React.ReactNode {
    const { error } = this.state
    if (!error) return this.props.children
    return (
      <div role="alert" className="mx-auto mt-16 max-w-lg rounded-xl border border-line bg-white p-8 text-center">
        <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-full bg-[#FDF1DC] text-doubtful">
          <AlertTriangle size={22} />
        </div>
        <h1 className="text-[18px] font-bold text-ink">Something went wrong on this screen</h1>
        <p className="mt-2 text-[13.5px] leading-relaxed text-muted">
          Your saved reconciliations, mappings and settings are safe. Try again, or go back to the dashboard.
        </p>
        <details className="mt-4 rounded-lg bg-[#F6F8FB] px-3 py-2 text-left text-[12px] text-muted">
          <summary className="cursor-pointer font-semibold">Technical details</summary>
          <pre className="mt-2 font-mono break-words whitespace-pre-wrap">{error.message}</pre>
        </details>
        <div className="mt-5 flex justify-center gap-2.5">
          <Button variant="secondary" onClick={() => this.setState({ error: null })}>
            Try again
          </Button>
          <Button
            onClick={() => {
              window.location.hash = '#/'
              this.setState({ error: null })
            }}
          >
            Go to dashboard
          </Button>
        </div>
      </div>
    )
  }
}
