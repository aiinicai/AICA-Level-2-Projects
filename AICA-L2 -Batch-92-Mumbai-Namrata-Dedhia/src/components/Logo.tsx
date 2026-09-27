import React from 'react';

interface LogoProps {
  className?: string;
}

export const Logo: React.FC<LogoProps> = ({ className = 'w-10 h-10' }) => {
  return (
    <div className={`relative inline-flex items-center justify-center shrink-0 ${className}`}>
      {/* Soft AI Glow Aura */}
      <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/20 via-amber-400/20 to-indigo-500/20 rounded-full blur-md animate-pulse" />

      {/* SVG Assistant Emblem */}
      <svg
        viewBox="0 0 512 512"
        className="w-full h-full relative z-10 drop-shadow-[0_4px_16px_rgba(56,189,248,0.3)]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Background Gradient */}
          <linearGradient id="asstBgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0b0f19" />
            <stop offset="50%" stopColor="#0f172a" />
            <stop offset="100%" stopColor="#1e1b4b" />
          </linearGradient>

          {/* Gold Accent Gradient */}
          <linearGradient id="asstGoldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fef08a" />
            <stop offset="35%" stopColor="#f59e0b" />
            <stop offset="70%" stopColor="#d97706" />
            <stop offset="100%" stopColor="#92400e" />
          </linearGradient>

          {/* Cyan AI Glow Gradient */}
          <linearGradient id="asstCyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#0284c7" />
          </linearGradient>

          {/* Emerald Tax Shield Gradient */}
          <linearGradient id="asstEmeraldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#34d399" />
            <stop offset="100%" stopColor="#059669" />
          </linearGradient>

          <filter id="asstGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="10" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Dark Luxury Rounded Base */}
        <rect width="512" height="512" rx="128" fill="url(#asstBgGrad)" />

        {/* Outer Orbit Rings */}
        <circle cx="256" cy="256" r="230" fill="none" stroke="url(#asstGoldGrad)" strokeWidth="6" opacity="0.4" />
        <circle cx="256" cy="256" r="218" fill="none" stroke="url(#asstCyanGrad)" strokeWidth="2" strokeDasharray="8 8" opacity="0.6" />

        {/* Assistant Shoulders & Suit Collar */}
        <path d="M128 420 C128 340 180 300 256 300 C332 300 384 340 384 420 V440 H128 Z" fill="#1e293b" stroke="url(#asstGoldGrad)" strokeWidth="8" strokeLinejoin="round"/>
        <path d="M220 300 L256 370 L292 300 L320 440 H192 Z" fill="#0f172a"/>
        <path d="M256 350 L266 420 L256 440 L246 420 Z" fill="url(#asstGoldGrad)"/>

        {/* Assistant Head & Face Contour */}
        <ellipse cx="256" cy="210" rx="72" ry="84" fill="#1e293b" stroke="url(#asstGoldGrad)" strokeWidth="6"/>
        
        {/* Friendly AI Visor Glasses */}
        <path d="M204 195 Q256 185 308 195 C316 215 296 225 256 225 C216 225 196 215 204 195 Z" fill="url(#asstCyanGrad)" filter="url(#asstGlow)"/>
        <circle cx="230" cy="206" r="6" fill="#ffffff"/>
        <circle cx="282" cy="206" r="6" fill="#ffffff"/>

        {/* Hair / Crown Contour */}
        <path d="M184 190 C180 130 220 110 256 110 C292 110 332 130 328 190 C310 160 280 150 256 150 C232 150 202 160 184 190 Z" fill="url(#asstGoldGrad)"/>

        {/* Advisor Headset & Mic */}
        <path d="M180 200 C170 140 342 140 332 200" fill="none" stroke="url(#asstCyanGrad)" strokeWidth="7" strokeLinecap="round"/>
        <rect x="172" y="190" width="16" height="36" rx="8" fill="url(#asstGoldGrad)"/>
        <rect x="324" y="190" width="16" height="36" rx="8" fill="url(#asstGoldGrad)"/>
        <path d="M332 215 Q340 255 290 265" fill="none" stroke="url(#asstCyanGrad)" strokeWidth="5" strokeLinecap="round"/>
        <circle cx="284" cy="266" r="10" fill="url(#asstGoldGrad)" filter="url(#asstGlow)"/>

        {/* Left Floating Badge: Rupee ₹ */}
        <g transform="translate(85, 170)">
          <circle cx="30" cy="30" r="28" fill="#0f172a" stroke="url(#asstEmeraldGrad)" strokeWidth="4" filter="url(#asstGlow)"/>
          <text x="30" y="38" fontFamily="sans-serif" fontWeight="900" fontSize="26" fill="#ffffff" textAnchor="middle">₹</text>
        </g>

        {/* Right Floating Badge: FEMA Scale */}
        <g transform="translate(365, 170)">
          <circle cx="30" cy="30" r="28" fill="#0f172a" stroke="url(#asstGoldGrad)" strokeWidth="4" filter="url(#asstGlow)"/>
          <path d="M18 24 Q30 18 42 24 M30 18 V38 M22 38 H38 M18 28 L14 36 H22 Z M42 28 L38 36 H46 Z" stroke="url(#asstGoldGrad)" strokeWidth="2.5" strokeLinecap="round" fill="none"/>
        </g>

        {/* AI Sparkles */}
        <path d="M130 90 L134 102 L146 106 L134 110 L130 122 L126 110 L114 106 L126 102 Z" fill="url(#asstGoldGrad)"/>
        <path d="M380 90 L384 102 L396 106 L384 110 L380 122 L376 110 L364 106 L376 102 Z" fill="url(#asstCyanGrad)"/>
      </svg>
    </div>
  );
};
