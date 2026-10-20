import { Navigate, useParams } from 'react-router-dom'
import { Lock } from 'lucide-react'
import { getTool, type ToolId } from '@shared/tools'
import { PageHeader } from '@/components/ui'
import { DataCleanerScreen } from '@/features/tools/DataCleanerScreen'
import { ExcelToPdfScreen } from '@/features/tools/ExcelToPdfScreen'
import { MergeFilesScreen } from '@/features/tools/MergeFilesScreen'
import { MergePdfsScreen } from '@/features/tools/MergePdfsScreen'
import { PdfToExcelScreen } from '@/features/tools/PdfToExcelScreen'
import { SplitPdfScreen } from '@/features/tools/SplitPdfScreen'

const SCREENS: Record<ToolId, () => React.JSX.Element> = {
  'pdf-to-excel': PdfToExcelScreen,
  'excel-to-pdf': ExcelToPdfScreen,
  'merge-pdfs': MergePdfsScreen,
  'split-pdf': SplitPdfScreen,
  'merge-files': MergeFilesScreen,
  'data-cleaner': DataCleanerScreen
}

export function ToolPage(): React.JSX.Element {
  const { id = '' } = useParams()
  const tool = getTool(id)
  if (!tool) return <Navigate to="/" replace />
  const Screen = SCREENS[tool.id]

  return (
    <>
      <PageHeader
        title={tool.name}
        subtitle={tool.description}
        right={
          <span className="inline-flex items-center gap-1.5 text-[12.5px] whitespace-nowrap text-matched" data-privacy-note>
            <Lock size={13} strokeWidth={2.4} /> Runs on this computer. Nothing is uploaded.
          </span>
        }
      />
      {/* key: a fresh screen (and state) per tool */}
      <Screen key={tool.id} />
    </>
  )
}
