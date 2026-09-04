import React from 'react';
import { Palette, Check, Sparkles, X, Layers } from 'lucide-react';
import { ThemeStyle, IconConcept } from '../types';
import { THEMES, ICON_CONCEPTS } from '../utils/theme';
import { AppLogo } from './AppLogo';

interface ThemeSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTheme: ThemeStyle;
  onSelectTheme: (theme: ThemeStyle) => void;
  currentIcon: IconConcept;
  onSelectIcon: (icon: IconConcept) => void;
}

export const ThemeSelectorModal: React.FC<ThemeSelectorModalProps> = ({
  isOpen,
  onClose,
  currentTheme,
  onSelectTheme,
  currentIcon,
  onSelectIcon,
}) => {
  if (!isOpen) return null;

  const activeTheme = THEMES[currentTheme] || THEMES.navy;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
      <div className={`relative w-full max-w-2xl rounded-2xl ${activeTheme.cardBg} border ${activeTheme.cardBorder} shadow-2xl p-6 overflow-hidden backdrop-blur-xl transition-colors duration-300`}>
        {/* Header */}
        <div className={`flex items-center justify-between pb-4 border-b ${activeTheme.cardBorder}`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-xl ${activeTheme.badgeBg} border ${activeTheme.textAccent}`}>
              <Palette className="w-5 h-5" />
            </div>
            <div>
              <h2 className={`text-lg font-bold ${activeTheme.textPrimary} flex items-center gap-2`}>
                Firm Theme & App Icon Customizer
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-medium">
                  Live Preview
                </span>
              </h2>
              <p className={`text-xs ${activeTheme.textMuted}`}>
                Instantly change your firm's background theme, font colors, and official app icon.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className={`p-1.5 rounded-lg ${activeTheme.textMuted} hover:${activeTheme.textPrimary} ${activeTheme.cardHover} transition-colors`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="py-5 space-y-6 max-h-[70vh] overflow-y-auto pr-1">
          {/* Section 1: Color Themes */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className={`text-xs font-semibold uppercase tracking-wider ${activeTheme.textMuted} flex items-center gap-1.5`}>
                <Sparkles className={`w-3.5 h-3.5 ${activeTheme.textAccent}`} />
                1. Select Whole-Screen Color Palette
              </label>
              <span className={`text-xs ${activeTheme.textAccent} font-medium`}>Changes Background & Typography</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(Object.keys(THEMES) as ThemeStyle[]).map((key) => {
                const theme = THEMES[key];
                const isSelected = currentTheme === key;
                return (
                  <button
                    key={key}
                    onClick={() => onSelectTheme(key)}
                    className={`relative text-left p-4 rounded-xl border transition-all ${
                      isSelected
                        ? `border-blue-500 ${activeTheme.subCardBg} ring-2 ring-blue-500/40 shadow-lg`
                        : `${activeTheme.subCardBg} border ${activeTheme.cardBorder} ${activeTheme.cardHover}`
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="w-4 h-4 rounded-full border border-slate-300 dark:border-white/20 shadow-inner"
                          style={{ backgroundColor: theme.accentColor }}
                        />
                        <span className={`font-semibold text-sm ${activeTheme.textPrimary}`}>{theme.name}</span>
                      </div>
                      {isSelected && (
                        <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 text-white text-xs">
                          <Check className="w-3 h-3 stroke-[3]" />
                        </span>
                      )}
                    </div>
                    <p className={`mt-1.5 text-xs ${activeTheme.textSecondary} line-clamp-2 leading-relaxed`}>
                      {theme.description}
                    </p>
                    <div className="mt-3 flex items-center gap-1.5">
                      <div className="h-2 w-8 rounded-full border border-black/10 dark:border-white/10" style={{ backgroundColor: theme.primaryColor }} />
                      <div className="h-2 w-8 rounded-full border border-black/10 dark:border-white/10" style={{ backgroundColor: theme.secondaryColor }} />
                      <div className="h-2 w-8 rounded-full border border-black/10 dark:border-white/10" style={{ backgroundColor: theme.accentColor }} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 2: App Icon & Insignia */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className={`text-xs font-semibold uppercase tracking-wider ${activeTheme.textMuted} flex items-center gap-1.5`}>
                <Layers className={`w-3.5 h-3.5 ${activeTheme.textAccent}`} />
                2. Select App Logo & PWA Icon
              </label>
              <span className={`text-xs ${activeTheme.textMuted} font-medium`}>Home Screen & App Header</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {(Object.keys(ICON_CONCEPTS) as IconConcept[]).map((iconKey) => {
                const icon = ICON_CONCEPTS[iconKey];
                const isSelected = currentIcon === iconKey;
                return (
                  <button
                    key={iconKey}
                    onClick={() => onSelectIcon(iconKey)}
                    className={`flex flex-col items-center text-center p-4 rounded-xl border transition-all ${
                      isSelected
                        ? `border-blue-500 ${activeTheme.subCardBg} ring-2 ring-blue-500/40 shadow-lg`
                        : `${activeTheme.subCardBg} border ${activeTheme.cardBorder} ${activeTheme.cardHover}`
                    }`}
                  >
                    <div className="mb-3">
                      <AppLogo concept={iconKey} themeStyle={currentTheme} size="md" showText={false} />
                    </div>
                    <span className={`font-semibold text-xs ${activeTheme.textPrimary}`}>{icon.name}</span>
                    <span className={`text-[10px] ${activeTheme.textAccent} mt-0.5 font-medium`}>{icon.tag}</span>
                    <p className={`text-[11px] ${activeTheme.textMuted} mt-1 leading-snug`}>
                      {icon.description}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className={`flex items-center justify-between pt-4 border-t ${activeTheme.cardBorder}`}>
          <div className="flex items-center gap-2">
            <AppLogo concept={currentIcon} themeStyle={currentTheme} size="sm" showText={true} />
          </div>
          <button
            onClick={onClose}
            className={`px-5 py-2 rounded-xl ${activeTheme.primaryBtn} text-xs font-semibold transition-all shadow-lg`}
          >
            Apply & Continue
          </button>
        </div>
      </div>
    </div>
  );
};
