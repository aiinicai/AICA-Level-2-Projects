import { NavLink } from 'react-router-dom';

const SECTIONS = [
  { to: '/revenue', label: 'Revenue' },
  { to: '/cost', label: 'Cost' },
  { to: '/profitability', label: 'Profitability' },
  { to: '/balance-sheet', label: 'Balance Sheet' },
  { to: '/liquidity', label: 'Liquidity' },
  { to: '/cash-flow', label: 'Cash Flow' },
  { to: '/returns', label: 'Returns' },
  { to: '/debt', label: 'Debt' },
];

export default function SectionNav() {
  return (
    <nav className="bg-graphite border-b border-ink sticky top-14 z-20 overflow-x-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex gap-1">
        {SECTIONS.map((s) => (
          <NavLink
            key={s.to}
            to={s.to}
            className={({ isActive }) =>
              `whitespace-nowrap px-3 py-2.5 text-xs sm:text-sm font-body border-b-[3px] focus:outline-none focus:ring-2 focus:ring-verdigris focus:ring-inset ${
                isActive ? 'text-paper border-verdigris' : 'text-mist border-transparent hover:text-paper'
              }`
            }
          >
            {s.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
