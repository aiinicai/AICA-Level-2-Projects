import React from 'react';
import { IconConcept, ThemeStyle } from '../types';
import { THEMES } from '../utils/theme';

interface AppLogoProps {
  concept?: IconConcept;
  themeStyle?: ThemeStyle;
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
}

export const AppLogo: React.FC<AppLogoProps> = ({
  concept = 'parceldesk_official',
  themeStyle = 'navy',
  size = 'md',
  showText = true,
}) => {
  const getDimension = () => {
    switch (size) {
      case 'sm': return { w: 32, h: 32, textClass: 'text-base font-bold' };
      case 'lg': return { w: 52, h: 52, textClass: 'text-2xl font-extrabold' };
      default: return { w: 40, h: 40, textClass: 'text-lg font-bold' };
    }
  };

  const { w, h, textClass } = getDimension();
  const theme = THEMES[themeStyle] || THEMES.navy;

  return (
    <div className="flex items-center gap-2.5 select-none">
      <div
        className="relative flex items-center justify-center rounded-xl p-0.5 shrink-0 overflow-hidden shadow-md"
        style={{ width: w, height: h }}
      >
        {/* Concept: Official ParcelDesk Logo (User's Icon) */}
        {concept === 'parceldesk_official' && (
          <svg viewBox="0 0 512 512" className="w-full h-full rounded-xl">
            <defs>
              <linearGradient id="logoBgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#0284c7" />
                <stop offset="50%" stopColor="#2563eb" />
                <stop offset="100%" stopColor="#1d4ed8" />
              </linearGradient>
              <linearGradient id="logoBoxTop" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#ffffff" />
                <stop offset="100%" stopColor="#f8fafc" />
              </linearGradient>
              <linearGradient id="logoBoxLeft" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#f1f5f9" />
                <stop offset="100%" stopColor="#e2e8f0" />
              </linearGradient>
              <linearGradient id="logoBoxRight" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#e2e8f0" />
                <stop offset="100%" stopColor="#cbd5e1" />
              </linearGradient>
              <linearGradient id="logoTape" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#3b82f6" />
                <stop offset="100%" stopColor="#1d4ed8" />
              </linearGradient>
              <linearGradient id="logoStreak" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
                <stop offset="40%" stopColor="#ffffff" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#ffffff" stopOpacity="0.95" />
              </linearGradient>
              <linearGradient id="logoPin" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#ffffff" />
                <stop offset="100%" stopColor="#f1f5f9" />
              </linearGradient>
            </defs>

            <rect width="512" height="512" rx="112" fill="url(#logoBgGrad)" />

            {/* Speed streaks */}
            <path d="M72 196 L164 196" stroke="url(#logoStreak)" strokeWidth="16" strokeLinecap="round" />
            <path d="M102 240 L176 240" stroke="url(#logoStreak)" strokeWidth="16" strokeLinecap="round" />
            <path d="M134 276 L158 276" stroke="url(#logoStreak)" strokeWidth="14" strokeLinecap="round" />

            <ellipse cx="276" cy="340" rx="120" ry="32" fill="#0f172a" fillOpacity="0.35" />

            {/* 3D Parcel Box */}
            <path d="M260 118 L366 160 L274 216 L168 174 Z" fill="url(#logoBoxTop)" />
            <path d="M274 216 L366 160 L366 288 L274 340 Z" fill="url(#logoBoxRight)" />
            <path d="M168 174 L274 216 L274 340 L168 298 Z" fill="url(#logoBoxLeft)" />

            <path d="M204 140 L238 154 L308 195 L274 216 Z" fill="url(#logoTape)" />
            <path d="M204 188 L232 200 L232 232 L218 220 L204 232 Z" fill="url(#logoTape)" />

            <path d="M188 266 L226 280" stroke="#1e293b" strokeWidth="6" strokeLinecap="round" strokeOpacity="0.75" />
            <path d="M188 282 L216 292" stroke="#1e293b" strokeWidth="6" strokeLinecap="round" strokeOpacity="0.75" />

            {/* Location Pin */}
            <ellipse cx="356" cy="330" rx="38" ry="12" fill="#1e3a8a" fillOpacity="0.45" />
            <path d="M356 220 C322 220 296 246 296 280 C296 322 356 338 356 338 C356 338 416 322 416 280 C416 246 390 220 356 220 Z" fill="url(#logoPin)" />
            <circle cx="356" cy="268" r="18" fill="#1d4ed8" />
          </svg>
        )}

        {/* Concept 1: 3D Prism Cube */}
        {concept === 'dynamic_cube' && (
          <div className={`w-full h-full rounded-xl bg-gradient-to-br ${theme.accentGlow} p-1.5 flex items-center justify-center`}>
            <svg viewBox="0 0 48 48" className="w-full h-full text-white" fill="none">
              <path d="M24 5 L42 15 L24 25 L6 15 Z" fill="white" fillOpacity="0.95" />
              <path d="M24 25 L42 15 L42 35 L24 45 Z" fill="white" fillOpacity="0.75" />
              <path d="M6 15 L24 25 L24 45 L6 35 Z" fill="white" fillOpacity="0.55" />
              <path d="M24 15 L24 25 M6 15 L24 25 L42 15" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.4" />
              <circle cx="24" cy="25" r="3.5" fill="#facc15" stroke="#ffffff" strokeWidth="1.2" />
            </svg>
          </div>
        )}

        {/* Concept 2: Smart Beacon Pin */}
        {concept === 'beacon_pin' && (
          <div className={`w-full h-full rounded-xl bg-gradient-to-br ${theme.accentGlow} p-1.5 flex items-center justify-center`}>
            <svg viewBox="0 0 48 48" className="w-full h-full text-white" fill="none">
              <path d="M24 4 C15.16 4 8 11.16 8 20 C8 29.5 22 43 24 44 C26 43 40 29.5 40 20 C40 11.16 32.84 4 24 4 Z" fill="currentColor" fillOpacity="0.25" stroke="white" strokeWidth="2" />
              <rect x="16" y="14" width="16" height="14" rx="2" fill="white" fillOpacity="0.9" />
              <path d="M16 19 L32 19 M24 14 L24 28" stroke="#0f172a" strokeWidth="1.8" />
              <circle cx="24" cy="21" r="2" fill="#38bdf8" />
            </svg>
          </div>
        )}

        {/* Concept 3: Monogram "P" Fold */}
        {concept === 'monogram_p' && (
          <div className={`w-full h-full rounded-xl bg-gradient-to-br ${theme.accentGlow} p-1.5 flex items-center justify-center`}>
            <svg viewBox="0 0 48 48" className="w-full h-full text-white" fill="none">
              <path d="M12 8 L22 8 L22 40 L12 40 Z" fill="white" fillOpacity="0.9" />
              <path d="M22 8 L34 8 C38.5 8 41 11.5 41 16 C41 20.5 38.5 24 34 24 L22 24 Z" fill="white" fillOpacity="0.75" />
              <path d="M26 14 L36 14 L30 20 L26 20 Z" fill="#f59e0b" />
              <circle cx="17" cy="16" r="2" fill="#0f172a" />
            </svg>
          </div>
        )}

        {/* Concept 4: Dual-Route Nexus */}
        {concept === 'flow_arrows' && (
          <div className={`w-full h-full rounded-xl bg-gradient-to-br ${theme.accentGlow} p-1.5 flex items-center justify-center`}>
            <svg viewBox="0 0 48 48" className="w-full h-full text-white" fill="none">
              <rect x="7" y="9" width="34" height="30" rx="7" fill="white" fillOpacity="0.2" stroke="white" strokeWidth="2" />
              <path d="M13 19 L25 19 M20 14 L25 19 L20 24" stroke="#34d399" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M35 29 L23 29 M28 24 L23 29 L28 34" stroke="#60a5fa" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        )}

        {/* Concept 5: Custody Vault Shield */}
        {concept === 'shield_vault' && (
          <div className={`w-full h-full rounded-xl bg-gradient-to-br ${theme.accentGlow} p-1.5 flex items-center justify-center`}>
            <svg viewBox="0 0 48 48" className="w-full h-full text-white" fill="none">
              <path d="M24 4 L40 10 L40 24 C40 34 24 44 24 44 C24 44 8 34 8 24 L8 10 Z" fill="white" fillOpacity="0.3" stroke="white" strokeWidth="2.2" />
              <rect x="17" y="16" width="14" height="13" rx="2.5" fill="white" fillOpacity="0.9" />
              <path d="M19 22.5 L23 26.5 L29 19.5" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        )}

        {/* Concept 6: Swift Express Wing */}
        {concept === 'origami_wing' && (
          <div className={`w-full h-full rounded-xl bg-gradient-to-br ${theme.accentGlow} p-1.5 flex items-center justify-center`}>
            <svg viewBox="0 0 48 48" className="w-full h-full text-white" fill="none">
              <path d="M6 34 L20 12 L32 20 Z" fill="white" fillOpacity="0.9" />
              <path d="M20 12 L42 6 L32 20 Z" fill="white" fillOpacity="0.75" />
              <path d="M20 24 L32 20 L38 38 L24 42 Z" fill="white" fillOpacity="0.5" />
              <circle cx="30" cy="18" r="2.5" fill="#f59e0b" />
            </svg>
          </div>
        )}
      </div>

      {showText && (
        <div className="flex items-center gap-1.5 sm:gap-2">
          <span className={`tracking-tight font-sans font-extrabold ${textClass} ${theme.textPrimary}`}>
            Parcel<span className={theme.isLight ? 'text-blue-600' : 'text-[#38bdf8]'}>Desk</span>
          </span>
          <span className={`hidden sm:inline text-[10px] uppercase tracking-wider font-mono font-semibold px-1.5 py-0.5 rounded border ${theme.badgeBg}`}>
            PWA
          </span>
        </div>
      )}
    </div>
  );
};

