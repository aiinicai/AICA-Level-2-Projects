import { Slot } from 'radix-ui'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/cn'
import { Spinner } from './spinner'

export const buttonVariants = cva(
  'inline-flex shrink-0 items-center justify-center gap-2 rounded-lg font-semibold whitespace-nowrap transition-colors outline-none select-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-white hover:bg-[#185fba] active:bg-[#14529f]',
        outline: 'border-[1.5px] border-primary bg-white text-primary hover:bg-[#EEF4FD]',
        secondary: 'border border-line bg-white text-ink hover:bg-[#F7F9FB]',
        ghost: 'text-ink hover:bg-[#EEF1F5]',
        danger: 'bg-unmatched text-white hover:bg-[#a52224]',
        'danger-outline': 'border-[1.5px] border-unmatched bg-white text-unmatched hover:bg-[#FDECEC]',
        teal: 'bg-teal text-white hover:bg-[#35ad8d]',
        link: 'h-auto px-0 text-primary hover:underline'
      },
      size: {
        sm: 'h-8 px-3 text-[12.5px]',
        md: 'h-9 px-4 text-[13.5px]',
        lg: 'h-11 px-5 text-[15px]',
        icon: 'h-8 w-8 p-0',
        'icon-sm': 'h-7 w-7 p-0'
      }
    },
    compoundVariants: [{ variant: 'link', className: 'h-auto px-0' }],
    defaultVariants: { variant: 'primary', size: 'md' }
  }
)

export type ButtonProps = React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    /** Render the child element (e.g. a router Link) with button styles. */
    asChild?: boolean
    /** Shows a spinner and disables the button. */
    loading?: boolean
  }

export function Button({ className, variant, size, asChild, loading, disabled, children, type, ...props }: ButtonProps): React.JSX.Element {
  if (asChild) {
    return (
      <Slot.Root className={cn(buttonVariants({ variant, size }), className)} {...props}>
        {children}
      </Slot.Root>
    )
  }
  return (
    <button
      type={type ?? 'button'}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Spinner size={14} className="text-current" />}
      {children}
    </button>
  )
}
