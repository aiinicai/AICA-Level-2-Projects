import { cn } from '@/lib/cn'

export function EmptyState({
  icon,
  title,
  description,
  action,
  className
}: {
  icon?: React.ReactNode
  title: React.ReactNode
  description?: React.ReactNode
  /** Usually a Button. */
  action?: React.ReactNode
  className?: string
}): React.JSX.Element {
  return (
    <div className={cn('flex flex-col items-center justify-center px-6 py-12 text-center', className)}>
      {icon && <div className="mb-3 grid h-12 w-12 place-items-center rounded-full bg-[#EEF4FD] text-primary">{icon}</div>}
      <div className="text-[15px] font-bold text-ink">{title}</div>
      {description && <p className="mt-1 max-w-md text-[13px] leading-relaxed text-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
