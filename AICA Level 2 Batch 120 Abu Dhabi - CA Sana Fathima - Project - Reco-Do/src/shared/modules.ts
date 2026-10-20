// Every reconciliation module is configuration on top of the one shared engine and wizard.
// Adding GL or Credit Card later means filling in an entry here, not writing new screens.

export type ModuleId = 'bank' | 'ar' | 'ap' | 'general' | 'gl' | 'cc'
export type ModuleStatus = 'live' | 'phase2'
export type SignConvention = 'same' | 'inverse'

export interface ModuleConfig {
  id: ModuleId
  name: string
  code: string
  color: string
  status: ModuleStatus
  description: string
  sideA: string
  sideB: string
  /** General lets the user rename both sides. */
  editableSideNames: boolean
  defaultSign: SignConvention
  dateToleranceDays: number
}

export const MODULES: ModuleConfig[] = [
  {
    id: 'bank',
    name: 'Bank Reconciliation',
    code: 'B',
    color: '#1D6FD8',
    status: 'live',
    description: 'Bank statement vs GL cash account. Exact, fuzzy reference and many-to-one matching.',
    sideA: 'Bank statement',
    sideB: 'General ledger extract',
    editableSideNames: false,
    defaultSign: 'inverse',
    dateToleranceDays: 3
  },
  {
    id: 'ar',
    name: 'AR Reconciliation',
    code: 'AR',
    color: '#11865F',
    status: 'live',
    description: 'Our AR ledger vs customer SOA. Invoice no., date and amount matching.',
    sideA: 'Our AR ledger (customer account)',
    sideB: "Customer's statement of account",
    editableSideNames: false,
    defaultSign: 'inverse',
    dateToleranceDays: 7
  },
  {
    id: 'ap',
    name: 'AP Reconciliation',
    code: 'AP',
    color: '#C25500',
    status: 'live',
    description: 'Our AP ledger vs supplier SOA. Spots missing invoices, payments, credit notes.',
    sideA: 'Our AP ledger (supplier account)',
    sideB: "Supplier's statement of account",
    editableSideNames: false,
    defaultSign: 'inverse',
    dateToleranceDays: 7
  },
  {
    id: 'general',
    name: 'General Reconciliation',
    code: 'G',
    color: '#3E4A5C',
    status: 'live',
    description: 'Any two files. Pick any column in File A to match any column in File B. No amount needed.',
    sideA: 'File A',
    sideB: 'File B',
    editableSideNames: true,
    defaultSign: 'same',
    dateToleranceDays: 3
  },
  {
    id: 'gl',
    name: 'GL Reconciliation',
    code: 'GL',
    color: '#5A43D6',
    status: 'phase2',
    description: 'Account-to-account or GL vs sub-ledger (intercompany, suspense, accruals).',
    sideA: 'Account A',
    sideB: 'Account B',
    editableSideNames: false,
    defaultSign: 'same',
    dateToleranceDays: 3
  },
  {
    id: 'cc',
    name: 'Credit Card Recon',
    code: 'CC',
    color: '#C0292B',
    status: 'phase2',
    description: 'Card statement vs expense claims / GL. Merchant name fuzzy matching.',
    sideA: 'Card statement',
    sideB: 'Expense claims / GL',
    editableSideNames: false,
    defaultSign: 'inverse',
    dateToleranceDays: 3
  }
]

export function getModule(id: string): ModuleConfig | undefined {
  return MODULES.find((m) => m.id === id)
}
