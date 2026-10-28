// Reco-Do UI kit (shadcn/ui style: Radix primitives + Tailwind + cn). Import from '@/components/ui'.

export { Button, buttonVariants, type ButtonProps } from './button'
export { Input, Textarea, Label, Field } from './input'
export { Select, type SelectOption, type SelectProps } from './select'
export { Checkbox, Switch, type CheckboxProps, type SwitchProps, type CheckedState } from './checkbox'
export { RadioGroup, SegmentedControl, type ChoiceOption, type RadioGroupProps, type SegmentedControlProps } from './radio'
export { Tabs, TabsList, TabsTrigger, TabsContent, type TabsTriggerProps } from './tabs'
export {
  Dialog,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogFooter,
  DialogTitle,
  DialogDescription,
  ConfirmDialog,
  ConfirmProvider,
  useConfirm,
  type ConfirmOptions,
  type DialogContentProps
} from './dialog'
export { Tooltip, TooltipProvider, type TooltipProps } from './tooltip'
export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuGroup,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator
} from './dropdown-menu'
export { ToastProvider, useToast, type ToastApi, type ToastOptions, type ToastTone } from './toast'
export { Badge, TIER_LABEL, type BadgeProps, type BadgeTone } from './badge'
export { Card, SectionTitle, PageHeader, PAGE_TITLE, KeyValue, type KeyValueItem } from './card'
export { Stepper, type StepItem, type StepperProps } from './stepper'
export { DropZone, FileTile, fileExtension, formatBytes, EXCEL_FILTER, PDF_FILTER, type DropZoneProps } from './dropzone'
export { DataTable, formatCell, type DataColumn, type DataTableProps } from './data-table'
export { EmptyState } from './empty-state'
export { Spinner, Progress, type ProgressProps } from './spinner'
export { TechnicalDetails } from './technical-details'
