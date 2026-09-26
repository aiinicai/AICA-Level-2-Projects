import { Response } from 'express';
import prisma from '../lib/prisma';
import { AuthRequest } from '../middleware/auth';
import { getSettings, SETTINGS_ID } from '../lib/settings';
import { num, r2 } from '../lib/money';

const TAX_TYPES = ['CGST_SGST', 'IGST', 'NONE'] as const;
type TaxType = (typeof TAX_TYPES)[number];

/** Longest sensible invoice prefix — it has to fit on a printed invoice. */
const MAX_PREFIX_LENGTH = 12;
/** A year of credit is not a payment term, it is a mistake. */
const MAX_PAYMENT_TERM_DAYS = 365;

/**
 * Everyone signed in may read the settings: the invoice form needs the
 * defaults and the PDF needs the firm's letterhead. Only an admin may change
 * them — that gate is on the route.
 */
export const getSettingsHandler = async (_req: AuthRequest, res: Response) => {
  try {
    res.json(await getSettings());
  } catch (err) {
    console.error('[settings] read failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

export const updateSettings = async (req: AuthRequest, res: Response) => {
  const {
    firmName, firmAddress, firmGstin, firmEmail, firmPhone,
    invoicePrefix, defaultTaxType, defaultGstRate, defaultPaymentTermDays,
  } = req.body as Record<string, unknown>;

  const name = String(firmName ?? '').trim();
  if (!name) return res.status(400).json({ message: 'Firm name is required' });

  const prefix = String(invoicePrefix ?? '').trim();
  if (!prefix) return res.status(400).json({ message: 'Invoice prefix is required' });
  if (prefix.length > MAX_PREFIX_LENGTH) {
    return res.status(400).json({ message: `Invoice prefix cannot be longer than ${MAX_PREFIX_LENGTH} characters` });
  }
  // The prefix becomes part of a unique key and is shown in filenames, so the
  // separators the number itself uses are not available to it.
  if (/[/\\]/.test(prefix)) {
    return res.status(400).json({ message: 'Invoice prefix cannot contain slashes' });
  }

  const taxType = String(defaultTaxType ?? 'CGST_SGST') as TaxType;
  if (!TAX_TYPES.includes(taxType)) return res.status(400).json({ message: 'Invalid default tax type' });

  const gstRate = r2(num(defaultGstRate));
  if (gstRate < 0 || gstRate > 100) {
    return res.status(400).json({ message: 'Default GST rate must be between 0 and 100' });
  }

  const termDays = Number(defaultPaymentTermDays);
  if (!Number.isInteger(termDays) || termDays < 0 || termDays > MAX_PAYMENT_TERM_DAYS) {
    return res.status(400).json({ message: `Payment terms must be a whole number of days, 0 to ${MAX_PAYMENT_TERM_DAYS}` });
  }

  try {
    const data = {
      firmName: name,
      firmAddress: String(firmAddress ?? '').trim(),
      firmGstin: String(firmGstin ?? '').trim().toUpperCase(),
      firmEmail: String(firmEmail ?? '').trim().toLowerCase(),
      firmPhone: String(firmPhone ?? '').trim(),
      invoicePrefix: prefix,
      defaultTaxType: taxType,
      defaultGstRate: gstRate,
      defaultPaymentTermDays: termDays,
    };

    const settings = await prisma.settings.upsert({
      where: { id: SETTINGS_ID },
      create: { id: SETTINGS_ID, ...data },
      update: data,
    });

    res.json(settings);
  } catch (err) {
    console.error('[settings] update failed:', err);
    res.status(500).json({ message: 'Server error' });
  }
};
