import { useDeferredValue, useMemo } from 'react'
import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-react'
import type { EngineLine, ParsedTable, ReconConfig } from '@shared/contracts'
import type { ModuleId, SignConvention } from '@shared/modules'
import { formatAmount, formatDate } from '@shared/format'
import { detectSignMismatch, previewFirstPair } from '@engine/index'
import { Button, SectionTitle, SegmentedControl } from '@/components/ui'
import { signExplanation } from '../helpers'
import { cellText } from '../review/model'

function refText(cfg: ReconConfig, line: EngineLine): string {
  const key = cfg.keys.find((k) => k.use && (k.type === 'id' || k.type === 'text'))
  if (!key) return ''
  const v = cellText(line.values[line.side === 'A' ? key.columnA : key.columnB])
  return v.length > 28 ? `${v.slice(0, 27)}…` : v
}

function previewLine(cfg: ReconConfig, label: string, line: EngineLine): string {
  const parts = [label.padEnd(5, ' ') + ':']
  if (line.date) parts.push(formatDate(line.date).slice(0, 6))
  const ref = refText(cfg, line)
  if (ref) parts.push(`"${ref}"`)
  if (line.amount !== null) parts.push(`${line.amount < 0 ? 'CR' : 'DR'} ${formatAmount(Math.abs(line.amount))}`)
  return parts.join(' ')
}

/** Sign toggle, plain-English explanation, live preview of the first likely pair and the >80% warning. */
export function SignCard({
  moduleId,
  config,
  tableA,
  tableB,
  shortA,
  shortB,
  onSign
}: {
  moduleId: ModuleId
  config: ReconConfig
  tableA: ParsedTable
  tableB: ParsedTable
  shortA: string
  shortB: string
  onSign: (s: SignConvention) => void
}): React.JSX.Element {
  // Recomputed on a deferred copy so typing in the key table stays responsive on large files.
  const deferred = useDeferredValue(config)
  const preview = useMemo(() => {
    try {
      return previewFirstPair(tableA, tableB, deferred)
    } catch {
      return null
    }
  }, [tableA, tableB, deferred])
  const mismatch = useMemo(() => {
    try {
      return detectSignMismatch(tableA, tableB, deferred)
    } catch {
      return { opposite: 0, same: 0, warn: false }
    }
  }, [tableA, tableB, deferred])
  const agree = preview && preview.a.comparableAmount !== null && preview.b.comparableAmount !== null && Math.abs(preview.a.comparableAmount - preview.b.comparableAmount) < 0.005
  const other: SignConvention = config.sign === 'same' ? 'inverse' : 'same'
  const pct = mismatch.opposite + mismatch.same > 0 ? Math.round((mismatch.opposite / (mismatch.opposite + mismatch.same)) * 100) : 0

  return (
    <div>
      <SectionTitle className="mb-3">Sign convention</SectionTitle>
      <SegmentedControl
        aria-label="Sign convention"
        value={config.sign}
        onValueChange={onSign}
        options={[
          { value: 'same', label: 'Same sign' },
          { value: 'inverse', label: 'Inverse sign' }
        ]}
      />
      <p className="mt-2.5 text-[13px] leading-relaxed text-muted">{signExplanation(moduleId, config.sign, config.sideAName, config.sideBName)}</p>

      {mismatch.warn && (
        <div role="alert" className="mt-3 flex gap-2.5 rounded-lg border border-[#F2D7A6] bg-[#FFF8EB] p-3 text-[13px]">
          <AlertTriangle size={17} className="mt-0.5 shrink-0 text-doubtful" />
          <div>
            <div className="font-semibold text-ink">The sign setting looks wrong</div>
            <div className="mt-0.5 leading-snug text-muted">
              {pct}% of the amounts that appear in both files only agree with the {other === 'same' ? 'Same sign' : 'Inverse sign'} setting.
            </div>
            <Button size="sm" variant="outline" className="mt-2" onClick={() => onSign(other)}>
              Switch to {other === 'same' ? 'Same sign' : 'Inverse sign'}
            </Button>
          </div>
        </div>
      )}

      <SectionTitle className="mt-5 mb-2">Preview (first likely pair)</SectionTitle>
      {preview ? (
        <div className="rounded-lg bg-[#F4F6F9] px-3.5 py-3">
          <pre className="font-mono text-[12px] leading-relaxed whitespace-pre-wrap text-ink">
            {previewLine(config, shortA, preview.a)}
            {'\n'}
            {previewLine(config, shortB, preview.b)}
          </pre>
          {preview.a.comparableAmount !== null && (
            <div className={`mt-2 flex items-center gap-1.5 text-[12.5px] font-semibold ${agree ? 'text-matched' : 'text-unmatched'}`}>
              {agree ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
              {agree ? 'With this sign setting the amounts agree.' : 'With this sign setting the amounts do not agree.'}
            </div>
          )}
        </div>
      ) : (
        <p className="rounded-lg bg-[#F4F6F9] px-3.5 py-3 text-[12.5px] text-muted">No likely pair found yet. Check the key columns.</p>
      )}
    </div>
  )
}
