import { useId } from 'react'
import { Checkbox as CheckboxPrimitive, Switch as SwitchPrimitive } from 'radix-ui'
import { Check, Minus } from 'lucide-react'
import { cn } from '@/lib/cn'

export type CheckedState = boolean | 'indeterminate'

export interface CheckboxProps extends Omit<React.ComponentProps<typeof CheckboxPrimitive.Root>, 'children'> {
  /** Optional text shown to the right; clicking it toggles the box. */
  label?: React.ReactNode
  description?: React.ReactNode
}

export function Checkbox({ className, label, description, id, ...props }: CheckboxProps): React.JSX.Element {
  const autoId = useId()
  const boxId = id ?? autoId
  const box = (
    <CheckboxPrimitive.Root
      id={boxId}
      className={cn(
        'peer grid h-[18px] w-[18px] shrink-0 place-items-center rounded-[5px] border-[1.5px] border-[#B9C3D0] bg-white text-white outline-none transition-colors hover:border-primary focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=indeterminate]:border-primary data-[state=indeterminate]:bg-primary',
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator>
        {props.checked === 'indeterminate' ? <Minus size={12} strokeWidth={3.5} /> : <Check size={12} strokeWidth={3.5} />}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
  if (!label) return box
  return (
    <div className="flex items-start gap-2.5">
      <div className="pt-[1px]">{box}</div>
      <label htmlFor={boxId} className="cursor-pointer text-[13.5px] leading-snug text-ink select-none peer-disabled:cursor-not-allowed">
        {label}
        {description && <span className="mt-0.5 block text-[12px] text-muted">{description}</span>}
      </label>
    </div>
  )
}

export interface SwitchProps extends Omit<React.ComponentProps<typeof SwitchPrimitive.Root>, 'children'> {
  label?: React.ReactNode
  description?: React.ReactNode
}

export function Switch({ className, label, description, id, ...props }: SwitchProps): React.JSX.Element {
  const autoId = useId()
  const switchId = id ?? autoId
  const control = (
    <SwitchPrimitive.Root
      id={switchId}
      className={cn(
        'relative inline-flex h-[22px] w-[38px] shrink-0 items-center rounded-full bg-[#CBD3DE] outline-none transition-colors focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary',
        className
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb className="block h-[18px] w-[18px] translate-x-[2px] rounded-full bg-white shadow transition-transform data-[state=checked]:translate-x-[18px]" />
    </SwitchPrimitive.Root>
  )
  if (!label) return control
  return (
    <div className="flex items-start justify-between gap-4">
      <label htmlFor={switchId} className="cursor-pointer text-[13.5px] leading-snug text-ink select-none">
        {label}
        {description && <span className="mt-0.5 block text-[12px] text-muted">{description}</span>}
      </label>
      {control}
    </div>
  )
}
