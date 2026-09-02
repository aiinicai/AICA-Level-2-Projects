import { Company, CompanyData, Asset, CapexItem, RiskFinding, VerificationScanRecord } from '../types';
import { DEFAULT_COMPANIES, INITIAL_COMPANY_DATA_MAP } from '../data/initialCompanies';

const STORAGE_KEYS = {
  COMPANIES_LIST: 'assettrust_companies_v1',
  ACTIVE_COMPANY_ID: 'assettrust_active_company_id_v1',
  DATA_PREFIX: 'assettrust_company_data_v1_'
};

/**
 * Load all registered companies from localStorage or initialize with defaults.
 */
export function getStoredCompanies(): Company[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.COMPANIES_LIST);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.warn('Error reading stored companies:', e);
  }
  // Initialize defaults
  saveStoredCompanies(DEFAULT_COMPANIES);
  return DEFAULT_COMPANIES;
}

export function saveStoredCompanies(companies: Company[]): void {
  try {
    localStorage.setItem(STORAGE_KEYS.COMPANIES_LIST, JSON.stringify(companies));
  } catch (e) {
    console.error('Error saving companies list:', e);
  }
}

export function getActiveCompanyId(): string {
  try {
    const active = localStorage.getItem(STORAGE_KEYS.ACTIVE_COMPANY_ID);
    if (active) return active;
  } catch (e) {
    // ignore
  }
  return DEFAULT_COMPANIES[0].id;
}

export function setActiveCompanyId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEYS.ACTIVE_COMPANY_ID, id);
  } catch (e) {
    console.error('Error setting active company:', e);
  }
}

/**
 * Load complete dataset for a given company ID.
 */
export function getCompanyData(companyId: string, companyMeta?: Company): CompanyData {
  try {
    const key = `${STORAGE_KEYS.DATA_PREFIX}${companyId}`;
    const raw = localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw);
      return parsed;
    }
  } catch (e) {
    console.warn(`Error loading company data for ${companyId}:`, e);
  }

  // Fallback to preset map if available
  if (INITIAL_COMPANY_DATA_MAP[companyId]) {
    const preset = INITIAL_COMPANY_DATA_MAP[companyId];
    saveCompanyData(companyId, preset);
    return preset;
  }

  // Blank new company data template
  const fallbackCompany = companyMeta || DEFAULT_COMPANIES[0];
  const blankData: CompanyData = {
    company: fallbackCompany,
    assets: [],
    capexQueue: [],
    risks: [],
    scanLogs: []
  };
  saveCompanyData(companyId, blankData);
  return blankData;
}

export function saveCompanyData(companyId: string, data: CompanyData): void {
  try {
    const key = `${STORAGE_KEYS.DATA_PREFIX}${companyId}`;
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) {
    console.error(`Error saving data for company ${companyId}:`, e);
  }
}

/**
 * Create a new company entity and store its initial dataset.
 */
export function createNewCompany(
  companyInput: Omit<Company, 'id' | 'createdAt'>,
  initialMode: 'blank' | 'template' | 'custom_assets',
  customAssets?: Asset[]
): { newCompany: Company; companyData: CompanyData } {
  const newId = `comp-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
  const newCompany: Company = {
    ...companyInput,
    id: newId,
    createdAt: new Date().toISOString().split('T')[0],
    isCustom: true,
    logoColor: companyInput.logoColor || 'from-indigo-600 to-purple-700'
  };

  const currentCompanies = getStoredCompanies();
  const updatedCompanies = [...currentCompanies, newCompany];
  saveStoredCompanies(updatedCompanies);

  let initialAssets: Asset[] = [];
  let initialCapex: CapexItem[] = [];
  let initialRisks: RiskFinding[] = [];
  let initialScans: VerificationScanRecord[] = [];

  if (initialMode === 'custom_assets' && customAssets && customAssets.length > 0) {
    initialAssets = customAssets;
  } else if (initialMode === 'template') {
    // Generate template starter assets matching the company's first plant
    const defaultPlant = newCompany.plants[0] || 'Main Manufacturing Facility';
    initialAssets = [
      {
        id: `AST-${newCompany.shortCode}-0001`,
        name: `Primary Industrial Processing Unit - ${newCompany.industry.split('&')[0].trim()}`,
        category: 'Plant & Machinery',
        plant: defaultPlant as any,
        subLocation: 'Main Production Bay 1',
        costINR: 3500000,
        accumulatedDepINR: 350000,
        nbvINR: 3150000,
        capitalisationDate: `${new Date().getFullYear() - 1}-04-01`,
        usefulLifeYears: 15,
        schIILifeYears: 15,
        verificationStatus: 'Verified',
        lastVerifiedDate: new Date().toISOString().split('T')[0],
        riskLevel: 'Clean',
        custodian: 'Plant Operations Lead',
        department: 'Operations',
        serialNumber: `SN-${newCompany.shortCode}-001`,
        qrCode: `QR-AST-${newCompany.shortCode}-0001`,
        poNumber: `PO-${newCompany.shortCode}-001`,
        grnNumber: `GRN-${newCompany.shortCode}-001`,
        invoiceNumber: `INV-${newCompany.shortCode}-001`,
        vendor: 'Standard Industrial Suppliers Ltd.',
        description: `Core operational asset registered for ${newCompany.name}.`,
        gstPaidINR: 630000,
        itcClaimed: true,
        components: [
          {
            id: `CMP-${newCompany.shortCode}-001-A`,
            name: 'Main Structural & Mechanical Block',
            costINR: 2450000,
            usefulLifeYears: 15,
            depreciationMethod: 'SLM',
            accumulatedDepINR: 245000,
            nbvINR: 2205000,
            notes: 'Core foundation & structural assembly'
          },
          {
            id: `CMP-${newCompany.shortCode}-001-B`,
            name: 'Electric Drive & Controller Unit',
            costINR: 1050000,
            usefulLifeYears: 6,
            depreciationMethod: 'SLM',
            accumulatedDepINR: 105000,
            nbvINR: 945000,
            notes: 'Power electronics drive unit'
          }
        ],
        historyEvents: [],
        anomalies: [],
        status: 'Active'
      }
    ];
  }

  const companyData: CompanyData = {
    company: newCompany,
    assets: initialAssets,
    capexQueue: initialCapex,
    risks: initialRisks,
    scanLogs: initialScans
  };

  saveCompanyData(newId, companyData);
  setActiveCompanyId(newId);

  return { newCompany, companyData };
}

/**
 * Delete a custom company and its data.
 */
export function deleteCompany(companyId: string): Company[] {
  const companies = getStoredCompanies().filter((c) => c.id !== companyId);
  saveStoredCompanies(companies);
  localStorage.removeItem(`${STORAGE_KEYS.DATA_PREFIX}${companyId}`);
  
  if (getActiveCompanyId() === companyId) {
    const fallback = companies[0]?.id || DEFAULT_COMPANIES[0].id;
    setActiveCompanyId(fallback);
  }
  return companies;
}
