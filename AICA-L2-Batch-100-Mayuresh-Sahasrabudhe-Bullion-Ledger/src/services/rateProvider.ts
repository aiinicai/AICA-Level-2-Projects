import { RateRecord } from '../types';
import { ibjaRateService } from './ibjaRateService';

export interface RateProviderConfig {
  providerId: string;
  providerName: string;
  baseUrl: string;
  requiresApiKey: boolean;
  isConfigured: boolean;
  notes: string;
}

export interface FetchRatesResult {
  success: boolean;
  rates: RateRecord[];
  marketDate?: string;
  retrievalTimestamp: string;
  statusMessage: string;
  sourceLabel?: string;
  isSimulatedFallback?: boolean;
  error?: string;
}

/**
 * Replaceable Rate Provider Interface for Future API Updates
 */
export interface IRateProvider {
  getConfig(): RateProviderConfig;
  checkStatus(): Promise<{ available: boolean; message: string; quotaRemaining?: number }>;
  fetchRates(marketDate?: string): Promise<FetchRatesResult>;
}

/**
 * IBJA Free Official Rate Provider Implementation
 * Sourced directly once a day from India Bullion and Jewellers Association (ibjarates.com)
 * Extracts Gold 999 PM, Gold 995 PM, and Silver 999 PM benchmark closing rates.
 */
export class IbjaRateProvider implements IRateProvider {
  private config: RateProviderConfig = {
    providerId: 'ibja-free',
    providerName: 'IBJA Official Benchmark (Free Daily PM Source)',
    baseUrl: 'https://ibjarates.com/',
    requiresApiKey: false,
    isConfigured: true,
    notes: 'Sources free daily PM closing benchmark rates directly from India Bullion and Jewellers Association (IBJA) for Gold 999 (₹/10g), Gold 995 (₹/10g), and Silver 999 (₹/kg). Automatically normalized to ₹/gram with session and provenance metadata.',
  };

  getConfig(): RateProviderConfig {
    return this.config;
  }

  async checkStatus(): Promise<{ available: boolean; message: string; quotaRemaining?: number }> {
    return {
      available: true,
      message: 'Active free public benchmark feed ready. No API key or rate quota limit required.',
    };
  }

  async fetchRates(_marketDate?: string): Promise<FetchRatesResult> {
    try {
      const res = await ibjaRateService.fetchLatestRates();
      return {
        success: res.success,
        rates: res.records,
        marketDate: res.marketDate,
        retrievalTimestamp: res.retrievedAt,
        statusMessage: res.statusMessage,
        sourceLabel: res.sourceLabel,
        isSimulatedFallback: res.isSimulatedFallback,
        error: res.success ? undefined : 'FETCH_FAILED',
      };
    } catch (err: any) {
      return {
        success: false,
        rates: [],
        retrievalTimestamp: new Date().toISOString(),
        statusMessage: 'Failed to retrieve rates from IBJA service.',
        error: err.message || 'UNKNOWN_ERROR',
      };
    }
  }
}

/**
 * Metals.Dev Adapter Interface Specification
 * Evaluates Metals.Dev physical benchmark symbols and documented limitations.
 */
export class MetalsDevProvider implements IRateProvider {
  private config: RateProviderConfig = {
    providerId: 'metals-dev',
    providerName: 'Metals.Dev (IBJA Indian Physical Benchmark)',
    baseUrl: 'https://api.metals.dev/v1',
    requiresApiKey: true,
    isConfigured: false, // Honesty: unconfigured in prototype
    notes: 'Metals.Dev provides 100 free requests/mo. Indian physical gold closing rates are published under INR symbols, but an explicit IBJA Silver PM closing rate feed is unverified in standard documentation. International spot and MCX futures are prohibited from substitution.',
  };

  getConfig(): RateProviderConfig {
    return this.config;
  }

  async checkStatus(): Promise<{ available: boolean; message: string; quotaRemaining?: number }> {
    return {
      available: false,
      message: 'Metals.Dev candidate adapter unconfigured. Use IBJA Free Benchmark provider for live rates.',
    };
  }

  async fetchRates(_marketDate?: string): Promise<FetchRatesResult> {
    return {
      success: false,
      rates: [],
      retrievalTimestamp: new Date().toISOString(),
      statusMessage: 'Provider not activated: Server-side API key required.',
      error: 'UNCONFIGURED_API_CREDENTIALS',
    };
  }
}

/**
 * Factory to retrieve current active rate provider.
 * Returns the free IBJA provider as the default primary source.
 */
export function getActiveRateProvider(): IRateProvider {
  return new IbjaRateProvider();
}
