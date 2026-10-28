import { Eraser, FileSpreadsheet, FileText, Files, Layers, Scissors, type LucideIcon } from 'lucide-react'
import type { ToolConfig, ToolId } from '@shared/tools'

const ICONS: Record<ToolId, LucideIcon> = {
  'pdf-to-excel': FileSpreadsheet,
  'excel-to-pdf': FileText,
  'merge-pdfs': Files,
  'split-pdf': Scissors,
  'merge-files': Layers,
  'data-cleaner': Eraser
}

export function ToolIcon({ tool, size = 34 }: { tool: ToolConfig; size?: number }): React.JSX.Element {
  const Icon = ICONS[tool.id]
  return (
    <div className="grid place-items-center rounded-lg" style={{ width: size, height: size, background: tool.bg, color: tool.fg }}>
      <Icon size={size * 0.55} strokeWidth={2} />
    </div>
  )
}
