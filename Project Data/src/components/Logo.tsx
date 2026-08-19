import React from 'react';
import logoImg from '../assets/images/ai_ki_rasoi_logo_1786132381816.jpg';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showSubtitle?: boolean;
  className?: string;
}

export const Logo: React.FC<LogoProps> = ({
  size = 'md',
  showSubtitle = true,
  className = '',
}) => {
  const logoHeights = {
    sm: 'h-10 w-10 sm:h-12 sm:w-12',
    md: 'h-16 w-16 sm:h-20 sm:w-20',
    lg: 'h-24 w-24 sm:h-28 sm:w-28 md:h-32 md:w-32',
  };

  return (
    <div className={`flex items-center gap-3.5 select-none ${className}`}>
      {/* 1:1 Original Logo Image intact */}
      <img
        src={logoImg}
        alt="Ai ki RASOI - AI Powered Home Cooking"
        referrerPolicy="no-referrer"
        className={`aspect-square object-contain rounded-2xl shadow-xs shrink-0 transition-transform hover:scale-105 ${logoHeights[size]}`}
      />
      {showSubtitle && (
        <div className="flex flex-col justify-center min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className={`${size === 'lg' ? 'text-2xl sm:text-3xl font-black' : size === 'sm' ? 'text-base font-bold' : 'text-xl font-bold'} text-slate-800 dark:text-slate-100 tracking-tight`}>
              Ai ki Rasoi
            </h1>
            <span className="text-[10px] font-extrabold uppercase tracking-wider bg-orange-500/15 text-orange-600 dark:text-orange-400 px-2.5 py-0.5 rounded-full border border-orange-500/20">
              Kitchen OS
            </span>
          </div>
          <p className={`${size === 'lg' ? 'text-xs sm:text-sm font-semibold' : 'text-[11px] font-medium'} text-slate-600 dark:text-slate-300 mt-0.5 line-clamp-1`}>
            Smart AI-Powered Meal Planning App
          </p>
        </div>
      )}
    </div>
  );
};
