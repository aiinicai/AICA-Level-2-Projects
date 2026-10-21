import { TaxCode, TaxCodeConfig } from '../core/types';

export const TAX_CODES: Record<TaxCode, TaxCodeConfig> = {
  STANDARD_5: {
    code: 'STANDARD_5',
    name: 'VAT 5% Standard',
    rate: 0.05,
    description: 'UAE standard 5% VAT rate on taxable goods and non-qualifying services',
  },
  ZERO_0: {
    code: 'ZERO_0',
    name: 'VAT 0% Zero-rated',
    rate: 0.0,
    description: 'Qualifying healthcare services, registered pharmaceuticals, medical equipment',
  },
  EXEMPT: {
    code: 'EXEMPT',
    name: 'VAT Exempt',
    rate: 0.0,
    description: 'Exempt healthcare and financial transactions under UAE VAT legislation',
  },
  OUT_OF_SCOPE: {
    code: 'OUT_OF_SCOPE',
    name: 'Out of Scope',
    rate: 0.0,
    description: 'Transactions outside the scope of UAE VAT law',
  },
};

export function getTaxRate(code: TaxCode): number {
  return TAX_CODES[code]?.rate ?? 0;
}
