import React, { useState } from 'react';
import { X } from 'lucide-react';
import type { CurrencyCode, FontSizeScale, LanguageCode, MisDataset, ThemeId } from '../types/mis';

interface SetupWizardModalProps {
  open: boolean;
  dataset: MisDataset;
  currency: CurrencyCode;
  theme: ThemeId;
  lang: LanguageCode;
  fontScale: FontSizeScale;
  onClose: () => void;
  onApplyPreferences: (prefs: {
    currency: CurrencyCode;
    theme: ThemeId;
    lang: LanguageCode;
    fontScale: FontSizeScale;
  }) => void;
}

export const SetupWizardModal: React.FC<SetupWizardModalProps> = ({
  open,
  dataset,
  currency,
  theme,
  lang,
  fontScale,
  onClose,
  onApplyPreferences,
}) => {
  const [step, setStep] = useState(1);
  const [localCurrency, setLocalCurrency] = useState<CurrencyCode>(currency);
  const [localTheme, setLocalTheme] = useState<ThemeId>(theme);
  const [localLang, setLocalLang] = useState<LanguageCode>(lang);
  const [localFontScale, setLocalFontScale] = useState<FontSizeScale>(fontScale);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="RealEstate 360 Setup Wizard"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
    >
      <div
        className="w-full max-w-2xl rounded-xl border p-6 space-y-5 shadow-xl"
        style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
      >
        <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--re-border)' }}>
          <div>
            <h2 className="font-display text-base font-semibold">RealEstate 360 — Workspace Setup Wizard</h2>
            <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
              Step {step} of 3 · Company, Chart of Accounts, Projects & Display Preferences
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close setup wizard" className="p-1.5 rounded hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>

        {step === 1 && (
          <div className="space-y-3 text-xs">
            <h3 className="font-semibold text-sm">1. Legal Entities, Financial Year & Projects</h3>
            <div className="space-y-2">
              {dataset.companies.map((c) => (
                <div key={c.id} className="p-3 rounded border flex justify-between" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
                  <div>
                    <div className="font-medium">{c.name}</div>
                    <div style={{ color: 'var(--re-text-muted)' }}>CR {c.crNumber} · VAT {c.vatNumber} · FY Start Month {c.fiscalYearStartMonth}</div>
                  </div>
                  <span className="font-mono-num">{c.type} ({c.ownershipPct}%)</span>
                </div>
              ))}
            </div>
            <div className="text-[11px]" style={{ color: 'var(--re-text-muted)' }}>
              Active Developments: {dataset.projects.map((p) => `${p.code} (${p.totalUnits} units)`).join(', ')}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3 text-xs">
            <h3 className="font-semibold text-sm">2. Chart of Accounts & IFRS Mapping Rules</h3>
            <div className="max-h-52 overflow-y-auto space-y-1.5">
              {dataset.glMappings.map((m) => (
                <div key={m.id} className="p-2.5 rounded border flex justify-between" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
                  <span>
                    <strong className="font-mono-num">{m.accountCode}</strong> · {m.accountNamePattern}
                  </span>
                  <span className="font-medium" style={{ color: 'var(--re-accent)' }}>{m.targetClass}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4 text-xs">
            <h3 className="font-semibold text-sm">3. Reporting Currency, Theme & Language Preferences</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="block">
                <span style={{ color: 'var(--re-text-muted)' }}>Default Reporting Currency</span>
                <select
                  value={localCurrency}
                  onChange={(e) => setLocalCurrency(e.target.value as CurrencyCode)}
                  className="mt-1 w-full px-3 py-2 rounded border"
                  style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
                >
                  <option value="OMR">OMR (3 Decimals — Default)</option>
                  <option value="AED">AED (2 Decimals)</option>
                  <option value="SAR">SAR (2 Decimals)</option>
                  <option value="USD">USD (2 Decimals)</option>
                </select>
              </label>
              <label className="block">
                <span style={{ color: 'var(--re-text-muted)' }}>Interface Theme</span>
                <select
                  value={localTheme}
                  onChange={(e) => setLocalTheme(e.target.value as ThemeId)}
                  className="mt-1 w-full px-3 py-2 rounded border"
                  style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
                >
                  <option value="navy-gold">Executive Navy & Gold</option>
                  <option value="corporate-blue">Corporate White & Blue</option>
                  <option value="midnight-dark">Midnight Dark</option>
                  <option value="emerald-finance">Emerald Finance</option>
                  <option value="graphite-copper">Graphite & Copper</option>
                  <option value="minimal-pro">Minimal Professional</option>
                </select>
              </label>
              <label className="block">
                <span style={{ color: 'var(--re-text-muted)' }}>Language & Layout Direction</span>
                <select
                  value={localLang}
                  onChange={(e) => setLocalLang(e.target.value as LanguageCode)}
                  className="mt-1 w-full px-3 py-2 rounded border"
                  style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
                >
                  <option value="en">English (LTR)</option>
                  <option value="ar">العربية (RTL)</option>
                </select>
              </label>
              <label className="block">
                <span style={{ color: 'var(--re-text-muted)' }}>Typography Scale</span>
                <select
                  value={localFontScale}
                  onChange={(e) => setLocalFontScale(e.target.value as FontSizeScale)}
                  className="mt-1 w-full px-3 py-2 rounded border"
                  style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
                >
                  <option value="compact">Compact</option>
                  <option value="standard">Standard</option>
                  <option value="large">Executive Large</option>
                </select>
              </label>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between pt-3 border-t" style={{ borderColor: 'var(--re-border)' }}>
          <button
            type="button"
            disabled={step === 1}
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            className="px-3.5 py-2 rounded-lg border text-xs font-medium disabled:opacity-40"
            style={{ borderColor: 'var(--re-border)' }}
          >
            Previous
          </button>
          <div className="flex gap-2">
            {step < 3 ? (
              <button
                type="button"
                onClick={() => setStep((s) => Math.min(3, s + 1))}
                className="px-4 py-2 rounded-lg text-xs font-medium"
                style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
              >
                Next Step
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  onApplyPreferences({
                    currency: localCurrency,
                    theme: localTheme,
                    lang: localLang,
                    fontScale: localFontScale,
                  });
                  onClose();
                }}
                className="px-4 py-2 rounded-lg text-xs font-medium"
                style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
              >
                Apply & Enter Workspace
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
