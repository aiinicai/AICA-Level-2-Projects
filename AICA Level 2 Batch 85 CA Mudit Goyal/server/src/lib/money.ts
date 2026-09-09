/**
 * Money helpers.
 *
 * Prisma hands Decimal columns back as Decimal objects, so everything that
 * arrives from the database is normalised through `num` before arithmetic.
 * Amounts are kept to 2 decimals in the database; rounding for display is the
 * UI's job (see client/src/utils/format.ts).
 */

export const num = (v: unknown): number => {
  if (v === null || v === undefined || v === '') return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

/** Round to 2 decimals without floating-point drift. */
export const r2 = (n: number): number => Math.round((n + Number.EPSILON) * 100) / 100;

export type TaxType = 'CGST_SGST' | 'IGST' | 'NONE';

export interface TaxBreakup {
  cgstRate: number | null;
  sgstRate: number | null;
  igstRate: number | null;
  cgstAmount: number | null;
  sgstAmount: number | null;
  igstAmount: number | null;
  totalAmount: number;
}

/**
 * Split a taxable value into its GST components.
 *
 * `gstRate` is the combined rate the user picked (18 means 18%): an intra-state
 * invoice halves it into CGST and SGST, an inter-state one charges it all as
 * IGST. Passing the combined rate — rather than three separate ones — is what
 * keeps the two branches impossible to get out of step.
 */
export function computeTax(amount: number, taxType: TaxType, gstRate: number): TaxBreakup {
  const taxable = r2(amount);

  if (taxType === 'CGST_SGST') {
    const half = r2(gstRate / 2);
    const cgst = r2(taxable * (half / 100));
    const sgst = r2(taxable * (half / 100));
    return {
      cgstRate: half, sgstRate: half, igstRate: null,
      cgstAmount: cgst, sgstAmount: sgst, igstAmount: null,
      totalAmount: r2(taxable + cgst + sgst),
    };
  }

  if (taxType === 'IGST') {
    const igst = r2(taxable * (gstRate / 100));
    return {
      cgstRate: null, sgstRate: null, igstRate: r2(gstRate),
      cgstAmount: null, sgstAmount: null, igstAmount: igst,
      totalAmount: r2(taxable + igst),
    };
  }

  return {
    cgstRate: null, sgstRate: null, igstRate: null,
    cgstAmount: null, sgstAmount: null, igstAmount: null,
    totalAmount: taxable,
  };
}
