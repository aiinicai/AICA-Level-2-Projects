import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { AlertDialog as AlertPrimitive, Dialog as DialogPrimitive } from 'radix-ui'
import { X } from 'lucide-react'
import { cn } from '@/lib/cn'
import { buttonVariants } from './button'

const OVERLAY = 'fixed inset-0 z-50 bg-[#0F2A44]/40 data-[state=open]:animate-[fade-in_120ms_ease-out]'
const PANEL =
  'fixed top-1/2 left-1/2 z-50 flex max-h-[88vh] w-[min(92vw,var(--dialog-width,520px))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-xl border border-line bg-white shadow-2xl outline-none data-[state=open]:animate-[dialog-in_140ms_ease-out]'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogClose = DialogPrimitive.Close

export interface DialogContentProps extends React.ComponentProps<typeof DialogPrimitive.Content> {
  /** Panel width in px (default 520). */
  width?: number
  /** Hide the × button in the corner. */
  hideClose?: boolean
}

export function DialogContent({ className, width, hideClose, style, children, ...props }: DialogContentProps): React.JSX.Element {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className={OVERLAY} />
      <DialogPrimitive.Content
        className={cn(PANEL, className)}
        style={{ ...(width ? ({ '--dialog-width': `${width}px` } as React.CSSProperties) : {}), ...style }}
        {...props}
      >
        {children}
        {!hideClose && (
          <DialogPrimitive.Close
            className="absolute top-3.5 right-3.5 grid h-7 w-7 place-items-center rounded-md text-muted outline-none hover:bg-[#EEF1F5] hover:text-ink focus-visible:ring-2 focus-visible:ring-primary/40"
            aria-label="Close"
          >
            <X size={16} />
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

export function DialogHeader({ className, ...props }: React.ComponentProps<'div'>): React.JSX.Element {
  return <div className={cn('flex flex-col gap-1 px-6 pt-5 pb-3 pr-12', className)} {...props} />
}

export function DialogBody({ className, ...props }: React.ComponentProps<'div'>): React.JSX.Element {
  return <div className={cn('min-h-0 flex-1 overflow-y-auto px-6 py-2', className)} {...props} />
}

export function DialogFooter({ className, ...props }: React.ComponentProps<'div'>): React.JSX.Element {
  return <div className={cn('flex justify-end gap-2.5 px-6 pt-3 pb-5', className)} {...props} />
}

export function DialogTitle({ className, ...props }: React.ComponentProps<typeof DialogPrimitive.Title>): React.JSX.Element {
  return <DialogPrimitive.Title className={cn('text-[17px] font-bold text-ink', className)} {...props} />
}

export function DialogDescription({ className, ...props }: React.ComponentProps<typeof DialogPrimitive.Description>): React.JSX.Element {
  return <DialogPrimitive.Description className={cn('text-[13.5px] leading-relaxed text-muted', className)} {...props} />
}

// ───────────────────────── Confirm (AlertDialog) ─────────────────────────

export interface ConfirmOptions {
  title: React.ReactNode
  description?: React.ReactNode
  confirmLabel?: string
  cancelLabel?: string
  /** "danger" makes the confirm button red (delete, forget key…). */
  tone?: 'primary' | 'danger'
}

export interface ConfirmDialogProps extends ConfirmOptions {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}

/** Controlled confirmation dialog. For a one-line promise API, use `useConfirm()` instead. */
export function ConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'primary'
}: ConfirmDialogProps): React.JSX.Element {
  return (
    <AlertPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <AlertPrimitive.Portal>
        <AlertPrimitive.Overlay className={OVERLAY} />
        <AlertPrimitive.Content className={cn(PANEL, '[--dialog-width:440px]')}>
          <div className="flex flex-col gap-1.5 px-6 pt-5 pb-2">
            <AlertPrimitive.Title className="text-[17px] font-bold text-ink">{title}</AlertPrimitive.Title>
            {description ? (
              <AlertPrimitive.Description className="text-[13.5px] leading-relaxed text-muted">{description}</AlertPrimitive.Description>
            ) : (
              <AlertPrimitive.Description className="sr-only">Please confirm.</AlertPrimitive.Description>
            )}
          </div>
          <div className="flex justify-end gap-2.5 px-6 pt-3 pb-5">
            <AlertPrimitive.Cancel className={buttonVariants({ variant: 'secondary' })}>{cancelLabel}</AlertPrimitive.Cancel>
            <AlertPrimitive.Action className={buttonVariants({ variant: tone === 'danger' ? 'danger' : 'primary' })} onClick={onConfirm}>
              {confirmLabel}
            </AlertPrimitive.Action>
          </div>
        </AlertPrimitive.Content>
      </AlertPrimitive.Portal>
    </AlertPrimitive.Root>
  )
}

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>
const ConfirmContext = createContext<ConfirmFn | null>(null)

/** Provides `useConfirm()`. Mounted once in App.tsx. */
export function ConfirmProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [state, setState] = useState<(ConfirmOptions & { open: boolean }) | null>(null)
  const resolver = useRef<((ok: boolean) => void) | null>(null)

  const confirm = useCallback<ConfirmFn>((options) => {
    resolver.current?.(false)
    setState({ ...options, open: true })
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve
    })
  }, [])

  const settle = (ok: boolean): void => {
    resolver.current?.(ok)
    resolver.current = null
    setState((s) => (s ? { ...s, open: false } : s))
  }

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {state && (
        <ConfirmDialog
          {...state}
          onOpenChange={(open) => {
            if (!open) settle(false)
          }}
          onConfirm={() => settle(true)}
        />
      )}
    </ConfirmContext.Provider>
  )
}

/** `const confirm = useConfirm(); if (await confirm({ title: 'Delete?', tone: 'danger' })) …` */
export function useConfirm(): ConfirmFn {
  const ctx = useContext(ConfirmContext)
  if (!ctx) throw new Error('useConfirm must be used inside <ConfirmProvider>.')
  return ctx
}
