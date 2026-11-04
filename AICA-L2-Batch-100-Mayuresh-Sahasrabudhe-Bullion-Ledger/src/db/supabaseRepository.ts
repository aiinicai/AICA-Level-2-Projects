import { Purchase, RateRecord, AppSettings, RateCorrection, MetalType, BullionForm } from '../types';
import { getSupabase, isSupabaseConfigured } from '../services/supabaseClient';

// -------------------------------------------------------------
// Type Converters: TypeScript Types <-> Postgres Snake_case Rows
// -------------------------------------------------------------

export function purchaseToRow(p: Purchase) {
  return {
    id: p.id,
    purchase_date: p.purchaseDate,
    seller: p.seller,
    invoice_number: p.invoiceNumber,
    metal: p.metal,
    form: p.form,
    purity: Number(p.purity),
    weight_grams: Number(p.weightGrams),
    purchase_rate: Number(p.purchaseRate),
    taxes_paid: Number(p.taxesPaid || 0),
    other_charges: Number(p.otherCharges || 0),
    notes: p.notes || null,
    bullion_value: Number(p.bullionValue),
    invested_amount: Number(p.investedAmount),
    batch_id: p.batchId || null,
    is_demo: !!p.isDemo,
    deleted: !!p.deleted,
    deleted_at: p.deletedAt || null,
    created_at: p.createdAt || new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

export function rowToPurchase(row: any): Purchase {
  return {
    id: String(row.id),
    purchaseDate: String(row.purchase_date),
    seller: String(row.seller || ''),
    invoiceNumber: String(row.invoice_number || ''),
    metal: row.metal as MetalType,
    form: row.form as BullionForm,
    purity: Number(row.purity),
    weightGrams: Number(row.weight_grams),
    purchaseRate: Number(row.purchase_rate),
    taxesPaid: Number(row.taxes_paid || 0),
    otherCharges: Number(row.other_charges || 0),
    notes: row.notes || undefined,
    bullionValue: Number(row.bullion_value),
    investedAmount: Number(row.invested_amount),
    batchId: row.batch_id || undefined,
    isDemo: !!row.is_demo,
    deleted: !!row.deleted,
    deletedAt: row.deleted_at || undefined,
    createdAt: row.created_at || new Date().toISOString(),
    updatedAt: row.updated_at || new Date().toISOString(),
  };
}

export function rateToRow(r: RateRecord) {
  return {
    id: r.id,
    date: r.date,
    metal: r.metal,
    purity: Number(r.purity),
    price_per_gram: Number(r.pricePerGram),
    source: r.source,
    source_type: r.sourceType,
    original_unit: r.originalUnit,
    original_price: Number(r.originalPrice),
    session: r.session || 'PM',
    gst_included: !!r.gstIncluded,
    notes: r.notes || null,
    provenance: r.provenance,
    imported_at: r.importedAt || new Date().toISOString(),
  };
}

export function rowToRate(row: any): RateRecord {
  return {
    id: String(row.id),
    date: String(row.date),
    metal: row.metal as MetalType,
    purity: Number(row.purity),
    pricePerGram: Number(row.price_per_gram),
    source: String(row.source),
    sourceType: row.source_type,
    originalUnit: String(row.original_unit),
    originalPrice: Number(row.original_price),
    session: row.session || 'PM',
    gstIncluded: !!row.gst_included,
    notes: row.notes || undefined,
    provenance: String(row.provenance),
    importedAt: row.imported_at || undefined,
  };
}

export function settingsToRow(s: AppSettings) {
  return {
    id: 'default',
    gold_markdown_pct: Number(s.goldMarkdownPct),
    silver_markdown_pct: Number(s.silverMarkdownPct),
    rate_provider_enabled: !!s.rateProviderEnabled,
    rate_provider_name: s.rateProviderName,
    confirm_tax_treatment: s.confirmTaxTreatment,
    confirm_session: s.confirmSession,
    last_api_check: s.lastApiCheck || null,
    last_successful_update: s.lastSuccessfulUpdate || null,
    updated_at: new Date().toISOString(),
  };
}

export function rowToSettings(row: any): AppSettings {
  return {
    goldMarkdownPct: Number(row.gold_markdown_pct ?? 3.0),
    silverMarkdownPct: Number(row.silver_markdown_pct ?? 3.0),
    rateProviderEnabled: !!row.rate_provider_enabled,
    rateProviderName: row.rate_provider_name || 'IBJA Official Benchmark (Free Daily PM Source)',
    confirmTaxTreatment: row.confirm_tax_treatment || 'UNCONFIRMED',
    confirmSession: row.confirm_session || 'UNSPECIFIED',
    lastApiCheck: row.last_api_check || undefined,
    lastSuccessfulUpdate: row.last_successful_update || undefined,
  };
}

export function correctionToRow(c: RateCorrection) {
  return {
    id: c.id,
    rate_id: c.rateId,
    date: c.date,
    metal: c.metal,
    purity: Number(c.purity),
    original_price_per_gram: Number(c.originalPricePerGram),
    corrected_price_per_gram: Number(c.correctedPricePerGram),
    reason: c.reason,
    corrected_at: c.correctedAt,
  };
}

export function rowToCorrection(row: any): RateCorrection {
  return {
    id: String(row.id),
    rateId: String(row.rate_id),
    date: String(row.date),
    metal: row.metal as MetalType,
    purity: Number(row.purity),
    originalPricePerGram: Number(row.original_price_per_gram),
    correctedPricePerGram: Number(row.corrected_price_per_gram),
    reason: String(row.reason),
    correctedAt: String(row.corrected_at),
  };
}

// -------------------------------------------------------------
// Supabase Cloud Data Services
// -------------------------------------------------------------

export const supabasePurchases = {
  async getAll(): Promise<Purchase[] | null> {
    const supabase = getSupabase();
    if (!supabase) return null;

    try {
      const { data, error } = await supabase
        .from('purchases')
        .select('*')
        .order('purchase_date', { ascending: false });

      if (error) {
        console.warn('Supabase purchases.getAll error:', error.message);
        return null;
      }

      return (data || []).map(rowToPurchase);
    } catch (err) {
      console.warn('Supabase purchases.getAll exception:', err);
      return null;
    }
  },

  async save(purchase: Purchase): Promise<boolean> {
    const supabase = getSupabase();
    if (!supabase) return false;

    try {
      const row = purchaseToRow(purchase);
      const { error } = await supabase.from('purchases').upsert(row, { onConflict: 'id' });
      if (error) {
        console.warn('Supabase purchases.save error:', error.message);
        return false;
      }
      return true;
    } catch (err) {
      console.warn('Supabase purchases.save exception:', err);
      return false;
    }
  },

  async saveBatch(purchases: Purchase[]): Promise<{ success: boolean; error?: string }> {
    const supabase = getSupabase();
    if (!supabase || purchases.length === 0) {
      return { success: false, error: 'Supabase client is not configured or purchases array is empty.' };
    }

    try {
      const rows = purchases.map(purchaseToRow);
      // Process in chunks of 50 for safety
      const chunkSize = 50;
      for (let i = 0; i < rows.length; i += chunkSize) {
        const chunk = rows.slice(i, i + chunkSize);
        const { error } = await supabase.from('purchases').upsert(chunk, { onConflict: 'id' });
        if (error) {
          console.warn('Supabase purchases.saveBatch error:', error.message);
          return { success: false, error: error.message };
        }
      }
      return { success: true };
    } catch (err: any) {
      console.warn('Supabase purchases.saveBatch exception:', err);
      return { success: false, error: err.message || 'Unknown network error' };
    }
  },

  async softDelete(id: string): Promise<boolean> {
    const supabase = getSupabase();
    if (!supabase) return false;

    try {
      const { error } = await supabase
        .from('purchases')
        .update({ deleted: true, deleted_at: new Date().toISOString() })
        .eq('id', id);
      return !error;
    } catch {
      return false;
    }
  },

  async restore(id: string): Promise<boolean> {
    const supabase = getSupabase();
    if (!supabase) return false;

    try {
      const { error } = await supabase
        .from('purchases')
        .update({ deleted: false, deleted_at: null })
        .eq('id', id);
      return !error;
    } catch {
      return false;
    }
  },

  async permanentDelete(id: string): Promise<boolean> {
    const supabase = getSupabase();
    if (!supabase) return false;

    try {
      const { error } = await supabase.from('purchases').delete().eq('id', id);
      return !error;
    } catch {
      return false;
    }
  },

  async undoBatch(batchId: string): Promise<boolean> {
    const supabase = getSupabase();
    if (!supabase) return false;

    try {
      const { error } = await supabase.from('purchases').delete().eq('batch_id', batchId);
      return !error;
    } catch {
      return false;
    }
  },

  async clearAll(): Promise<boolean> {
    const supabase = getSupabase();
    if (!supabase) return false;

    try {
      const { error } = await supabase.from('purchases').delete().neq('id', '');
      return !error;
    } catch {
      return false;
    }
  },
};

export const supabaseRates = {
  async getAll(): Promise<RateRecord[] | null> {
    const supabase = getSupabase();
    if (!supabase) return null;

    try {
      const allRows: any[] = [];
      const pageSize = 1000;
      let from = 0;
      let hasMore = true;

      while (hasMore) {
        const { data, error } = await supabase
          .from('rates')
          .select('*')
          .order('date', { ascending: false })
          .range(from, from + pageSize - 1);

        if (error) {
          console.warn('Supabase rates.getAll error:', error.message);
          break;
        }

        if (data && data.length > 0) {
          allRows.push(...data);
          if (data.length < pageSize) {
            hasMore = false;
          } else {
            from += pageSize;
          }
        } else {
          hasMore = false;
        }
      }

      if (allRows.length === 0) return null;
      return allRows.map(rowToRate);
    } catch (err) {
      console.warn('Supabase rates.getAll exception:', err);
      return null;
    }
  },

  async saveBatch(rates: RateRecord[]): Promise<{ success: boolean; count: number; error?: string }> {
    const supabase = getSupabase();
    if (!supabase || rates.length === 0) {
      return { success: false, count: 0, error: 'Supabase is not configured or rates array is empty.' };
    }

    try {
      const rows = rates.map(rateToRow);
      const chunkSize = 200;
      let totalUpserted = 0;
      for (let i = 0; i < rows.length; i += chunkSize) {
        const chunk = rows.slice(i, i + chunkSize);
        const { error } = await supabase.from('rates').upsert(chunk, { onConflict: 'id' });
        if (error) {
          console.warn('Supabase rates.saveBatch error at chunk:', error.message);
          return { success: false, count: totalUpserted, error: error.message };
        }
        totalUpserted += chunk.length;
      }
      return { success: true, count: totalUpserted };
    } catch (err: any) {
      console.warn('Supabase rates.saveBatch exception:', err);
      return { success: false, count: 0, error: err.message || 'Unknown network error' };
    }
  },
};

export const supabaseSettings = {
  async get(): Promise<AppSettings | null> {
    const supabase = getSupabase();
    if (!supabase) return null;

    try {
      const { data, error } = await supabase
        .from('app_settings')
        .select('*')
        .eq('id', 'default')
        .single();

      if (error || !data) return null;
      return rowToSettings(data);
    } catch {
      return null;
    }
  },

  async save(settings: AppSettings): Promise<{ success: boolean; error?: string }> {
    const supabase = getSupabase();
    if (!supabase) return { success: false, error: 'Supabase client not configured.' };

    try {
      const row = settingsToRow(settings);
      const { error } = await supabase.from('app_settings').upsert(row, { onConflict: 'id' });
      if (error) {
        return { success: false, error: error.message };
      }
      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message || 'Settings save exception' };
    }
  },
};

export const supabaseCorrections = {
  async getAll(): Promise<RateCorrection[] | null> {
    const supabase = getSupabase();
    if (!supabase) return null;

    try {
      const { data, error } = await supabase
        .from('rate_corrections')
        .select('*')
        .order('corrected_at', { ascending: false });

      if (error || !data) return null;
      return data.map(rowToCorrection);
    } catch {
      return null;
    }
  },

  async save(correction: RateCorrection): Promise<boolean> {
    const supabase = getSupabase();
    if (!supabase) return false;

    try {
      const row = correctionToRow(correction);
      const { error } = await supabase.from('rate_corrections').upsert(row, { onConflict: 'id' });
      return !error;
    } catch {
      return false;
    }
  },
};

/**
 * Test connectivity to the configured Supabase instance.
 */
export async function testSupabaseConnection(): Promise<{
  success: boolean;
  message: string;
  purchasesCount?: number;
}> {
  const supabase = getSupabase();
  if (!supabase) {
    return {
      success: false,
      message: 'Supabase credentials are not configured.',
    };
  }

  try {
    const { count, error } = await supabase
      .from('purchases')
      .select('*', { count: 'exact', head: true });

    if (error) {
      return {
        success: false,
        message: `Database error: ${error.message} (${error.code})`,
      };
    }

    return {
      success: true,
      message: 'Successfully connected to Supabase PostgreSQL database!',
      purchasesCount: count || 0,
    };
  } catch (err: any) {
    return {
      success: false,
      message: err.message || 'Connection failed.',
    };
  }
}
