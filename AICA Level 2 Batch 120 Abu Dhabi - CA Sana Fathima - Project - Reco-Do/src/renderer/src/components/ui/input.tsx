import { Label as LabelPrimitive } from 'radix-ui'
import { cn } from '@/lib/cn'

const FIELD =
  'w-full rounded-lg border border-[#D5DCE5] bg-white px-3 text-[13.5px] text-ink outline-none transition-colors placeholder:text-[#9AA4B2] hover:border-[#C2CBD7] focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-[#F4F6F9] disabled:text-muted aria-invalid:border-unmatched aria-invalid:ring-unmatched/15'

export function Input({ className, type = 'text', ...props }: React.ComponentProps<'input'>): React.JSX.Element {
  return <input type={type} className={cn(FIELD, 'h-9', className)} {...props} />
}

export function Textarea({ className, ...props }: React.ComponentProps<'textarea'>): React.JSX.Element {
  return <textarea className={cn(FIELD, 'min-h-20 py-2 leading-relaxed', className)} {...props} />
}

export function Label({ className, ...props }: React.ComponentProps<typeof LabelPrimitive.Root>): React.JSX.Element {
  return <LabelPrimitive.Root className={cn('text-[13px] font-semibold text-ink select-none', className)} {...props} />
}

/** Label + control + optional hint or error, stacked. */
export function Field({
  label,
  htmlFor,
  hint,
  error,
  className,
  children
}: {
  label: React.ReactNode
  htmlFor?: string
  hint?: React.ReactNode
  error?: React.ReactNode
  className?: string
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? (
        <p role="alert" className="text-[12px] text-unmatched">
          {error}
        </p>
      ) : (
        hint && <p className="text-[12px] leading-snug text-muted">{hint}</p>
      )}
    </div>
  )
}
