import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import { Toast as ToastPrimitive } from 'radix-ui'
import { AlertTriangle, CheckCircle2, Info, Sparkles, X, XCircle } from 'lucide-react'
import { cn } from '@/lib/cn'

export type ToastTone = 'success' | 'error' | 'warning' | 'info' | 'ai'

export interface ToastOptions {
  title: React.ReactNode
  description?: React.ReactNode
  tone?: ToastTone
  /** Milliseconds before it closes. Errors default to 8 s, others to 4.5 s. */
  duration?: number
  action?: { label: string; onClick: () => void }
}

interface ToastItem extends ToastOptions {
  id: number
  open: boolean
}

export interface ToastApi {
  (options: ToastOptions): number
  success: (title: React.ReactNode, description?: React.ReactNode) => number
  error: (title: React.ReactNode, description?: React.ReactNode) => number
  info: (title: React.ReactNode, description?: React.ReactNode) => number
  dismiss: (id: number) => void
}

const ToastContext = createContext<ToastApi | null>(null)

const TONE: Record<ToastTone, { icon: React.ReactNode; bar: string }> = {
  success: { icon: <CheckCircle2 size={18} className="text-matched" />, bar: 'bg-matched' },
  error: { icon: <XCircle size={18} className="text-unmatched" />, bar: 'bg-unmatched' },
  warning: { icon: <AlertTriangle size={18} className="text-doubtful" />, bar: 'bg-doubtful' },
  info: { icon: <Info size={18} className="text-primary" />, bar: 'bg-primary' },
  ai: { icon: <Sparkles size={18} className="text-ai" />, bar: 'bg-ai' }
}

/** Mounted once in App.tsx; use `useToast()` anywhere below it. */
export function ToastProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [items, setItems] = useState<ToastItem[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setItems((list) => list.map((t) => (t.id === id ? { ...t, open: false } : t)))
    // Leave time for the closing animation before removing it.
    window.setTimeout(() => setItems((list) => list.filter((t) => t.id !== id)), 300)
  }, [])

  const api = useMemo<ToastApi>(() => {
    const show = (options: ToastOptions): number => {
      const id = nextId.current++
      setItems((list) => [...list.slice(-4), { ...options, id, open: true }])
      return id
    }
    return Object.assign(show, {
      success: (title: React.ReactNode, description?: React.ReactNode) => show({ title, description, tone: 'success' }),
      error: (title: React.ReactNode, description?: React.ReactNode) => show({ title, description, tone: 'error' }),
      info: (title: React.ReactNode, description?: React.ReactNode) => show({ title, description, tone: 'info' }),
      dismiss
    })
  }, [dismiss])

  return (
    <ToastContext.Provider value={api}>
      <ToastPrimitive.Provider swipeDirection="right" label="Notification">
        {children}
        {items.map((t) => {
          const tone = TONE[t.tone ?? 'info']
          return (
            <ToastPrimitive.Root
              key={t.id}
              open={t.open}
              onOpenChange={(open) => {
                if (!open) dismiss(t.id)
              }}
              duration={t.duration ?? (t.tone === 'error' ? 8000 : 4500)}
              type={t.tone === 'error' ? 'foreground' : 'background'}
              className="relative flex w-[380px] items-start gap-3 overflow-hidden rounded-xl border border-line bg-white py-3 pr-9 pl-4 shadow-xl data-[state=closed]:animate-[toast-out_200ms_ease-in] data-[state=open]:animate-[toast-in_180ms_ease-out] data-[swipe=end]:animate-[toast-out_150ms_ease-in] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)]"
            >
              <span className={cn('absolute inset-y-0 left-0 w-1', tone.bar)} />
              <span className="mt-[1px]">{tone.icon}</span>
              <div className="min-w-0 flex-1">
                <ToastPrimitive.Title className="text-[13.5px] font-semibold text-ink">{t.title}</ToastPrimitive.Title>
                {t.description && (
                  <ToastPrimitive.Description className="mt-0.5 text-[12.5px] leading-snug text-muted">{t.description}</ToastPrimitive.Description>
                )}
                {t.action && (
                  <ToastPrimitive.Action
                    altText={t.action.label}
                    onClick={t.action.onClick}
                    className="mt-1.5 text-[12.5px] font-semibold text-primary hover:underline"
                  >
                    {t.action.label}
                  </ToastPrimitive.Action>
                )}
              </div>
              <ToastPrimitive.Close aria-label="Close" className="absolute top-2.5 right-2.5 rounded p-0.5 text-muted hover:bg-[#EEF1F5] hover:text-ink">
                <X size={14} />
              </ToastPrimitive.Close>
            </ToastPrimitive.Root>
          )
        })}
        <ToastPrimitive.Viewport className="fixed right-5 bottom-5 z-[60] flex max-h-screen flex-col gap-2.5 outline-none" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  )
}

/** `const toast = useToast(); toast.success('Saved'); toast({ title, description, tone: 'warning' })` */
export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>.')
  return ctx
}
