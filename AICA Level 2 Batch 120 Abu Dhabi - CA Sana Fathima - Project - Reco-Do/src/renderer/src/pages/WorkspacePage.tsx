import { Navigate, useParams } from 'react-router-dom'
import { PageHeader } from '@/components/ui'
import { WORKSPACE } from './workspace/sections'
import { HistoryPage } from './workspace/HistoryPage'
import { MappingsPage } from './workspace/MappingsPage'
import { SettingsPage } from './workspace/SettingsPage'

export { WORKSPACE } from './workspace/sections'

export function WorkspacePage(): React.JSX.Element {
  const { id = '' } = useParams()
  const page = WORKSPACE.find((w) => w.id === id)
  if (!page) return <Navigate to="/" replace />

  return (
    <>
      <PageHeader title={page.name} subtitle={page.subtitle} />
      {page.id === 'settings' && <SettingsPage />}
      {page.id === 'mappings' && <MappingsPage />}
      {page.id === 'history' && <HistoryPage />}
    </>
  )
}
