export type WorkspaceId = 'mappings' | 'history' | 'settings'

export const WORKSPACE: ReadonlyArray<{ id: WorkspaceId; name: string; subtitle: string }> = [
  {
    id: 'mappings',
    name: 'Mappings & Templates',
    subtitle: 'Saved column mappings load automatically when the same files come back. Templates and recipes are reusable setups.'
  },
  {
    id: 'history',
    name: 'Recon History',
    subtitle: 'Every reconciliation you have saved on this computer, with its results and audit trail.'
  },
  {
    id: 'settings',
    name: 'Settings & API Key',
    subtitle: 'Your details for sign-off, the default currency, and the optional AI provider and API key for Smart Recon.'
  }
]
