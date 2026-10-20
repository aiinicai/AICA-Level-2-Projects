import { Tooltip as TooltipPrimitive } from 'radix-ui'
import { cn } from '@/lib/cn'

/** Mounted once in App.tsx. */
export function TooltipProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <TooltipPrimitive.Provider delayDuration={300} skipDelayDuration={200}>
      {children}
    </TooltipPrimitive.Provider>
  )
}

export interface TooltipProps {
  content: React.ReactNode
  /** A single focusable element (button, link…). */
  children: React.ReactElement
  side?: 'top' | 'right' | 'bottom' | 'left'
  align?: 'start' | 'center' | 'end'
  className?: string
  /** Render nothing extra when false/empty, e.g. to show a tooltip only when a button is disabled. */
  disabled?: boolean
}

export function Tooltip({ content, children, side = 'top', align = 'center', className, disabled }: TooltipProps): React.JSX.Element {
  if (disabled || content === null || content === undefined || content === '') return children
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          align={align}
          sideOffset={6}
          collisionPadding={8}
          className={cn(
            'z-50 max-w-[320px] rounded-md bg-[#1A2433] px-2.5 py-1.5 text-[12px] leading-snug text-white shadow-lg data-[state=delayed-open]:animate-[fade-in_100ms_ease-out]',
            className
          )}
        >
          {content}
          <TooltipPrimitive.Arrow className="fill-[#1A2433]" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  )
}
