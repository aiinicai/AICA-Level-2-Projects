export const TAX_TYPE_OPTIONS = [
  { value: "VAT", label: "Value Added Tax" },
  { value: "GST", label: "Goods and Services Tax" },
  { value: "SALES_TAX", label: "Sales Tax" },
  { value: "WHT", label: "Withholding Tax" },
  { value: "CORPORATE_TAX", label: "Corporate / Income Tax" },
  { value: "STATUTORY", label: "Statutory Contributions" },
]

const TAX_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  TAX_TYPE_OPTIONS.map((t) => [t.value, t.label])
)

export function taxTypeLabel(code: string | null | undefined): string {
  if (!code) return "-"
  return TAX_TYPE_LABELS[code] || code
}
