import { Link } from 'react-router-dom'
import { ArrowLeft, Clock } from 'lucide-react'
import type { ModuleConfig } from '@shared/modules'
import { Badge, Button, Card, KeyValue, PageHeader } from '@/components/ui'

/** Phase 2 modules: a polished "Coming soon" page describing what the module will do. */
export function ComingSoon({ module: m }: { module: ModuleConfig }): React.JSX.Element {
  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            {m.name} <Badge tone="phase2">Phase 2</Badge>
          </span>
        }
        subtitle={m.description}
      />
      <div className="grid max-w-4xl gap-5 md:grid-cols-[1.3fr_1fr]">
        <Card className="p-6">
          <div className="mb-4 flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-xl text-white" style={{ background: m.color }} aria-hidden>
              <Clock size={20} />
            </div>
            <div>
              <div className="text-[16px] font-bold">Coming soon</div>
              <div className="text-[13px] text-muted">Planned for the next release of Reco-Do.</div>
            </div>
          </div>
          <p className="text-[14px] leading-relaxed text-ink">{m.description}</p>
          <p className="mt-3 text-[13.5px] leading-relaxed text-muted">
            It will use the same five steps as the live modules (Upload, Map &amp; rules, Reconcile, Smart Recon, Review &amp; export) and
            the same matching engine, with its own defaults. Until then, the General Reconciliation module can match any two files.
          </p>
          <div className="mt-5 flex gap-2.5">
            <Button asChild>
              <Link to="/module/general">Open General Reconciliation</Link>
            </Button>
            <Button variant="secondary" asChild>
              <Link to="/">
                <ArrowLeft size={15} /> Dashboard
              </Link>
            </Button>
          </div>
        </Card>
        <Card className="p-6">
          <div className="mb-2 text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase">Planned defaults</div>
          <KeyValue
            items={[
              { label: 'File A', value: m.sideA },
              { label: 'File B', value: m.sideB },
              { label: 'Sign convention', value: m.defaultSign === 'inverse' ? 'Inverse sign' : 'Same sign' },
              { label: 'Date tolerance', value: `± ${m.dateToleranceDays} days` }
            ]}
          />
        </Card>
      </div>
    </>
  )
}
