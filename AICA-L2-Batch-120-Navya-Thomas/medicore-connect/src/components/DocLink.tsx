import React from 'react';
import { FileText } from 'lucide-react';
import { getDocPrefix } from '../core/docLinkRegistry';

interface DocLinkProps {
  number?: string | null;
  className?: string;
  showIcon?: boolean;
  prefixBadge?: boolean;
  onClick?: () => void;
}

export const DocLink: React.FC<DocLinkProps> = ({
  number,
  className = '',
  showIcon = false,
  prefixBadge = false,
  onClick,
}) => {
  if (!number) return <span className="text-gray-400">—</span>;

  const prefix = getDocPrefix(number);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onClick) {
      onClick();
    } else {
      window.dispatchEvent(new CustomEvent('medicore-open-doc', { detail: { number } }));
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      title={`Open details for ${number}`}
      className={`inline-flex items-center space-x-1 font-mono font-semibold text-[#5B2C83] hover:text-[#3F1D5C] hover:underline cursor-pointer group text-left ${className}`}
    >
      {prefixBadge && prefix && (
        <span className="text-[9px] uppercase px-1.5 py-0.2 rounded bg-plum-100 text-[#5B2C83] group-hover:bg-plum-200">
          {prefix}
        </span>
      )}
      {showIcon && <FileText className="w-3.5 h-3.5 text-plum-400 group-hover:text-[#5B2C83] shrink-0" />}
      <span>{number}</span>
    </button>
  );
};
