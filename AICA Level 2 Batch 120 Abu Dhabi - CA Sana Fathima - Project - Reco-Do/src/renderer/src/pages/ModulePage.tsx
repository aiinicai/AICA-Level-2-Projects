import { Navigate, useParams } from 'react-router-dom'
import { getModule } from '@shared/modules'
import { ComingSoon } from '@/features/wizard/ComingSoon'
import { WizardPage } from '@/features/wizard/WizardPage'

export function ModulePage(): React.JSX.Element {
  const { id = '' } = useParams()
  const m = getModule(id)
  if (!m) return <Navigate to="/" replace />
  if (m.status === 'phase2') return <ComingSoon module={m} />
  // Keyed by module so each module keeps its own wizard store.
  return <WizardPage key={m.id} moduleId={m.id} />
}
