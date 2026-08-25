import React from 'react';
import { motion } from 'framer-motion';
import { ChevronRight } from 'lucide-react';

const ResultCard = ({ title, count, icon: Icon, color, description, onClick }) => {
  const getColorClasses = () => {
    switch (color) {
      case 'accent-green':
        return {
          icon: 'text-accent-green',
          glow: 'hover:shadow-glow-green',
          border: 'border-accent-green'
        };
      case 'accent-blue':
        return {
          icon: 'text-accent-blue',
          glow: 'hover:shadow-glow-blue',
          border: 'border-accent-blue'
        };
      case 'accent-purple':
        return {
          icon: 'text-accent-purple',
          glow: 'hover:shadow-glow-purple',
          border: 'border-accent-purple'
        };
      case 'red-400':
        return {
          icon: 'text-red-400',
          glow: 'hover:shadow-red-500/30',
          border: 'border-red-400'
        };
      default:
        return {
          icon: 'text-accent-green',
          glow: 'hover:shadow-glow-green',
          border: 'border-accent-green'
        };
    }
  };

  const colorClasses = getColorClasses();

  return (
    <motion.div
      onClick={onClick}
      className={`relative flex flex-col justify-between h-full w-full neumorphic-card bg-dark-bg/80 border border-dark-border rounded-2xl p-8 cursor-pointer transition-all duration-300 ${colorClasses.glow} group shadow-xl hover:scale-[1.025] hover:z-10`}
      whileHover={{ y: -4, boxShadow: '0 8px 32px 0 rgba(0,0,0,0.25)' }}
    >
      {/* Icon */}
      <div className="flex items-center justify-between mb-6">
        <div className={`flex items-center justify-center w-12 h-12 rounded-full bg-opacity-15 ${colorClasses.icon.replace('text-', 'bg-')} shadow-inner`}>
          <Icon className={`w-7 h-7 ${colorClasses.icon}`} />
        </div>
        <ChevronRight className="w-6 h-6 text-text-secondary group-hover:text-text-primary transition-colors duration-300 group-hover:translate-x-1" />
      </div>

      {/* Count & Title */}
      <div className="flex items-baseline gap-3 mb-2">
        <span className="text-4xl font-extrabold text-white tracking-tight drop-shadow-md">{count}</span>
        <span className="text-base text-text-secondary font-medium">invoices</span>
      </div>

      {/* Title */}
      <h3 className="text-xl font-bold text-white mb-1 leading-snug">{title}</h3>

      {/* Description */}
      <p className="text-sm text-text-secondary leading-relaxed mb-4 min-h-[48px]">
        {description}
      </p>

      {/* Bottom CTA */}
      {count > 0 && (
        <div className={`absolute left-0 right-0 bottom-0 px-8 py-3 border-t ${colorClasses.border} bg-dark-bg/70 rounded-b-2xl flex items-center justify-between`}> 
          <span className="text-xs text-text-secondary tracking-wide">
            Click to view details →
          </span>
        </div>
      )}
    </motion.div>
  );
};

export default ResultCard;
