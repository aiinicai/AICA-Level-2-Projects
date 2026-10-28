import { useId } from 'react'
import { RadioGroup as RadioPrimitive, ToggleGroup } from 'radix-ui'
import { cn } from '@/lib/cn'

export interface ChoiceOption<T extends string> {
  value: T
  label: React.ReactNode
  description?: React.ReactNode
  disabled?: boolean
}

export interface RadioGroupProps<T extends string> {
  value: T
  onValueChange: (value: T) => void
  options: ChoiceOption<T>[]
  orientation?: 'vertical' | 'horizontal'
  disabled?: boolean
  className?: string
  'aria-label'?: string
}

export function RadioGroup<T extends string>({
  value,
  onValueChange,
  options,
  orientation = 'vertical',
  disabled,
  className,
  ...aria
}: RadioGroupProps<T>): React.JSX.Element {
  const baseId = useId()
  return (
    <RadioPrimitive.Root
      value={value}
      onValueChange={(v) => onValueChange(v as T)}
      orientation={orientation}
      disabled={disabled}
      aria-label={aria['aria-label']}
      className={cn('flex gap-2.5', orientation === 'vertical' ? 'flex-col' : 'flex-row flex-wrap gap-5', className)}
    >
      {options.map((o) => {
        const id = `${baseId}-${o.value}`
        return (
          <div key={o.value} className="flex items-start gap-2.5">
            <RadioPrimitive.Item
              id={id}
              value={o.value}
              disabled={o.disabled}
              className="mt-[1px] grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full border-[1.5px] border-[#B9C3D0] bg-white outline-none hover:border-primary focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-50 data-[state=checked]:border-primary"
            >
              <RadioPrimitive.Indicator className="h-2 w-2 rounded-full bg-primary" />
            </RadioPrimitive.Item>
            <label htmlFor={id} className="cursor-pointer text-[13.5px] leading-snug text-ink select-none">
              {o.label}
              {o.description && <span className="mt-0.5 block text-[12px] text-muted">{o.description}</span>}
            </label>
          </div>
        )
      })}
    </RadioPrimitive.Root>
  )
}

export interface SegmentedControlProps<T extends string> {
  value: T
  onValueChange: (value: T) => void
  options: ChoiceOption<T>[]
  disabled?: boolean
  size?: 'sm' | 'md'
  className?: string
  'aria-label'?: string
}

/** Two or more joined buttons where exactly one is selected (e.g. "Raw tables | Bank statement layout"). */
export function SegmentedControl<T extends string>({
  value,
  onValueChange,
  options,
  disabled,
  size = 'md',
  className,
  ...aria
}: SegmentedControlProps<T>): React.JSX.Element {
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(v) => {
        // Radix sends "" when the selected item is clicked again; keep the current choice.
        if (v) onValueChange(v as T)
      }}
      disabled={disabled}
      aria-label={aria['aria-label']}
      className={cn('inline-flex w-full overflow-hidden rounded-lg border border-[#D5DCE5] bg-white', className)}
    >
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          disabled={o.disabled}
          className={cn(
            'flex-1 border-l border-[#D5DCE5] px-3 font-medium text-ink outline-none transition-colors first:border-l-0 hover:bg-[#F4F7FB] focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50 data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:font-semibold data-[state=on]:text-white',
            size === 'sm' ? 'h-8 text-[12.5px]' : 'h-10 text-[14px]'
          )}
        >
          {o.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  )
}
